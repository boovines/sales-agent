import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from adela_outbound.agents.drafting.channels.email import draft_email, _parse_response
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
        recommended_channel="email",
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
async def test_draft_email_parses_subject_and_hook():
    text = (
        "Subject: Test\n\n"
        "Body here under 150 words.\n\n"
        "HOOK: Anchored on their multi-tenant deployment challenge."
    )
    client = _mock_client(text)
    brief = _make_brief()
    qual = _make_qual_brief()

    result = await draft_email(brief, qual, client)

    assert result["subject"] == "Test"
    assert result["personalization_hook"] == "Anchored on their multi-tenant deployment challenge."
    assert "Body here" in result["body"]
    client.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_draft_email_no_hook_fallback():
    text = "Subject: Hello\n\nFirst sentence here. Second sentence."
    client = _mock_client(text)
    brief = _make_brief()
    qual = _make_qual_brief()

    result = await draft_email(brief, qual, client)

    assert result["subject"] == "Hello"
    # Fallback: first sentence used as hook
    assert result["personalization_hook"] == "First sentence here."


@pytest.mark.asyncio
async def test_draft_email_word_count_retry():
    long_body = "Subject: Long\n\n" + " ".join(["word"] * 200) + "\n\nHOOK: test hook"
    short_body = "Subject: Short\n\nShort email body.\n\nHOOK: final hook"

    client = AsyncMock()
    msg_long = MagicMock()
    msg_long.content = [MagicMock(text=long_body)]
    msg_short = MagicMock()
    msg_short.content = [MagicMock(text=short_body)]
    client.messages.create = AsyncMock(side_effect=[msg_long, msg_short])

    brief = _make_brief()
    qual = _make_qual_brief()

    result = await draft_email(brief, qual, client)

    assert result["personalization_hook"] == "final hook"
    assert client.messages.create.await_count == 2


@pytest.mark.asyncio
async def test_draft_email_fallback_on_exception():
    client = AsyncMock()
    client.messages.create = AsyncMock(side_effect=Exception("API down"))

    brief = _make_brief()
    qual = _make_qual_brief()

    result = await draft_email(brief, qual, client)

    assert "Fallback draft" in result["personalization_hook"]
    assert result["subject"] == "Context infrastructure for test-co"


def test_parse_response_with_hook():
    text = "Subject: Infra\n\nGreat email body.\n\nHOOK: The hook detail."
    result = _parse_response(text)
    assert result["subject"] == "Infra"
    assert result["personalization_hook"] == "The hook detail."


def test_parse_response_without_subject():
    text = "Just a body with no subject.\n\nHOOK: Some hook."
    result = _parse_response(text)
    assert result["subject"] is None
    assert result["body"] == "Just a body with no subject."
    assert result["personalization_hook"] == "Some hook."
