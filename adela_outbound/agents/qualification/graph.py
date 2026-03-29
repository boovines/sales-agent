from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()


async def run_qualification(company_id: str) -> dict:
    return {}


async def resume_qualification(company_id: str, decision: str, rejection_note: str = None) -> dict:
    return {}
