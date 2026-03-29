from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import aiosqlite
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
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


@router.get("/agents/drafting/{company_id}/package")
async def get_package(company_id: str):
    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row

        cursor = await conn.execute(
            "SELECT * FROM outreach_packages WHERE company_id = ?",
            (company_id,),
        )
        pkg_row = await cursor.fetchone()
        if pkg_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"No outreach package found for company_id {company_id}",
            )
        pkg = dict(pkg_row)

        # Parse JSON columns
        try:
            primary_draft = json.loads(pkg["primary_draft"])
        except (json.JSONDecodeError, TypeError):
            primary_draft = {}
        try:
            secondary_drafts = json.loads(pkg["secondary_drafts"])
        except (json.JSONDecodeError, TypeError):
            secondary_drafts = []
        creative_action = None
        if pkg.get("creative_action"):
            try:
                creative_action = json.loads(pkg["creative_action"])
            except (json.JSONDecodeError, TypeError):
                pass
        send_result = None
        if pkg.get("send_result"):
            try:
                send_result = json.loads(pkg["send_result"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Fetch brief_summary and adela_relevance from prospect_briefs
        cursor = await conn.execute(
            "SELECT summary, adela_relevance FROM prospect_briefs WHERE company_id = ?",
            (company_id,),
        )
        brief_row = await cursor.fetchone()
        brief_dict = dict(brief_row) if brief_row else {}

    return {
        "personalization_hook": primary_draft.get("personalization_hook"),
        "company_id": pkg["company_id"],
        "primary_channel": pkg["primary_channel"],
        "primary_draft": primary_draft,
        "secondary_drafts": secondary_drafts,
        "creative_action": creative_action,
        "status": pkg["status"],
        "send_result": send_result,
        "rejection_note": pkg.get("rejection_note"),
        "created_at": pkg["created_at"],
        "brief_summary": brief_dict.get("summary"),
        "adela_relevance": brief_dict.get("adela_relevance"),
    }


@router.get("/outreach/log")
async def get_outreach_log(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    query = """SELECT ol.company_id, ol.channel, ol.sent_at, ol.success, ol.error,
                      dc.company_name
               FROM outreach_log ol
               LEFT JOIN discovery_queue dc ON ol.company_id = dc.id"""
    conditions = []
    params: list[str] = []

    if start_date:
        conditions.append("ol.sent_at >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("ol.sent_at <= ?")
        params.append(end_date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

    return [
        {
            "company_id": dict(row)["company_id"],
            "company_name": dict(row).get("company_name"),
            "channel": dict(row)["channel"],
            "sent_at": dict(row)["sent_at"],
            "success": bool(dict(row)["success"]),
            "error": dict(row).get("error"),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------


@router.get("/stream/drafts")
async def drafts_sse_stream(request: Request) -> StreamingResponse:
    from adela_outbound.agents.drafting.events import drafting_sse_queues

    queue: asyncio.Queue = asyncio.Queue()
    drafting_sse_queues.append(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {event_data['event']}\ndata: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            try:
                drafting_sse_queues.remove(queue)
            except ValueError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
