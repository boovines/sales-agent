import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from adela_outbound.agents.drafting.channels.github import draft_github_comment
from adela_outbound.db.contracts import ProspectBrief


def _make_brief() -> ProspectBrief:
    return ProspectBrief(
        id="pb-1",
        company_id="test-co",
        summary="Building a multi-tenant deployment platform for enterprise SaaS.",
        current_focus="Scaling configuration management across clients.",
        pain_points=["Per-client config overhead", "Context isolation"],
        adela_relevance="Adela's SOP versioning maps directly to their multi-tenant context isolation.",
        personalization_hooks=["Multi-tenant deployment challenge"],
        creative_outreach_opportunity=True,
        creative_outreach_detail='[{"issue_url": "https://github.com/test-co/repo/issues/47", "issue_title": "Context isolation bug", "issue_body": "We need better isolation", "repo": "test-co/repo"}]',
        recommended_channel="github",
        research_sources=["https://example.com"],
        confidence_score=0.85,
        raw_research={},
        created_at=datetime.now(),
    )


def _make_issue_detail() -> dict:
    return {
        "issue_url": "https://github.com/test-co/repo/issues/47",
        "issue_title": "Context isolation bug in multi-tenant mode",
        "issue_body": "When deploying across multiple tenants, context leaks between sessions.",
        "repo": "test-co/repo",
    }


def _mock_client(response_text: str) -> AsyncMock:
    client = AsyncMock()
    message = MagicMock()
    message.content = [MagicMock(text=response_text)]
    client.messages.create = AsyncMock(return_value=message)
    return client


@pytest.mark.asyncio
async def test_draft_github_skip():
    """Claude returns SKIP — result should have skip=True and comment_body=None."""
    client = _mock_client("SKIP")
    brief = _make_brief()
    issue = _make_issue_detail()

    result = await draft_github_comment(brief, issue, client)

    assert result["skip"] is True
    assert result["comment_body"] is None
    assert result["repo"] == "test-co/repo"
    assert result["issue_url"] == "https://github.com/test-co/repo/issues/47"
    assert "skipped" in result["personalization_hook"]
    client.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_draft_github_skip_case_insensitive():
    """SKIP detection is case-insensitive."""
    client = _mock_client("  skip  ")
    brief = _make_brief()
    issue = _make_issue_detail()

    result = await draft_github_comment(brief, issue, client)

    assert result["skip"] is True
    assert result["comment_body"] is None


@pytest.mark.asyncio
async def test_draft_github_real_comment():
    """Claude returns a real comment — result should have skip=False."""
    comment = (
        "This looks like a session context leaking through shared state. "
        "Try scoping your context manager per-tenant using a factory pattern."
    )
    client = _mock_client(comment)
    brief = _make_brief()
    issue = _make_issue_detail()

    result = await draft_github_comment(brief, issue, client)

    assert result["skip"] is False
    assert result["comment_body"] == comment
    assert result["repo"] == "test-co/repo"
    assert result["issue_url"] == "https://github.com/test-co/repo/issues/47"
    assert "Context isolation bug" in result["personalization_hook"]
    client.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_draft_github_fallback_on_exception():
    """API failure returns skip=True with failure hook."""
    client = AsyncMock()
    client.messages.create = AsyncMock(side_effect=Exception("API down"))

    brief = _make_brief()
    issue = _make_issue_detail()

    result = await draft_github_comment(brief, issue, client)

    assert result["skip"] is True
    assert result["comment_body"] is None
    assert "Claude unavailable" in result["personalization_hook"]
