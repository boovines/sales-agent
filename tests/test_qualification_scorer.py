from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiosqlite

from adela_outbound.agents.qualification.icp import (
    SEED_ICP_CRITERIA,
    load_icp,
    seed_icp_if_empty,
)
from adela_outbound.agents.qualification.scorer import (
    aggregate_scores,
    score_criterion,
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


def test_aggregate_scores_strong():
    icp = {'criteria': [{'id': 'c1', 'weight': 'high'}, {'id': 'c2', 'weight': 'medium'}]}
    scores = [{'criterion_id': 'c1', 'score': 3}, {'criterion_id': 'c2', 'score': 3}]
    result = aggregate_scores(scores, icp)
    assert result['fit_tier'] == 'strong'
    assert result['fit_score'] >= 0.75


def test_aggregate_scores_disqualified():
    icp = {'criteria': [{'id': 'c1', 'weight': 'high'}]}
    scores = [{'criterion_id': 'c1', 'score': 0}]
    result = aggregate_scores(scores, icp)
    assert result['fit_tier'] == 'disqualified'
    assert result['fit_score'] == 0.0


def test_aggregate_scores_handles_missing_criterion():
    icp = {'criteria': [{'id': 'c1', 'weight': 'high'}, {'id': 'c2', 'weight': 'low'}]}
    scores = [{'criterion_id': 'c1', 'score': 3}]
    result = aggregate_scores(scores, icp)
    assert 0.0 <= result['fit_score'] <= 1.0


async def test_score_criterion_returns_zero_on_claude_failure(tmp_path):
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception('API error'))
    result = await score_criterion(
        {'summary': 'test'},
        {'id': 'test_crit', 'name': 'Test', 'description': 'test', 'weight': 'high'},
        mock_client,
    )
    assert result['criterion_id'] == 'test_crit'
    assert result['score'] == 0
