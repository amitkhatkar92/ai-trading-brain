"""institutional_learning/ilc_priority.py — Phase 6: Expected Improvement Gain + Priority."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

from .ilc_config import EIG_WEIGHTS, TARGET_COST
from .ilc_models import LearningConfidence

log = logging.getLogger(__name__)

# Confidence factor (scales raw EIG)
_CONFIDENCE_FACTOR = {
    LearningConfidence.HIGH:         1.00,
    LearningConfidence.MEDIUM:       0.70,
    LearningConfidence.LOW:          0.40,
    LearningConfidence.EXPERIMENTAL: 0.20,
}

# Historical miss frequency by root cause (rough empirical prior)
_CAUSE_FREQUENCY = {
    "Scanner":               0.25,
    "PMCI":                  0.20,
    "CDS":                   0.15,
    "DNA":                   0.18,
    "Knowledge":             0.10,
    "Research":              0.08,
    "PortfolioConstraint":   0.05,
    "RiskFilter":            0.05,
    "MissingFeature":        0.12,
    "MissingData":           0.10,
    "MissingHistoricalPattern": 0.15,
    "WrongThreshold":        0.20,
    "ExternalEvent":         0.02,
    "None":                  0.00,
}

# Category portfolio distribution weights (from design doc example)
_CATEGORY_PORTFOLIO_WEIGHT = {
    "A": 0.32,   # Portfolio / calibration — highest impact
    "E": 0.18,   # Scanner / DNA
    "B": 0.14,   # DNA confidence
    "C": 0.11,   # PMCI / hypothesis
    "D": 0.08,   # Knowledge / research
    "F": 0.09,   # Historical
    "G": 0.08,   # Relationship
}


@dataclass
class EIGResult:
    action_id: str
    symbol: str
    category: str
    target_system: str
    description: str
    primary_cause: str
    confidence: str
    move_pct: float
    eig_raw: float          # unscaled
    eig_score: float        # confidence-adjusted
    implementation_cost: float
    priority_rank: int = 0  # set after sorting


def compute_eig(
    action_id: str,
    symbol: str,
    category: str,
    target_system: str,
    description: str,
    primary_cause: str,
    confidence: str,
    move_pct: float,
) -> EIGResult:
    """
    Compute Expected Improvement Gain for one learning action.

    EIG = base_weight * cause_frequency * |move_magnitude| * portfolio_weight
          / implementation_cost
    Adjusted by confidence_factor.
    """
    base_weight    = EIG_WEIGHTS.get(category, 0.50)
    cause_freq     = _CAUSE_FREQUENCY.get(primary_cause, 0.10)
    move_magnitude = min(abs(move_pct) / 5.0, 1.0)   # normalise to 0-1 (5% = max)
    port_weight    = _CATEGORY_PORTFOLIO_WEIGHT.get(category, 0.10)
    impl_cost      = max(TARGET_COST.get(target_system, 0.30), 0.05)   # avoid div/0
    conf_factor    = _CONFIDENCE_FACTOR.get(confidence, 0.30)

    eig_raw = (base_weight * cause_freq * move_magnitude * port_weight) / impl_cost
    eig_adj = eig_raw * conf_factor

    return EIGResult(
        action_id=action_id,
        symbol=symbol,
        category=category,
        target_system=target_system,
        description=description,
        primary_cause=primary_cause,
        confidence=confidence,
        move_pct=move_pct,
        eig_raw=round(eig_raw, 4),
        eig_score=round(eig_adj, 4),
        implementation_cost=impl_cost,
    )


def prioritize_actions(
    actions: list,
    confidences: List[str],
    analyses: list,
    causes: list,
) -> List[EIGResult]:
    """
    Compute EIG for every learning action and return them sorted by priority.

    Args:
        actions:     List[LearningAction] from pga_learning
        confidences: parallel list of confidence strings (from Phase 5)
        analyses:    List[StockAnalysis] from pga_analyzer
        causes:      List[RootCause] from pga_root_cause

    Returns list of EIGResult sorted by eig_score descending.
    """
    analysis_map = {a.symbol: a for a in analyses}
    cause_map    = {c.symbol: c for c in causes}
    eig_results: List[EIGResult] = []

    for action, conf in zip(actions, confidences):
        sym      = action.symbol
        analysis = analysis_map.get(sym)
        cause    = cause_map.get(sym)
        move_pct = analysis.stock_move.daily_return_pct if analysis else 0.0
        p_cause  = cause.primary_cause if cause else "Unknown"

        eig = compute_eig(
            action_id=action.action_id,
            symbol=sym,
            category=action.category,
            target_system=action.target_system,
            description=action.description,
            primary_cause=p_cause,
            confidence=conf,
            move_pct=move_pct,
        )
        eig_results.append(eig)

    eig_results.sort(key=lambda e: e.eig_score, reverse=True)
    for rank, e in enumerate(eig_results, 1):
        e.priority_rank = rank

    # Log top 3
    for e in eig_results[:3]:
        log.info(
            "[ILC] Phase 6 Priority #%d: %s %s EIG=%.4f conf=%s",
            e.priority_rank, e.symbol, e.category, e.eig_score, e.confidence,
        )

    if eig_results:
        # Log overall distribution by category
        cat_eig: dict = {}
        for e in eig_results:
            cat_eig[e.category] = cat_eig.get(e.category, 0.0) + e.eig_score
        total = sum(cat_eig.values()) or 1
        cat_pct = {k: f"{100*v/total:.0f}%" for k, v in sorted(cat_eig.items(), key=lambda x: -x[1])}
        log.info("[ILC] EIG distribution: %s", cat_pct)

    return eig_results
