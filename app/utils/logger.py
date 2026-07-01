# app/utils/logger.py

import json
import logging
from typing import Any

logger = logging.getLogger("mtca")


def _serialize(obj: Any):
    """
    Safely serialize objects that aren't JSON serializable by default.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    if hasattr(obj, "dict"):
        return obj.dict()

    return str(obj)


def divider(title: str):
    logger.info("")
    logger.info("=" * 100)
    logger.info(title)
    logger.info("=" * 100)


def info(title: str, value: Any):
    logger.info(f"{title}: {value}")


def json_block(title: str, payload: Any):
    logger.info(title)
    logger.info(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            default=_serialize,
        )
    )


def router_trace(
    *,
    tenant_name: str,
    user_message: str,
    retrieved_examples: list,
    prompt: str,
    router_result: Any,
):
    """
    Pretty logs the complete router execution.
    """
    divider("🧠 ROUTER TRACE")

    info("Tenant", tenant_name)

    divider("👤 USER MESSAGE")
    logger.info(user_message)

    divider("📚 RETRIEVED ROUTING EXAMPLES")

    if not retrieved_examples:
        logger.info("No routing examples retrieved.")
    else:
        for idx, ex in enumerate(retrieved_examples, start=1):
            logger.info("-" * 100)
            logger.info(f"Example {idx}")
            logger.info(f"Similarity : {ex.get('score', 'N/A')}")
            logger.info(f"User       : {ex.get('user_message')}")
            logger.info(f"Intent     : {ex.get('expected_action')}")
            logger.info(f"Reasoning  : {ex.get('reasoning')}")

    divider("📜 FINAL SYSTEM PROMPT")
    logger.info(prompt)

    divider("🤖 ROUTER OUTPUT")

    json_block(
        "Structured Result",
        router_result,
    )

    logger.info("=" * 100)


def lead_capture_trace(
    *,
    tenant_name: str,
    incoming_lead: Any,
    prompt: str,
    structured_result: Any,
):
    """
    Pretty logs the complete lead capture execution layer.
    """
    divider("🎯 LEAD CAPTURE TRACE")
    info("Tenant", tenant_name)

    divider("📥 INCOMING LEAD STATE")
    json_block("State Before Turn", incoming_lead)

    divider("📜 LEAD CAPTURE SYSTEM PROMPT")
    logger.info(prompt)

    divider("🤖 LEAD CAPTURE OUTPUT")
    json_block("Structured Output", structured_result)
    logger.info(f"Is Capture Complete? -> {getattr(structured_result, 'complete', False)}")
    logger.info("=" * 100)


def agentic_rag_trace(
    *,
    tenant_name: str = "N/A",
    user_message: str = "N/A",
    decision_prompt: str = "N/A",
    decision_result: Any = None,
    action: str = "N/A",
    search_query: str = "N/A",
    context: str = "N/A",
    final_response: str = "N/A",
):
    """
    Complete Agentic RAG execution trace.

    Tracks:
    - LLM routing decision
    - retrieval decision
    - vector context
    - final response
    """

    divider("🧠 AGENTIC RAG TRACE")

    info("Tenant", tenant_name)

    divider("👤 USER MESSAGE")
    logger.info(user_message)

    divider("📜 DECISION SYSTEM PROMPT")
    logger.info(decision_prompt)

    divider("🤖 ROUTER DECISION")

    json_block(
        "Decision Output",
        decision_result,
    )

    info("Selected Action", action)

    if action == "search":

        divider("🔎 RETRIEVAL")

        info(
            "Vector Search Query",
            search_query
        )

        divider("📚 RETRIEVED CONTEXT")

        logger.info(
            context or "No context retrieved."
        )

    else:

        divider("⚡ DIRECT RESPONSE")
        logger.info(
            "Answered from conversation context without retrieval."
        )


    divider("💬 FINAL RESPONSE")

    logger.info(
        final_response
    )

    logger.info("=" * 100)

def booking_trace(
    *,
    tenant_name: str,
    user_message: str,
    action: str,
    slots_this_turn: Any,
    accumulated_data: Any,
    duration_minutes: int,
    final_response: str,
    flow_complete: bool,
):
    """
    Pretty logs the complete booking node execution for a single turn.

    Tracks:
    - Classified action (create / edit / delete / unknown)
    - Slots extracted from this message only
    - Full accumulated slot state after merge
    - Resolved service duration
    - Node reply and whether the flow closed
    """
    divider("📅 BOOKING NODE TRACE")

    info("Tenant", tenant_name)

    divider("👤 USER MESSAGE")
    logger.info(user_message)

    divider("🎯 ACTION CLASSIFICATION")
    info("Classified Action", action.upper())

    divider("🔍 SLOT EXTRACTION — THIS TURN")
    json_block("Newly Extracted Slots", slots_this_turn)

    divider("🗂️  ACCUMULATED SLOT STATE (POST-MERGE)")
    json_block("Full Booking Data", accumulated_data)

    divider("⏱️  DURATION RESOLUTION")
    info("Resolved Duration", f"{duration_minutes} minutes")

    divider("💬 NODE REPLY")
    logger.info(final_response)
    info("Flow Complete", flow_complete)

    logger.info("=" * 100)