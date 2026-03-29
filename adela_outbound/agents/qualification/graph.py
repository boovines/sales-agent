from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from adela_outbound.agents.qualification.state import QualificationState
from adela_outbound.agents.qualification.nodes import (
    input_loader,
    criterion_scorer,
    aggregate_scorer,
    qualification_brief_builder,
    hitl_gate,
    resume_handler,
)

checkpointer = MemorySaver()


def _route_after_brief(state: QualificationState) -> str:
    if state.get('decision') == 'auto_rejected':
        return 'resume_handler'
    return 'hitl_gate'


builder = StateGraph(QualificationState)
builder.add_node('input_loader', input_loader)
builder.add_node('criterion_scorer', criterion_scorer)
builder.add_node('aggregate_scorer', aggregate_scorer)
builder.add_node('qualification_brief_builder', qualification_brief_builder)
builder.add_node('hitl_gate', hitl_gate)
builder.add_node('resume_handler', resume_handler)

builder.set_entry_point('input_loader')
builder.add_edge('input_loader', 'criterion_scorer')
builder.add_edge('criterion_scorer', 'aggregate_scorer')
builder.add_edge('aggregate_scorer', 'qualification_brief_builder')
builder.add_conditional_edges(
    'qualification_brief_builder',
    _route_after_brief,
    {'resume_handler': 'resume_handler', 'hitl_gate': 'hitl_gate'},
)
builder.add_edge('hitl_gate', 'resume_handler')
builder.add_edge('resume_handler', END)

qualification_graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=['hitl_gate'],
)


async def run_qualification(company_id: str) -> dict:
    config = {'configurable': {'thread_id': company_id}}
    initial: QualificationState = {
        'company_id': company_id,
        'prospect_brief': {},
        'icp_definition': {},
        'criterion_scores': [],
        'qualification_brief': None,
        'decision': None,
        'rejection_note': None,
        'errors': [],
    }
    result = await qualification_graph.ainvoke(initial, config=config)
    return result


async def resume_qualification(
    company_id: str, decision: str, rejection_note: str = None
) -> dict:
    config = {'configurable': {'thread_id': company_id}}
    resume_data = {'decision': decision, 'rejection_note': rejection_note}
    result = await qualification_graph.ainvoke(
        Command(resume=resume_data), config=config
    )
    return result
