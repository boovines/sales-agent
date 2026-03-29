import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from adela_outbound.agents.discovery.sources.github import search_repos


def _make_item(name, stars, owner_login='testorg', owner_type='Organization'):
    return {
        'name': name,
        'owner': {
            'login': owner_login,
            'type': owner_type,
            'html_url': f'https://github.com/{owner_login}',
        },
        'description': 'A test repo',
        'homepage': 'https://example.com',
        'topics': ['ai', 'ml'],
        'stargazers_count': stars,
        'pushed_at': '2026-03-01T00:00:00Z',
        'html_url': f'https://github.com/{owner_login}/{name}',
    }


async def test_search_repos_normalises_response():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'items': [_make_item('cool-repo', 10)]
    }
    with patch('adela_outbound.agents.discovery.sources.github.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch('adela_outbound.agents.discovery.sources.github.config') as mock_config:
            mock_config.GITHUB_TOKEN = 'test-token'
            result = await search_repos('ai deployment')
            assert len(result) == 1
            assert result[0]['repo_name'] == 'cool-repo'
            assert result[0]['owner_login'] == 'testorg'
            assert result[0]['_source'] == 'github'


async def test_search_repos_filters_zero_star_repos():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'items': [
            _make_item('no-stars', 0),
            _make_item('has-stars', 5),
        ]
    }
    with patch('adela_outbound.agents.discovery.sources.github.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch('adela_outbound.agents.discovery.sources.github.config') as mock_config:
            mock_config.GITHUB_TOKEN = 'test-token'
            result = await search_repos('ai deployment')
            assert len(result) == 1
            assert result[0]['repo_name'] == 'has-stars'


async def test_search_repos_returns_empty_on_missing_token():
    with patch('adela_outbound.agents.discovery.sources.github.config') as mock_config:
        mock_config.GITHUB_TOKEN = ''
        result = await search_repos('ai deployment')
        assert result == []
