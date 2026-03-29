CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS discovery_queue (
    id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    website TEXT,
    twitter_handle TEXT,
    github_handle TEXT,
    linkedin_url TEXT,
    discovery_source TEXT NOT NULL,
    discovery_signal TEXT NOT NULL,
    pre_score REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prospect_briefs (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    current_focus TEXT NOT NULL,
    pain_points TEXT NOT NULL,
    adela_relevance TEXT NOT NULL,
    personalization_hooks TEXT NOT NULL,
    creative_outreach_opportunity INTEGER NOT NULL DEFAULT 0,
    creative_outreach_detail TEXT,
    recommended_channel TEXT NOT NULL DEFAULT 'email',
    research_sources TEXT NOT NULL,
    confidence_score REAL NOT NULL DEFAULT 0.0,
    raw_research TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qualification_briefs (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    fit_score REAL NOT NULL,
    fit_tier TEXT NOT NULL,
    criterion_scores TEXT NOT NULL,
    why_now TEXT NOT NULL,
    suggested_outreach_angle TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_review',
    rejection_note TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS icp_definition (
    id TEXT PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 1,
    criteria TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS icp_feedback (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    rejection_note TEXT,
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS icp_suggestions (
    id TEXT PRIMARY KEY,
    suggestion_text TEXT NOT NULL,
    evidence TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_packages (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    primary_channel TEXT NOT NULL,
    primary_draft TEXT NOT NULL,
    secondary_drafts TEXT NOT NULL DEFAULT '[]',
    creative_action TEXT,
    status TEXT NOT NULL DEFAULT 'pending_review',
    send_result TEXT,
    rejection_note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_log (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    message_preview TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    company_id TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    trace TEXT,
    error TEXT,
    cost_estimate REAL
);

CREATE TABLE IF NOT EXISTS discovery_runs (
    id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    sources_queried TEXT NOT NULL,
    results_count INTEGER NOT NULL DEFAULT 0,
    cap_applied INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
"""
