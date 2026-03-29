from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adela_outbound.agents.drafting.nodes import (
    _parse_json_fields,
    channel_router,
    input_loader,
)
from adela_outbound.agents.drafting.state import DraftingState


def _make_prospect_row() -> dict:
    """Simulates a dict(row) from prospect_briefs table."""
    return {
        "id": "pb-1",
        "company_id": "test-co",
        "summary": "Building a multi-tenant deployment platform.",
        "current_focus": "Scaling configuration management.",
        "pain_points": json.dumps(["Per-client config overhead"]),
        "adela_relevance": "Adela SOP versioning maps to their needs.",
        "personalization_hooks": json.dumps(["Multi-tenant deployment challenge"]),
        "creative_outreach_opportunity": 0,
        "creative_outreach_detail": None,
        "recommended_channel": "email",
        "research_sources": json.dumps(["https://example.com"]),
        "confidence_score": 0.85,
        "raw_research": json.dumps({}),
        "created_at": datetime.now().isoformat(),
    }


def _make_qual_row() -> dict:
    """Simulates a dict(row) from qualification_briefs table."""
    return {
        "id": "qb-1",
        "company_id": "test-co",
        "fit_score": 0.9,
        "fit_tier": "Tier 1",
        "criterion_scores": json.dumps({"technical_fit": 0.95}),
        "why_now": "Actively hiring for deployment engineering roles.",
        "suggested_outreach_angle": "Multi-tenant context isolation.",
        "status": "approved",
        "rejection_note": None,
        "reviewed_at": None,
        "created_at": datetime.now().isoformat(),
    }


def _make_state(company_id: str = "test-co") -> DraftingState:
    return DraftingState(
        company_id=company_id,
        prospect_brief={},
        qualification_brief={},
        outreach_package=None,
        decision=None,
        edited_draft=None,
        rejection_note=None,
        redraft_feedback=None,
        errors=[],
    )


def _mock_aiosqlite_conn(prospect_row: dict, qual_row: dict, name_row: dict | None = None):
    """Create a mock aiosqlite connection context manager."""
    conn = AsyncMock()
    conn.row_factory = None

    # Track which query is being executed to return appropriate rows
    call_count = {"n": 0}

    async def mock_execute(sql: str, params=None):
        cursor = AsyncMock()
        if "prospect_briefs" in sql:
            row = MagicMock()
            row.__iter__ = MagicMock(return_value=iter(prospect_row.values()))
            row.keys = MagicMock(return_value=prospect_row.keys())

            def dict_converter(r):
                return prospect_row

            cursor.fetchone = AsyncMock(return_value=MagicMock(**{"__iter__": lambda s: iter(prospect_row.values())}))
            # Make dict(row) work by returning a mock that converts to prospect_row
            mock_row = MagicMock()
            mock_row.keys.return_value = prospect_row.keys()
            for k, v in prospect_row.items():
                mock_row[k] = v
            cursor.fetchone = AsyncMock(return_value=mock_row)
        elif "qualification_briefs" in sql:
            mock_row = MagicMock()
            mock_row.keys.return_value = qual_row.keys()
            for k, v in qual_row.items():
                mock_row[k] = v
            cursor.fetchone = AsyncMock(return_value=mock_row)
        elif "discovery_queue" in sql:
            if name_row:
                mock_row = MagicMock()
                mock_row.keys.return_value = name_row.keys()
                for k, v in name_row.items():
                    mock_row[k] = v
                cursor.fetchone = AsyncMock(return_value=mock_row)
            else:
                cursor.fetchone = AsyncMock(return_value=None)
        elif "INSERT" in sql:
            # DB write — just return
            return cursor
        return cursor

    conn.execute = mock_execute
    conn.commit = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_input_loader_loads_briefs():
    prospect_row = _make_prospect_row()
    qual_row = _make_qual_row()
    state = _make_state()

    conn = _mock_aiosqlite_conn(prospect_row, qual_row)

    with patch("adela_outbound.agents.drafting.nodes.aiosqlite") as mock_aiosqlite:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_aiosqlite.connect.return_value = ctx
        mock_aiosqlite.Row = object  # sentinel

        # We need dict(row) to work — patch at the node level
        with patch(
            "adela_outbound.agents.drafting.nodes.aiosqlite.connect"
        ) as mock_connect:
            # Simpler approach: mock the entire DB interaction
            mock_conn = AsyncMock()

            prospect_mock = AsyncMock()
            prospect_mock.fetchone = AsyncMock(return_value=prospect_row)
            qual_mock = AsyncMock()
            qual_mock.fetchone = AsyncMock(return_value=qual_row)

            call_count = 0

            async def execute_side_effect(sql, params=None):
                nonlocal call_count
                call_count += 1
                if "prospect_briefs" in sql:
                    return prospect_mock
                elif "qualification_briefs" in sql:
                    return qual_mock
                return AsyncMock()

            mock_conn.execute = execute_side_effect
            mock_conn.row_factory = None

            ctx_mgr = AsyncMock()
            ctx_mgr.__aenter__ = AsyncMock(return_value=mock_conn)
            ctx_mgr.__aexit__ = AsyncMock(return_value=False)
            mock_connect.return_value = ctx_mgr

            # dict(row) — since fetchone returns a plain dict, dict(dict) = dict
            result = await input_loader(state)

    assert result["prospect_brief"]["company_id"] == "test-co"
    assert result["qualification_brief"]["company_id"] == "test-co"
    # JSON fields should be parsed
    assert isinstance(result["prospect_brief"]["pain_points"], list)
    assert isinstance(result["qualification_brief"]["criterion_scores"], dict)


