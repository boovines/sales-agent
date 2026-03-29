from __future__ import annotations

from typing import Optional, TypedDict


class DraftingState(TypedDict):
    company_id: str
    prospect_brief: dict
    qualification_brief: dict
    outreach_package: Optional[dict]
    decision: Optional[str]
    edited_draft: Optional[str]
    rejection_note: Optional[str]
    redraft_feedback: Optional[str]
    errors: list[str]
