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


# Adela Outbound — ICP Qualification Agent

## What This Agent Does

The Qualification Agent scores each researched company against the Adela ICP (Ideal Customer Profile) definition using Claude Sonnet. It produces a per-criterion `QualificationBrief`, then **pauses for human-in-the-loop (HITL) approval** before advancing the company through the pipeline.

- Companies scoring above the disqualification threshold pause for manual review
- Companies with `fit_tier = disqualified` (fit_score < 0.30) are auto-rejected — never auto-approved
- Approved companies move to `status = 'qualified'` in `discovery_queue` for pickup by the Drafting Agent
- Rejection notes feed a weekly ICP refinement loop

## HITL Architecture

Every qualification decision must come from Justin via the API — the graph **never** auto-approves.

1. `POST /qualification/run/{company_id}` triggers the LangGraph graph
2. The graph scores all ICP criteria, builds a qualification brief, and writes it to SQLite as `pending_review`
3. The graph **pauses at `hitl_gate`** via LangGraph `interrupt_before`
4. Justin reviews the brief via `GET /qualification/{company_id}/brief` or `GET /qualification/queue`
5. `POST /qualification/approve/{company_id}` or `POST /qualification/reject/{company_id}` resumes the graph
6. The `resume_handler` node updates `qualification_briefs` and `discovery_queue` accordingly

Exception: companies with `fit_tier = disqualified` bypass the HITL gate — they are routed directly to `resume_handler` with `decision = 'auto_rejected'`.

## Parallel Branch Architecture

This agent is one of four built concurrently in separate repo clones:

| Branch | Agent | Port |
|---|---|---|
| `feature/agent-discovery` | Discovery | 8000 |
| `feature/agent-research` | Research | 8001 |
| `feature/agent-qualification` | Qualification | 8002 |
| `feature/agent-drafting` | Drafting | 8003 |

All inter-agent communication goes through **SQLite only** — never direct Python calls between agents.

**Cherry-pick requirement:** `feature/agent-discovery` US-001 must be cherry-picked into this branch before development. This provides the shared DB schemas and contracts.

**Locked files (do not modify):**
- `adela_outbound/db/schemas.py` — owned by `feature/agent-discovery`
- `adela_outbound/db/contracts.py` — owned by `feature/agent-discovery`
- `adela_outbound/api/main.py` — owned by `feature/agent-discovery`
- `adela_outbound/scheduler.py` — owned by `feature/agent-discovery`

## Setup

```bash
# Clone and checkout
git clone <repo-url>
git checkout feature/agent-qualification

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

## Running

```bash
# Development server (port 8002 to avoid conflict with discovery 8000 and research 8001)
uvicorn adela_outbound.api.main:app --port 8002 --reload
```

## API Endpoints

All endpoints are under the `/qualification` prefix.

| Method | Path | Description |
|---|---|---|
| `POST` | `/qualification/run/{company_id}` | Trigger qualification for a researched company |
| `POST` | `/qualification/approve/{company_id}` | Approve a paused qualification |
| `POST` | `/qualification/reject/{company_id}` | Reject a paused qualification (note required) |
| `GET` | `/qualification/queue` | List pending_review briefs ordered by fit_score |
| `GET` | `/qualification/{company_id}/brief` | Get full qualification brief with criterion scores |
| `GET` | `/qualification/icp` | Get current ICP definition |
| `PUT` | `/qualification/icp` | Update ICP criteria (creates new version) |
| `GET` | `/qualification/icp/suggestions` | List pending ICP refinement suggestions |
| `POST` | `/qualification/icp/suggestions/{id}/accept` | Accept an ICP suggestion |
| `POST` | `/qualification/icp/suggestions/{id}/reject` | Reject an ICP suggestion |
| `GET` | `/qualification/stream` | SSE stream of qualification events |

> :warning: **Rejection notes are mandatory.** `POST /reject/{company_id}` returns HTTP 422 if the `note` field is missing or empty. This is enforced at the API layer and is intentional — rejection notes feed the weekly ICP refinement loop.

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run qualification-specific tests
python3 -m pytest tests/test_qualification_scorer.py tests/test_qualification_graph.py -v
```

## Shared Contract Warning

The `QualificationBrief`, `ICPCriterion`, and `ICPDefinition` contracts in `adela_outbound/db/contracts.py` are shared across all four agent branches. **Do not modify these files** — they are owned by `feature/agent-discovery` and any changes must be coordinated there first.