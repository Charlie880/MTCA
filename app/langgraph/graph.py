# app/langgraph/graph.py
from langgraph.graph import StateGraph, END
from app.langgraph.state import MultiTenantState
from app.langgraph.nodes.router import router_node
from app.langgraph.nodes.booking_node import booking_node
from app.langgraph.nodes.lead_node import lead_capture_node
from app.langgraph.nodes.conversational_agent import conversational_agent_node 
from app.db.redis import checkpointer

builder = StateGraph(MultiTenantState)

# Nodes
builder.add_node("router", router_node)
builder.add_node("booking_node", booking_node)
builder.add_node("lead_node", lead_capture_node)
builder.add_node("conversational_agent", conversational_agent_node) # Unified Node

builder.set_entry_point("router")

# Conditional Router Edge (Now cleaner and faster!)
builder.add_conditional_edges(
    "router",
    lambda state: state["intent"],
    {
        "conversational_agent": "conversational_agent",
        "lead_capture": "lead_node",
        "booking": "booking_node"
    }
)

builder.add_edge("booking_node", END)
builder.add_edge("lead_node", END)
builder.add_edge("conversational_agent", END)

compiled_rag_graph = builder.compile(checkpointer=checkpointer)