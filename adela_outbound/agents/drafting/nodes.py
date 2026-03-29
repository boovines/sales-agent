from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import aiosqlite
from anthropic import AsyncAnthropic

from adela_outbound.agents.drafting.channels.email import draft_email
from adela_outbound.agents.drafting.channels.github import draft_github_comment
from adela_outbound.agents.drafting.channels.linkedin import draft_linkedin
from adela_outbound.agents.drafting.events import drafting_sse_queues
from adela_outbound.agents.drafting.state import DraftingState
from adela_outbound.config import config
from adela_outbound.db.contracts import ProspectBrief, QualificationBrief

logger = logging.getLogger(__name__)

# Fields stored as JSON strings in SQLite that need parsing before model_validate
_PROSPECT_JSON_FIELDS = {
    "pain_points",
    "personalization_hooks",
    "research_sources",
    "raw_research",
}
_QUAL_JSON_FIELDS = {"criterion_scores"}


def _parse_json_fields(row_dict: dict, json_fields: set[str]) -> dict:
    """Parse JSON-encoded TEXT columns into Python objects."""
    result = dict(row_dict)
    for field in json_fields:
        val = result.get(field)
        if isinstance(val, str):
            try:
                result[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
    return result


async def input_loader(state: DraftingState) -> DraftingState:
    """Load prospect and qualification briefs from the database."""
    company_id = state["company_id"]

    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row

        cursor = await conn.execute(
            "SELECT * FROM prospect_briefs WHERE company_id = ?",
            (company_id,),
        )
        prospect_row = await cursor.fetchone()
        if prospect_row is None:
            raise ValueError(f"No prospect brief found for {company_id}")

        cursor = await conn.execute(
            "SELECT * FROM qualification_briefs WHERE company_id = ? AND status = 'approved'",
            (company_id,),
        )
        qual_row = await cursor.fetchone()
        if qual_row is None:
            raise ValueError(f"No approved qualification for {company_id}")

    state["prospect_brief"] = _parse_json_fields(
        dict(prospect_row), _PROSPECT_JSON_FIELDS
    )
    state["qualification_brief"] = _parse_json_fields(
        dict(qual_row), _QUAL_JSON_FIELDS
    )
    return state


async def channel_router(state: DraftingState) -> DraftingState:
    """Route to the correct channel drafter and assemble the OutreachPackage."""
    client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    brief = ProspectBrief.model_validate(state["prospect_brief"])
    qual_brief = QualificationBrief.model_validate(state["qualification_brief"])

    recommended = brief.recommended_channel
    redraft_feedback: Optional[str] = state.get("redraft_feedback")

    primary_draft: dict = {}
    secondary_drafts: list[dict] = []
    creative_action: Optional[dict] = None
    resolved_channel = recommended

    if (
        recommended == "github"
        and brief.creative_outreach_opportunity
        and brief.creative_outreach_detail
    ):
        # creative_outreach_detail is Optional[str] in contracts — JSON-parse it
        details = brief.creative_outreach_detail
        if isinstance(details, str):
            details = json.loads(details)

        if details:
            issue_detail = details[0] if isinstance(details, list) else details
            github_result = await draft_github_comment(brief, issue_detail, client)

            creative_action = {
                "proposed": not github_result["skip"],
                "action_type": "github_comment",
                "draft": github_result.get("comment_body") or "",
            }

            if github_result["skip"]:
                # Fall back to email as primary
                resolved_channel = "email"
                primary_draft = await draft_email(
                    brief, qual_brief, client, redraft_feedback
                )
            else:
                resolved_channel = "github"
                primary_draft = github_result
                # Also draft email as secondary
                email_draft = await draft_email(brief, qual_brief, client)
                secondary_drafts.append(email_draft)
        else:
            # Empty details — fall back to email
            resolved_channel = "email"
            primary_draft = await draft_email(
                brief, qual_brief, client, redraft_feedback
            )
    elif recommended == "linkedin":
        resolved_channel = "linkedin"
        primary_draft = await draft_linkedin(
            brief, qual_brief, client, redraft_feedback
        )
        # Also draft email as secondary
        email_draft = await draft_email(brief, qual_brief, client)
        secondary_drafts.append(email_draft)
    else:
        # Default / email / github-skipped fallback
        resolved_channel = "email"
        primary_draft = await draft_email(
            brief, qual_brief, client, redraft_feedback
        )

    package_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()

    package_dict: dict = {
        "id": package_id,
        "company_id": state["company_id"],
        "primary_channel": resolved_channel,
        "primary_draft": primary_draft,
        "secondary_drafts": secondary_drafts,
        "creative_action": creative_action,
        "status": "pending_review",
        "send_result": None,
        "rejection_note": None,
        "created_at": now_iso,
    }

    # Hard invariant: personalization_hook must always be populated
    assert package_dict["primary_draft"].get(
        "personalization_hook"
    ), f"personalization_hook must be populated for {state['company_id']}"

    # Write to outreach_packages table (schema from schemas.py)
    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """INSERT OR REPLACE INTO outreach_packages
               (id, company_id, primary_channel, primary_draft, secondary_drafts,
                creative_action, status, send_result, rejection_note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                package_id,
                state["company_id"],
                resolved_channel,
                json.dumps(primary_draft),
                json.dumps(secondary_drafts),
                json.dumps(creative_action) if creative_action else None,
                "pending_review",
                None,
                None,
                now_iso,
            ),
        )
        await conn.commit()

        # Look up company_name from discovery_queue for SSE event
        cursor = await conn.execute(
            "SELECT company_name FROM discovery_queue WHERE id = ?",
            (state["company_id"],),
        )
        name_row = await cursor.fetchone()
        company_name = dict(name_row)["company_name"] if name_row else state["company_id"]

    # Emit SSE event
    event_data = {
        "event": "draft_ready",
        "company_id": state["company_id"],
        "company_name": company_name,
        "primary_channel": resolved_channel,
        "personalization_hook": primary_draft["personalization_hook"],
        "timestamp": datetime.utcnow().isoformat(),
    }
    for q in drafting_sse_queues:
        await q.put(event_data)

    state["outreach_package"] = package_dict
    return state
