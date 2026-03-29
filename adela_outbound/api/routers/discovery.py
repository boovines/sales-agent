from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
import aiosqlite
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

from adela_outbound.config import config
from adela_outbound.db.connection import get_db
from adela_outbound.db.contracts import DiscoveryRecord
from adela_outbound.agents.discovery import events as discovery_events

router = APIRouter()


def _row_to_discovery_record(row: aiosqlite.Row) -> DiscoveryRecord:
    d = dict(row)
    return DiscoveryRecord(
        id=d['id'],
        company_name=d['company_name'],
        website=d.get('website'),
        twitter_handle=d.get('twitter_handle'),
        github_handle=d.get('github_handle'),
        linkedin_url=d.get('linkedin_url'),
        discovery_source=d['discovery_source'],
        discovery_signal=d['discovery_signal'],
        pre_score=d['pre_score'],
        status=d['status'],
        created_at=d['created_at'],
        updated_at=d['updated_at'],
    )


@router.post('/run')
async def trigger_discovery_run(background_tasks: BackgroundTasks) -> dict:
    from adela_outbound.agents.discovery.graph import run_discovery
    background_tasks.add_task(run_discovery, run_type='manual')
    return {'status': 'started', 'message': 'Discovery run started in background'}


@router.get('/status')
async def get_discovery_status(request: Request) -> dict:
    sched = getattr(request.app.state, 'scheduler', None)
    next_run = None
    if sched:
        job = sched.get_job('discovery_job')
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        'scheduler_running': sched.running if sched else False,
        'next_run_at': next_run,
        'daily_cap': config.DAILY_DISCOVERY_CAP,
        'interval_hours': config.DISCOVERY_INTERVAL_HOURS,
    }


@router.get('/pipeline')
async def get_pipeline(
    status: Optional[str] = None,
    source: Optional[str] = None,
    sort: str = 'created_at_desc',
    limit: int = 100,
) -> list[dict]:
    sort_map = {
        'created_at_desc': 'created_at DESC',
        'created_at_asc': 'created_at ASC',
        'pre_score_desc': 'pre_score DESC',
    }
    order_clause = sort_map.get(sort, 'created_at DESC')
    query = 'SELECT * FROM discovery_queue WHERE 1=1'
    params: list = []
    if status:
        query += ' AND status = ?'
        params.append(status)
    if source:
        query += ' AND discovery_source = ?'
        params.append(source)
    query += f' ORDER BY {order_clause} LIMIT ?'
    params.append(limit)
    try:
        async with get_db() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [_row_to_discovery_record(r).model_dump(mode='json') for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Database error: {str(e)}')


@router.get('/pipeline/stats')
async def get_pipeline_stats() -> dict:
    try:
        async with get_db() as conn:
            queries = {
                'total_in_queue': 'SELECT COUNT(*) FROM discovery_queue',
                'pending_qualification': "SELECT COUNT(*) FROM discovery_queue WHERE status = 'queued'",
                'pending_draft_review': "SELECT COUNT(*) FROM discovery_queue WHERE status = 'qualified'",
                'sent_this_week': "SELECT COUNT(*) FROM outreach_log WHERE DATE(sent_at) >= DATE('now', '-7 days')",
            }
            result = {}
            for key, sql in queries.items():
                cursor = await conn.execute(sql)
                row = await cursor.fetchone()
                result[key] = row[0] if row else 0
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Database error: {str(e)}')


@router.get('/pipeline/{company_id}')
async def get_company(company_id: str) -> dict:
    try:
        async with get_db() as conn:
            cursor = await conn.execute(
                'SELECT * FROM discovery_queue WHERE id = ?', [company_id]
            )
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404, detail=f'Company {company_id} not found'
                )
            return _row_to_discovery_record(row).model_dump(mode='json')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Database error: {str(e)}')
