import uuid
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from adela_outbound.agents.discovery.state import DiscoveryState
from adela_outbound.agents.discovery.nodes import (
    signal_collector,
    deduplicator,
    thin_record_builder,
    pre_scorer,
    rate_limiter,
    queue_writer,
)

builder = StateGraph(DiscoveryState)
builder.add_node('signal_collector', signal_collector)
builder.add_node('deduplicator', deduplicator)
builder.add_node('thin_record_builder', thin_record_builder)
builder.add_node('pre_scorer', pre_scorer)
builder.add_node('rate_limiter', rate_limiter)
builder.add_node('queue_writer', queue_writer)

builder.set_entry_point('signal_collector')
builder.add_edge('signal_collector', 'deduplicator')
builder.add_edge('deduplicator', 'thin_record_builder')
builder.add_edge('thin_record_builder', 'pre_scorer')
builder.add_edge('pre_scorer', 'rate_limiter')
builder.add_edge('rate_limiter', 'queue_writer')
builder.add_edge('queue_writer', END)

discovery_graph = builder.compile()


async def run_discovery(run_type: str = 'scheduled') -> dict:
    initial_state: DiscoveryState = {
        'run_id': str(uuid.uuid4()),
        'raw_results': [],
        'deduped_results': [],
        'thin_records': [],
        'pre_scored_records': [],
        'final_records': [],
        'cap_applied': False,
        'run_type': run_type,
        'errors': [],
        'sources_queried': [],
        'started_at': datetime.now(timezone.utc).isoformat(),
    }
    result = await discovery_graph.ainvoke(initial_state)
    return result
