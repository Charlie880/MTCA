# app/langgraph/nodes/booking_node.py

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from app.core.models import BookingSlots, BookingAction

from app.core.config import settings
from app.core.models import BookingData
from app.services.booking_service import (
    ServiceResult,
    cancel_booking,
    check_slot_available,
    create_booking,
    fetch_calendar_events,
    get_user_bookings,
    make_event_id,
    reschedule_booking,
)

from app.utils.logger import booking_trace

logger = logging.getLogger("mtca")

LLM_TIMEOUT = 8.0

_llm: Optional[ChatOpenAI] = None
_llm_lock = asyncio.Lock()


async def _get_llm() -> ChatOpenAI:
    global _llm
    async with _llm_lock:
        if _llm is None:
            _llm = ChatOpenAI(
                model=settings.CHAT_MODEL,
                temperature=0,
                api_key=settings.OPENAI_API_KEY,
            )
    return _llm


# ----------------------------------------------------------------------------
# LLM calls
# ----------------------------------------------------------------------------

async def _classify(llm: ChatOpenAI, user_text: str) -> str:
    try:
        result = await asyncio.wait_for(
            llm.with_structured_output(BookingAction).ainvoke(
                f"Classify the user's intent as create / edit / delete / unknown.\n\nMessage: {user_text}"
            ),
            timeout=LLM_TIMEOUT,
        )
        return result.action
    except Exception:
        logger.exception("Action classification failed; defaulting to unknown.")
        return "unknown"


async def _extract_slots(
    llm: ChatOpenAI,
    messages: list,
    known: dict,
    tz: str,
) -> BookingSlots:
    """
    Extracts ONLY values the user explicitly states in their latest message.
    Does not re-extract or carry forward from `known` -- the node handles
    merging. This keeps extraction strict and prevents stale slots from
    leaking in via the LLM.
    """
    
    # FIX: Provide the LLM with the current date and time so it can resolve relative dates.
    today_str = datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %A %H:%M")
    
    prompt = f"""Extract ONLY values the user explicitly states in their latest message.
Do not infer, assume, or carry forward values from the known state below.

CURRENT SYSTEM DATE AND TIME: {today_str}

Known state (for context only -- do not re-extract from this):
{known}

Fields to extract:
- service: the service name if stated
- requested_date: YYYY-MM-DD if a date is stated (resolve relative terms like 'tomorrow' using the system date).
- requested_time: HH:MM (24h) if a time is stated
- appointment_reference: a booking/event reference ID if stated

Return null for any field not explicitly mentioned by the user."""
    try:
        return await asyncio.wait_for(
            llm.with_structured_output(BookingSlots).ainvoke(
                [SystemMessage(content=prompt), *messages[-4:]]
            ),
            timeout=LLM_TIMEOUT,
        )
    except Exception:
        logger.exception("Slot extraction failed; returning empty slots.")
        return BookingSlots()


# ----------------------------------------------------------------------------
# Main node
# ----------------------------------------------------------------------------

