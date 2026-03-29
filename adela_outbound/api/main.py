from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite
from adela_outbound.db.connection import init_db
from adela_outbound.scheduler import scheduler, setup_scheduler
from adela_outbound.config import config
from adela_outbound.api.routers.discovery import router as discovery_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    setup_scheduler(app)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title='Adela Outbound API', version='0.1.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(discovery_router, prefix='/agents/discovery', tags=['discovery'])

# from adela_outbound.api.routers.research import router as research_router
# app.include_router(research_router, prefix='/agents/research', tags=['research'])
# from adela_outbound.api.routers.qualification import router as qualification_router
# app.include_router(qualification_router, prefix='/agents/qualification', tags=['qualification'])
# from adela_outbound.api.routers.drafting import router as drafting_router
# app.include_router(drafting_router, prefix='/agents/drafting', tags=['drafting'])


@app.get('/health')
async def health(request: Request) -> dict:
    try:
        async with aiosqlite.connect(config.DB_PATH) as conn:
            await conn.execute('SELECT 1')
        db_status = 'ok'
    except Exception:
        db_status = 'error'

    sched = request.app.state.scheduler if hasattr(request.app.state, 'scheduler') else None
    scheduler_status = 'running' if (sched and sched.running) else 'stopped'

    return {
        'status': 'ok',
        'db': db_status,
        'scheduler': scheduler_status,
        'version': '0.1.0',
    }
