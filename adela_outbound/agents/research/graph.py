from langgraph.graph import StateGraph, END

from adela_outbound.agents.research.state import ResearchState
from adela_outbound.agents.research.nodes import (
    input_loader,
    parallel_researcher,
    brief_synthesiser,
    github_opportunity_detector,
    output_writer,
)

builder = StateGraph(ResearchState)
builder.add_node('input_loader', input_loader)
builder.add_node('parallel_researcher', parallel_researcher)
builder.add_node('brief_synthesiser', brief_synthesiser)
builder.add_node('github_opportunity_detector', github_opportunity_detector)
builder.add_node('output_writer', output_writer)

builder.set_entry_point('input_loader')
builder.add_edge('input_loader', 'parallel_researcher')
builder.add_edge('parallel_researcher', 'brief_synthesiser')
builder.add_edge('brief_synthesiser', 'github_opportunity_detector')
builder.add_edge('github_opportunity_detector', 'output_writer')
builder.add_edge('output_writer', END)

research_graph = builder.compile()


async def run_research(company_id: str) -> dict:
    initial: ResearchState = {
        'company_id': company_id,
        'discovery_record': {},
        'firecrawl_result': {},
        'perplexity_result': {},
        'github_result': {},
        'grok_result': {},
        'brief': None,
        'errors': [],
    }
    return await research_graph.ainvoke(initial)
