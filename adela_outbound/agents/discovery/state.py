from typing import TypedDict


class DiscoveryState(TypedDict):
    run_id: str
    raw_results: list[dict]
    deduped_results: list[dict]
    thin_records: list[dict]
    pre_scored_records: list[dict]
    final_records: list[dict]
    cap_applied: bool
    run_type: str
    errors: list[str]
    sources_queried: list[str]
    started_at: str
