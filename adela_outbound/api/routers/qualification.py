from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from adela_outbound.db.connection import get_db
from adela_outbound.agents.qualification import events as qual_events
from adela_outbound.agents.qualification.icp import (
    load_icp,
    save_icp_version,
    save_icp_suggestion,
)

router = APIRouter()


class ApproveRequest(BaseModel):
    pass


class RejectRequest(BaseModel):
    note: str

    @field_validator('note')
    @classmethod
    def note_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Rejection note required')
        return v.strip()


@router.post('/run/{company_id}')
async def trigger_qualification(
    company_id: str, background_tasks: BackgroundTasks
) -> dict:
    from adela_outbound.agents.qualification.graph import run_qualification

    background_tasks.add_task(run_qualification, company_id)
    return {'status': 'started', 'company_id': company_id}


@router.post('/approve/{company_id}')
async def approve_qualification(company_id: str) -> dict:
    from adela_outbound.agents.qualification.graph import (
        qualification_graph,
        resume_qualification,
    )

    config = {'configurable': {'thread_id': company_id}}
    state = qualification_graph.get_state(config)
    if not state or not state.next:
        raise HTTPException(
            status_code=404,
            detail=(
                f'No paused qualification found for company_id={company_id}. '
                'Either the graph has not run yet or already completed.'
            ),
        )

    result = await resume_qualification(company_id, decision='approved')
    return {'status': 'approved', 'company_id': company_id}


@router.post('/reject/{company_id}')
async def reject_qualification(company_id: str, body: RejectRequest) -> dict:
    from adela_outbound.agents.qualification.graph import (
        qualification_graph,
        resume_qualification,
    )

    if not body.note.strip():
        raise HTTPException(status_code=400, detail='Rejection note is required')

    config = {'configurable': {'thread_id': company_id}}
    state = qualification_graph.get_state(config)
    if not state or not state.next:
        raise HTTPException(
            status_code=404,
            detail=(
                f'No paused qualification found for company_id={company_id}. '
                'Either the graph has not run yet or already completed.'
            ),
        )

    result = await resume_qualification(
        company_id, decision='rejected', rejection_note=body.note.strip()
    )
    return {'status': 'rejected', 'company_id': company_id, 'note_recorded': True}


@router.get('/queue')
async def get_qualification_queue(limit: int = 50) -> list:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT qb.id, qb.company_id, dq.company_name, qb.fit_score, '
            'qb.fit_tier, qb.why_now, qb.suggested_outreach_angle, qb.status, '
            'qb.created_at '
            'FROM qualification_briefs qb '
            'JOIN discovery_queue dq ON qb.company_id = dq.id '
            'WHERE qb.status = ? '
            'ORDER BY qb.fit_score DESC LIMIT ?',
            ['pending_review', limit],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get('/icp')
async def get_icp() -> dict:
    async with get_db() as conn:
        icp = await load_icp(conn)
    return icp


@router.put('/icp')
async def update_icp(body: dict) -> dict:
    if 'criteria' not in body or not isinstance(body['criteria'], list):
        raise HTTPException(400, 'Body must have criteria as list')
    for c in body['criteria']:
        if not all(k in c for k in ['id', 'name', 'description', 'weight']):
            raise HTTPException(400, f'Criterion missing required fields: {c}')
    async with get_db() as conn:
        new_version = await save_icp_version(conn, body['criteria'])
    return {
        'status': 'saved',
        'version': new_version,
        'criteria_count': len(body['criteria']),
    }


@router.get('/icp/suggestions')
async def get_icp_suggestions() -> list:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT * FROM icp_suggestions WHERE status = ? ORDER BY created_at DESC',
            ['pending'],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.post('/icp/suggestions/{suggestion_id}/accept')
async def accept_suggestion(suggestion_id: str) -> dict:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT * FROM icp_suggestions WHERE id = ?', [suggestion_id]
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, 'Suggestion not found')
        try:
            new_criteria = json.loads(dict(row).get('suggestion_text', '[]'))
        except Exception:
            raise HTTPException(400, 'Could not parse suggestion as criteria JSON')
        new_version = await save_icp_version(conn, new_criteria)
        await conn.execute(
            'UPDATE icp_suggestions SET status = ? WHERE id = ?',
            ['accepted', suggestion_id],
        )
        await conn.commit()
    return {'status': 'accepted', 'new_version': new_version}


@router.post('/icp/suggestions/{suggestion_id}/reject')
async def reject_suggestion(suggestion_id: str) -> dict:
    async with get_db() as conn:
        result = await conn.execute(
            'UPDATE icp_suggestions SET status = ? WHERE id = ?',
            ['rejected', suggestion_id],
        )
        await conn.commit()
        if result.rowcount == 0:
            raise HTTPException(404, 'Suggestion not found')
    return {'status': 'rejected'}


@router.get('/{company_id}/brief')
async def get_qualification_brief(company_id: str) -> dict:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT qb.*, dq.company_name, dq.website '
            'FROM qualification_briefs qb '
            'JOIN discovery_queue dq ON qb.company_id = dq.id '
            'WHERE qb.company_id = ?',
            [company_id],
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f'No qualification brief for {company_id}',
            )
        d = dict(row)
        d['criterion_scores'] = json.loads(d.get('criterion_scores') or '[]')

        cursor2 = await conn.execute(
            'SELECT summary, adela_relevance, personalization_hooks, '
            'recommended_channel, creative_outreach_opportunity '
            'FROM prospect_briefs WHERE company_id = ?',
            [company_id],
        )
        brief_row = await cursor2.fetchone()
        d['prospect_brief_summary'] = dict(brief_row) if brief_row else {}
        return d


@router.get('/stream')
async def stream_qualify_events(request: Request) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()
    qual_events.sse_queues.append(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            qual_events.sse_queues.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    )
