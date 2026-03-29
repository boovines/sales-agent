# Adela Outbound — Company Discovery Agent

## Overview

The Company Discovery Agent is a continuously running background process that finds net-new companies matching the Adela ICP from real-time signals across Brave Search, GitHub, and Grok (for X/Twitter context). It outputs thin DiscoveryRecord objects into a SQLite `discovery_queue` table for downstream agents to process.

## Parallel Branch Architecture

This project is built across four concurrent branches, each running in a separate repo clone:

- **`feature/agent-discovery`** (this branch) — finds and queues new companies
- **`feature/agent-research`** — deep-dives on queued companies, writes prospect briefs
- **`feature/agent-qualification`** — scores and qualifies prospects, writes qualification briefs
- **`feature/agent-drafting`** — generates personalized outreach, writes outreach packages

All four agents communicate exclusively through the shared SQLite database (`adela.db`). No agent imports code from another agent's module. After all four branches merge, a fifth branch (`feature/dashboard`) adds the monitoring UI.

> :warning: **Shared Files — Do Not Modify**
>
> `adela_outbound/db/schemas.py` and `adela_outbound/db/contracts.py` are the canonical data contracts shared with three other agent branches running concurrently: `feature/agent-research`, `feature/agent-qualification`, `feature/agent-drafting`. Any modification to table schemas or Pydantic model field names will break those branches. These files are locked after the initial commit of US-001. If a schema change is truly necessary, coordinate across all four branches simultaneously before modifying.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your API keys

4. Start the server:
   ```bash
   uvicorn adela_outbound.api.main:app --reload --port 8000
   ```

5. Visit http://localhost:8000/docs

## Running Tests

```bash
pytest tests/ -v
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check with DB and scheduler status |
| POST | `/agents/discovery/run` | Trigger a manual discovery run |
| GET | `/agents/discovery/status` | Scheduler state and next run time |
| GET | `/agents/discovery/pipeline` | List discovery queue (filterable by status, source) |
| GET | `/agents/discovery/pipeline/stats` | Aggregate pipeline counts |
| GET | `/agents/discovery/pipeline/{company_id}` | Single company record by ID |
| GET | `/agents/discovery/stream` | SSE stream for live discovery updates |

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `BRAVE_API_KEY` | — | Brave Search API key for web signal collection |
| `GROK_API_KEY` | — | Grok API key for X/Twitter context research |
| `GITHUB_TOKEN` | — | GitHub personal access token (public repo read only) |
| `ANTHROPIC_API_KEY` | — | Anthropic Claude API key (used by Research/Qualification agents) |
| `FIRECRAWL_API_KEY` | — | Firecrawl API key (used by Research agent) |
| `PERPLEXITY_API_KEY` | — | Perplexity API key (used by Research agent) |
| `COMPOSIO_API_KEY` | — | Composio API key (used by Drafting agent) |
| `DAILY_DISCOVERY_CAP` | `20` | Maximum new companies added to queue per day |
| `DISCOVERY_INTERVAL_HOURS` | `12` | Scheduled discovery run interval in hours |
| `DB_PATH` | `adela.db` | Path to SQLite database file (auto-created) |
| `DASHBOARD_TOKEN` | `dev-token` | Bearer token for dashboard API authentication |

---

## Adela Outbound — Prospect Research Agent

### What This Agent Does

The Research Agent is triggered per company from the `discovery_queue`, runs deep parallel research using Firecrawl, Perplexity, GitHub, and Grok, then synthesises a prospect brief using Claude Sonnet. It writes output to the `prospect_briefs` SQLite table for pickup by the Qualification Agent.

### Parallel Branch Architecture

This agent is built on the `feature/agent-research` branch — one of four agents developed concurrently in separate repo clones. All inter-agent communication goes through SQLite only (never direct Python calls).

**Locked files** (owned by `feature/agent-discovery` — do not modify):
- `adela_outbound/db/schemas.py`
- `adela_outbound/db/contracts.py`

The `feature/agent-discovery` US-001 commit must be cherry-picked before any code on this branch will import correctly.

### Prerequisites

1. **Python 3.9.6+**
2. Cherry-pick the discovery agent's US-001 commit to get shared schemas:
   ```bash
   git fetch origin
   git cherry-pick <US-001-commit-hash>
   ```

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

### Running

```bash
uvicorn adela_outbound.api.main:app --reload --port 8001
```

> **Note:** Port 8001 is used to avoid conflict with the discovery agent running on 8000 during development. In the merged service both share port 8000 under different prefixes.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/research/run/{company_id}` | Trigger research for a company (runs in background) |
| GET | `/research/queue` | List queued companies ordered by pre_score |
| GET | `/research/{company_id}/brief` | Get the completed research brief for a company |
| GET | `/research/stream` | SSE stream of real-time research events |

### Testing

```bash
python3 -m pytest tests/ -v
```

### Shared Contract Warning

The files `adela_outbound/db/schemas.py` and `adela_outbound/db/contracts.py` are shared contracts across all four agent branches. They are owned by `feature/agent-discovery` and must never be modified on this branch. If you need schema changes, coordinate with the discovery branch first.