async def booking_node(state: dict) -> dict:
    logger.info("Entering booking_node.")

    llm = await _get_llm()
    config = state["mongo_rules"]
    integrations = config.get("integrations", {})

    org_id: str = state["org_id"]
    branch_id: str = state["branch_id"]

    tenant_name: str = config.get("tenantName", "our company")

    # User-specific identity (runtime state)
    user_id: Optional[str] = state.get("user_id")
    user_email: Optional[str] = state.get("user_email") or state.get("email")
    user_name: str = state.get("user_name") or state.get("username") or "there"

    # Tenant-specific integrations (Mongo configuration)
    org_email: Optional[str] = integrations.get("notificationEmail")

    tz: str = state.get("timezone", "UTC")

    if not user_id or not user_email:
        return _reply("Please log in before managing bookings.", state, flow_complete=False)

    # Restore or initialise slot accumulator from state
    raw = state.get("booking_state_data")
    data: dict = (
        BookingData(**raw).model_dump() if isinstance(raw, dict)
        else raw.model_dump()            if raw
        else BookingData().model_dump()
    )
    data.update({"user_id": user_id, "user_email": user_email})

    # Isolate conversation messages and the latest user turn
    messages = [
        m for m in state.get("messages", [])
        if isinstance(m, (HumanMessage, AIMessage))
    ]
    user_text = messages[-1].content if messages else ""

    # Classify + extract this turn's slots in parallel
    action_task = asyncio.create_task(_classify(llm, user_text))
    slots_task  = asyncio.create_task(_extract_slots(llm, messages, data, tz)) # FIX: Pass timezone
    action, slots = await asyncio.gather(action_task, slots_task)

    logger.info("booking_node: action=%s", action)

    # Snapshot the raw extraction before merging so the trace can show
    # exactly what was pulled from this turn vs what was already accumulated.
    slots_this_turn = slots.model_dump()

    # Merge newly extracted slots into the accumulator (only overwrite if set)
    if slots.service:               data["service"] = slots.service
    if slots.requested_date:        data["requested_date"] = slots.requested_date
    if slots.requested_time:        data["requested_time"] = slots.requested_time
    if slots.appointment_reference: data["appointment_reference"] = slots.appointment_reference

    # Duration resolution: per-service map takes priority, then branch default,
    # then hardcoded fallback. mongo_rules shape:
    #   { "defaultDuration": 60, "serviceDurations": { "Haircut": 45, ... } }
    service_for_duration = data.get("service") or ""
    duration_minutes: int = (
        config.get("serviceDurations", {}).get(service_for_duration)
        or config.get("defaultDuration")
        or 60
    )

    ctx = dict(
        state=state, data=data,
        org_id=org_id, branch_id=branch_id,
        user_id=user_id, user_email=user_email,
        user_name=user_name, tenant_name=tenant_name,
        org_email=org_email, tz=tz,
        duration_minutes=duration_minutes,
    )

    if action == "create":
        result = await _handle_create(**ctx)
    elif action == "edit":
        result = await _handle_edit(**ctx)
    elif action == "delete":
        result = await _handle_delete(**ctx)
    else:
        result = _reply(
            "I can help you book, reschedule, or cancel an appointment — what would you like to do?",
            state, booking_data=data, flow_complete=False,
        )

    booking_trace(
        tenant_name=tenant_name,
        user_message=user_text,
        action=action,
        slots_this_turn=slots_this_turn,
        accumulated_data=data,
        duration_minutes=duration_minutes,
        final_response=result.get("final_response", ""),
        flow_complete=result.get("flow_complete", False),
    )

    return result


# ----------------------------------------------------------------------------
# Sub-flows
# ----------------------------------------------------------------------------

async def _handle_create(
    *, state, data, org_id, branch_id, user_id, user_email, user_name, tenant_name,
    org_email, tz, duration_minutes,
) -> dict:
    # Slot-fill gate
    if not data.get("service"):
        return _reply("What service would you like to book?", state, booking_data=data, flow_complete=False)
    if not data.get("requested_date"):
        return _reply("What date works for you? (e.g. 2026-07-15)", state, booking_data=data, flow_complete=False)
    if not data.get("requested_time"):
        return _reply("What time would you prefer? (e.g. 14:00)", state, booking_data=data, flow_complete=False)

    # Availability check
    try:
        events = await asyncio.to_thread(fetch_calendar_events, state)
    except Exception:
        logger.exception("Calendar fetch failed.")
        return _reply(
            "I'm having trouble reaching the calendar right now — please try again.",
            state, booking_data=data, flow_complete=False,
        )

    if not check_slot_available(events, data["requested_date"], data["requested_time"], duration_minutes, tz):
        data["requested_date"] = None
        data["requested_time"] = None
        return _reply(
            "That slot isn't available. Could you suggest another date or time?",
            state, booking_data=data, flow_complete=False,
        )

    # Generate idempotent event ID once; persist so retries reuse it
    if not data.get("pending_event_id"):
        data["pending_event_id"] = make_event_id()

    result: ServiceResult = await create_booking(
        state=state,
        org_id=org_id, branch_id=branch_id,
        user_id=user_id, user_email=user_email, user_name=user_name,
        tenant_name=tenant_name, org_email=org_email,
        service=data["service"],
        date=data["requested_date"], time=data["requested_time"],
        duration_minutes=duration_minutes,
        event_id=data["pending_event_id"],
        tz=tz,
    )

    if not result.ok:
        return _reply(
            "Something went wrong while creating your booking — please try again.",
            state, booking_data=data, flow_complete=False,
        )

    return _reply(
        f"Your {data['service']} on {data['requested_date']} at {data['requested_time']} is confirmed. "
        f"A confirmation has been sent to {user_email}.",
        state, booking_data=None, flow_complete=True,
    )


