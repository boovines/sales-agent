from __future__ import annotations

import pytest
import aiosqlite
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_research_graph_writes_brief_to_sqlite(tmp_path):
    db_path = str(tmp_path / 'test.db')

    # Create tables
    from adela_outbound.db.schemas import CREATE_TABLES_SQL
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(CREATE_TABLES_SQL)
        await conn.commit()

    # Insert test company
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            'INSERT INTO discovery_queue VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (
                'test-co-001', 'FDE Tools', 'https://fdetools.io', None,
                'fdetools', None, 'github',
                'forward deployed enterprise agent deployment',
                0.7, 'queued', now, now,
            ),
        )
        await conn.commit()

    # Patch all sources and DB path
    with patch('adela_outbound.db.connection.config') as mock_db_cfg, \
         patch('adela_outbound.agents.research.nodes.config') as mock_nodes_cfg, \
         patch('adela_outbound.agents.research.sources.firecrawl.scrape', new=AsyncMock(return_value={
             'success': True,
             'markdown': 'FDE Tools builds enterprise agent deployment tooling for forward deployed engineers scaling to multiple clients.',
             'url': 'https://fdetools.io',
             'title': 'FDE Tools',
             'description': None,
             'error': None,
         })), \
         patch('adela_outbound.agents.research.sources.perplexity.synthesise', new=AsyncMock(return_value={
             'success': False,
             'synthesis': '',
             'sources': [],
             'error': 'Skipped: pre_score below threshold',
         })), \
         patch('adela_outbound.agents.research.sources.github.research_org', new=AsyncMock(return_value={
             'success': True,
             'repos': [{'name': 'fde-toolkit', 'description': 'enterprise toolkit', 'topics': ['fde'], 'stars': 8, 'url': 'https://github.com/fdetools/fde-toolkit'}],
             'open_issues': [],
             'adela_opportunity_issues': [],
             'error': None,
         })), \
         patch('adela_outbound.agents.research.sources.grok.get_founder_context', new=AsyncMock(return_value={
             'success': False,
             'recent_focus': '',
             'pain_points_mentioned': [],
             'notable_posts': [],
             'error': 'No Twitter handle provided',
         })), \
         patch('adela_outbound.agents.research.synthesiser.build_brief', new=AsyncMock(return_value={
             'summary': 'FDE Tools is a forward deployed engineering tooling company.',
             'current_focus': 'Building enterprise agent deployment tooling.',
             'pain_points': ['Context fragmentation across clients'],
             'adela_relevance': 'Direct ICP match — scaling enterprise deployments with no SOP tooling.',
             'personalization_hooks': ['They have 8 stars on fde-toolkit'],
             'recommended_channel': 'email',
             'research_sources': ['https://fdetools.io'],
         })):
        mock_db_cfg.DB_PATH = db_path
        mock_nodes_cfg.DB_PATH = db_path
        mock_nodes_cfg.ANTHROPIC_API_KEY = 'test'

        from adela_outbound.agents.research.graph import run_research
        result = await run_research('test-co-001')

    assert isinstance(result, dict)

    # Verify brief was written
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            'SELECT COUNT(*) FROM prospect_briefs WHERE company_id = ?',
            ['test-co-001'],
        )
        row = await cursor.fetchone()
        assert row[0] == 1, 'ProspectBrief not written to DB'

        cursor2 = await conn.execute(
            'SELECT status FROM discovery_queue WHERE id = ?',
            ['test-co-001'],
        )
        row2 = await cursor2.fetchone()
        assert row2[0] == 'researched', f'Expected researched, got {row2[0]}'