@pytest.mark.asyncio
async def test_input_loader_raises_on_missing_qualification():
    prospect_row = _make_prospect_row()
    state = _make_state()

    with patch(
        "adela_outbound.agents.drafting.nodes.aiosqlite.connect"
    ) as mock_connect:
        mock_conn = AsyncMock()

        prospect_mock = AsyncMock()
        prospect_mock.fetchone = AsyncMock(return_value=prospect_row)
        qual_mock = AsyncMock()
        qual_mock.fetchone = AsyncMock(return_value=None)

        async def execute_side_effect(sql, params=None):
            if "prospect_briefs" in sql:
                return prospect_mock
            return qual_mock

        mock_conn.execute = execute_side_effect
        mock_conn.row_factory = None

        ctx_mgr = AsyncMock()
        ctx_mgr.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx_mgr.__aexit__ = AsyncMock(return_value=False)
        mock_connect.return_value = ctx_mgr

        with pytest.raises(ValueError, match="No approved qualification"):
            await input_loader(state)


@pytest.mark.asyncio
async def test_channel_router_email_produces_pending_package():
    """Full flow: channel_router with email channel produces a pending_review package."""
    prospect_data = _make_prospect_row()
    # Parse JSON fields as input_loader would
    prospect_data = _parse_json_fields(
        prospect_data, {"pain_points", "personalization_hooks", "research_sources", "raw_research"}
    )
    qual_data = _make_qual_row()
    qual_data = _parse_json_fields(qual_data, {"criterion_scores"})

    state = _make_state()
    state["prospect_brief"] = prospect_data
    state["qualification_brief"] = qual_data

    mock_email_result = {
        "subject": "Test Subject",
        "body": "Test email body.",
        "personalization_hook": "Anchored on their deployment challenge.",
    }

    with patch(
        "adela_outbound.agents.drafting.nodes.draft_email",
        new_callable=AsyncMock,
        return_value=mock_email_result,
    ) as mock_draft_email, patch(
        "adela_outbound.agents.drafting.nodes.AsyncAnthropic"
    ), patch(
        "adela_outbound.agents.drafting.nodes.aiosqlite.connect"
    ) as mock_connect:
        # Mock DB connection for INSERT and discovery_queue lookup
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.commit = AsyncMock()

        name_mock = AsyncMock()
        name_mock.fetchone = AsyncMock(return_value=None)

        async def execute_side_effect(sql, params=None):
            if "discovery_queue" in sql:
                return name_mock
            return AsyncMock()

        mock_conn.execute = execute_side_effect

        ctx_mgr = AsyncMock()
        ctx_mgr.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx_mgr.__aexit__ = AsyncMock(return_value=False)
        mock_connect.return_value = ctx_mgr

        result = await channel_router(state)

    assert result["outreach_package"] is not None
    assert result["outreach_package"]["status"] == "pending_review"
    assert result["outreach_package"]["primary_channel"] == "email"
    assert result["outreach_package"]["primary_draft"]["personalization_hook"] is not None
    assert result["outreach_package"]["primary_draft"]["personalization_hook"] == "Anchored on their deployment challenge."
    mock_draft_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_channel_router_github_skip_falls_back_to_email():
    """When GitHub draft returns skip=True, channel_router falls back to email."""
    prospect_data = _make_prospect_row()
    prospect_data["recommended_channel"] = "email"  # will set to github below
    prospect_data["creative_outreach_opportunity"] = True  # will be 1 in sqlite
    prospect_data["creative_outreach_detail"] = json.dumps([{
        "issue_url": "https://github.com/org/repo/issues/1",
        "issue_title": "Context isolation bug",
        "issue_body": "Getting context bleed between tenants",
        "repo": "org/repo",
    }])
    prospect_data["recommended_channel"] = "github"
    prospect_data = _parse_json_fields(
        prospect_data, {"pain_points", "personalization_hooks", "research_sources", "raw_research"}
    )

    qual_data = _make_qual_row()
    qual_data = _parse_json_fields(qual_data, {"criterion_scores"})

    state = _make_state()
    state["prospect_brief"] = prospect_data
    state["qualification_brief"] = qual_data

    skip_result = {
        "comment_body": None,
        "repo": "org/repo",
        "issue_url": "https://github.com/org/repo/issues/1",
        "personalization_hook": "GitHub comment skipped.",
        "skip": True,
    }
    email_result = {
        "subject": "Fallback Subject",
        "body": "Fallback email body.",
        "personalization_hook": "Email fallback hook.",
    }

    with patch(
        "adela_outbound.agents.drafting.nodes.draft_github_comment",
        new_callable=AsyncMock,
        return_value=skip_result,
    ), patch(
        "adela_outbound.agents.drafting.nodes.draft_email",
        new_callable=AsyncMock,
        return_value=email_result,
    ), patch(
        "adela_outbound.agents.drafting.nodes.AsyncAnthropic"
    ), patch(
        "adela_outbound.agents.drafting.nodes.aiosqlite.connect"
    ) as mock_connect:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.commit = AsyncMock()
        name_mock = AsyncMock()
        name_mock.fetchone = AsyncMock(return_value=None)

        async def execute_side_effect(sql, params=None):
            if "discovery_queue" in sql:
                return name_mock
            return AsyncMock()

        mock_conn.execute = execute_side_effect

        ctx_mgr = AsyncMock()
        ctx_mgr.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx_mgr.__aexit__ = AsyncMock(return_value=False)
        mock_connect.return_value = ctx_mgr

        result = await channel_router(state)

    assert result["outreach_package"]["primary_channel"] == "email"
    assert result["outreach_package"]["creative_action"]["proposed"] is False
    assert result["outreach_package"]["primary_draft"]["personalization_hook"] == "Email fallback hook."


