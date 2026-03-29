from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DiscoveryRecord(BaseModel):
    id: str
    company_name: str
    website: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_handle: Optional[str] = None
    linkedin_url: Optional[str] = None
    discovery_source: str
    discovery_signal: str
    pre_score: float = 0.0
    status: str = 'queued'
    created_at: datetime
    updated_at: datetime


class ProspectBrief(BaseModel):
    id: str
    company_id: str
    summary: str
    current_focus: str
    pain_points: list[str]
    adela_relevance: str
    personalization_hooks: list[str]
    creative_outreach_opportunity: bool = False
    creative_outreach_detail: Optional[str] = None
    recommended_channel: str = 'email'
    research_sources: list[str]
    confidence_score: float = 0.0
    raw_research: dict
    created_at: datetime


class QualificationBrief(BaseModel):
    id: str
    company_id: str
    fit_score: float
    fit_tier: str
    criterion_scores: dict
    why_now: str
    suggested_outreach_angle: str
    status: str = 'pending_review'
    rejection_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class ICPCriterion(BaseModel):
    id: str
    name: str
    description: str
    weight: str


class ICPDefinition(BaseModel):
    id: str
    version: int = 1
    criteria: list[ICPCriterion]
    created_at: datetime


class OutreachPackage(BaseModel):
    id: str
    company_id: str
    primary_channel: str
    primary_draft: dict
    secondary_drafts: list[dict] = []
    creative_action: Optional[dict] = None
    status: str = 'pending_review'
    send_result: Optional[dict] = None
    rejection_note: Optional[str] = None
    created_at: datetime
