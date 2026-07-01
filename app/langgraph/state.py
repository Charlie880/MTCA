# app/langgraph/state.py
from typing import Annotated, Dict, Any, List, Optional
from typing_extensions import TypedDict, NotRequired
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class BookingData(BaseModel):
    service: Optional[str] = None
    requested_date: Optional[str] = None       # Always normalised to YYYY-MM-DD
    requested_time: Optional[str] = None       # Always normalised to HH:MM
    pending_event_id: Optional[str] = None     # Idempotency key; set once, reused on retry
    appointment_reference: Optional[str] = None  # event_id stated by user for edit/delete


class MultiTenantState(TypedDict):
    # Conversation
    messages: Annotated[List[Any], add_messages]

    # Tenant context
    org_id: str
    branch_id: str
    mongo_rules: Dict[str, Any]

    # Authenticated identity
    user_id: NotRequired[str]
    user_email: NotRequired[str]
    user_name: NotRequired[str]
    timezone: NotRequired[str]           # IANA tz string; defaults to "UTC" in node

    # Router
    intent: NotRequired[str]
    routing_examples: NotRequired[List[Dict[str, Any]]]

    # RAG / conversational
    search_query: NotRequired[str]
    vector_context: NotRequired[str]
    rag_reasoning_log: NotRequired[str]

    # Workflow control
    active_flow: NotRequired[Optional[str]]
    suspended_flow: NotRequired[Optional[str]]  # <--- FIX: Added to support detour logic
    flow_complete: NotRequired[bool]

    # Booking workflow
    booking_state_data: NotRequired[Dict[str, Any]]

    # Lead workflow
    lead_state: NotRequired[Dict[str, Any]]
    lead_saved_flag: NotRequired[bool]

    # Output
    final_response: NotRequired[str]
    tool_data: NotRequired[Any]