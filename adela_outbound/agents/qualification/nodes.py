from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def input_loader(state: dict) -> dict:
    return {}


async def criterion_scorer(state: dict) -> dict:
    return {}


async def aggregate_scorer(state: dict) -> dict:
    return {}


async def qualification_brief_builder(state: dict) -> dict:
    return {}


async def hitl_gate(state: dict) -> dict:
    return {}


async def resume_handler(state: dict) -> dict:
    return {}