async def _handle_edit(
    *, state, data, org_id, branch_id, user_id, user_email, user_name, tenant_name,
    org_email, tz, duration_minutes,
) -> dict:
    # Fetch from DB -- no calendar scan required for ownership resolution
    try:
        bookings = await get_user_bookings(org_id=org_id, branch_id=branch_id, user_id=user_id)
    except Exception:
        logger.exception("Booking lookup failed.")
        return _reply(
            "I'm having trouble looking up your bookings — please try again.",
            state, booking_data=data, flow_complete=False,
        )

    if not bookings:
        return _reply("I don't see any active bookings on your account.", state, booking_data=data, flow_complete=False)

    # Auto-select if only one booking exists, else ask the user to pick
    if not data.get("appointment_reference"):
        if len(bookings) == 1:
            data["appointment_reference"] = bookings[0]["event_id"]
        else:
            listing = "\n".join(
                f"- {b['service']} on {b['start_iso'][:10]} at {b['start_iso'][11:16]} (ref: {b['event_id']})"
                for b in bookings
            )
            return _reply(
                f"Which appointment would you like to reschedule?\n{listing}",
                state, booking_data=data, flow_complete=False,
            )

    target = next((b for b in bookings if b["event_id"] == data["appointment_reference"]), None)
    if not target:
        return _reply(
            "I couldn't find that booking on your account.",
            state, booking_data=data, flow_complete=False,
        )

    if not data.get("requested_date") and not data.get("requested_time"):
        return _reply("What new date or time would you like?", state, booking_data=data, flow_complete=False)

    new_date = data.get("requested_date") or target["start_iso"][:10]
    new_time = data.get("requested_time") or target["start_iso"][11:16]

    # Availability check (exclude the event being moved from conflict detection)
    try:
        events = await asyncio.to_thread(fetch_calendar_events, state)
    except Exception:
        logger.exception("Calendar fetch failed.")
        return _reply(
            "I'm having trouble reaching the calendar right now — please try again.",
            state, booking_data=data, flow_complete=False,
        )

    if not check_slot_available(
        events, new_date, new_time, duration_minutes, tz,
        exclude_event_id=target["event_id"],
    ):
        data["requested_date"] = None
        data["requested_time"] = None
        return _reply(
            "That slot isn't available. Could you suggest another date or time?",
            state, booking_data=data, flow_complete=False,
        )

    result: ServiceResult = await reschedule_booking(
        state=state,
        org_id=org_id,
        user_email=user_email, user_name=user_name,
        tenant_name=tenant_name, org_email=org_email,
        event_id=target["event_id"],
        service=target["service"],
        new_date=new_date, new_time=new_time,
        duration_minutes=duration_minutes,
        tz=tz,
    )

    if not result.ok:
        return _reply(
            "Something went wrong while rescheduling — please try again.",
            state, booking_data=data, flow_complete=False,
        )

    return _reply(
        f"Done — your {target['service']} has been moved to {new_date} at {new_time}. "
        f"Updated confirmation sent to {user_email}.",
        state, booking_data=None, flow_complete=True,
    )


async def _handle_delete(
    *, state, data, org_id, branch_id, user_id, user_email, user_name, tenant_name,
    org_email, tz, duration_minutes,
) -> dict:
    try:
        bookings = await get_user_bookings(org_id=org_id, branch_id=branch_id, user_id=user_id)
    except Exception:
        logger.exception("Booking lookup failed.")
        return _reply(
            "I'm having trouble looking up your bookings — please try again.",
            state, booking_data=data, flow_complete=False,
        )

    if not bookings:
        return _reply("I don't see any active bookings on your account.", state, booking_data=data, flow_complete=False)

    if not data.get("appointment_reference"):
        if len(bookings) == 1:
            data["appointment_reference"] = bookings[0]["event_id"]
        else:
            listing = "\n".join(
                f"- {b['service']} on {b['start_iso'][:10]} at {b['start_iso'][11:16]} (ref: {b['event_id']})"
                for b in bookings
            )
            return _reply(
                f"Which appointment would you like to cancel?\n{listing}",
                state, booking_data=data, flow_complete=False,
            )

    target = next((b for b in bookings if b["event_id"] == data["appointment_reference"]), None)
    if not target:
        return _reply(
            "I couldn't find that booking on your account.",
            state, booking_data=data, flow_complete=False,
        )

    result: ServiceResult = await cancel_booking(
        state=state,
        org_id=org_id,
        user_email=user_email, user_name=user_name,
        tenant_name=tenant_name, org_email=org_email,
        event_id=target["event_id"],
        service=target["service"],
        date=target["start_iso"][:10],
    )

    if not result.ok:
        return _reply(
            "Something went wrong while cancelling — please try again.",
            state, booking_data=data, flow_complete=False,
        )

    return _reply(
        f"Your {target['service']} on {target['start_iso'][:10]} has been cancelled. "
        f"Confirmation sent to {user_email}.",
        state, booking_data=None, flow_complete=True,
    )


# ----------------------------------------------------------------------------
# Reply helper
# ----------------------------------------------------------------------------

def _reply(text: str, state: dict, *, booking_data=None, flow_complete: bool) -> dict:
    return {
        "messages":           [AIMessage(content=text)],
        "final_response":     text,
        "booking_state_data": booking_data,
        "active_flow":        None if flow_complete else "booking",
        "flow_complete":      flow_complete,
        "tool_data":          None,
    }