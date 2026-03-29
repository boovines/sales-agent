from __future__ import annotations

import json
import logging
from typing import Optional

import aiosqlite
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from adela_outbound.config import config

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    edited_draft: Optional[str] = None


class RejectRequest(BaseModel):
    note: str
    redraft: bool


# ---------------------------------------------------------------------------
# HITL endpoints
# ---------------------------------------------------------------------------


@router.post("/hitl/draft/{company_id}/approve")
async def approve_draft(company_id: str, body: Optional[ApproveRequest] = None):
    from adela_outbound.agents.drafting.graph import drafting_graph

    graph_config: dict = {"configurable": {"thread_id": company_id}}

    snapshot = drafting_graph.get_state(graph_config)  # type: ignore[arg-type]
    if not snapshot or not snapshot.next:
        raise HTTPException(
            status_code=404,
            detail=f"No paused draft for company_id {company_id}",
        )

    state_update: dict = {"decision": "approved"}
    if body and body.edited_draft:
        state_update["edited_draft"] = body.edited_draft

    await drafting_graph.aupdate_state(
        graph_config, state_update, as_node="hitl_gate"  # type: ignore[arg-type]
    )
    await drafting_graph.ainvoke(None, config=graph_config)  # type: ignore[arg-type]

    # Read current package from state for the response
    final_snapshot = drafting_graph.get_state(graph_config)  # type: ignore[arg-type]
    current_package = (final_snapshot.values or {}).get("outreach_package", {})

    return {
        "status": "approved",
        "company_id": company_id,
        "channel": current_package.get("primary_channel", "unknown"),
    }


@router.post("/hitl/draft/{company_id}/reject")
async def reject_draft(company_id: str, body: RejectRequest):
    from adela_outbound.agents.drafting.graph import drafting_graph

    if not body.note or not body.note.strip():
        raise HTTPException(
            status_code=400,
            detail="Rejection note is required and cannot be empty",
        )

    graph_config: dict = {"configurable": {"thread_id": company_id}}

    snapshot = drafting_graph.get_state(graph_config)  # type: ignore[arg-type]
    if not snapshot or not snapshot.next:
        raise HTTPException(
            status_code=404,
            detail=f"No paused draft for company_id {company_id}",
        )

    state_update: dict = {
        "decision": "rejected",
        "rejection_note": body.note,
        "redraft_feedback": body.note if body.redraft else None,
    }

    await drafting_graph.aupdate_state(
        graph_config, state_update, as_node="hitl_gate"  # type: ignore[arg-type]
    )
    await drafting_graph.ainvoke(None, config=graph_config)  # type: ignore[arg-type]

    return {
        "status": "redrafting" if body.redraft else "rejected",
        "company_id": company_id,
    }


# ---------------------------------------------------------------------------
# Queue / read endpoints
# ---------------------------------------------------------------------------


@router.get("/queue/drafts")
async def list_pending_drafts():
    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """SELECT op.company_id, op.primary_draft, op.primary_channel, op.status,
                      dc.company_name, qb.fit_tier
               FROM outreach_packages op
               JOIN discovery_queue dc ON op.company_id = dc.id
               JOIN qualification_briefs qb ON op.company_id = qb.company_id
               WHERE op.status = 'pending_review'"""
        )
        rows = await cursor.fetchall()

    results = []
    for row in rows:
        row_dict = dict(row)
        company_name = row_dict.get("company_name")
        try:
            primary_draft = json.loads(row_dict["primary_draft"])
        except (json.JSONDecodeError, TypeError):
            primary_draft = {}
        personalization_hook = primary_draft.get("personalization_hook")

        if company_name is None or personalization_hook is None:
            logger.warning(
                "Skipping draft row for %s: missing company_name or personalization_hook",
                row_dict.get("company_id"),
            )
            continue

        results.append(
            {
                "company_id": row_dict["company_id"],
                "company_name": company_name,
                "primary_channel": row_dict["primary_channel"],
                "personalization_hook": personalization_hook,
                "fit_tier": row_dict["fit_tier"],
            }
        )

    return results
