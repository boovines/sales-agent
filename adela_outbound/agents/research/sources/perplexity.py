from __future__ import annotations

import logging

from openai import AsyncOpenAI

from adela_outbound.config import config

logger = logging.getLogger(__name__)


async def synthesise(company_name: str, website: str = None) -> dict:
    """Query Perplexity for synthesised news, funding, and press mentions."""
    if not config.PERPLEXITY_API_KEY:
        logger.warning('PERPLEXITY_API_KEY not configured')
        return {'success': False, 'synthesis': '', 'sources': [], 'error': 'API key not configured'}

    try:
        client = AsyncOpenAI(api_key=config.PERPLEXITY_API_KEY, base_url='https://api.perplexity.ai')

        website_clause = f' (website: {website})' if website else ''
        prompt = (
            f'Research the company "{company_name}"{website_clause}. '
            'Provide specific, factual information on: '
            '(1) Recent funding rounds \u2014 amounts, dates, investors. '
            '(2) Product launches or major updates in the last 12 months. '
            '(3) Press mentions or notable coverage. '
            '(4) Team size estimate. '
            '(5) Any signals of scaling challenges, enterprise customer growth, or deployment complexity. '
            'If information is unavailable for any point, say "Not found" rather than guessing. '
            'Be concise and specific.'
        )

        response = await client.chat.completions.create(
            model='llama-3.1-sonar-large-128k-online',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=600,
            temperature=0.1,
        )

        synthesis = ''
        if response.choices and response.choices[0].message.content:
            synthesis = response.choices[0].message.content

        citations = []
        if hasattr(response, 'citations') and isinstance(response.citations, list):
            citations = response.citations

        return {'success': bool(synthesis), 'synthesis': synthesis, 'sources': citations, 'error': None}

    except Exception as e:
        logger.warning(f'Perplexity failed for {company_name}: {type(e).__name__}: {str(e)[:100]}')
        return {'success': False, 'synthesis': '', 'sources': [], 'error': str(e)[:100]}
