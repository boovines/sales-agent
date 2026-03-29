from __future__ import annotations

import asyncio
import logging

from adela_outbound.config import config

logger = logging.getLogger(__name__)

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FirecrawlApp = None
    FIRECRAWL_AVAILABLE = False
    logger.warning('firecrawl-py not installed — Firecrawl source unavailable')


async def scrape(url: str) -> dict:
    """Scrape a company website via Firecrawl and return clean markdown content."""
    if not config.FIRECRAWL_API_KEY:
        logger.warning('FIRECRAWL_API_KEY not configured')
        return {'success': False, 'url': url, 'markdown': '', 'title': None, 'description': None, 'error': 'API key not configured'}

    if not FIRECRAWL_AVAILABLE:
        return {'success': False, 'url': url, 'markdown': '', 'title': None, 'description': None, 'error': 'firecrawl-py not installed'}

    if not url or not str(url).startswith('http'):
        return {'success': False, 'url': url, 'markdown': '', 'title': None, 'description': None, 'error': 'Invalid URL — must start with http'}

    try:
        loop = asyncio.get_event_loop()
        app_instance = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)
        result = await loop.run_in_executor(
            None,
            lambda: app_instance.scrape_url(str(url), params={'formats': ['markdown'], 'timeout': 25000}),
        )

        if not isinstance(result, dict):
            return {'success': False, 'url': url, 'markdown': '', 'title': None, 'description': None, 'error': 'Unexpected response type'}

        markdown = result.get('markdown') or ''
        title = result.get('metadata', {}).get('title') if isinstance(result.get('metadata'), dict) else None
        description = result.get('metadata', {}).get('description') if isinstance(result.get('metadata'), dict) else None
        markdown = markdown[:8000]

        return {'success': bool(markdown), 'url': url, 'markdown': markdown, 'title': title, 'description': description, 'error': None}

    except Exception as e:
        logger.warning(f'Firecrawl failed for {url}: {type(e).__name__}: {str(e)[:100]}')
        return {'success': False, 'url': url, 'markdown': '', 'title': None, 'description': None, 'error': str(e)[:100]}
