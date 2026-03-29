from __future__ import annotations

from typing import TypedDict, Optional


class QualificationState(TypedDict):
    company_id: str
    prospect_brief: dict
    icp_definition: dict
    criterion_scores: list
    qualification_brief: Optional[dict]
    decision: Optional[str]
    rejection_note: Optional[str]
    errors: list
