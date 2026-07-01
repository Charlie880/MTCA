# app/langgraph/nodes/lead_node.py
import logging
import asyncio
from typing import Optional

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.utils.logger import lead_capture_trace
from app.core.models import LeadCaptureModel, LeadData
from app.services.lead_capture import process_and_save_qualified_lead

logger = logging.getLogger("mtca")

LLM_TIMEOUT_SECONDS = 8.0

_llm = None
_llm_lock = asyncio.Lock()


async def _get_lead_llm() -> ChatOpenAI:
    global _llm
    async with _llm_lock:
        if _llm is None:
            _llm = ChatOpenAI(
                model="gpt-4.1-nano",
                temperature=0,
                api_key=settings.OPENAI_API_KEY,
            )
    return _llm


LEAD_FIELDS = [
    ("product", "What product or service are you interested in?"),
    ("reason",  "What is the main reason you are interested?"),
    ("budget",  "What is your estimated budget?"),
    ("phone",   "What phone number can we reach you on?"),
]


def _get_next_missing_field(lead_data: LeadData) -> Optional[tuple[str, str]]:
    """Return (field_name, question) for the first missing required field, or None if complete."""
    for field, question in LEAD_FIELDS:
        if not getattr(lead_data, field, None):
            return field, question
    return None


def _build_system_prompt(tenant_name: str, lead_data: LeadData) -> str:
    return f"""
You are the Dedicated Lead Management Assistant for {tenant_name}.

You are collecting lead information conversationally.

CURRENT LEAD STATE (already captured -- do NOT re-ask for these):
{lead_data.model_dump()}

STRICT DATA RULES:

1. NEVER ASSUME.
   Only extract a field if the user explicitly provides it in their latest message.
   Never use previous conversation context, package descriptions, inferred intent,
   or assistant messages as a source of field values.
   The only pre-trusted fields are authenticated name and authenticated email,
   which are already pre-filled in the lead state above.

2. EXTRACT ONLY THESE FIELDS when explicitly stated by the user:
   product, reason, budget, phone.

3. PRODUCT RULE: accept vague descriptions if the user explicitly says them
   (e.g. "the travel package", "one of your tours"). Store exactly what they said.

4. DO NOT CREATE DATA. Never generate fake phone numbers, estimated budgets,
   guessed products, or inferred reasons.

5. RESPONSE: keep replies short and friendly. If information is missing, ask
   only for the single next missing field. Do not explain internal logic.

Return structured output only.
"""


# ----------------------------------------------------------------------------
# Lead Capture Node
# ----------------------------------------------------------------------------
async def lead_capture_node(state: dict) -> dict:

    config = state.get("mongo_rules", {})
    tenant_name = config.get("tenantName", "our company")
    suspended_flow: Optional[str] = state.get("suspended_flow")

    # ------------------------------------------------------------------------
    # Restore lead state
    # ------------------------------------------------------------------------
    lead_raw = state.get("lead_state")

    if lead_raw is None:
        lead_data = LeadData()
    elif isinstance(lead_raw, dict):
        lead_data = LeadData(**lead_raw)
    else:
        lead_data = lead_raw


    user_name = state.get("user_name") or state.get("username")
    user_email = state.get("user_email") or state.get("email")

    if user_name:
        lead_data.name = user_name
    if user_email:
        lead_data.email = user_email

    logger.info("Authenticated identity -- name=%s email=%s", lead_data.name, lead_data.email)

    # ------------------------------------------------------------------------
    # Structured extraction
    # ------------------------------------------------------------------------
    llm = await _get_lead_llm()
    structured_llm = llm.with_structured_output(LeadCaptureModel)

    history = [m for m in state.get("messages", []) if isinstance(m, (HumanMessage, AIMessage))][-5:]
    system_prompt = _build_system_prompt(tenant_name, lead_data)
    messages = [SystemMessage(content=system_prompt), *history]

    parsed = None
    try:
        parsed = await asyncio.wait_for(
            structured_llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.error("Lead LLM call timed out after %.1fs.", LLM_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("Lead LLM call failed.")

    # If the LLM failed entirely, give a safe fallback response and preserve state.
    if parsed is None:
        fallback = "Sorry, I had trouble processing that -- could you try again?"
        return {
            "messages": [AIMessage(content=fallback)],
            "final_response": fallback,
            "lead_state": lead_data.model_dump(),
            "active_flow": "lead_capture",
            "suspended_flow": suspended_flow,
            "flow_complete": False,
            "lead_saved_flag": False,
            "tool_data": None,
        }

    lead_capture_trace(
        tenant_name=tenant_name,
        incoming_lead=lead_data,
        prompt=system_prompt,
        structured_result=parsed,
    )

    if not parsed.is_relevant_to_lead_capture:
        logger.info("Topic breakout detected in lead_capture_node; handing off to conversational_agent.")
        handoff = "Of course -- let me help with that. We can pick up where we left off when you're ready."
        return {
            "messages": [AIMessage(content=handoff)],
            "final_response": handoff,
            "lead_state": lead_data.model_dump(),   # preserve partial progress
            "active_flow": "conversational_agent",  # signal re-route
            "suspended_flow": "lead_capture",       # stash so dispatcher can resume
            "flow_complete": False,
            "lead_saved_flag": state.get("lead_saved_flag", False),
            "tool_data": None,
        }

    # ------------------------------------------------------------------------
    # Merge ONLY values explicitly extracted this turn
    # ------------------------------------------------------------------------
    if parsed.product:
        lead_data.product = parsed.product
    if parsed.reason:
        lead_data.reason = parsed.reason
    if parsed.budget:
        lead_data.budget = parsed.budget
    if parsed.phone:
        lead_data.phone = parsed.phone

    # ------------------------------------------------------------------------
    # Completion check
    # ------------------------------------------------------------------------
    missing = [field for field, _ in LEAD_FIELDS if not getattr(lead_data, field, None)]
    is_complete = len(missing) == 0

    logger.info("Lead completeness -- missing=%s", missing)

    # ------------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------------
    lead_saved = state.get("lead_saved_flag", False)

    if is_complete and not lead_saved:
        try:
            lead_id = await process_and_save_qualified_lead(
                org_id=state["org_id"],
                branch_id=state["branch_id"],
                lead_data=lead_data,
                user_email=lead_data.email,
                username=lead_data.name,
            )
            logger.info("Lead saved -- id=%s", lead_id)
            lead_saved = True
        except Exception:
            logger.exception("Lead save failed; keeping flow active to retry.")
            is_complete = False

    # ------------------------------------------------------------------------
    # Final response
    # ------------------------------------------------------------------------
    if lead_saved:
        assistant_reply = (
            getattr(parsed, "assistant_response", None)
            or "Thank you. Your details have been recorded and our team will be in touch."
        )
    else:
        next_field = _get_next_missing_field(lead_data)
        assistant_reply = (
            next_field[1]
            if next_field
            else "We have all your details -- just finalising things on our end, one moment."
        )

    return {
        "messages": [AIMessage(content=assistant_reply)],
        "final_response": assistant_reply,
        "lead_state": None if lead_saved else lead_data.model_dump(),
        "active_flow": None if lead_saved else "lead_capture",
        "suspended_flow": suspended_flow, 
        "flow_complete": lead_saved,
        "lead_saved_flag": lead_saved,
        "tool_data": None,
    }