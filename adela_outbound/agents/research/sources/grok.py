from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from adela_outbound.config import config

logger = logging.getLogger(__name__)

_EMPTY = {
    'success': False,
    'recent_focus': '',
    'pain_points_mentioned': [],
    'notable_posts': [],
}


async def get_founder_context(company_name: str, twitter_handle: str = None) -> dict:
    try:
        if not config.GROK_API_KEY:
            return {**_EMPTY, 'error': 'API key not configured'}

        if not twitter_handle:
            logger.debug(f'No Twitter handle for {company_name}')
            return {**_EMPTY, 'error': 'No Twitter handle provided'}

        client = AsyncOpenAI(
            api_key=config.GROK_API_KEY,
            base_url='https://api.x.ai/v1',
        )

        system = (
            'You are a research assistant. Respond only with a valid JSON object. '
            'No markdown, no code fences, no explanation.'
        )
        user = (
            f'Research the X/Twitter account @{twitter_handle} associated with the '
            f'company {company_name}. Return a JSON object with exactly these keys: '
            f'recent_focus (string: 2-3 sentences on what they post about recently), '
            f'pain_points_mentioned (array of strings: specific pain points or challenges '
            f'they have mentioned), notable_posts (array of strings: 2-3 sentence summaries '
            f'of their most notable recent posts). If you cannot find information, return '
            f'empty strings/arrays for those fields.'
        )

        response = await client.chat.completions.create(
            model='grok-3-mini',
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            max_tokens=500,
            temperature=0.1,
        )

        content = ''
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content or ''
        content = content.strip()

        # Strip markdown fences
        if content.startswith('```'):
            lines = content.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            content = '\n'.join(lines).strip()
        if content.startswith('json'):
            content = content[4:].strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f'Grok non-JSON for @{twitter_handle}: {content[:80]}... Error: {e}')
            return {**_EMPTY, 'error': 'JSON parse failed'}

        if not isinstance(parsed, dict):
            return {**_EMPTY, 'error': 'Response not a dict'}

        return {
            'success': True,
            'recent_focus': parsed.get('recent_focus', '') or '',
            'pain_points_mentioned': parsed.get('pain_points_mentioned', [])
            if isinstance(parsed.get('pain_points_mentioned'), list)
            else [],
            'notable_posts': parsed.get('notable_posts', [])
            if isinstance(parsed.get('notable_posts'), list)
            else [],
            'error': None,
        }

    except Exception as e:
        logger.warning(f'Grok failed for @{twitter_handle}: {e}')
        return {**_EMPTY, 'error': str(e)[:100]}
