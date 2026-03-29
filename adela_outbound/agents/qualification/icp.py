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
