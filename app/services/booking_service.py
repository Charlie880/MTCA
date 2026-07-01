# app/services/booking_service.py
#
# Booking service: owns the full side-effect chain for every booking action.
#
#   Calendar (source of truth) → DB record (lookup index) → Email (notification)
#
# Rule: Calendar write always happens first. If the Calendar call succeeds but
# a later step (DB or email) fails, we log it and return success -- the
# appointment exists. DB records can be reconciled from Calendar; emails are
# best-effort notifications, never blockers.
#
# Public surface (called by booking_node):
#   create_booking(...)    -> ServiceResult
#   reschedule_booking(..) -> ServiceResult
#   cancel_booking(...)    -> ServiceResult
#   get_user_bookings(..)  -> list[dict]
#   fetch_calendar_events(..) -> list[dict]
#   check_slot_available(..)  -> bool
#   make_event_id()           -> str

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import resend
from googleapiclient.discovery import build
from google.oauth2 import service_account
from app.core.models import ServiceResult

from app.core.config import settings
from app.db.operations import (
    db_insert_booking,
    db_update_booking,
    db_cancel_booking,
    db_get_user_bookings,
)

logger = logging.getLogger("mtca")

# ----------------------------------------------------------------------------
# Resend init (global, single-key pattern required by Resend SDK)
# ----------------------------------------------------------------------------
resend.api_key = settings.RESEND_API_KEY
_FROM_ADDRESS = settings.RESEND_EMAIL

# ----------------------------------------------------------------------------
# Calendar helpers
# ----------------------------------------------------------------------------

def _build_calendar():
    """
    Builds a Google Calendar API client using a Google Service Account JSON file.
    Expects settings.GOOGLE_SERVICE_ACCOUNT_FILE to contain the valid local path.
    """
    scopes = ["https://www.googleapis.com/auth/calendar"]
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def _get_calendar_id(state: dict) -> str:
    return (
        state.get("mongo_rules", {})
        .get("integrations", {})
        .get("calendarId", "primary")
    )

def make_event_id() -> str:
    """
    Generates a stable, idempotent event ID. Called once per booking attempt
    and stored in slot state so retries reuse the same ID rather than creating
    duplicates.
    Constraint: Google Calendar event IDs must be 5-1024 chars, lowercase a-z
    and 0-9 only.
    """
    return uuid.uuid4().hex  # 32 chars, hex only -- Calendar-safe


def _to_rfc3339(date: str, time: str, tz: str) -> str:
    """Combines YYYY-MM-DD + HH:MM + IANA tz into an RFC 3339 datetime string."""
    local_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").replace(
        tzinfo=ZoneInfo(tz)
    )
    return local_dt.isoformat()


def fetch_calendar_events(state: dict, days_ahead: int = 30) -> list[dict]:
    """
    Fetches all Calendar events in the next `days_ahead` days.
    Returns a list of raw event dicts from the API.
    This is synchronous -- wrap in asyncio.to_thread if calling from async context.
    """
    calendar = _build_calendar()
    calendar_id = _get_calendar_id(state)
    
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    # FIX: Add pagination loop to ensure all events in the timeframe are returned.
    events = []
    page_token = None
    
    while True:
        response = calendar.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token
        ).execute()

        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        
        if not page_token:
            break

    return events


def check_slot_available(
    events: list[dict],
    date: str,
    time: str,
    duration_minutes: int,
    tz: str = "UTC",
    exclude_event_id: Optional[str] = None,
) -> bool:
    """
    Returns True if no existing event overlaps the requested window.
    Pass exclude_event_id when checking a reschedule so the event being
    moved doesn't block its own target slot.
    """
    req_start = datetime.fromisoformat(_to_rfc3339(date, time, tz))
    req_end = req_start + timedelta(minutes=duration_minutes)

    for ev in events:
        if exclude_event_id and ev.get("id") == exclude_event_id:
            continue

        ev_start_raw = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
        ev_end_raw   = ev.get("end",   {}).get("dateTime") or ev.get("end",   {}).get("date")
        if not ev_start_raw or not ev_end_raw:
            continue

        try:
            ev_start = datetime.fromisoformat(ev_start_raw)
            # FIX: Prevent crash when comparing timezone-naive all-day events with aware requests
            if ev_start.tzinfo is None:
                ev_start = ev_start.replace(tzinfo=ZoneInfo(tz))
                
            ev_end   = datetime.fromisoformat(ev_end_raw)
            if ev_end.tzinfo is None:
                ev_end = ev_end.replace(tzinfo=ZoneInfo(tz))
        except ValueError:
            continue

        # Overlap: the two windows share any time
        if req_start < ev_end and req_end > ev_start:
            return False

    return True


# ----------------------------------------------------------------------------
# Email templates (inline -- replace with Jinja2 + per-tenant branding later)
# ----------------------------------------------------------------------------

