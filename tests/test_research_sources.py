from __future__ import annotations

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from adela_outbound.agents.research.sources.firecrawl import scrape
from adela_outbound.agents.research.sources.github import research_org
from adela_outbound.agents.research.sources.perplexity import synthesise


@pytest.mark.asyncio
async def test_firecrawl_returns_failure_on_missing_key():
    with patch('adela_outbound.agents.research.sources.firecrawl.config') as m:
        m.FIRECRAWL_API_KEY = ''
        result = await scrape('https://test.com')
        assert result['success'] is False
        assert result['markdown'] == ''
        assert 'API key' in result['error']


@pytest.mark.asyncio
async def test_firecrawl_returns_failure_on_invalid_url():
    with patch('adela_outbound.agents.research.sources.firecrawl.config') as m:
        m.FIRECRAWL_API_KEY = 'test'
        with patch('adela_outbound.agents.research.sources.firecrawl.FIRECRAWL_AVAILABLE', True):
            result = await scrape('not-a-url')
            assert result['success'] is False


@pytest.mark.asyncio
async def test_firecrawl_truncates_markdown_to_8000():
    with patch('adela_outbound.agents.research.sources.firecrawl.config') as m:
        m.FIRECRAWL_API_KEY = 'test'
        with patch('adela_outbound.agents.research.sources.firecrawl.FIRECRAWL_AVAILABLE', True):
            with patch('adela_outbound.agents.research.sources.firecrawl.FirecrawlApp', MagicMock()):
                with patch('adela_outbound.agents.research.sources.firecrawl.asyncio.get_event_loop') as mock_loop:
                    mock_loop.return_value.run_in_executor = AsyncMock(
                        return_value={'markdown': 'x' * 10000, 'metadata': {}}
                    )
                    result = await scrape('https://test.com')
                    assert len(result['markdown']) == 8000


@pytest.mark.asyncio
async def test_perplexity_returns_failure_on_missing_key():
    with patch('adela_outbound.agents.research.sources.perplexity.config') as m:
        m.PERPLEXITY_API_KEY = ''
        result = await synthesise('Test Co')
        assert result['success'] is False
        assert result['synthesis'] == ''


@pytest.mark.asyncio
async def test_perplexity_returns_synthesis_on_success():
    with patch('adela_outbound.agents.research.sources.perplexity.config') as m:
        m.PERPLEXITY_API_KEY = 'test-key'
        with patch('adela_outbound.agents.research.sources.perplexity.AsyncOpenAI') as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = 'TestCo raised $5M seed in March 2025.'
            mock_response.citations = ['https://techcrunch.com/testco']
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = await synthesise('TestCo', 'https://testco.io')
            assert result['success'] is True
            assert 'TestCo' in result['synthesis']
            assert len(result['sources']) == 1


@pytest.mark.asyncio
async def test_github_research_org_returns_empty_on_missing_token():
    with patch('adela_outbound.agents.research.sources.github.config') as m:
        m.GITHUB_TOKEN = ''
        result = await research_org('testorg')
        assert result['success'] is False


@pytest.mark.asyncio
async def test_github_research_org_returns_empty_on_empty_handle():
    result = await research_org('')
    assert result['success'] is False


@pytest.mark.asyncio
async def test_github_research_org_detects_opportunity_issues():
    with patch('adela_outbound.agents.research.sources.github.config') as m:
        m.GITHUB_TOKEN = 'test'

        repos_response = MagicMock()
        repos_response.status_code = 200
        repos_response.json.return_value = [
            {
                'name': 'fde-toolkit',
                'description': 'enterprise toolkit',
                'topics': [],
                'stargazers_count': 5,
                'html_url': 'https://github.com/testorg/fde-toolkit',
            }
        ]

        issues_response = MagicMock()
        issues_response.status_code = 200
        issues_response.json.return_value = [
            {
                'title': 'Multi-tenant context isolation',
                'body': 'Need better context management across client deployments',
                'html_url': 'https://github.com/testorg/fde-toolkit/issues/1',
                'number': 1,
            }
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[repos_response, issues_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('adela_outbound.agents.research.sources.github.httpx.AsyncClient', return_value=mock_client):
            result = await research_org('testorg')

        assert result['success'] is True
        assert len(result['adela_opportunity_issues']) == 1
        assert 'context' in result['adela_opportunity_issues'][0]['matched_keywords']
