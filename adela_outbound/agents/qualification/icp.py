from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from adela_outbound.db.connection import get_db

logger = logging.getLogger(__name__)

SEED_ICP_CRITERIA: list = [
    {
        "id": "services_mode",
        "name": "Services company in infrastructure mode",
        "description": "Has crossed from project work into infrastructure mode \u2014 deploying the same core product across 5+ enterprise clients",
        "weight": "high",
    },
    {
        "id": "regulated_clients",
        "name": "Regulated industry clients",
        "description": "Serves clients in financial services, healthcare, government, or other regulated verticals where per-client context governance is non-negotiable",
        "weight": "high",
    },
    {
        "id": "ai_agent_deployment",
        "name": "AI or agent-heavy deployment",
        "description": "Core offering involves deploying AI agents or bespoke technical work into enterprise environments",
        "weight": "high",
    },
    {
        "id": "team_size",
        "name": "Team size 5-50",
        "description": "Large enough to feel scaling pain, small enough to not have built internal tooling yet",
        "weight": "medium",
    },
    {
        "id": "funding_stage",
        "name": "Pre-seed through Series B",
        "description": "Later stage companies have budget but also internal tooling capacity. Earlier stage may not yet feel the pain.",
        "weight": "medium",
    },
    {
        "id": "fde_role_signal",
        "name": "FDE or solutions engineer role signal",
        "description": "Has forward deployed engineer, solutions engineer, or deployment engineer titles \u2014 explicit signal they are in the problem space",
        "weight": "high",
    },
    {
        "id": "scaling_signal",
        "name": "Recent scaling signal",
        "description": "Growing headcount, new funding, expanding client list \u2014 signal they are in the scaling pain window right now",
        "weight": "medium",
    },
    {
        "id": "technical_founder",
        "name": "Technical founding team",
        "description": "Founding team has engineering background \u2014 more likely to appreciate and evaluate infrastructure tooling seriously",
        "weight": "low",
    },
]


async def seed_icp_if_empty(conn) -> None:
    cursor = await conn.execute("SELECT COUNT(*) FROM icp_definition")
    row = await cursor.fetchone()
    count = row[0] if row else 0
    if count > 0:
        logger.debug("ICP definition already seeded, skipping")
        return
    seed_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO icp_definition (id, version, criteria, created_at) VALUES (?,?,?,?)",
        (seed_id, 1, json.dumps(SEED_ICP_CRITERIA), now),
    )
    await conn.commit()
    logger.info(f"Seeded ICP definition with {len(SEED_ICP_CRITERIA)} criteria")


async def load_icp(conn) -> dict:
    cursor = await conn.execute(
        "SELECT * FROM icp_definition ORDER BY version DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    if not row:
        await seed_icp_if_empty(conn)
        cursor2 = await conn.execute(
            "SELECT * FROM icp_definition ORDER BY version DESC LIMIT 1"
        )
        row = await cursor2.fetchone()
        if not row:
            raise RuntimeError("ICP seeding failed")
    d = dict(row)
    d["criteria"] = json.loads(d.get("criteria", "[]"))
    return d


async def save_icp_version(conn, criteria: list) -> int:
    cursor = await conn.execute("SELECT MAX(version) FROM icp_definition")
    row = await cursor.fetchone()
    next_version = (row[0] or 0) + 1
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO icp_definition (id, version, criteria, created_at) VALUES (?,?,?,?)",
        (str(uuid.uuid4()), next_version, json.dumps(criteria), now),
    )
    await conn.commit()
    return next_version


async def generate_icp_suggestions() -> None:
    """Weekly job: analyse recent rejection patterns and save ICP refinement suggestions."""
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT f.company_id, f.decision, f.rejection_note, "
            "dq.company_name, dq.discovery_signal "
            "FROM icp_feedback f "
            "JOIN discovery_queue dq ON f.company_id = dq.id "
            "WHERE DATE(f.decided_at) >= DATE('now', '-30 days') "
            "ORDER BY f.decided_at DESC"
        )
        rows = await cursor.fetchall()
        feedback_list = [dict(r) for r in rows]

    if len(feedback_list) < 3:
        logger.info(
            "Not enough feedback data for ICP suggestions (need >= 3 rejections)"
        )
        return

    feedback_summary = json.dumps(
        [
            {
                "company": f["company_name"],
                "decision": f["decision"],
                "note": f["rejection_note"],
                "signal": f["discovery_signal"],
            }
            for f in feedback_list
        ],
        indent=2,
    )
    prompt = (
        "You are analysing prospect rejection patterns to improve ICP targeting. "
        f"Here are the last 30 days of qualification decisions:\n{feedback_summary}\n\n"
        "Identify up to 3 specific, actionable ICP refinement suggestions. "
        "Each suggestion must: (1) cite specific evidence from the rejection notes, "
        "(2) propose a concrete change to ICP criteria, "
        "(3) be expressed as updated criteria JSON. "
        "Return a JSON array of up to 3 objects, each with keys: "
        "suggestion_text (string: the human-readable suggestion), "
        "evidence (string: specific evidence from the data), "
        "new_criteria (array: the full updated criteria list as it should be stored). "
        "Return only the JSON array."
    )

    from anthropic import AsyncAnthropic
    from adela_outbound.config import config as app_config

    client = AsyncAnthropic(api_key=app_config.ANTHROPIC_API_KEY)

    async with get_db() as conn:
        current_icp = await load_icp(conn)

    icp_str = json.dumps(current_icp.get("criteria", []))
    system = f"Current ICP criteria for context: {icp_str}"

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text.strip() if response.content else "[]"
    # Strip markdown fences
    if content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    try:
        suggestions = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("ICP suggestion generation returned invalid JSON")
        return

    if not isinstance(suggestions, list):
        return

    async with get_db() as conn:
        for s in suggestions[:3]:
            if (
                isinstance(s, dict)
                and s.get("suggestion_text")
                and s.get("new_criteria")
            ):
                await save_icp_suggestion(
                    conn,
                    json.dumps(s.get("new_criteria", [])),
                    s.get("evidence", ""),
                )


async def save_icp_suggestion(conn, suggestion_text: str, evidence: str) -> None:
    await conn.execute(
        "INSERT INTO icp_suggestions (id, suggestion_text, evidence, status, created_at) VALUES (?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            suggestion_text,
            evidence,
            "pending",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    await conn.commit()
