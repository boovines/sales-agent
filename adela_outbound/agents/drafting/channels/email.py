from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

from adela_outbound.db.contracts import ProspectBrief, QualificationBrief

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a cold outreach specialist writing on behalf of Justin Hou, "
    "co-founder of Adela (adela.dev). Adela is the context and governance layer "
    "for services companies deploying bespoke technical work across enterprise "
    "clients. Write a cold email to a founder or operator at the target company. "
    "Rules: (1) First sentence must reference a SPECIFIC detail from the research "
    "brief — not the company name alone, but something specific about what they are "
    "building or a specific pain point. (2) Body must be 150 words or fewer. Count "
    "words carefully. (3) Never open with: I hope this finds you well / My name is / "
    "I wanted to reach out / Just following up. (4) One CTA only at the end — specific "
    "and low-friction (e.g., \"Worth a 20-min call?\" not \"Please schedule a meeting "
    "at your earliest convenience\"). (5) Tone: knowledgeable peer, confident, specific, "
    "not salesy. (6) After the email, on a new line, write HOOK: followed by one sentence "
    "explaining exactly what specific detail from the brief you anchored the email on. "
    "This hook sentence is mandatory."
)


def _build_user_message(
    brief: ProspectBrief,
    qual_brief: QualificationBrief,
    redraft_feedback: str | None = None,
) -> str:
    parts = [
        f"Company ID: {brief.company_id}",
        f"Research summary: {brief.summary}",
        f"Current focus: {brief.current_focus}",
        f"Adela relevance: {brief.adela_relevance}",
        f"Fit tier: {qual_brief.fit_tier}",
    ]
    if redraft_feedback:
        parts.append(
            f"Previous draft was rejected. Feedback from reviewer: {redraft_feedback}. "
            "Address this feedback in the new draft."
        )
    return "\n".join(parts)


def _parse_response(text: str) -> dict:
    hook = None
    if "HOOK:" in text:
        body_part, hook_part = text.split("HOOK:", 1)
        body_raw = body_part.strip()
        hook = hook_part.strip()
    else:
        body_raw = text.strip()

    # Extract subject if present
    subject = None
    body = body_raw
    if body_raw.lower().startswith("subject:"):
        lines = body_raw.split("\n", 1)
        subject = lines[0].split(":", 1)[1].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

    # Fallback hook: first sentence of body (after subject extraction)
    if hook is None:
        first_sentence = body.split(".")[0] + "." if "." in body else body
        hook = first_sentence

    return {"subject": subject, "body": body, "personalization_hook": hook}


async def draft_email(
    brief: ProspectBrief,
    qual_brief: QualificationBrief,
    client: AsyncAnthropic,
    redraft_feedback: str | None = None,
) -> dict:
    """Generate a cold email draft grounded in the prospect brief."""
    try:
        user_msg = _build_user_message(brief, qual_brief, redraft_feedback)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text  # type: ignore[union-attr]
        result = _parse_response(text)

        # Word count validation
        word_count = len(result["body"].split())
        if word_count > 150:
            retry_msg = (
                f"{user_msg}\n\nYour previous draft was {word_count} words. "
                "Rewrite to be 150 words or fewer while keeping all key points."
            )
            response2 = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": retry_msg}],
            )
            result = _parse_response(response2.content[0].text)  # type: ignore[union-attr]
            word_count = len(result["body"].split())
            if word_count > 150:
                logger.warning(
                    f"Email draft for {brief.company_id} is {word_count} words, "
                    "exceeds 150 word target"
                )

        return result

    except Exception:
        # Hardcoded fallback
        return {
            "subject": f"Context infrastructure for {brief.company_id}",
            "body": (
                f"Hi — saw what you're building. {brief.adela_relevance} "
                "Adela handles the context and governance layer so your team "
                "can scale deployment without the per-client configuration "
                "overhead. Worth a 20-min call?"
            ),
            "personalization_hook": (
                f"Fallback draft — Claude unavailable. "
                f"Adela relevance: {brief.adela_relevance}"
            ),
        }
