# app/langgraph/nodes/conversational_agent.py
import logging
import json
import asyncio
from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.services.rag_retriever import retrieve_vector_context
from app.utils.logger import agentic_rag_trace
from app.core.config import settings

logger = logging.getLogger("mtca")

LLM_TIMEOUT_SECONDS = 8.0

_decision_llm = None
_answer_llm = None
_llm_lock = asyncio.Lock()


async def _get_decision_llm():
    global _decision_llm
    async with _llm_lock:
        if _decision_llm is None:
            _decision_llm = ChatOpenAI(
                model=settings.CHAT_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
    return _decision_llm


async def _get_answer_llm():
    global _answer_llm
    async with _llm_lock:
        if _answer_llm is None:
            _answer_llm = ChatOpenAI(
                model="gpt-4.1-nano",
                api_key=settings.OPENAI_API_KEY,
                temperature=0,
            )
    return _answer_llm


# ----------------------------------------------------------------------------
# Agentic RAG Decision Parser
# ----------------------------------------------------------------------------
def parse_agent_decision(content: str):
    """
    Parse the model decision while safely handling markdown wrappers.

    CHANGE: the old fallback silently reinterpreted any unparseable content
    as a direct "answer" containing the raw model output -- meaning a
    malformed response could surface un-vetted text straight to the user.
    Now an unparseable response is flagged explicitly as a parse failure so
    the caller can decide to retry or degrade gracefully, instead of
    pretending it was a valid answer.
    """
    clean_content = content.strip()

    if clean_content.startswith("```"):
        clean_content = clean_content.split("\n", 1)[-1]
        if clean_content.endswith("```"):
            clean_content = clean_content.rsplit("```", 1)[0]

    clean_content = clean_content.strip()

    try:
        parsed = json.loads(clean_content)
        if isinstance(parsed, dict) and parsed.get("action") in ("answer", "search"):
            return parsed
        logger.warning("Decision JSON parsed but missing a valid 'action' field: %r", parsed)
    except Exception:
        pass

    if clean_content.upper().startswith("SEARCH:"):
        return {"action": "search", "query": clean_content[7:].strip()}

    logger.warning("Could not parse a valid agent decision from model output; treating as parse failure.")
    return {"action": "_parse_failed", "raw": content}


# ----------------------------------------------------------------------------
# Main Conversational Agent Node
# ----------------------------------------------------------------------------
async def conversational_agent_node(state: dict) -> dict:
    logger.info("Entering Agentic RAG Conversation Agent Node")

    decision_result = None
    action = "N/A"
    search_query = "N/A"
    context = ""
    final_response_text = ""

    config = state["mongo_rules"]
    tenant_name = config.get("tenantName", "Our Business")
    tenant_description = config.get("tenantDescription", "A premium operator.")

    suspended_flow: Optional[str] = state.get("suspended_flow")

    latest_message = ""
    if state.get("messages"):
        latest_message = state["messages"][-1].content.strip()

    decision_prompt = f"""
You are the Elite Customer Care AI for {tenant_name}.

Company Description:
{tenant_description}

You are using an adaptive RAG architecture.

Your task: decide whether you can answer the user accurately using ONLY
information already explicitly present in this conversation (things the
assistant has already told this user, or the user has already told you),
or whether you need to search the knowledge base.

If, and only if, the exact answer was already stated earlier in this
conversation, return:

{{
    "action": "answer",
    "response": "your answer, restating only what was already established"
}}

For ANY question involving business-specific facts you have not already
explicitly stated in this conversation -- pricing, hours, policies,
services, locations, availability, or anything else specific to this
business -- you MUST search rather than answer from general knowledge.
Return:

{{
    "action": "search",
    "query": "expanded semantic search query"
}}

Greetings and pure small talk with no factual claims can be answered
directly without searching.

Rules:
- Resolve references using conversation history.
- Expand vague questions into a concrete, specific search query.
- Never invent or assume business facts -- if in doubt, search.
- Return ONLY JSON, nothing else.
"""

    decision_llm = await _get_decision_llm()
    decision_messages = [SystemMessage(content=decision_prompt), *state["messages"]]

    parsed = None
    try:
        decision = await asyncio.wait_for(
            decision_llm.ainvoke(decision_messages), timeout=LLM_TIMEOUT_SECONDS
        )
        parsed = parse_agent_decision(decision.content)
    except asyncio.TimeoutError:
        logger.error("Decision LLM call timed out after %.1fs.", LLM_TIMEOUT_SECONDS)
        parsed = {"action": "_parse_failed", "raw": None}
    except Exception:
        logger.exception("Decision LLM call failed.")
        parsed = {"action": "_parse_failed", "raw": None}

    decision_result = parsed
    new_messages = []
    action = parsed.get("action", "_parse_failed")

    if action == "answer":
        ai_reply = parsed.get("response", "")
        final_response_text = ai_reply
        new_messages.append(AIMessage(content=ai_reply))

    elif action == "search":
        query = parsed.get("query", "")
        search_query = query
        logger.info("Agentic RAG retrieval query: %s", query)

        try:
            context = await asyncio.wait_for(
                asyncio.to_thread(
                    retrieve_vector_context,
                    query=query,
                    org_id=state.get("org_id"),
                    branch_id=state.get("branch_id"),
                ),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("Vector retrieval timed out after %.1fs.", LLM_TIMEOUT_SECONDS)
            context = None
        except Exception:
            logger.exception("Vector retrieval failed.")
            context = None

        if not context:
            ai_reply = "I couldn't find that information in our knowledge base."
        else:
            answer_llm = await _get_answer_llm()

            final_prompt = f"""
You are the Elite Customer Care AI for {tenant_name}.

Answer the user's question using ONLY the supplied knowledge context.

If the context does not contain the answer, say you do not have
that information available rather than guessing.

Knowledge Context:

{context}

Provide a warm and accurate customer response.
"""
            final_messages = [SystemMessage(content=final_prompt), *state["messages"]]

            try:
                final_response = await asyncio.wait_for(
                    answer_llm.ainvoke(final_messages), timeout=LLM_TIMEOUT_SECONDS
                )
                ai_reply = final_response.content
            except asyncio.TimeoutError:
                logger.error("Answer LLM call timed out after %.1fs.", LLM_TIMEOUT_SECONDS)
                ai_reply = "Sorry, I'm having trouble retrieving that right now -- could you try again in a moment?"
            except Exception:
                logger.exception("Answer LLM call failed.")
                ai_reply = "Sorry, I'm having trouble retrieving that right now -- could you try again in a moment?"

        final_response_text = ai_reply
        new_messages.append(AIMessage(content=ai_reply))

    else:
        # action == "_parse_failed" or any other unrecognized value.
        logger.warning("Unrecognized or failed agent decision: %r", parsed)
        ai_reply = "I apologize, but I was unable to process that request -- could you rephrase it?"
        final_response_text = ai_reply
        new_messages.append(AIMessage(content=ai_reply))

    if suspended_flow:
        nudge = {
            "booking": "By the way, want to pick back up on your booking?",
            "lead_capture": "By the way, want to continue where we left off with your earlier request?",
        }.get(suspended_flow)
        if nudge:
            final_response_text = f"{final_response_text}\n\n{nudge}"
            new_messages[-1] = AIMessage(content=final_response_text)

    agentic_rag_trace(
        tenant_name=tenant_name,
        user_message=latest_message,
        decision_prompt=decision_prompt,
        decision_result=decision_result,
        action=action,
        search_query=search_query,
        context=context,
        final_response=final_response_text,
    )

    return {
        "messages": new_messages,
        "final_response": final_response_text,
        "active_flow": None,
        "suspended_flow": suspended_flow,
        "flow_complete": True,
    }