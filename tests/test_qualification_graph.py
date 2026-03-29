from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import aiosqlite

from adela_outbound.db.schemas import CREATE_TABLES_SQL
from adela_outbound.agents.qualification.icp import SEED_ICP_CRITERIA


async def _setup_db(db_path: str) -> None:
    """Create tables and insert test data."""
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(CREATE_TABLES_SQL)

        # Insert discovery_queue entry
        await conn.execute(
            "INSERT INTO discovery_queue "
            "(id, company_name, website, twitter_handle, github_handle, "
            "linkedin_url, discovery_source, discovery_signal, pre_score, "
            "status, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "qual-test-001",
                "FDE Tools",
                "https://fdetools.io",
                "@fdetools",
                "fdetools",
                "",
                "github",
                "Forward deployed engineering tooling",
                0.8,
                "researched",
                now,
                now,
            ),
        )

        # Insert prospect_brief
        await conn.execute(
            "INSERT INTO prospect_briefs "
            "(id, company_id, summary, current_focus, pain_points, "
            "adela_relevance, personalization_hooks, creative_outreach_opportunity, "
            "creative_outreach_detail, recommended_channel, research_sources, "
            "confidence_score, raw_research, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                "qual-test-001",
                "FDE Tools builds forward deployed engineering tooling for enterprise "
                "clients scaling across multiple regulated industries.",
                "Scaling from 3 to 12 enterprise fintech clients.",
                json.dumps(
                    [
                        "Context fragmentation across client deployments",
                        "No SOP versioning for agent configurations",
                    ]
                ),
                "Direct ICP match — scaling regulated enterprise deployments "
                "with no governance tooling.",
                json.dumps(
                    ["Open GitHub issue about multi-tenant context isolation"]
                ),
                1,
                "GitHub issue #5",
                "github",
                json.dumps(["https://fdetools.io"]),
                0.8,
                "{}",
                now,
            ),
        )

        # Seed ICP definition
        await conn.execute(
            "INSERT INTO icp_definition (id, version, criteria, created_at) "
            "VALUES (?,?,?,?)",
            (str(uuid.uuid4()), 1, json.dumps(SEED_ICP_CRITERIA), now),
        )

        await conn.commit()


def _make_strong_scores() -> list:
    """Return 8 criterion scores all with score=2 (strong signals)."""
    return [
        {
            "criterion_id": c["id"],
            "score": 2,
            "evidence": "Strong signal",
            "confidence": 0.8,
        }
        for c in SEED_ICP_CRITERIA
    ]


def _make_zero_scores() -> list:
    """Return 8 criterion scores all with score=0 (disqualified)."""
    return [
        {
            "criterion_id": c["id"],
            "score": 0,
            "evidence": "No evidence",
            "confidence": 0.5,
        }
        for c in SEED_ICP_CRITERIA
    ]


