"""
scripts/knowledge_system/research_priority_engine_001.py
=========================================================
Stage 4 — Research Priority Engine (KSL-001).

Scores and ranks research questions by trading relevance, effect size,
data availability, implementation cost and risk reduction value.

Scoring model: weighted sum of 9 factors, each 0-10.
Final priority is 0-100.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .ksl_models import ResearchArea, ResearchQuestion

# Factor weights (must sum to 1.0)
WEIGHTS: Dict[str, float] = {
    "trading_relevance":   0.20,  # does it affect live trading quality directly?
    "effect_size":         0.20,  # magnitude of observed problem
    "selection_importance":0.15,  # affects 20→5 selection (most critical path)
    "frequency":           0.10,  # how often does the pattern occur?
    "confidence":          0.10,  # statistical confidence (pattern strength)
    "data_availability":   0.10,  # can we run the experiment now?
    "impact":              0.08,  # potential improvement to ge2_rate
    "risk_reduction":      0.05,  # reduces risk of false selections
    "implementation_cost": 0.02,  # lower cost → higher score (inverse)
}

# Relevance of each ResearchArea to live trading quality
AREA_RELEVANCE: Dict[str, float] = {
    ResearchArea.C2_RANKING.value:   10.0,  # 20→5 selection is core
    ResearchArea.V3_DISCOVERY.value:  9.0,  # 20-pool quality
    ResearchArea.STRATEGY.value:      8.0,  # strategy gate affects pool
    ResearchArea.DIRECTION.value:     7.5,  # separate UP/DOWN handling
    ResearchArea.REGIME.value:        7.0,  # regime-specific adjustments
    ResearchArea.POOL.value:          6.5,
    ResearchArea.EXECUTION.value:     4.0,
    ResearchArea.OTHER.value:         3.0,
}


def _score_trading_relevance(rq: ResearchQuestion) -> float:
    return AREA_RELEVANCE.get(rq.problem_area.value, 5.0)


def _score_effect_size(rq: ResearchQuestion, patterns_by_id: Dict) -> float:
    """Score based on pattern effect size."""
    pid = rq.source_pattern_ids[0] if rq.source_pattern_ids else None
    if not pid:
        return 5.0
    p = patterns_by_id.get(pid)
    if not p:
        return 5.0
    # Scale effect_size to 0-10
    return min(abs(p.effect_size) / 0.20 * 10, 10.0)


def _score_selection_importance(rq: ResearchQuestion) -> float:
    """Questions about 20→5 selection path score highest."""
    q_lower = rq.question.lower()
    if any(kw in q_lower for kw in ["top-5", "top5", "c2", "ranking", "capture"]):
        return 10.0
    if any(kw in q_lower for kw in ["miss", "false reject", "strategy"]):
        return 8.0
    return 5.0


def _score_frequency(rq: ResearchQuestion, patterns_by_id: Dict) -> float:
    """Score based on pattern sample size."""
    pid = rq.source_pattern_ids[0] if rq.source_pattern_ids else None
    if not pid:
        return 5.0
    p = patterns_by_id.get(pid)
    if not p:
        return 5.0
    return min(p.sample_size / 50 * 10, 10.0)


def _score_confidence(rq: ResearchQuestion, patterns_by_id: Dict) -> float:
    """Score based on pattern strength."""
    pid = rq.source_pattern_ids[0] if rq.source_pattern_ids else None
    if not pid:
        return 5.0
    p = patterns_by_id.get(pid)
    if not p:
        return 5.0
    return p.strength * 10


def _score_data_availability(rq: ResearchQuestion) -> float:
    """Penalize questions with known data gaps."""
    if not rq.known_data_gaps:
        return 10.0
    if len(rq.known_data_gaps) == 1:
        return 7.0
    return 5.0


def _score_impact(rq: ResearchQuestion) -> float:
    """Higher for questions that could improve ge2_rate."""
    if "ge2" in rq.target_metric.lower():
        return 8.0
    if "dir_acc" in rq.target_metric.lower():
        return 7.0
    return 5.0


def _score_risk_reduction(rq: ResearchQuestion) -> float:
    """Higher for questions that reduce selection error risk."""
    if "false reject" in rq.question.lower() or "false_reject" in rq.question.lower():
        return 8.0
    if "miss" in rq.question.lower():
        return 7.0
    return 5.0


def _score_implementation_cost(rq: ResearchQuestion) -> float:
    """Lower cost = higher score. Research-only questions score high."""
    if rq.leakage_risk == "LOW":
        return 9.0
    if rq.leakage_risk == "MEDIUM":
        return 6.0
    return 3.0


def compute_priority(rq: ResearchQuestion, patterns_by_id: Dict) -> float:
    """Compute 0-100 priority score for a research question."""
    scores = {
        "trading_relevance":    _score_trading_relevance(rq),
        "effect_size":          _score_effect_size(rq, patterns_by_id),
        "selection_importance": _score_selection_importance(rq),
        "frequency":            _score_frequency(rq, patterns_by_id),
        "confidence":           _score_confidence(rq, patterns_by_id),
        "data_availability":    _score_data_availability(rq),
        "impact":               _score_impact(rq),
        "risk_reduction":       _score_risk_reduction(rq),
        "implementation_cost":  _score_implementation_cost(rq),
    }
    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(total * 10, 1)  # scale to 0-100


def prioritize_questions(
    questions: List[ResearchQuestion],
    patterns: List = None,
) -> List[ResearchQuestion]:
    """
    Assign priority scores and return sorted list (highest first).
    Patterns list is used for effect-size and sample-size scoring.
    """
    patterns_by_id: Dict = {}
    if patterns:
        for p in patterns:
            patterns_by_id[p.pattern_id] = p

    from .ksl_models import ResearchQuestionStatus
    for rq in questions:
        rq.research_priority = compute_priority(rq, patterns_by_id)

    eligible = [q for q in questions if q.status != ResearchQuestionStatus.SUPERSEDED]
    return sorted(eligible, key=lambda q: q.research_priority, reverse=True)
