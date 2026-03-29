from apscheduler.schedulers.asyncio import AsyncIOScheduler
from adela_outbound.config import config

scheduler = AsyncIOScheduler()


def setup_scheduler(app) -> None:
    from adela_outbound.agents.discovery.graph import run_discovery

    async def _run_discovery_job():
        await run_discovery(run_type='scheduled')

    scheduler.add_job(
        _run_discovery_job,
        'interval',
        hours=config.DISCOVERY_INTERVAL_HOURS,
        id='discovery_job',
        replace_existing=True,
        misfire_grace_time=300,
    )
    app.state.scheduler = scheduler
