from __future__ import annotations

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from adela_outbound.agents.research.sources.firecrawl import scrape


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
