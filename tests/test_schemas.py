import pytest
from adela_outbound.db.schemas import CREATE_TABLES_SQL


def test_all_tables_present():
    expected = [
        'discovery_queue',
        'prospect_briefs',
        'qualification_briefs',
        'icp_definition',
        'icp_feedback',
        'icp_suggestions',
        'outreach_packages',
        'outreach_log',
        'agent_runs',
        'discovery_runs',
    ]
    for table in expected:
        assert table in CREATE_TABLES_SQL, f'Missing table: {table}'
