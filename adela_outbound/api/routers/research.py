from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import asyncio
from datetime import datetime, timezone

from adela_outbound.db.connection import get_db
from adela_outbound.agents.research import events as research_events

router = APIRouter()


def _row_to_brief(row) -> dict:
    d = dict(row)
    d['pain_points'] = json.loads(d.get('pain_points') or '[]')
    d['personalization_hooks'] = json.loads(d.get('personalization_hooks') or '[]')
    d['research_sources'] = json.loads(d.get('research_sources') or '[]')
    d['raw_research'] = json.loads(d.get('raw_research') or '{}')
    d['creative_outreach_opportunity'] = bool(d.get('creative_outreach_opportunity', 0))
    return d


@router.post('/run/{company_id}')
async def trigger_research(company_id: str, background_tasks: BackgroundTasks) -> dict:
    from adela_outbound.agents.research.graph import run_research
    background_tasks.add_task(run_research, company_id)
    return {
        'status': 'started',
        'company_id': company_id,
        'message': 'Research started in background',
    }


@router.get('/queue')
async def get_research_queue(limit: int = 50) -> list:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT id, company_name, website, github_handle, twitter_handle, '
            'discovery_source, discovery_signal, pre_score, status, created_at '
            'FROM discovery_queue WHERE status = ? ORDER BY pre_score DESC LIMIT ?',
            ['queued', limit],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get('/{company_id}/brief')
async def get_brief(company_id: str) -> dict:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT * FROM prospect_briefs WHERE company_id = ?',
            [company_id],
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f'No research brief found for company_id={company_id}. Research may still be in progress.',
            )
        return _row_to_brief(row)


@router.get('/stream')
async def stream_research_events(request: Request) -> StreamingResponse:
    async def event_generator():
        q: asyncio.Queue = asyncio.Queue()
        research_events.sse_queues.append(q)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f'event: {item["event"]}\ndata: {json.dumps(item["data"])}\n\n'
                except asyncio.TimeoutError:
                    yield f'event: heartbeat\ndata: {json.dumps({"ts": datetime.now(timezone.utc).isoformat()})}\n\n'
        finally:
            if q in research_events.sse_queues:
                research_events.sse_queues.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
