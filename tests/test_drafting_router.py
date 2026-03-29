from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from adela_outbound.api.routers.drafting import router

app = FastAPI()
app.include_router(router)


def _make_snapshot(is_paused: bool = True, package: dict | None = None):
    """Create a mock StateSnapshot."""
    snapshot = MagicMock()
    snapshot.next = ("hitl_gate",) if is_paused else ()
    snapshot.values = {
        "company_id": "test-co",
        "outreach_package": package
        or {
            "primary_channel": "email",
            "primary_draft": {
                "subject": "Test",
                "body": "Body",
                "personalization_hook": "Hook",
            },
            "status": "pending_review",
        },
    }
    return snapshot


@pytest.fixture()
async def client():
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ---------------------------------------------------------------------------
# POST /hitl/draft/{company_id}/approve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_draft_success(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.agents.drafting.graph.drafting_graph"
    ) as mock_g:
        paused = _make_snapshot(is_paused=True)
        approved = _make_snapshot(
            is_paused=False,
            package={
                "primary_channel": "email",
                "primary_draft": {
                    "subject": "Test",
                    "body": "Body",
                    "personalization_hook": "Hook",
                },
                "status": "sent",
            },
        )
        mock_g.get_state = MagicMock(side_effect=[paused, approved])
        mock_g.aupdate_state = AsyncMock()
        mock_g.ainvoke = AsyncMock()

        resp = await client.post("/hitl/draft/test-co/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["company_id"] == "test-co"
        assert data["channel"] == "email"


@pytest.mark.asyncio
async def test_approve_draft_not_found(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.agents.drafting.graph.drafting_graph"
    ) as mock_g:
        mock_g.get_state = MagicMock(return_value=_make_snapshot(is_paused=False))

        resp = await client.post("/hitl/draft/test-co/approve")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_draft_with_edited_draft(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.agents.drafting.graph.drafting_graph"
    ) as mock_g:
        paused = _make_snapshot(is_paused=True)
        approved = _make_snapshot(is_paused=False)
        mock_g.get_state = MagicMock(side_effect=[paused, approved])
        mock_g.aupdate_state = AsyncMock()
        mock_g.ainvoke = AsyncMock()

        resp = await client.post(
            "/hitl/draft/test-co/approve",
            json={"edited_draft": "Updated body text"},
        )
        assert resp.status_code == 200

        call_args = mock_g.aupdate_state.call_args
        state_update = call_args[0][1]
        assert state_update["edited_draft"] == "Updated body text"


# ---------------------------------------------------------------------------
# POST /hitl/draft/{company_id}/reject
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_draft_with_empty_note(client: httpx.AsyncClient):
    """Reject with empty note should return 400."""
    resp = await client.post(
        "/hitl/draft/test-co/reject",
        json={"note": "", "redraft": False},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reject_draft_with_whitespace_note(client: httpx.AsyncClient):
    """Reject with whitespace-only note should return 400."""
    resp = await client.post(
        "/hitl/draft/test-co/reject",
        json={"note": "   ", "redraft": False},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reject_draft_not_found(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.agents.drafting.graph.drafting_graph"
    ) as mock_g:
        mock_g.get_state = MagicMock(return_value=_make_snapshot(is_paused=False))

        resp = await client.post(
            "/hitl/draft/test-co/reject",
            json={"note": "Not relevant", "redraft": False},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reject_draft_no_redraft(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.agents.drafting.graph.drafting_graph"
    ) as mock_g:
        paused = _make_snapshot(is_paused=True)
        done = _make_snapshot(is_paused=False)
        mock_g.get_state = MagicMock(side_effect=[paused, done])
        mock_g.aupdate_state = AsyncMock()
        mock_g.ainvoke = AsyncMock()

        resp = await client.post(
            "/hitl/draft/test-co/reject",
            json={"note": "Not a good fit", "redraft": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["company_id"] == "test-co"

        call_args = mock_g.aupdate_state.call_args
        state_update = call_args[0][1]
        assert state_update["redraft_feedback"] is None


@pytest.mark.asyncio
async def test_reject_draft_with_redraft(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.agents.drafting.graph.drafting_graph"
    ) as mock_g:
        paused = _make_snapshot(is_paused=True)
        done = _make_snapshot(is_paused=False)
        mock_g.get_state = MagicMock(side_effect=[paused, done])
        mock_g.aupdate_state = AsyncMock()
        mock_g.ainvoke = AsyncMock()

        resp = await client.post(
            "/hitl/draft/test-co/reject",
            json={"note": "Make it shorter", "redraft": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "redrafting"
        assert data["company_id"] == "test-co"

        call_args = mock_g.aupdate_state.call_args
        state_update = call_args[0][1]
        assert state_update["redraft_feedback"] == "Make it shorter"


# ---------------------------------------------------------------------------
# GET /queue/drafts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_pending_drafts(client: httpx.AsyncClient):
    mock_rows = [
        {
            "company_id": "co-1",
            "primary_draft": json.dumps(
                {
                    "subject": "Test",
                    "body": "Body",
                    "personalization_hook": "Hook for co-1",
                }
            ),
            "primary_channel": "email",
            "status": "pending_review",
            "company_name": "Test Company",
            "fit_tier": "Tier 1",
        },
    ]

    with patch(
        "adela_outbound.api.routers.drafting.aiosqlite"
    ) as mock_aiosqlite:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_aiosqlite.connect.return_value = ctx
        mock_aiosqlite.Row = object

        resp = await client.get("/queue/drafts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["company_id"] == "co-1"
        assert data[0]["company_name"] == "Test Company"
        assert data[0]["personalization_hook"] == "Hook for co-1"
        assert data[0]["fit_tier"] == "Tier 1"


# ---------------------------------------------------------------------------
# GET /agents/drafting/{company_id}/package
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_package_success(client: httpx.AsyncClient):
    pkg_row = {
        "id": "pkg-1",
        "company_id": "co-1",
        "primary_channel": "email",
        "primary_draft": json.dumps(
            {
                "subject": "Test Subject",
                "body": "Test body",
                "personalization_hook": "Hook for co-1",
            }
        ),
        "secondary_drafts": json.dumps([]),
        "creative_action": None,
        "status": "pending_review",
        "send_result": None,
        "rejection_note": None,
        "created_at": "2026-03-29T10:00:00",
    }
    brief_row = {
        "summary": "They build multi-tenant platforms",
        "adela_relevance": "Context layer for deployments",
    }

    with patch(
        "adela_outbound.api.routers.drafting.aiosqlite"
    ) as mock_aiosqlite:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_cursor_pkg = AsyncMock()
        mock_cursor_pkg.fetchone = AsyncMock(return_value=pkg_row)
        mock_cursor_brief = AsyncMock()
        mock_cursor_brief.fetchone = AsyncMock(return_value=brief_row)
        mock_conn.execute = AsyncMock(
            side_effect=[mock_cursor_pkg, mock_cursor_brief]
        )

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_aiosqlite.connect.return_value = ctx
        mock_aiosqlite.Row = object

        resp = await client.get("/agents/drafting/co-1/package")
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_id"] == "co-1"
        assert data["personalization_hook"] == "Hook for co-1"
        assert data["primary_draft"]["personalization_hook"] == "Hook for co-1"
        assert data["brief_summary"] == "They build multi-tenant platforms"
        assert data["adela_relevance"] == "Context layer for deployments"
        assert data["status"] == "pending_review"


@pytest.mark.asyncio
async def test_get_package_not_found(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.api.routers.drafting.aiosqlite"
    ) as mock_aiosqlite:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_aiosqlite.connect.return_value = ctx
        mock_aiosqlite.Row = object

        resp = await client.get("/agents/drafting/nonexistent/package")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /outreach/log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_outreach_log(client: httpx.AsyncClient):
    log_rows = [
        {
            "company_id": "co-1",
            "company_name": "Test Company",
            "channel": "email",
            "sent_at": "2026-03-29T10:00:00",
            "success": 1,
            "error": None,
        },
    ]

    with patch(
        "adela_outbound.api.routers.drafting.aiosqlite"
    ) as mock_aiosqlite:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=log_rows)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_aiosqlite.connect.return_value = ctx
        mock_aiosqlite.Row = object

        resp = await client.get("/outreach/log")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["company_id"] == "co-1"
        assert data[0]["success"] is True
        assert data[0]["channel"] == "email"


@pytest.mark.asyncio
async def test_get_outreach_log_with_date_filter(client: httpx.AsyncClient):
    with patch(
        "adela_outbound.api.routers.drafting.aiosqlite"
    ) as mock_aiosqlite:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_aiosqlite.connect.return_value = ctx
        mock_aiosqlite.Row = object

        resp = await client.get(
            "/outreach/log",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
        assert resp.status_code == 200

        # Verify that the SQL query included WHERE conditions
        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "ol.sent_at >= ?" in query
        assert "ol.sent_at <= ?" in query
        assert params == ["2026-03-01", "2026-03-31"]


@pytest.mark.asyncio
async def test_list_pending_drafts_skips_missing_hook(client: httpx.AsyncClient):
    """Rows with missing personalization_hook or company_name are skipped."""
    mock_rows = [
        {
            "company_id": "co-bad",
            "primary_draft": json.dumps({"subject": "Test", "body": "Body"}),
            "primary_channel": "email",
            "status": "pending_review",
            "company_name": "Bad Company",
            "fit_tier": "Tier 2",
        },
    ]

    with patch(
        "adela_outbound.api.routers.drafting.aiosqlite"
    ) as mock_aiosqlite:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_aiosqlite.connect.return_value = ctx
        mock_aiosqlite.Row = object

        resp = await client.get("/queue/drafts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0
