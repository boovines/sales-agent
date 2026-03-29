import asyncio
import logging
import json
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from adela_outbound.agents.discovery.state import DiscoveryState
from adela_outbound.agents.discovery.sources import brave, github, grok
from adela_outbound.agents.discovery.events import broadcast
from adela_outbound.db.connection import get_db
from adela_outbound.config import config

logger = logging.getLogger(__name__)

# Search queries per source
BRAVE_QUERIES: list[str] = [
    'AI services company forward deployed engineer hiring site:techcrunch.com OR site:linkedin.com',
    'Series A AI deployment company solutions engineer job posting 2025',
    'enterprise AI agent deployment scaling company funding announcement',
    'devops consultancy AI agents enterprise clients deployment tooling',
]

GITHUB_QUERIES: list[str] = [
    'enterprise agent deployment multi-tenant',
    'forward deployed engineering internal tools sop',
    'AI deployment governance enterprise clients',
]

GROK_QUERIES: list[str] = [
    'founders scaling AI agent deployment across enterprise clients pain points',
    'forward deployed engineer tooling challenges context management multiple clients',
]

# ICP keyword scoring
ICP_KEYWORDS_HIGH: list[str] = ['forward deployed', 'fde', 'forward-deployed']
ICP_KEYWORDS_MEDIUM: list[str] = ['enterprise deployment', 'ai agent', 'solutions engineer', 'client deployment', 'enterprise client']
ICP_KEYWORDS_LOW: list[str] = ['multi-tenant', 'bespoke', 'sop', 'governance', 'deployment scale']

HIGH_SCORE = 0.4
MEDIUM_SCORE = 0.2
LOW_SCORE = 0.1


def _extract_candidate_name(result: dict) -> str:
    source = result.get('_source', '')
    if source == 'brave':
        url = result.get('url', '')
        parsed = urlparse(url)
        netloc = parsed.netloc.replace('www.', '')
        return netloc.split('.')[0] if netloc else ''
    if source == 'github':
        return result.get('owner_login', '')
    if source == 'grok':
        company = result.get('company_mentioned')
        return company if company else result.get('author_handle', '')
    return ''


async def signal_collector(state: DiscoveryState) -> dict:
    try:
        brave_tasks = [brave.search(q) for q in BRAVE_QUERIES]
        github_tasks = [github.search_repos(q) for q in GITHUB_QUERIES]
        grok_tasks = [grok.search_x_context(q) for q in GROK_QUERIES]
        all_tasks = brave_tasks + github_tasks + grok_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        flattened = []
        errors = list(state.get('errors', []))
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f'Source task raised exception: {r}')
                errors.append(str(r))
            elif isinstance(r, list):
                flattened.extend(r)

        return {'raw_results': flattened, 'sources_queried': ['brave', 'github', 'grok'], 'errors': errors}
    except Exception as e:
        logger.error(f'signal_collector error: {e}')
        errors = list(state.get('errors', []))
        errors.append(str(e))
        return {'raw_results': [], 'sources_queried': [], 'errors': errors}


async def deduplicator(state: DiscoveryState) -> dict:
    try:
        async with get_db() as conn:
            cursor = await conn.execute('SELECT LOWER(company_name) FROM discovery_queue')
            rows = await cursor.fetchall()
            existing_names = {row[0] for row in rows}

        deduped = []
        for result in state['raw_results']:
            candidate = _extract_candidate_name(result)
            if candidate and candidate.lower() not in existing_names:
                deduped.append(result)
                existing_names.add(candidate.lower())

        return {'deduped_results': deduped}
    except Exception as e:
        logger.error(f'deduplicator error: {e}')
        errors = list(state.get('errors', []))
        errors.append(str(e))
        return {'deduped_results': [], 'errors': errors}


