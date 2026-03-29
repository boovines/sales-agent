from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adela_outbound.agents.drafting.sender import (
    post_github_comment,
    send_email,
    send_linkedin,
)

SENDER_MOD = "adela_outbound.agents.drafting.sender"


def _mock_aiosqlite(cnt: int):
    """Return a patched aiosqlite.connect that reports the given outreach_log count."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = {"cnt": cnt}
    mock_conn.execute.return_value = mock_cursor
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    return patch(f"{SENDER_MOD}.aiosqlite.connect", return_value=mock_conn)


def _mock_toolset(return_value=None, side_effect=None):
    """Return a patched _get_toolset that returns a mock ComposioToolSet."""
    mock_ts = MagicMock()
    if side_effect:
        mock_ts.execute_action.side_effect = side_effect
    else:
        mock_ts.execute_action.return_value = return_value or {}
    return patch(f"{SENDER_MOD}._get_toolset", return_value=mock_ts)


def _mock_action():
    """Return a patched _get_action that returns a sentinel string."""
    return patch(f"{SENDER_MOD}._get_action", return_value="MOCK_ACTION")


# ---------------------------------------------------------------------------
# send_email tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_email_success():
    """send_email succeeds when cap not reached and Composio returns ok."""
    with _mock_aiosqlite(0), _mock_toolset({"messageId": "msg-123"}), _mock_action():
        result = await send_email("co-1", "test@example.com", "Subject", "Body")

    assert result["success"] is True
    assert result["message_id"] == "msg-123"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_send_email_daily_cap_reached():
    """send_email returns failure when daily cap is reached."""
    with _mock_aiosqlite(20):
        result = await send_email("co-1", "test@example.com", "Subject", "Body")

    assert result["success"] is False
    assert "Daily cap" in result["error"]


@pytest.mark.asyncio
async def test_send_email_composio_error():
    """send_email catches Composio exceptions gracefully."""
    with (
        _mock_aiosqlite(0),
        _mock_toolset(side_effect=Exception("Composio error")),
        _mock_action(),
    ):
        result = await send_email("co-1", "test@example.com", "Subject", "Body")

    assert result["success"] is False
    assert result["error"] == "Composio error"


# ---------------------------------------------------------------------------
# post_github_comment tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_github_comment_success():
    """post_github_comment succeeds with valid issue URL."""
    with _mock_aiosqlite(0), _mock_toolset({"id": 456}), _mock_action():
        result = await post_github_comment(
            "co-1", "https://github.com/owner/repo/issues/42", "Helpful comment"
        )

    assert result["success"] is True
    assert result["comment_id"] == 456


@pytest.mark.asyncio
async def test_post_github_comment_invalid_url():
    """post_github_comment returns error for invalid issue URL."""
    with _mock_aiosqlite(0):
        result = await post_github_comment("co-1", "https://example.com/bad", "comment")

    assert result["success"] is False
    assert "Invalid issue URL" in result["error"]


@pytest.mark.asyncio
async def test_post_github_comment_daily_cap():
    """post_github_comment blocked by daily cap."""
    with _mock_aiosqlite(5):
        result = await post_github_comment(
            "co-1", "https://github.com/owner/repo/issues/42", "comment"
        )

    assert result["success"] is False
    assert "Daily cap" in result["error"]


# ---------------------------------------------------------------------------
# send_linkedin tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_linkedin_failure_returns_manual_message():
    """send_linkedin returns manual action message on Composio failure."""
    with (
        _mock_aiosqlite(0),
        _mock_toolset(side_effect=Exception("Browser tool failed")),
        _mock_action(),
    ):
        result = await send_linkedin("co-1", "https://linkedin.com/in/test", "Hello")

    assert result["success"] is False
    assert "manual action" in result["error"]


@pytest.mark.asyncio
async def test_send_linkedin_daily_cap():
    """send_linkedin blocked by daily cap."""
    with _mock_aiosqlite(10):
        result = await send_linkedin("co-1", "https://linkedin.com/in/test", "Hello")

    assert result["success"] is False
    assert "Daily cap" in result["error"]