def _mock_claude_why_now():
    """Return a mock AsyncAnthropic that returns why_now JSON."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = json.dumps(
        {
            "why_now": "FDE Tools is scaling from 3 to 12 fintech clients right now.",
            "suggested_outreach_angle": "Multi-tenant context isolation pain point.",
        }
    )
    mock_response.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    return mock_client


async def test_hitl_pause_and_resume_approval(tmp_path):
    """Full graph run: pause at HITL, resume with approval, verify DB."""
    db_path = str(tmp_path / "test_qual.db")
    await _setup_db(db_path)

    with (
        patch(
            "adela_outbound.db.connection.config"
        ) as mock_conn_config,
        patch(
            "adela_outbound.agents.qualification.nodes.config"
        ) as mock_nodes_config,
        patch(
            "adela_outbound.agents.qualification.scorer.config"
        ) as mock_scorer_config,
        patch(
            "adela_outbound.agents.qualification.nodes.score_all_criteria",
            new_callable=AsyncMock,
            return_value=_make_strong_scores(),
        ),
        patch(
            "adela_outbound.agents.qualification.nodes.AsyncAnthropic",
            return_value=_mock_claude_why_now(),
        ),
        patch(
            "adela_outbound.agents.qualification.nodes.broadcast",
            new_callable=AsyncMock,
        ),
    ):
        mock_conn_config.DB_PATH = db_path
        mock_nodes_config.DB_PATH = db_path
        mock_nodes_config.ANTHROPIC_API_KEY = "test"
        mock_scorer_config.ANTHROPIC_API_KEY = "test"

        # Need fresh graph for each test to avoid checkpoint collisions
        from adela_outbound.agents.qualification.graph import (
            run_qualification,
            resume_qualification,
            qualification_graph,
        )

        # Run graph — should pause at HITL
        result = await run_qualification("qual-test-001")
        assert result is not None

        # Verify graph is paused at hitl_gate
        config = {"configurable": {"thread_id": "qual-test-001"}}
        state = qualification_graph.get_state(config)
        assert state is not None
        assert "hitl_gate" in (state.next or ()), (
            f"Expected graph to be paused at hitl_gate, got next={state.next}"
        )

        # Verify brief was written to DB before pause
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT status FROM qualification_briefs WHERE company_id = ?",
                ["qual-test-001"],
            )
            row = await cursor.fetchone()
            assert row is not None, "qualification_brief should exist before HITL pause"
            assert row[0] == "pending_review"

        # Resume with approval
        result2 = await resume_qualification(
            "qual-test-001", decision="approved"
        )

        # Verify DB updated after approval
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT status FROM qualification_briefs WHERE company_id = ?",
                ["qual-test-001"],
            )
            row = await cursor.fetchone()
            assert row[0] == "approved"

            cursor2 = await conn.execute(
                "SELECT status FROM discovery_queue WHERE id = ?",
                ["qual-test-001"],
            )
            row2 = await cursor2.fetchone()
            assert row2[0] == "qualified"


async def test_auto_disqualify(tmp_path):
    """Graph auto-rejects when all scores are 0 (fit_tier=disqualified)."""
    db_path = str(tmp_path / "test_qual_auto.db")
    now = datetime.now(timezone.utc).isoformat()

    # Set up DB with a second company
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(CREATE_TABLES_SQL)

        await conn.execute(
            "INSERT INTO discovery_queue "
            "(id, company_name, website, twitter_handle, github_handle, "
            "linkedin_url, discovery_source, discovery_signal, pre_score, "
            "status, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "qual-test-002",
                "Bad Fit Corp",
                "https://badfit.com",
                "",
                "",
                "",
                "twitter",
                "Generic SaaS company",
                0.2,
                "researched",
                now,
                now,
            ),
        )

        await conn.execute(
            "INSERT INTO prospect_briefs "
            "(id, company_id, summary, current_focus, pain_points, "
            "adela_relevance, personalization_hooks, creative_outreach_opportunity, "
            "creative_outreach_detail, recommended_channel, research_sources, "
            "confidence_score, raw_research, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                "qual-test-002",
                "Bad Fit Corp sells generic SaaS to small businesses.",
                "Expanding into retail.",
                json.dumps(["Generic pain point"]),
                "No clear Adela relevance.",
                json.dumps([]),
                0,
                None,
                "email",
                json.dumps([]),
                0.3,
                "{}",
                now,
            ),
        )

        await conn.execute(
            "INSERT INTO icp_definition (id, version, criteria, created_at) "
            "VALUES (?,?,?,?)",
            (str(uuid.uuid4()), 1, json.dumps(SEED_ICP_CRITERIA), now),
        )

        await conn.commit()

    with (
        patch(
            "adela_outbound.db.connection.config"
        ) as mock_conn_config,
        patch(
            "adela_outbound.agents.qualification.nodes.config"
        ) as mock_nodes_config,
        patch(
            "adela_outbound.agents.qualification.scorer.config"
        ) as mock_scorer_config,
        patch(
            "adela_outbound.agents.qualification.nodes.score_all_criteria",
            new_callable=AsyncMock,
            return_value=_make_zero_scores(),
        ),
        patch(
            "adela_outbound.agents.qualification.nodes.AsyncAnthropic",
            return_value=_mock_claude_why_now(),
        ),
        patch(
            "adela_outbound.agents.qualification.nodes.broadcast",
            new_callable=AsyncMock,
        ),
    ):
        mock_conn_config.DB_PATH = db_path
        mock_nodes_config.DB_PATH = db_path
        mock_nodes_config.ANTHROPIC_API_KEY = "test"
        mock_scorer_config.ANTHROPIC_API_KEY = "test"

        from adela_outbound.agents.qualification.graph import (
            run_qualification,
            qualification_graph,
        )

        # Run graph — should auto-disqualify without pausing
        result = await run_qualification("qual-test-002")

        # Verify graph is NOT paused (completed)
        config = {"configurable": {"thread_id": "qual-test-002"}}
        state = qualification_graph.get_state(config)
        assert not state.next, (
            f"Expected graph to be completed (no next nodes), got next={state.next}"
        )

        # Verify DB: qualification_brief auto_rejected
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT status FROM qualification_briefs WHERE company_id = ?",
                ["qual-test-002"],
            )
            row = await cursor.fetchone()
            assert row is not None, "qualification_brief should exist for auto-rejected"
            assert row[0] == "auto_rejected"

            # Verify discovery_queue status = disqualified
            cursor2 = await conn.execute(
                "SELECT status FROM discovery_queue WHERE id = ?",
                ["qual-test-002"],
            )
            row2 = await cursor2.fetchone()
            assert row2[0] == "disqualified"
