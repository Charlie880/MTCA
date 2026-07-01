# app/langgraph/nodes/router.py

import logging
import asyncio
from typing import Literal, Optional

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.core.models import RouterOutput
from app.services.routing_retriever import retrieve_routing_examples
from app.utils.logger import router_trace

logger = logging.getLogger(__name__)

_llm = None
_llm_lock = asyncio.Lock()

LLM_TIMEOUT_SECONDS = 8.0


def get_router_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.ROUTER_MODEL,
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )
    return _llm


def _latest_user_message(messages):
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return None


def _format_chat_history(messages, max_turns=4) -> str:
    """
    Formats prior turns, excluding the most recent HumanMessage (the one
    being evaluated as the current target input). Uses index-based exclusion
    rather than positional list slicing, so it's robust to trailing
    non-Human/AI messages (tool messages, partials, etc.) appended after the
    real latest user turn.
    """
    convo_messages = [m for m in messages if isinstance(m, (HumanMessage, AIMessage))]

    last_human_idx = None
    for i in range(len(convo_messages) - 1, -1, -1):
        if isinstance(convo_messages[i], HumanMessage):
            last_human_idx = i
            break

    history_messages = convo_messages[:last_human_idx] if last_human_idx is not None else convo_messages

    formatted = []
    for msg in history_messages[-max_turns:]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        formatted.append(f"{role}: {msg.content}")

    return "\n".join(formatted) if formatted else "No prior history (New Conversation)."


def _format_examples(examples: list[dict]) -> str:
    if not examples:
        return "No explicit matching routing examples retrieved. Use core rule parameters."

    formatted = []
    for i, example in enumerate(examples, start=1):
        formatted.append(
            f"Example {i}\nUser Input: {example.get('user_message')}\nExpected Intent: {example.get('expected_action')}\nReasoning: {example.get('reasoning')}"
        )
    return "\n---\n".join(formatted)


SYSTEM_INSTRUCTIONS = """You are the Intent Classifier and Coreference Resolution Engine for {tenant_name}.

Your task is to analyze the user's latest input within the context of the chat history and the current active workflow state, and output BOTH the single best-fit intent AND, if a workflow is active, how this message relates to it.

Available Intents:
- conversational_agent: General chitchat, broad inquiries, branch location/hours questions, random off-topic lookups, or the user explicitly cancelling/exiting/abandoning an active workflow.
- booking: Booking new slots, rescheduling, modifying existing bookings, or providing parameters (dates, times) to complete an open reservation.
- lead_capture: Showing clear transactional or buying interest in purchasing a service tier, product, or package.

REASONING PROCESS (internal -- do not output this, only the final structured result):
STEP 1 [Normalization]: Analyze colloquialisms, mixed languages, or Romanized text. Translate conceptually to English.
STEP 2 [Coreference Resolution]: Map generic pronouns ("it", "that", "pricing for that") to the specific asset last discussed in the history.
STEP 3 [Session Analysis]: Evaluate the user input against the ACTIVE WORKFLOW STATE. Determine if they are continuing it, explicitly cancelling/exiting it, or detouring onto an unrelated topic without cancelling.
STEP 4 [Final Assignment]: Select the intent, AND if a workflow is active, set flow_action to one of:
  - "continue": this message advances or fulfills the active workflow (e.g. providing a requested date/time while booking is active).
  - "exit": the user explicitly cancels, stops, or abandons the active workflow (e.g. "cancel", "nevermind", "forget it", or equivalent in any language/register). This is a deliberate exit.
  - "detour": the user has shifted to an unrelated topic ("what are your hours?") without explicitly cancelling. This is a soft detour -- the workflow is not being abandoned, just paused.

If there is no active workflow, leave flow_action null and only set intent.

FLOW ACTION CRITERIA:
1. TOP-OF-FUNNEL PRIORITY: If a user explicitly states they want to buy or sign up for an offering, route intent to `lead_capture` even if a 'booking' flow is active. This counts as a detour from booking unless the user is already mid-lead_capture.
2. SOFT-LOCK ROUTING: If active state is 'booking' and the user provides matching parameter details requested by the assistant, set flow_action to "continue" and intent to `booking`.
3. EXPLICIT CANCELLATION: If the user explicitly cancels, exits, or abandons the active flow, set intent to `conversational_agent` and flow_action to "exit".
4. SOFT DETOUR: If the user shifts to an unrelated topic without explicitly cancelling, set intent to `conversational_agent` and flow_action to "detour"."""


def _build_prompt_template(tenant_name: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_INSTRUCTIONS),
        ("human", """TENANT OPERATIONS DESCRIPTION:
{tenant_description}

CURRENT RUNTIME STATUS:
- ACTIVE WORKFLOW TRACKING STATE: {active_flow_status}
- RECENT CHAT HISTORY LOGS:
{chat_history}

TARGET USER MESSAGE TO EVALUATE:
"{latest_message}"

FEW-SHOT REFERENCE SAMPLES: Contextless
{formatted_examples}

Evaluate the target user message provided above according to your strict instruction set.""")
    ]).partial(tenant_name=tenant_name)