def _html_confirmation(tenant_name, user_name, service, date, time, event_id) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;color:#222;max-width:560px;margin:auto;padding:32px">
<h2 style="color:#1a1a2e">Booking Confirmed</h2>
<p>Hi {user_name},</p>
<p>Your appointment with <strong>{tenant_name}</strong> has been confirmed.</p>
<table style="border-collapse:collapse;width:100%;margin:24px 0">
  <tr><td style="padding:8px 0;color:#555;width:120px">Service</td><td><strong>{service}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#555">Date</td><td><strong>{date}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#555">Time</td><td><strong>{time}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#555">Reference</td><td style="font-family:monospace;font-size:13px;color:#888">{event_id}</td></tr>
</table>
<p>To reschedule or cancel, contact us with your reference number.</p>
<p style="color:#888;font-size:13px;margin-top:40px">— {tenant_name}</p>
</body></html>"""


def _html_reschedule(tenant_name, user_name, service, new_date, new_time, event_id) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;color:#222;max-width:560px;margin:auto;padding:32px">
<h2 style="color:#1a1a2e">Appointment Rescheduled</h2>
<p>Hi {user_name},</p>
<p>Your appointment with <strong>{tenant_name}</strong> has been moved.</p>
<table style="border-collapse:collapse;width:100%;margin:24px 0">
  <tr><td style="padding:8px 0;color:#555;width:120px">Service</td><td><strong>{service}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#555">New Date</td><td><strong>{new_date}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#555">New Time</td><td><strong>{new_time}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#555">Reference</td><td style="font-family:monospace;font-size:13px;color:#888">{event_id}</td></tr>
</table>
<p style="color:#888;font-size:13px;margin-top:40px">— {tenant_name}</p>
</body></html>"""


