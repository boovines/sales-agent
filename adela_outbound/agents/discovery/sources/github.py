import httpx
import logging

from adela_outbound.config import config

logger = logging.getLogger(__name__)


async def search_repos(query: str, max_results: int = 10) -> list[dict]:
    if not config.GITHUB_TOKEN:
        logger.warning('GITHUB_TOKEN not configured, skipping GitHub search')
        return []

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.get(
                'https://api.github.com/search/repositories',
                params={
                    'q': query,
                    'sort': 'updated',
                    'order': 'desc',
                    'per_page': max_results,
                },
                headers={
                    'Authorization': f'token {config.GITHUB_TOKEN}',
                    'Accept': 'application/vnd.github.v3+json',
                    'X-GitHub-Api-Version': '2022-11-28',
                },
            )

            if response.status_code == 200:
                items = response.json().get('items', [])
                items = [i for i in items if i.get('stargazers_count', 0) >= 1]
                return [
                    {
                        'repo_name': i['name'],
                        'owner_login': i['owner']['login'],
                        'owner_type': i['owner']['type'],
                        'owner_html_url': i['owner']['html_url'],
                        'description': i.get('description') or '',
                        'homepage': i.get('homepage') or None,
                        'topics': i.get('topics', []),
                        'stargazers_count': i.get('stargazers_count', 0),
                        'pushed_at': i.get('pushed_at', ''),
                        'repo_html_url': i['html_url'],
                        '_source': 'github',
                    }
                    for i in items
                ]

            if response.status_code == 401:
                logger.error('GitHub token invalid or missing')
                return []

            if response.status_code == 403:
                logger.warning('GitHub API forbidden or rate limited')
                return []

            if response.status_code == 422:
                logger.warning(f'GitHub search validation error for query: {query[:50]}')
                return []

            logger.warning(f'GitHub search returned {response.status_code}')
            return []

    except (httpx.TimeoutException, httpx.RequestError) as e:
        logger.warning(f'GitHub network error: {e}')
        return []
