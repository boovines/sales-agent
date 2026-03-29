from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def send_email(company_id: str, to_address: str, subject: str, body: str) -> dict:
    """Send email via Composio. Stub — full implementation in US-007."""
    logger.warning("send_email not yet implemented (US-007)")
    return {"success": False, "message_id": None, "error": "send_email not yet implemented"}


async def post_github_comment(company_id: str, issue_url: str, body: str) -> dict:
    """Post GitHub comment via Composio. Stub — full implementation in US-007."""
    logger.warning("post_github_comment not yet implemented (US-007)")
    return {"success": False, "comment_id": None, "error": "post_github_comment not yet implemented"}


async def send_linkedin(company_id: str, profile_url: str, body: str) -> dict:
    """Send LinkedIn message via Composio. Stub — full implementation in US-007."""
    logger.warning("send_linkedin not yet implemented (US-007)")
    return {"success": False, "error": "send_linkedin not yet implemented"}