def _html_cancellation(tenant_name, user_name, service, date, event_id) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;color:#222;max-width:560px;margin:auto;padding:32px">
<h2 style="color:#1a1a2e">Appointment Cancelled</h2>
<p>Hi {user_name},</p>
<p>Your <strong>{service}</strong> appointment on <strong>{date}</strong> with <strong>{tenant_name}</strong> has been cancelled.</p>
<p>If this was a mistake or you'd like to rebook, we're happy to help.</p>
<p style="color:#888;font-size:13px;margin-top:40px">— {tenant_name}</p>
</body></html>"""


def _send_email(*, to: list[str], subject: str, html: str, label: str, event_id: str) -> None:
    """
    Fire-and-forget email send to one or more recipients in a single API call.
    Logs on failure but never raises -- callers treat email as best-effort.
    Deduplicates recipients before sending so the org email == user email edge
    case doesn't result in a double-send.
    """
    recipients = list(dict.fromkeys(addr.strip().lower() for addr in to if addr))
    if not recipients:
        logger.warning("Email [%s] skipped -- no valid recipients -- event_id=%s", label, event_id)
        return
    try:
        resend.Emails.send({"from": _FROM_ADDRESS, "to": recipients, "subject": subject, "html": html})
        logger.info("Email sent [%s] -- to=%s event_id=%s", label, recipients, event_id)
    except Exception:
        logger.exception("Email failed [%s] -- to=%s event_id=%s", label, recipients, event_id)


# ----------------------------------------------------------------------------
# Public service functions
# ----------------------------------------------------------------------------

async def create_booking(
    *,
    state: dict,
    org_id: str,
    branch_id: str,
    user_id: str,
    user_email: str,
    user_name: str,
    tenant_name: str,
    org_email: Optional[str],
    service: str,
    date: str,
    time: str,
    duration_minutes: int,
    event_id: str,
    tz: str = "UTC",
) -> ServiceResult:
    """
    Full creation chain: Calendar → DB → Email.
    Confirmation is sent to both user_email and org_email (single API call,
    deduplicated). Returns ServiceResult(ok=True) on Calendar success
    regardless of whether DB/email steps fail (those are logged separately).
    """
    calendar_id = _get_calendar_id(state)

    # 1. Calendar (source of truth)
    try:
        calendar = _build_calendar()
        start_dt = _to_rfc3339(date, time, tz)
        end_dt = (
            datetime.fromisoformat(start_dt) + timedelta(minutes=duration_minutes)
        ).isoformat()

        calendar.events().insert(
            calendarId=calendar_id,
            body={
                "id":      event_id,
                "summary": f"{service} — {user_name}",
                "start":   {"dateTime": start_dt, "timeZone": tz},
                "end":     {"dateTime": end_dt,   "timeZone": tz},
                "attendees": [{"email": user_email}],
            },
        ).execute()
        logger.info("Calendar event created -- event_id=%s", event_id)
    except Exception:
        logger.exception("Calendar create failed -- event_id=%s", event_id)
        return ServiceResult(ok=False, error="calendar_create_failed")

    # 2. DB record
    try:
        start_iso = _to_rfc3339(date, time, tz)
        end_iso = (datetime.fromisoformat(start_iso) + timedelta(minutes=duration_minutes)).isoformat()
        await db_insert_booking(
            org_id=org_id, branch_id=branch_id,
            user_id=user_id, user_email=user_email,
            event_id=event_id, service=service,
            start_iso=start_iso, end_iso=end_iso, tz=tz,
        )
    except Exception:
        logger.exception(
            "DB insert failed after Calendar success -- event_id=%s. "
            "Calendar event is live; Mongo record must be reconciled manually.",
            event_id,
        )

    # 3. Email -- user + org in one send (deduplicated internally)
    _send_email(
        to=[user_email, org_email],
        subject=f"Booking Confirmed — {service} on {date}",
        html=_html_confirmation(tenant_name, user_name, service, date, time, event_id),
        label="confirmation",
        event_id=event_id,
    )

    return ServiceResult(ok=True)


async def reschedule_booking(
    *,
    state: dict,
    org_id: str,
    user_email: str,
    user_name: str,
    tenant_name: str,
    org_email: Optional[str],
    event_id: str,
    service: str,
    new_date: str,
    new_time: str,
    duration_minutes: int,
    tz: str = "UTC",
) -> ServiceResult:
    """
    Full reschedule chain: Calendar patch → DB update → Email.
    Notification sent to both user_email and org_email.
    """
    calendar_id = _get_calendar_id(state)

    # 1. Calendar
    try:
        calendar = _build_calendar()
        new_start = _to_rfc3339(new_date, new_time, tz)
        new_end = (datetime.fromisoformat(new_start) + timedelta(minutes=duration_minutes)).isoformat()

        calendar.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body={
                "start": {"dateTime": new_start, "timeZone": tz},
                "end":   {"dateTime": new_end,   "timeZone": tz},
            },
        ).execute()
        logger.info("Calendar event patched -- event_id=%s new_start=%s", event_id, new_start)
    except Exception:
        logger.exception("Calendar patch failed -- event_id=%s", event_id)
        return ServiceResult(ok=False, error="calendar_patch_failed")

    # 2. DB
    try:
        new_start_iso = _to_rfc3339(new_date, new_time, tz)
        new_end_iso = (datetime.fromisoformat(new_start_iso) + timedelta(minutes=duration_minutes)).isoformat()
        await db_update_booking(
            org_id=org_id, event_id=event_id,
            new_start_iso=new_start_iso, new_end_iso=new_end_iso,
        )
    except Exception:
        logger.exception(
            "DB update failed after Calendar reschedule -- event_id=%s. "
            "Calendar is updated; Mongo record must be reconciled manually.",
            event_id,
        )

    # 3. Email -- user + org in one send
    _send_email(
        to=[user_email, org_email],
        subject=f"Appointment Rescheduled — {service} now on {new_date}",
        html=_html_reschedule(tenant_name, user_name, service, new_date, new_time, event_id),
        label="reschedule",
        event_id=event_id,
    )

    return ServiceResult(ok=True)


async def cancel_booking(
    *,
    state: dict,
    org_id: str,
    user_email: str,
    user_name: str,
    tenant_name: str,
    org_email: Optional[str],
    event_id: str,
    service: str,
    date: str,
) -> ServiceResult:
    """
    Full cancellation chain: Calendar delete → DB soft-cancel → Email.
    Notification sent to both user_email and org_email.
    """
    calendar_id = _get_calendar_id(state)

    # 1. Calendar
    try:
        calendar = _build_calendar()
        calendar.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info("Calendar event deleted -- event_id=%s", event_id)
    except Exception:
        logger.exception("Calendar delete failed -- event_id=%s", event_id)
        return ServiceResult(ok=False, error="calendar_delete_failed")

    # 2. DB (soft delete -- preserves audit trail)
    try:
        await db_cancel_booking(org_id=org_id, event_id=event_id)
    except Exception:
        logger.exception(
            "DB soft-cancel failed after Calendar delete -- event_id=%s. "
            "Calendar event is deleted; Mongo record must be reconciled manually.",
            event_id,
        )

    # 3. Email -- user + org in one send
    _send_email(
        to=[user_email, org_email],
        subject=f"Appointment Cancelled — {service}",
        html=_html_cancellation(tenant_name, user_name, service, date, event_id),
        label="cancellation",
        event_id=event_id,
    )

    return ServiceResult(ok=True)


async def get_user_bookings(
    *,
    org_id: str,
    branch_id: str,
    user_id: str,
    status: str = "active",
) -> list[dict]:
    """Pass-through to DB layer -- service layer is the only caller of DB ops."""
    return await db_get_user_bookings(
        org_id=org_id,
        branch_id=branch_id,
        user_id=user_id,
        status=status,
    )