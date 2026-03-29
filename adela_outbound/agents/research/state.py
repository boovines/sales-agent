from __future__ import annotations

from typing import TypedDict, Optional, Any


class ResearchState(TypedDict):
    company_id: str
    discovery_record: dict
    firecrawl_result: dict
    perplexity_result: dict
    github_result: dict
    grok_result: dict
    brief: Optional[dict]
    errors: list
