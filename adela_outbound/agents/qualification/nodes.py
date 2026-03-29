from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from anthropic import AsyncAnthropic

from adela_outbound.agents.qualification.events import broadcast
from adela_outbound.agents.qualification.icp import load_icp
from adela_outbound.agents.qualification.scorer import aggregate_scores, score_all_criteria
from adela_outbound.agents.qualification.state import QualificationState
from adela_outbound.config import config
from adela_outbound.db.connection import get_db

logger = logging.getLogger(__name__)


async def input_loader(state: QualificationState) -> dict:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT pb.*, dq.company_name, dq.website, dq.github_handle, '
            'dq.twitter_handle, dq.discovery_signal '
            'FROM prospect_briefs pb '
            'JOIN discovery_queue dq ON pb.company_id = dq.id '
            'WHERE pb.company_id = ?',
            [state['company_id']],
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(
                f'No prospect brief found for company_id={state["company_id"]}. '
                'Research must complete before qualification.'
            )
        d = dict(row)
        d['pain_points'] = json.loads(d.get('pain_points') or '[]')
        d['personalization_hooks'] = json.loads(d.get('personalization_hooks') or '[]')
        d['research_sources'] = json.loads(d.get('research_sources') or '[]')
        d['creative_outreach_opportunity'] = bool(d.get('creative_outreach_opportunity', 0))

        icp = await load_icp(conn)

    return {'prospect_brief': d, 'icp_definition': icp, 'errors': []}


async def criterion_scorer(state: QualificationState) -> dict:
    client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    scores = await score_all_criteria(
        state['prospect_brief'], state['icp_definition'], client
    )
    return {'criterion_scores': scores}


async def aggregate_scorer(state: QualificationState) -> dict:
    result = aggregate_scores(state['criterion_scores'], state['icp_definition'])
    return {'qualification_brief': {**result, 'criterion_scores': state['criterion_scores']}}


async def qualification_brief_builder(state: QualificationState) -> dict:
    brief = dict(state.get('qualification_brief') or {})

    # Generate why_now and suggested_outreach_angle via Claude
    client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = (
        f'Given this ICP qualification result for company '
        f'"{state["prospect_brief"].get("company_name", "")}": '
        f'fit_score={brief.get("fit_score", 0)}, '
        f'fit_tier={brief.get("fit_tier", "")}, '
        f'top criterion scores: {json.dumps(state["criterion_scores"][:3])}. '
        f'In 1-2 sentences each, provide: '
        f'(1) why_now: why is now the right time to reach out to this company specifically? '
        f'(2) suggested_outreach_angle: what specific angle or hook should the outreach message lead with? '
        f'Return JSON with keys why_now and suggested_outreach_angle only.'
    )
    try:
        response = await client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}],
        )
        content = response.content[0].text.strip() if response.content else '{}'
        # Strip markdown fences
        if content.startswith('```'):
            lines = content.split('\n')
            lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines).strip()
        parsed = json.loads(content)
        brief['why_now'] = parsed.get('why_now', '')
        brief['suggested_outreach_angle'] = parsed.get('suggested_outreach_angle', '')
    except Exception as e:
        logger.warning(f'why_now generation failed: {e}')
        brief['why_now'] = f'Score: {brief.get("fit_score", 0)} ({brief.get("fit_tier", "")})'
        brief['suggested_outreach_angle'] = 'Review criterion scores for outreach angle'

    now = datetime.now(timezone.utc).isoformat()
    brief['id'] = str(uuid.uuid4())
    brief['company_id'] = state['company_id']
    brief['created_at'] = now

    # Auto-disqualify if fit_tier is disqualified
    if brief.get('fit_tier') == 'disqualified':
        brief['status'] = 'auto_rejected'
        async with get_db() as conn:
            await conn.execute(
                'INSERT OR REPLACE INTO qualification_briefs '
                '(id, company_id, fit_score, fit_tier, criterion_scores, why_now, '
                'suggested_outreach_angle, status, rejection_note, reviewed_at, created_at) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (
                    brief['id'],
                    brief['company_id'],
                    brief.get('fit_score', 0),
                    brief.get('fit_tier', ''),
                    json.dumps(state['criterion_scores']),
                    brief.get('why_now', ''),
                    brief.get('suggested_outreach_angle', ''),
                    'auto_rejected',
                    'Auto-rejected: fit_score below 0.30 threshold',
                    None,
                    brief['created_at'],
                ),
            )
            await conn.execute(
                'UPDATE discovery_queue SET status = ?, updated_at = ? WHERE id = ?',
                ['disqualified', now, state['company_id']],
            )
            await conn.commit()
        return {'qualification_brief': brief, 'decision': 'auto_rejected'}

    # Non-disqualified: pending review
    brief['status'] = 'pending_review'
    async with get_db() as conn:
        await conn.execute(
            'INSERT OR REPLACE INTO qualification_briefs '
            '(id, company_id, fit_score, fit_tier, criterion_scores, why_now, '
            'suggested_outreach_angle, status, rejection_note, reviewed_at, created_at) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (
                brief['id'],
                brief['company_id'],
                brief.get('fit_score', 0),
                brief.get('fit_tier', ''),
                json.dumps(state['criterion_scores']),
                brief.get('why_now', ''),
                brief.get('suggested_outreach_angle', ''),
                'pending_review',
                None,
                None,
                brief['created_at'],
            ),
        )
        await conn.commit()

    await broadcast('qualify_pending', {
        'company_id': state['company_id'],
        'company_name': state['prospect_brief'].get('company_name', ''),
        'fit_score': brief.get('fit_score', 0),
        'fit_tier': brief.get('fit_tier', ''),
        'timestamp': now,
    })

    return {'qualification_brief': brief}


async def hitl_gate(state: QualificationState) -> dict:
    logger.info(
        f'Resuming hitl_gate for {state["company_id"]} '
        f'with decision={state.get("decision")}'
    )
    return {}


async def resume_handler(state: QualificationState) -> dict:
    decision = state.get('decision', '')
    rejection_note = state.get('rejection_note')
    now = datetime.now(timezone.utc).isoformat()
    brief_id = state.get('qualification_brief', {}).get('id', '')

    if decision == 'approved':
        async with get_db() as conn:
            await conn.execute(
                'UPDATE qualification_briefs SET status = ?, reviewed_at = ? WHERE id = ?',
                ['approved', now, brief_id],
            )
            await conn.execute(
                'UPDATE discovery_queue SET status = ?, updated_at = ? WHERE id = ?',
                ['qualified', now, state['company_id']],
            )
            await conn.commit()
        logger.info(f'Approved: {state["company_id"]}')
    elif decision == 'rejected':
        async with get_db() as conn:
            await conn.execute(
                'UPDATE qualification_briefs SET status = ?, rejection_note = ?, reviewed_at = ? WHERE id = ?',
                ['rejected', rejection_note, now, brief_id],
            )
            await conn.execute(
                'UPDATE discovery_queue SET status = ?, updated_at = ? WHERE id = ?',
                ['disqualified', now, state['company_id']],
            )
            await conn.execute(
                'INSERT INTO icp_feedback (id, company_id, decision, rejection_note, decided_at) '
                'VALUES (?,?,?,?,?)',
                (str(uuid.uuid4()), state['company_id'], 'rejected', rejection_note, now),
            )
            await conn.commit()
    elif decision == 'auto_rejected':
        # Already written to DB in qualification_brief_builder
        pass

    return {'errors': state.get('errors', [])}