async def router_node(state: dict) -> dict:
    """
    LangGraph dispatcher node.

    CHANGE 3 (architecture): this node now runs on every turn, including
    turns where a flow is already active, and produces a `flow_action`
    alongside `intent` so downstream logic can tell a deliberate cancel
    apart from a soft detour -- the original prompt asked the model to make
    this distinction but the old RouterOutput schema discarded it.

    CHANGE 4 (suspend/resume): on a "detour", we no longer just leave
    active_flow untouched and hope the booking/lead_capture subgraph
    re-asks the right question -- we explicitly stash the in-progress flow
    name in `suspended_flow` so the conversational_agent node (or whichever
    node handles the detour) can hand control back with a natural
    "got it -- back to your booking, what time works?" instead of silently
    losing context or silently resuming with no acknowledgement.

    CHANGE 5 (resilience): the LLM call now has an explicit timeout via
    asyncio.wait_for, so a hung OpenAI call degrades to the safe fallback
    intent instead of stalling the graph indefinitely.
    """
    logger.info("Initializing context analysis and intent routing pass.")

    config = state["mongo_rules"]
    messages = state["messages"]

    last_message = _latest_user_message(messages)
    if last_message is None:
        logger.error("router_node invoked with no HumanMessage in state; defaulting to conversational_agent.")
        return {
            "intent": "conversational_agent",
            "routing_examples": [],
            "active_flow": state.get("active_flow"),
            "suspended_flow": state.get("suspended_flow"),
            "flow_complete": False,
        }

    active_flow = state.get("active_flow")
    suspended_flow = state.get("suspended_flow")
    tenant_name = config.get("tenantName", "the business")

    # FIX: Ensure the router LLM knows about the flow if it's currently suspended.
    current_context = active_flow or suspended_flow

    chat_history_str = _format_chat_history(messages)

    try:
        routing_examples = await asyncio.to_thread(
            retrieve_routing_examples,
            query=last_message,
            org_id=state["org_id"],
            branch_id=state["branch_id"],
            top_k=2,
        )
    except Exception:
        logger.exception("Routing example retrieval failed; continuing without few-shot examples.")
        routing_examples = []

    llm = get_router_llm()
    structured_llm = llm.with_structured_output(RouterOutput)

    prompt_template = _build_prompt_template(tenant_name)
    chain = prompt_template | structured_llm

    invoke_args = {
        "tenant_description": config.get("tenantDescription", "Standard Business Operations"),
        # FIX: Pass the unified context to the LLM so it doesn't think the state is open.
        "active_flow_status": f"IN_PROGRESS: '{current_context}'" if current_context else "None (Open State)",
        "chat_history": chat_history_str,
        "latest_message": last_message,
        "formatted_examples": _format_examples(routing_examples),
    }

    next_intent = "conversational_agent"
    flow_action: Optional[str] = None

    try:
        result = await asyncio.wait_for(chain.ainvoke(invoke_args), timeout=LLM_TIMEOUT_SECONDS)
        next_intent = result.intent
        flow_action = result.flow_action
    except asyncio.TimeoutError:
        logger.error("Router LLM call timed out after %.1fs; falling back to conversational_agent.", LLM_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("Router LLM call failed; falling back to conversational_agent.")

    try:
        rendered_prompt = prompt_template.format(**invoke_args)
    except Exception:
        rendered_prompt = SYSTEM_INSTRUCTIONS

    router_trace(
        tenant_name=tenant_name,
        user_message=last_message,
        retrieved_examples=routing_examples,
        prompt=rendered_prompt,
        router_result=f"{next_intent} (flow_action={flow_action})",
    )

    new_active_flow = active_flow
    new_suspended_flow = suspended_flow
    flow_complete = False

    if next_intent in ("lead_capture", "booking"):
        if active_flow and active_flow != next_intent:
            new_suspended_flow = active_flow
        new_active_flow = next_intent

    elif current_context:
        # A workflow is active/suspended and the model classified this turn as
        # conversational rather than advancing the flow -- flow_action tells
        # us which of the two prompt criteria actually fired.
        if flow_action == "exit":
            # Criterion 3: deliberate cancellation. Actually clear it now --
            # this is the fix for the original bug where cancellation never
            # took effect.
            new_active_flow = None
            new_suspended_flow = None
            flow_complete = False
        elif flow_action == "detour":
            # Criterion 4: soft detour. Preserve the context explicitly via suspended_flow
            # so the conversational response can acknowledge it and offer to resume.
            new_suspended_flow = current_context
            new_active_flow = active_flow
        else:
            # Model didn't return flow_action (e.g. older RouterOutput
            # behavior, or genuinely ambiguous) -- conservatively fall back
            # to the old "preserve, don't complete" behavior rather than
            # guessing at a cancellation.
            logger.warning(
                "current_context=%s but flow_action missing/unrecognized (%r); preserving flow conservatively.",
                current_context, flow_action,
            )
            new_active_flow = active_flow
            new_suspended_flow = suspended_flow

    return {
        "intent": next_intent,
        "routing_examples": routing_examples,
        "active_flow": new_active_flow,
        "suspended_flow": new_suspended_flow,
        "flow_complete": flow_complete,
    }