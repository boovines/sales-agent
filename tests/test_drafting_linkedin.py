import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from adela_outbound.agents.drafting.channels.linkedin import draft_linkedin, _parse_response
from adela_outbound.db.contracts import ProspectBrief, QualificationBrief


def _make_brief() -> ProspectBrief:
    return ProspectBrief(
        id="pb-1",
        company_id="test-co",
        summary="Building a multi-tenant deployment platform for enterprise SaaS.",
        current_focus="Scaling configuration management across clients.",
        pain_points=["Per-client config overhead", "Context isolation"],
        adela_relevance="Adela's SOP versioning maps directly to their multi-tenant context isolation.",
        personalization_hooks=["Multi-tenant deployment challenge"],
        creative_outreach_opportunity=False,
        creative_outreach_detail=None,
        recommended_channel="linkedin",
        research_sources=["https://example.com"],
        confidence_score=0.85,
        raw_research={},
        created_at=datetime.now(),
    )


def _make_qual_brief() -> QualificationBrief:
    return QualificationBrief(
        id="qb-1",
        company_id="test-co",
        fit_score=0.9,
        fit_tier="Tier 1",
        criterion_scores={"technical_fit": 0.95},
        why_now="Actively hiring for deployment engineering roles.",
        suggested_outreach_angle="Multi-tenant context isolation.",
        status="approved",
        created_at=datetime.now(),
    )


def _mock_client(response_text: str) -> AsyncMock:
    client = AsyncMock()
    message = MagicMock()
    message.content = [MagicMock(text=response_text)]
    client.messages.create = AsyncMock(return_value=message)
    return client


@pytest.mark.asyncio
async def test_draft_linkedin_parses_body_and_hook():
    text = "Your multi-tenant work is fascinating — the context isolation problem is exactly what we solve at Adela.\n\nHOOK: Anchored on multi-tenant context isolation."
    client = _mock_client(text)
    brief = _make_brief()
    qual = _make_qual_brief()

    result = await draft_linkedin(brief, qual, client)

    assert len(result["body"]) <= 300
    assert result["personalization_hook"] == "Anchored on multi-tenant context isolation."
    assert "body" in result
    assert "subject" not in result  # LinkedIn has no subject field
    client.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_draft_linkedin_raises_on_char_limit_exceeded():
    long_body = "x" * 400 + "\n\nHOOK: test hook"
    client = AsyncMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=long_body)]
    client.messages.create = AsyncMock(return_value=msg)

    brief = _make_brief()
    qual = _make_qual_brief()

    with pytest.raises(ValueError, match="exceeded 300 chars after retry"):
        await draft_linkedin(brief, qual, client)

    # Should have been called twice (initial + retry)
    assert client.messages.create.await_count == 2


@pytest.mark.asyncio
async def test_draft_linkedin_retry_succeeds():
    long_body = "x" * 400 + "\n\nHOOK: long hook"
    short_body = "Short LinkedIn note.\n\nHOOK: final hook"

    client = AsyncMock()
    msg_long = MagicMock()
    msg_long.content = [MagicMock(text=long_body)]
    msg_short = MagicMock()
    msg_short.content = [MagicMock(text=short_body)]
    client.messages.create = AsyncMock(side_effect=[msg_long, msg_short])

    brief = _make_brief()
    qual = _make_qual_brief()

    result = await draft_linkedin(brief, qual, client)

    assert len(result["body"]) <= 300
    assert result["personalization_hook"] == "final hook"
    assert client.messages.create.await_count == 2


@pytest.mark.asyncio
async def test_draft_linkedin_fallback_on_exception():
    client = AsyncMock()
    client.messages.create = AsyncMock(side_effect=Exception("API down"))

    brief = _make_brief()
    qual = _make_qual_brief()

    result = await draft_linkedin(brief, qual, client)

    assert "Fallback draft" in result["personalization_hook"]
    assert "body" in result


def test_parse_response_with_hook():
    body, hook = _parse_response("Short note here.\n\nHOOK: The hook detail.")
    assert body == "Short note here."
    assert hook == "The hook detail."


def test_parse_response_without_hook():
    body, hook = _parse_response("Just a body with no hook marker.")
    assert body == "Just a body with no hook marker."
    # Fallback: first sentence
    assert hook == "Just a body with no hook marker."