@pytest.mark.asyncio
async def test_channel_router_linkedin_with_email_secondary():
    """LinkedIn channel produces primary + email secondary draft."""
    prospect_data = _make_prospect_row()
    prospect_data["recommended_channel"] = "linkedin"
    prospect_data = _parse_json_fields(
        prospect_data, {"pain_points", "personalization_hooks", "research_sources", "raw_research"}
    )

    qual_data = _make_qual_row()
    qual_data = _parse_json_fields(qual_data, {"criterion_scores"})

    state = _make_state()
    state["prospect_brief"] = prospect_data
    state["qualification_brief"] = qual_data

    linkedin_result = {
        "body": "LinkedIn message.",
        "personalization_hook": "LinkedIn hook.",
    }
    email_result = {
        "subject": "Secondary Subject",
        "body": "Secondary email.",
        "personalization_hook": "Email hook.",
    }

    with patch(
        "adela_outbound.agents.drafting.nodes.draft_linkedin",
        new_callable=AsyncMock,
        return_value=linkedin_result,
    ), patch(
        "adela_outbound.agents.drafting.nodes.draft_email",
        new_callable=AsyncMock,
        return_value=email_result,
    ), patch(
        "adela_outbound.agents.drafting.nodes.AsyncAnthropic"
    ), patch(
        "adela_outbound.agents.drafting.nodes.aiosqlite.connect"
    ) as mock_connect:
        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.commit = AsyncMock()
        name_mock = AsyncMock()
        name_mock.fetchone = AsyncMock(return_value=None)

        async def execute_side_effect(sql, params=None):
            if "discovery_queue" in sql:
                return name_mock
            return AsyncMock()

        mock_conn.execute = execute_side_effect

        ctx_mgr = AsyncMock()
        ctx_mgr.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx_mgr.__aexit__ = AsyncMock(return_value=False)
        mock_connect.return_value = ctx_mgr

        result = await channel_router(state)

    assert result["outreach_package"]["primary_channel"] == "linkedin"
    assert len(result["outreach_package"]["secondary_drafts"]) == 1
    assert result["outreach_package"]["secondary_drafts"][0]["subject"] == "Secondary Subject"


def test_parse_json_fields():
    row = {
        "name": "test",
        "data": '["a", "b"]',
        "count": 5,
    }
    result = _parse_json_fields(row, {"data"})
    assert result["data"] == ["a", "b"]
    assert result["count"] == 5
    assert result["name"] == "test"
