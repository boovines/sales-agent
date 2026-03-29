from __future__ import annotations

import aiosqlite

from adela_outbound.agents.qualification.icp import (
    SEED_ICP_CRITERIA,
    load_icp,
    seed_icp_if_empty,
)
from adela_outbound.db.schemas import CREATE_TABLES_SQL


async def _make_conn(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(CREATE_TABLES_SQL)
    await conn.commit()
    return conn


async def test_seed_icp_if_empty_inserts_criteria(tmp_path):
    conn = await _make_conn(tmp_path)
    try:
        await seed_icp_if_empty(conn)
        cursor = await conn.execute("SELECT COUNT(*) FROM icp_definition")
        row = await cursor.fetchone()
        assert row[0] == 1
        cursor2 = await conn.execute("SELECT criteria FROM icp_definition")
        row2 = await cursor2.fetchone()
        import json

        criteria = json.loads(row2[0])
        assert len(criteria) == 8
    finally:
        await conn.close()


async def test_seed_icp_if_empty_is_idempotent(tmp_path):
    conn = await _make_conn(tmp_path)
    try:
        await seed_icp_if_empty(conn)
        await seed_icp_if_empty(conn)
        cursor = await conn.execute("SELECT COUNT(*) FROM icp_definition")
        row = await cursor.fetchone()
        assert row[0] == 1
    finally:
        await conn.close()


async def test_load_icp_returns_dict_with_criteria_list(tmp_path):
    conn = await _make_conn(tmp_path)
    try:
        await seed_icp_if_empty(conn)
        result = await load_icp(conn)
        assert isinstance(result, dict)
        assert "criteria" in result
        assert isinstance(result["criteria"], list)
        assert len(result["criteria"]) == 8
    finally:
        await conn.close()
