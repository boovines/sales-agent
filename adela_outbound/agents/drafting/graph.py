from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from adela_outbound.agents.drafting.nodes import (
    channel_router,
    hitl_gate_node,
    input_loader,
    resume_handler,
)
from adela_outbound.agents.drafting.state import DraftingState

memory = MemorySaver()

builder = StateGraph(DraftingState)
builder.add_node("input_loader", input_loader)
builder.add_node("channel_router", channel_router)
builder.add_node("hitl_gate", hitl_gate_node)
builder.add_node("resume_handler", resume_handler)

builder.set_entry_point("input_loader")
builder.add_edge("input_loader", "channel_router")
builder.add_edge("channel_router", "hitl_gate")
builder.add_edge("hitl_gate", "resume_handler")
builder.add_conditional_edges(
    "resume_handler",
    lambda s: "channel_router"
    if s.get("redraft_feedback") and s.get("decision") is None
    else END,
)

drafting_graph = builder.compile(checkpointer=memory, interrupt_before=["hitl_gate"])
