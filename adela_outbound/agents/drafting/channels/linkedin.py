from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

from adela_outbound.db.contracts import ProspectBrief, QualificationBrief

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are writing a LinkedIn connection note or InMail on behalf of Justin Hou, "
    "co-founder of Adela (adela.dev). Rules: (1) Maximum 300 characters total — this "
    "is a hard limit. (2) Single specific hook — reference something concrete about "
    "what they are building. (3) No ask in the first message. No call-to-action, no "
    "meeting request. (4) Never open with: I came across your profile / I noticed you / "
    "Hope you are doing well. (5) After the message, on a new line write HOOK: followed "
    "by one sentence explaining what specific detail you anchored on."
)


def _build_user_message(
    brief: ProspectBrief,
    qual_brief: QualificationBrief,
    redraft_feedback: str | None = None,
) -> str:
    parts = [
        f"Company: {brief.company_id}",
        f"Research summary: {brief.summary}",
        f"Adela relevance: {brief.adela_relevance}",
        f"Fit tier: {qual_brief.fit_tier}",
    ]
    if redraft_feedback:
        parts.append(
            f"Previous draft was rejected. Feedback: {redraft_feedback}"
        )
    return "\n".join(parts)


def _parse_response(text: str) -> tuple[str, str]:
    """Parse response into (body, hook). Returns body and hook strings."""
    if "HOOK:" in text:
        body_part, hook_part = text.split("HOOK:", 1)
        return body_part.strip(), hook_part.strip()
    return text.strip(), text.split(".")[0] + "." if "." in text else text.strip()


async def draft_linkedin(
    brief: ProspectBrief,
    qual_brief: QualificationBrief,
    client: AsyncAnthropic,
    redraft_feedback: str | None = None,
) -> dict:
    """Generate a LinkedIn connection note grounded in the prospect brief."""
    try:
        user_msg = _build_user_message(brief, qual_brief, redraft_feedback)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text  # type: ignore[union-attr]
        body, hook = _parse_response(text)

        # Character count validation
        if len(body) > 300:
            retry_msg = (
                f"{user_msg}\n\nYour previous draft was {len(body)} characters. "
                "LinkedIn has a 300 character hard limit. Rewrite to be 300 "
                "characters or fewer."
            )
            response2 = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": retry_msg}],
            )
            text2 = response2.content[0].text  # type: ignore[union-attr]
            body, hook = _parse_response(text2)
            if len(body) > 300:
                raise ValueError(
                    f"LinkedIn draft for {brief.company_id} exceeded 300 chars "
                    f"after retry: {len(body)} chars"
                )

        return {"body": body, "personalization_hook": hook}

    except ValueError:
        # Re-raise ValueError (char limit) — don't catch as fallback
        raise
    except Exception:
        # Hardcoded fallback for API failures
        return {
            "body": (
                f"Building {brief.company_id}? What you're working on with "
                "deployment context maps closely to what we're solving at Adela. "
                "Would love to connect."
            ),
            "personalization_hook": "Fallback draft — Claude unavailable.",
        }
