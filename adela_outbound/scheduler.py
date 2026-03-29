from apscheduler.schedulers.asyncio import AsyncIOScheduler
from adela_outbound.config import config

scheduler = AsyncIOScheduler(timezone='UTC')


def setup_scheduler(app) -> None:
    def _make_job():
        async def _run_discovery_job():
            from adela_outbound.agents.discovery.graph import run_discovery
            await run_discovery(run_type='scheduled')
        return _run_discovery_job

    scheduler.add_job(
        _make_job(),
        'interval',
        hours=config.DISCOVERY_INTERVAL_HOURS,
        id='discovery_job',
        replace_existing=True,
        misfire_grace_time=300,
    )
    app.state.scheduler = scheduler
