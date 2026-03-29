from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

from adela_outbound.config import config
from adela_outbound.db.connection import get_db
from adela_outbound.db.contracts import DiscoveryRecord
from adela_outbound.agents.discovery import events as discovery_events

router = APIRouter()


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
