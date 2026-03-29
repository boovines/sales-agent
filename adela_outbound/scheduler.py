from apscheduler.schedulers.asyncio import AsyncIOScheduler
from adela_outbound.config import config

scheduler = AsyncIOScheduler()


def setup_scheduler(app) -> None:
    app.state.scheduler = scheduler
