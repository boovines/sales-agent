from __future__ import annotations

import json
import logging

from adela_outbound.config import config

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = (
    'You are a B2B sales research analyst preparing a prospect brief for outbound sales. '
    'The product being sold is Adela \u2014 a context and governance layer for services companies '
    'deploying bespoke technical work across enterprise clients. '
    'Adela solves: (1) context fragmentation across client deployments, '
    '(2) lack of versioned SOPs and governance for AI agent deployments, '
    '(3) inability to compound learnings across client accounts. '
    'The ICP is services companies that have crossed from project work into infrastructure mode '
    '\u2014 deploying the same core product across 5+ enterprise clients, especially in regulated industries. '
    'Write as someone who has done 30 minutes of genuine research. '
    'Rules you must follow: '
    '(1) Lead with what the company is doing RIGHT NOW, not their general pitch. '
    '(2) Pain points must be specific and evidenced from the research provided \u2014 never generic assumptions. '
    '(3) adela_relevance must name the specific gap or signal that makes Adela relevant \u2014 '
    'specific enough to use verbatim in an outreach opening line. '
    'Bad example: "Adela could help with context management." '
    'Good example: "They are scaling from 3 to 12 enterprise fintech clients and their GitHub issue #31 '
    'describes a multi-tenant context isolation problem that maps directly to Adela SOP versioning." '
    '(4) personalization_hooks must be actionable concrete details a human can reference \u2014 not generic observations. '
    '(5) Never invent facts not in the research. Say "not found" rather than guessing.'
)

FALLBACK_BRIEF: dict = {
    'summary': 'Research synthesis unavailable \u2014 Claude API call failed. Raw research data is stored in the raw_research field for manual review.',
    'current_focus': '',
    'pain_points': [],
    'adela_relevance': 'Unable to determine \u2014 review raw_research field for manual assessment.',
    'personalization_hooks': [],
    'recommended_channel': 'email',
    'research_sources': [],
}


async def build_brief(state: dict, client: object) -> dict:
    record = state.get('discovery_record', {})
    company_name = record.get('company_name', 'Unknown')
    website = record.get('website', 'unknown')
    fc = state.get('firecrawl_result', {})
    px = state.get('perplexity_result', {})
    gh = state.get('github_result', {})
    gr = state.get('grok_result', {})

    user_prompt = (
        f'Company: {company_name}\n'
        f'Website: {website}\n\n'
        f'## Website Content (scraped)\n'
        f'{(fc.get("markdown") or "Not available")[:3000]}\n\n'
        f'## News / Funding / Press\n'
        f'{px.get("synthesis") or "Not available"}\n\n'
        f'## GitHub Activity\n'
        f'Public repos: {json.dumps([{"name": r.get("name"), "description": r.get("description")} for r in gh.get("repos", [])[:3]])}\n'
        f'Open issues count: {len(gh.get("open_issues", []))}\n'
        f'Adela-relevant issues: {json.dumps(gh.get("adela_opportunity_issues", [])[:2])}\n\n'
        f'## Founder Twitter/X Context\n'
        f'Recent focus: {gr.get("recent_focus") or "Not available"}\n'
        f'Pain points mentioned: {json.dumps(gr.get("pain_points_mentioned", []))}\n\n'
        f'Respond with a JSON object with EXACTLY these keys (no extras): '
        f'summary (string, 200-300 words synthesising all research), '
        f'current_focus (string, 1-2 sentences on what they are building right now), '
        f'pain_points (array of 2-4 strings, each a specific evidenced pain point), '
        f'adela_relevance (string, 1-2 sentences on why Adela is specifically relevant to this company now), '
        f'personalization_hooks (array of 2-3 strings, each a concrete detail for outreach opening), '
        f'recommended_channel (string, exactly one of: email, linkedin, github \u2014 choose github only if adela_opportunity_issues is non-empty), '
        f'research_sources (array of strings, source URLs or names). '
        f'Return only the JSON object.'
    )

    response = await client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
    )

    content = ''
    if response.content and len(response.content) > 0:
        content = response.content[0].text or ''
    content = content.strip()

    # Strip markdown fences
    if content.startswith('```'):
        lines = content.split('\n')
        lines = [l for l in lines if not l.strip().startswith('```')]
        content = '\n'.join(lines).strip()
    if content.startswith('json'):
        content = content[4:].strip()

    parsed = json.loads(content)

    required_keys = {
        'summary': '',
        'current_focus': '',
        'pain_points': [],
        'adela_relevance': '',
        'personalization_hooks': [],
        'recommended_channel': 'email',
        'research_sources': [],
    }
    for k, default in required_keys.items():
        if k not in parsed:
            parsed[k] = default

    return parsed
