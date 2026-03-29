from __future__ import annotations

import asyncio
import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from adela_outbound.agents.research.state import ResearchState
from adela_outbound.agents.research.sources import firecrawl, perplexity, github, grok
from adela_outbound.agents.research.events import broadcast
from adela_outbound.db.connection import get_db
from adela_outbound.config import config

logger = logging.getLogger(__name__)


async def _skip(default: dict) -> dict:
    return default


async def input_loader(state: ResearchState) -> dict:
    async with get_db() as conn:
        cursor = await conn.execute(
            'SELECT * FROM discovery_queue WHERE id = ?',
            [state['company_id']],
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(
                f'Company ID {state["company_id"]} not found in discovery_queue'
            )
        return {'discovery_record': dict(row)}


async def parallel_researcher(state: ResearchState) -> dict:
    record = state['discovery_record']
    company_name = record.get('company_name', '')
    website = record.get('website')
    github_handle = record.get('github_handle')
    twitter_handle = record.get('twitter_handle')
    pre_score = float(record.get('pre_score', 0.0))

    fc_task = firecrawl.scrape(website) if website else _skip({
        'success': False, 'markdown': '', 'url': None, 'title': None,
        'description': None, 'error': 'No website on record'
    })
    px_task = perplexity.synthesise(company_name, website) if pre_score >= 0.5 else _skip({
        'success': False, 'synthesis': '', 'sources': [],
        'error': f'Skipped: pre_score {pre_score} below 0.5 threshold'
    })
    gh_task = github.research_org(github_handle) if github_handle else _skip({
        'success': False, 'repos': [], 'open_issues': [],
        'adela_opportunity_issues': [], 'error': 'No github_handle on record'
    })
    gr_task = grok.get_founder_context(company_name, twitter_handle)

    results = await asyncio.gather(fc_task, px_task, gh_task, gr_task, return_exceptions=True)

    errors = list(state.get('errors', []))
    source_names = ['firecrawl', 'perplexity', 'github', 'grok']
    unpacked = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.warning(f'{source_names[i]} raised unexpected exception: {r}')
            errors.append(f'{source_names[i]}: {str(r)}')
            unpacked.append({'success': False, 'error': str(r)})
        else:
            unpacked.append(r if isinstance(r, dict) else {'success': False, 'error': 'non-dict result'})

    return {
        'firecrawl_result': unpacked[0],
        'perplexity_result': unpacked[1],
        'github_result': unpacked[2],
        'grok_result': unpacked[3],
        'errors': errors,
    }


async def brief_synthesiser(state: ResearchState) -> dict:
    from anthropic import AsyncAnthropic
    from adela_outbound.agents.research.synthesiser import build_brief, FALLBACK_BRIEF

    successes = [
        state.get('firecrawl_result', {}).get('success', False),
        state.get('perplexity_result', {}).get('success', False),
        state.get('github_result', {}).get('success', False),
        state.get('grok_result', {}).get('success', False),
    ]
    confidence_score = round(sum(successes) / 4, 2)

    client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    errors = list(state.get('errors', []))

    try:
        parsed = await build_brief(state, client)
        parsed['confidence_score'] = confidence_score
    except Exception as e:
        logger.warning(
            f'Claude synthesis failed for {state["company_id"]}: '
            f'{type(e).__name__}: {str(e)[:100]}'
        )
        parsed = dict(FALLBACK_BRIEF)
        parsed['confidence_score'] = min(confidence_score, 0.2)
        errors.append(f'Claude synthesis failed: {str(e)[:100]}')

    return {'brief': parsed, 'errors': errors}


async def github_opportunity_detector(state: ResearchState) -> dict:
    gh = state.get('github_result', {})
    opportunity_issues = gh.get('adela_opportunity_issues', [])
    brief = dict(state.get('brief') or {})

    if opportunity_issues:
        best = opportunity_issues[0]
        brief['creative_outreach_opportunity'] = True
        brief['creative_outreach_detail'] = (
            f'Open GitHub issue #{best["number"]} in repo "{best["repo"]}": '
            f'"{best["title"]}". Matched keywords: {best["matched_keywords"]}. '
            f'URL: {best["url"]}'
        )
        brief['recommended_channel'] = 'github'
    else:
        brief['creative_outreach_opportunity'] = False
        brief['creative_outreach_detail'] = None

    return {'brief': brief}


INSERT_SQL = (
    'INSERT OR REPLACE INTO prospect_briefs '
    '(id, company_id, summary, current_focus, pain_points, adela_relevance, '
    'personalization_hooks, creative_outreach_opportunity, creative_outreach_detail, '
    'recommended_channel, research_sources, confidence_score, raw_research, created_at) '
    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
)


async def output_writer(state: ResearchState) -> dict:
    record = state['discovery_record']
    brief = state.get('brief') or {}
    now = datetime.now(timezone.utc).isoformat()
    brief_id = str(uuid.uuid4())

    row = (
        brief_id,
        state['company_id'],
        str(brief.get('summary', '')),
        str(brief.get('current_focus', '')),
        json.dumps(brief.get('pain_points', [])),
        str(brief.get('adela_relevance', '')),
        json.dumps(brief.get('personalization_hooks', [])),
        1 if brief.get('creative_outreach_opportunity') else 0,
        brief.get('creative_outreach_detail'),
        str(brief.get('recommended_channel', 'email')),
        json.dumps(brief.get('research_sources', [])),
        float(brief.get('confidence_score', 0.0)),
        json.dumps({
            'firecrawl': state.get('firecrawl_result', {}),
            'perplexity': state.get('perplexity_result', {}),
            'github': state.get('github_result', {}),
            'grok': state.get('grok_result', {}),
        }),
        now,
    )

    async with get_db() as conn:
        await conn.execute(INSERT_SQL, row)
        await conn.execute(
            'UPDATE discovery_queue SET status = ?, updated_at = ? WHERE id = ?',
            ['researched', now, state['company_id']],
        )
        await conn.commit()

    await broadcast('research_complete', {
        'company_id': state['company_id'],
        'company_name': record.get('company_name', ''),
        'confidence_score': float(brief.get('confidence_score', 0.0)),
        'creative_outreach_opportunity': bool(brief.get('creative_outreach_opportunity', False)),
        'timestamp': now,
    })

    return {'errors': state.get('errors', [])}