async def thin_record_builder(state: DiscoveryState) -> dict:
    try:
        records = []
        for result in state['deduped_results']:
            source = result.get('_source', 'brave')
            now = datetime.now(timezone.utc).isoformat()
            record = {
                'id': str(uuid.uuid4()),
                'company_name': '',
                'website': None,
                'github_handle': None,
                'twitter_handle': None,
                'linkedin_url': None,
                'discovery_source': source,
                'discovery_signal': '',
                'pre_score': 0.0,
                'status': 'queued',
                'created_at': now,
                'updated_at': now,
            }

            if source == 'brave':
                record['company_name'] = (_extract_candidate_name(result) or result.get('title', 'unknown'))[:50]
                record['website'] = result.get('url')
                record['discovery_signal'] = (result.get('title', '') + ': ' + result.get('description', ''))[:500]
            elif source == 'github':
                record['company_name'] = result.get('owner_login', 'unknown')
                record['website'] = result.get('homepage') or result.get('owner_html_url')
                record['github_handle'] = result.get('owner_login')
                record['discovery_signal'] = ('GitHub: ' + result.get('repo_name', '') + ' - ' + result.get('description', ''))[:500]
            elif source == 'grok':
                record['company_name'] = (result.get('company_mentioned') or result.get('author_handle') or 'unknown')[:100]
                record['twitter_handle'] = result.get('author_handle')
                signal_parts = [result.get('post_summary', '')]
                if result.get('pain_point'):
                    signal_parts.append('Pain: ' + result['pain_point'])
                record['discovery_signal'] = ' '.join(signal_parts)[:500]

            if record['company_name'] in ('unknown', ''):
                continue

            records.append(record)

        return {'thin_records': records}
    except Exception as e:
        logger.error(f'thin_record_builder error: {e}')
        errors = list(state.get('errors', []))
        errors.append(str(e))
        return {'thin_records': [], 'errors': errors}


async def pre_scorer(state: DiscoveryState) -> dict:
    try:
        passing = []
        dropped = 0
        for record in state['thin_records']:
            text = (record.get('company_name', '') + ' ' + record.get('discovery_signal', '')).lower()
            score = 0.0

            for kw in ICP_KEYWORDS_HIGH:
                if kw in text:
                    score += HIGH_SCORE
            score = min(score, HIGH_SCORE)

            for kw in ICP_KEYWORDS_MEDIUM:
                if kw in text:
                    score += MEDIUM_SCORE

            for kw in ICP_KEYWORDS_LOW:
                if kw in text:
                    score += LOW_SCORE

            score = min(score, 1.0)

            if score < 0.3:
                dropped += 1
                continue

            record['pre_score'] = round(score, 3)
            passing.append(record)

        logger.info(f'Pre-scoring complete: {len(state["thin_records"])} in, {len(passing)} passing, {dropped} dropped below threshold')
        return {'pre_scored_records': passing}
    except Exception as e:
        logger.error(f'pre_scorer error: {e}')
        errors = list(state.get('errors', []))
        errors.append(str(e))
        return {'pre_scored_records': [], 'errors': errors}


async def rate_limiter(state: DiscoveryState) -> dict:
    try:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM discovery_queue WHERE DATE(created_at) = DATE('now')"
            )
            row = await cursor.fetchone()
            written_today = row[0] if row else 0

        remaining = max(0, config.DAILY_DISCOVERY_CAP - written_today)
        records = state['pre_scored_records']

        if remaining == 0:
            logger.warning(f'Daily discovery cap of {config.DAILY_DISCOVERY_CAP} reached, skipping all {len(records)} records')
            return {'final_records': [], 'cap_applied': True}

        if len(records) > remaining:
            logger.info(f'Cap applied: keeping {remaining} of {len(records)} records')
            return {'final_records': records[:remaining], 'cap_applied': True}

        return {'final_records': records, 'cap_applied': False}
    except Exception as e:
        logger.error(f'rate_limiter error: {e}')
        errors = list(state.get('errors', []))
        errors.append(str(e))
        return {'final_records': [], 'cap_applied': False, 'errors': errors}
