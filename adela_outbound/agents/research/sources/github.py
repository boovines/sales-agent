from __future__ import annotations

import asyncio
import logging

import httpx

from adela_outbound.config import config

logger = logging.getLogger(__name__)

ADELA_OPPORTUNITY_KEYWORDS = [
    'context', 'memory', 'sop', 'workflow', 'governance', 'multi-tenant',
    'client', 'agent', 'deployment', 'versioning', 'audit', 'traceability',
    'knowledge', 'forward deployed',
]

_FAILURE = {
    'success': False,
    'repos': [],
    'open_issues': [],
    'adela_opportunity_issues': [],
}


async def _fetch_repo_issues(handle: str, repo_name: str, headers: dict) -> list:
    """Fetch open issues for a single repo."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.get(
                f'https://api.github.com/repos/{handle}/{repo_name}/issues',
                params={'state': 'open', 'per_page': 10},
                headers=headers,
            )
            if response.status_code != 200:
                return []
            issues_data = response.json()
            if not isinstance(issues_data, list):
                return []
            return [
                {
                    'repo': repo_name,
                    'title': i.get('title', ''),
                    'body': (i.get('body') or '')[:500],
                    'url': i.get('html_url', ''),
                    'number': i.get('number', 0),
                }
                for i in issues_data
                if isinstance(i, dict) and i.get('title')
            ]
    except Exception:
        return []


async def research_org(handle: str) -> dict:
    """Research a GitHub org/user: repos, open issues, and Adela opportunity detection."""
    if not handle or not handle.strip():
        return {**_FAILURE, 'error': 'No handle provided'}

    if not config.GITHUB_TOKEN:
        logger.warning('GITHUB_TOKEN not configured')
        return {**_FAILURE, 'error': 'Token not configured'}

    headers = {
        'Authorization': f'token {config.GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.get(
                f'https://api.github.com/users/{handle.strip()}/repos',
                params={'sort': 'updated', 'direction': 'desc', 'per_page': 5},
                headers=headers,
            )

        if response.status_code != 200:
            logger.warning(f'GitHub repos fetch failed for {handle}: {response.status_code}')
            return {**_FAILURE, 'error': f'GitHub API returned {response.status_code}'}

        repos_data = response.json()
        if not isinstance(repos_data, list):
            logger.warning(
                f'GitHub repos response not a list for {handle} — may be an error dict: {repos_data.get("message", "")}'
            )
            return {**_FAILURE, 'error': 'Unexpected response format'}

        repos = [
            {
                'name': r['name'],
                'description': r.get('description') or '',
                'topics': r.get('topics', []),
                'stars': r.get('stargazers_count', 0),
                'url': r.get('html_url', ''),
            }
            for r in repos_data
            if isinstance(r, dict) and r.get('name')
        ]

        # Fetch issues for all repos concurrently
        issue_tasks = [_fetch_repo_issues(handle, r['name'], headers) for r in repos]
        issue_results = await asyncio.gather(*issue_tasks, return_exceptions=True)
        all_issues = [
            issue
            for sublist in issue_results
            if isinstance(sublist, list)
            for issue in sublist
        ]

        # ICP opportunity detection
        adela_opportunity_issues = []
        for issue in all_issues:
            text = (issue['title'] + ' ' + issue['body']).lower()
            matched = [kw for kw in ADELA_OPPORTUNITY_KEYWORDS if kw in text]
            if matched:
                adela_opportunity_issues.append({
                    'repo': issue['repo'],
                    'title': issue['title'],
                    'url': issue['url'],
                    'number': issue['number'],
                    'matched_keywords': matched,
                })

        return {
            'success': True,
            'repos': repos,
            'open_issues': all_issues,
            'adela_opportunity_issues': adela_opportunity_issues,
            'error': None,
        }

    except Exception as e:
        logger.warning(f'GitHub research failed for {handle}: {e}')
        return {**_FAILURE, 'error': str(e)[:100]}
