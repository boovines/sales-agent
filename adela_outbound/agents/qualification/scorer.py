from __future__ import annotations

import asyncio
import json
import logging

from adela_outbound.config import config

logger = logging.getLogger(__name__)

WEIGHT_VALUES = {'high': 3, 'medium': 2, 'low': 1}

FIT_TIER_THRESHOLDS = {'strong': 0.75, 'moderate': 0.50, 'weak': 0.30}

CRITERION_SCORING_PROMPT = (
    'You are evaluating a B2B prospect against a specific ICP criterion for '
    'Adela \u2014 a context and governance layer for services companies deploying '
    'bespoke technical work across enterprise clients. Score the prospect on a '
    '0-3 scale: 0=no evidence this criterion is met, 1=weak or indirect signal, '
    '2=moderate evidence, 3=strong clear evidence. Your evidence string must cite '
    'specific facts from the brief \u2014 never generic statements. Return a JSON '
    'object with exactly these keys: score (integer 0-3), evidence (string, 1-2 '
    'sentences citing specific details from the brief that justify the score), '
    'confidence (float 0.0-1.0 reflecting how certain you are given available '
    'information). Return only the JSON object.'
)


async def score_criterion(brief: dict, criterion: dict, client: object) -> dict:
    try:
        user_msg = (
            f'Criterion to evaluate: {criterion["name"]}\n'
            f'Criterion description: {criterion["description"]}\n'
            f'Weight: {criterion["weight"]}\n\n'
            f'Prospect information:\n'
            f'Company: {brief.get("company_name", brief.get("summary", "")[:50])}\n'
            f'Summary: {brief.get("summary", "")[:500]}\n'
            f'Current focus: {brief.get("current_focus", "")}\n'
            f'Pain points: {json.dumps(brief.get("pain_points", []))}\n'
            f'Adela relevance: {brief.get("adela_relevance", "")}\n'
            f'Personalization hooks: {json.dumps(brief.get("personalization_hooks", []))}'
        )

        response = await client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=300,
            system=CRITERION_SCORING_PROMPT,
            messages=[{'role': 'user', 'content': user_msg}],
        )

        content = response.content[0].text.strip() if response.content else ''

        # Strip markdown fences
        if content.startswith('```'):
            lines = content.split('\n')
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines).strip()

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return {
                'criterion_id': criterion['id'],
                'score': 0,
                'evidence': 'Scoring failed \u2014 JSON parse error',
                'confidence': 0.0,
            }

        score = int(parsed.get('score', 0))
        score = max(0, min(3, score))

        return {
            'criterion_id': criterion['id'],
            'score': score,
            'evidence': str(parsed.get('evidence', ''))[:500],
            'confidence': float(parsed.get('confidence', 0.5)),
        }
    except Exception as e:
        logger.warning(f'Criterion scoring failed for {criterion["id"]}: {e}')
        return {
            'criterion_id': criterion['id'],
            'score': 0,
            'evidence': f'Scoring unavailable: {str(e)[:100]}',
            'confidence': 0.0,
        }


async def score_all_criteria(brief: dict, icp: dict, client: object) -> list:
    criteria = icp.get('criteria', [])
    tasks = [score_criterion(brief, c, client) for c in criteria]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scores = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            criterion_id = criteria[i]['id'] if i < len(criteria) else f'criterion_{i}'
            logger.warning(f'score_criterion raised for {criterion_id}: {r}')
            scores.append({
                'criterion_id': criterion_id,
                'score': 0,
                'evidence': f'Exception: {str(r)[:100]}',
                'confidence': 0.0,
            })
        else:
            scores.append(r)

    return scores


def aggregate_scores(criterion_scores: list, icp: dict) -> dict:
    score_by_id = {s['criterion_id']: s['score'] for s in criterion_scores}
    weight_by_id = {
        c['id']: WEIGHT_VALUES.get(c['weight'], 1)
        for c in icp.get('criteria', [])
    }

    weighted_sum = sum(
        score_by_id.get(cid, 0) * w for cid, w in weight_by_id.items()
    )
    max_possible = sum(3 * w for w in weight_by_id.values())

    fit_score = round(weighted_sum / max_possible, 3) if max_possible > 0 else 0.0

    if fit_score >= FIT_TIER_THRESHOLDS['strong']:
        fit_tier = 'strong'
    elif fit_score >= FIT_TIER_THRESHOLDS['moderate']:
        fit_tier = 'moderate'
    elif fit_score >= FIT_TIER_THRESHOLDS['weak']:
        fit_tier = 'weak'
    else:
        fit_tier = 'disqualified'

    return {
        'fit_score': fit_score,
        'fit_tier': fit_tier,
        'weighted_sum': weighted_sum,
        'max_possible': max_possible,
    }
