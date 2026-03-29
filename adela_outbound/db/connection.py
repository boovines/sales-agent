import aiosqlite
import os
from adela_outbound.config import config
from adela_outbound.db.schemas import CREATE_TABLES_SQL
from contextlib import asynccontextmanager
from typing import AsyncGenerator


async def init_db() -> None:
    os.makedirs(os.path.dirname(os.path.abspath(config.DB_PATH)), exist_ok=True)
    async with aiosqlite.connect(config.DB_PATH) as conn:
        await conn.executescript(CREATE_TABLES_SQL)
        await conn.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn
