import pytest
import aiosqlite
import os
from unittest.mock import patch, AsyncMock

from adela_outbound.agents.discovery.graph import run_discovery
from adela_outbound.db.connection import init_db
from adela_outbound.db import schemas


async def test_discovery_graph_runs_end_to_end(tmp_path):
    db_path = str(tmp_path / 'test.db')

    with (
        patch('adela_outbound.db.connection.config') as mock_conn_config,
        patch('adela_outbound.agents.discovery.nodes.config') as mock_nodes_config,
    ):
        mock_conn_config.DB_PATH = db_path
        mock_nodes_config.DB_PATH = db_path
        mock_nodes_config.DAILY_DISCOVERY_CAP = 100
        mock_nodes_config.BRAVE_API_KEY = 'test'
        mock_nodes_config.GITHUB_TOKEN = 'test'
        mock_nodes_config.GROK_API_KEY = ''

        # Initialise DB
        async with aiosqlite.connect(db_path) as conn:
            await conn.executescript(schemas.CREATE_TABLES_SQL)
            await conn.commit()

        # Patch source adapters
        with (
            patch(
                'adela_outbound.agents.discovery.sources.brave.search',
                new=AsyncMock(return_value=[{
                    'title': 'AI Deploy Co',
                    'url': 'https://aideployco.ai',
                    'description': 'enterprise AI agent deployment solutions engineer',
                    'published_date': None,
                    '_source': 'brave',
                }]),
            ),
            patch(
                'adela_outbound.agents.discovery.sources.github.search_repos',
                new=AsyncMock(return_value=[{
                    'repo_name': 'fde-tools',
                    'owner_login': 'fdetools',
                    'owner_type': 'Organization',
                    'owner_html_url': 'https://github.com/fdetools',
                    'description': 'forward deployed engineering tools for enterprise clients',
                    'homepage': 'https://fdetools.io',
                    'topics': ['fde', 'enterprise'],
                    'stargazers_count': 15,
                    'pushed_at': '2025-01-01',
                    'repo_html_url': 'https://github.com/fdetools/fde-tools',
                    '_source': 'github',
                }]),
            ),
            patch(
                'adela_outbound.agents.discovery.sources.grok.search_x_context',
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await run_discovery(run_type='test')

        assert isinstance(result, dict)

        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.execute('SELECT COUNT(*) FROM discovery_queue')
            row = await cursor.fetchone()
            assert row[0] >= 1, 'Expected at least one record written to discovery_queue'

            cursor2 = await conn.execute('SELECT COUNT(*) FROM discovery_runs')
            row2 = await cursor2.fetchone()
            assert row2[0] == 1, 'Expected one discovery_runs record'
