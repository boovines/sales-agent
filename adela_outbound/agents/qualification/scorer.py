from __future__ import annotations


async def score_criterion(brief: dict, criterion: dict, client: object) -> dict:
    return {'criterion_id': '', 'score': 0, 'evidence': '', 'confidence': 0.0}


def aggregate_scores(criterion_scores: list, icp: dict) -> dict:
    return {'fit_score': 0.0, 'fit_tier': 'disqualified'}
