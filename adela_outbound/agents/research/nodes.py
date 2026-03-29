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


async def input_loader(state: dict) -> dict:
    return {}


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


async def brief_synthesiser(state: dict) -> dict:
    return {}


async def github_opportunity_detector(state: dict) -> dict:
    return {}


async def output_writer(state: dict) -> dict:
    return {}
