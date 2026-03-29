from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import aiosqlite

from adela_outbound.config import config

logger = logging.getLogger(__name__)


async def _check_daily_cap(channel: str, cap: int) -> bool:
    """Return True if the daily cap for this channel has been reached."""
    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM outreach_log WHERE channel=? AND DATE(sent_at)=DATE('now') AND success=1",
            (channel,),
        )
        row = await cursor.fetchone()
        count = dict(row)["cnt"] if row else 0
    return count >= cap


def _get_toolset():
    """Lazy import and instantiation of ComposioToolSet to avoid import-time failures on Python 3.9."""
    from composio import ComposioToolSet  # type: ignore[import-untyped]

    return ComposioToolSet(api_key=config.COMPOSIO_API_KEY)


def _get_action(name: str):
    """Lazy import of Composio Action enum."""
    from composio import Action  # type: ignore[import-untyped,attr-defined]

    return getattr(Action, name)


async def send_email(company_id: str, to_address: str, subject: str, body: str) -> dict:
    """Send email via Composio Gmail with daily rate limit enforcement."""
    if await _check_daily_cap("email", config.DAILY_EMAIL_CAP):
        return {
            "success": False,
            "message_id": None,
            "error": f"Daily cap reached for email ({config.DAILY_EMAIL_CAP}/day)",
        }

    try:
        toolset = _get_toolset()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: toolset.execute_action(
                action=_get_action("GMAIL_SEND_EMAIL"),
                params={
                    "recipient_email": to_address,
                    "subject": subject,
                    "body": body,
                    "sender_email": config.GMAIL_SENDER_ADDRESS,
                },
            ),
        )
        return {
            "success": True,
            "message_id": result.get("messageId") if isinstance(result, dict) else None,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Composio email send failed for {company_id}: {e}")
        return {"success": False, "message_id": None, "error": str(e)}


async def post_github_comment(company_id: str, issue_url: str, body: str) -> dict:
    """Post GitHub comment via Composio with daily rate limit enforcement."""
    if await _check_daily_cap("github", config.DAILY_GITHUB_CAP):
        return {
            "success": False,
            "comment_id": None,
            "error": f"Daily cap reached for github ({config.DAILY_GITHUB_CAP}/day)",
        }

    # Parse owner, repo, issue_number from URL
    # Pattern: https://github.com/{owner}/{repo}/issues/{number}
    try:
        parsed = urlparse(issue_url)
        parts = parsed.path.strip("/").split("/")
        owner = parts[0]
        repo = parts[1]
        issue_number = int(parts[3])
    except (IndexError, ValueError) as e:
        return {"success": False, "comment_id": None, "error": f"Invalid issue URL: {issue_url} ({e})"}

    try:
        toolset = _get_toolset()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: toolset.execute_action(
                action=_get_action("GITHUB_CREATE_ISSUE_COMMENT"),
                params={
                    "owner": owner,
                    "repo": repo,
                    "issue_number": issue_number,
                    "body": body,
                },
            ),
        )
        return {
            "success": True,
            "comment_id": result.get("id") if isinstance(result, dict) else None,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Composio GitHub comment failed for {company_id}: {e}")
        return {"success": False, "comment_id": None, "error": str(e)}


async def send_linkedin(company_id: str, profile_url: str, body: str) -> dict:
    """Send LinkedIn message via Composio browser tool — best effort."""
    if await _check_daily_cap("linkedin", config.DAILY_LINKEDIN_CAP):
        return {
            "success": False,
            "error": f"Daily cap reached for linkedin ({config.DAILY_LINKEDIN_CAP}/day)",
        }

    try:
        toolset = _get_toolset()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: toolset.execute_action(
                action=_get_action("LINKEDIN_SEND_MESSAGE"),
                params={
                    "profile_url": profile_url,
                    "message": body,
                },
            ),
        )
        return {"success": True, "error": None}
    except Exception as e:
        logger.warning(f"LinkedIn send failed for {company_id}: {e}")
        return {
            "success": False,
            "error": "LinkedIn send requires manual action — copy draft from dashboard",
        }
