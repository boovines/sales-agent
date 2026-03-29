from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

from adela_outbound.db.contracts import ProspectBrief

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior engineer reviewing a GitHub issue. You are considering "
    "whether to leave a helpful comment. Rules: (1) Your comment must provide "
    "genuine value — a specific diagnosis of the root cause, a concrete suggestion "
    "with a code snippet or approach, or a directly relevant resource or library. "
    "(2) Adela (the product you work on) may be mentioned as a potential solution "
    "if and only if it directly addresses the issue. If it does not directly address "
    "the issue, do not mention it at all. (3) Tone: engineer to engineer. Show you "
    "read the issue. (4) If you cannot write a genuinely helpful comment — if the "
    "issue is unclear, already resolved, or outside your expertise — respond with "
    "exactly the word SKIP and nothing else. Do not write a promotional comment. "
    "A promotional comment is worse than no comment."
)


def _build_skip_result(issue_detail: dict, hook: str) -> dict:
    """Build a skip result dict."""
    return {
        "comment_body": None,
        "repo": issue_detail["repo"],
        "issue_url": issue_detail["issue_url"],
        "personalization_hook": hook,
        "skip": True,
    }


async def draft_github_comment(
    brief: ProspectBrief,
    issue_detail: dict,
    client: AsyncAnthropic,
) -> dict:
    """Draft a genuinely helpful GitHub comment for a detected opportunity issue."""
    try:
        user_msg = (
            f"Issue title: {issue_detail['issue_title']}\n"
            f"Issue body: {issue_detail['issue_body']}\n"
            f"Repo: {issue_detail['repo']}\n"
            f"Adela context: {brief.adela_relevance}"
        )
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        response_text = response.content[0].text.strip()  # type: ignore[union-attr]

        if response_text.upper() == "SKIP":
            return _build_skip_result(
                issue_detail,
                "GitHub comment skipped — Claude could not write a genuinely helpful comment.",
            )

        return {
            "comment_body": response_text,
            "repo": issue_detail["repo"],
            "issue_url": issue_detail["issue_url"],
            "personalization_hook": (
                f"GitHub opportunity: {issue_detail['issue_title']} "
                f"in {issue_detail['repo']}"
            ),
            "skip": False,
        }

    except Exception:
        logger.error(
            f"GitHub draft failed for {brief.company_id}: Claude unavailable"
        )
        return _build_skip_result(
            issue_detail,
            "GitHub draft failed — Claude unavailable.",
        )
