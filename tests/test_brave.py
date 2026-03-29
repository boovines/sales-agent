import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from adela_outbound.agents.discovery.sources.brave import search


async def test_search_returns_normalised_dicts():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'web': {
            'results': [
                {
                    'title': 'Test Company',
                    'url': 'https://test.com',
                    'description': 'AI deployment',
                    'age': '2 days ago',
                }
            ]
        }
    }
    with patch('adela_outbound.agents.discovery.sources.brave.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch('adela_outbound.agents.discovery.sources.brave.config') as mock_config:
            mock_config.BRAVE_API_KEY = 'test-key'
            result = await search('test query')
            assert len(result) == 1
            assert result[0]['title'] == 'Test Company'
            assert result[0]['url'] == 'https://test.com'
            assert result[0]['_source'] == 'brave'


async def test_search_returns_empty_on_missing_key():
    with patch('adela_outbound.agents.discovery.sources.brave.config') as mock_config:
        mock_config.BRAVE_API_KEY = ''
        result = await search('test query')
        assert result == []


async def test_search_returns_empty_on_network_error():
    with patch('adela_outbound.agents.discovery.sources.brave.config') as mock_config:
        mock_config.BRAVE_API_KEY = 'test-key'
        with patch('adela_outbound.agents.discovery.sources.brave.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(side_effect=httpx.RequestError('connection failed'))))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await search('test query')
            assert result == []
