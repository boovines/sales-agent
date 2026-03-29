import httpx
import asyncio
import logging

from adela_outbound.config import config

logger = logging.getLogger(__name__)


async def search(query: str, count: int = 10) -> list[dict]:
    if not config.BRAVE_API_KEY:
        logger.warning('BRAVE_API_KEY not configured, skipping Brave search')
        return []

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            for attempt in range(3):
                response = await client.get(
                    'https://api.search.brave.com/res/v1/web/search',
                    params={'q': query, 'count': count},
                    headers={
                        'Accept': 'application/json',
                        'Accept-Encoding': 'gzip',
                        'X-Subscription-Token': config.BRAVE_API_KEY,
                    },
                )

                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f'Brave rate limited, waiting {wait_time}s (attempt {attempt+1}/3)')
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('web', {}).get('results', [])
                    return [
                        {
                            'title': r.get('title', ''),
                            'url': r.get('url', ''),
                            'description': r.get('description', ''),
                            'published_date': r.get('age', None),
                            '_source': 'brave',
                        }
                        for r in results
                    ]

                logger.warning(f'Brave search returned {response.status_code} for query: {query[:50]}')
                return []

            logger.warning('Brave rate limit retries exhausted')
            return []

    except (httpx.TimeoutException, httpx.RequestError) as e:
        logger.warning(f'Brave search network error: {type(e).__name__}: {e}')
        return []
