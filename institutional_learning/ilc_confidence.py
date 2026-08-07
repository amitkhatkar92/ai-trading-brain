"""institutional_learning/ilc_confidence.py — Phase 5: Learning Confidence Scoring."""
from __future__ import annotations

import logging
from typing import List

from .ilc_config import (
    CONFIDENCE_HIGH_DNA_MIN, CONFIDENCE_HIGH_MOVE_MIN_PCT,
    CONFIDENCE_MEDIUM_DNA_MIN, CONFIDENCE_MEDIUM_MOVE_MIN_PCT,
)
from .ilc_models import LearningConfidence

log = logging.getLogger(__name__)


def score_confidence(
    category: str,
    dna_coverage: int,
    move_pct: float,
    evidence_count: int,
    is_scanned: bool,
    primary_cause: str,
) -> str:
    """
    Assign a learning confidence level to a single action.

    Rules (in priority order):
        HIGH:         DNA ≥ 3 AND |move| ≥ 2% AND evidence ≥ 2
        MEDIUM:       DNA ≥ 1 AND |move| ≥ 1% OR (scanned AND evidence ≥ 1)
        LOW:          has some evidence OR was scanned
        EXPERIMENTAL: category C/D with no DNA and no scan history

    Only HIGH and MEDIUM actions may generate Institutional Knowledge.
    """
    abs_move = abs(move_pct)
    cause_is_external = primary_cause in ("ExternalEvent", "None")

    # External events → never HIGH (we can't predict them)
    if cause_is_external:
        return LearningConfidence.LOW

    # HIGH: strongest evidence base
    if (dna_coverage >= CONFIDENCE_HIGH_DNA_MIN
            and abs_move >= CONFIDENCE_HIGH_MOVE_MIN_PCT
            and evidence_count >= 2):
        return LearningConfidence.HIGH

    # MEDIUM: reasonable evidence
    if (dna_coverage >= CONFIDENCE_MEDIUM_DNA_MIN
            and abs_move >= CONFIDENCE_MEDIUM_MOVE_MIN_PCT):
        return LearningConfidence.MEDIUM

    if is_scanned and evidence_count >= 1:
        return LearningConfidence.MEDIUM

    # LOW: some signal exists
    if dna_coverage > 0 or is_scanned:
        return LearningConfidence.LOW

    # EXPERIMENTAL: no prior evidence
    return LearningConfidence.EXPERIMENTAL


def score_all_actions(
    actions: list,
    analyses: list,
    causes: list,
) -> List[str]:
    """
    Score confidence for every learning action.

    Returns list of confidence strings, parallel to actions list.
    """
    # Build quick-lookup maps
    analysis_map = {a.symbol: a for a in analyses}
    cause_map    = {c.symbol: c for c in causes}

    confidences: List[str] = []
    for action in actions:
        sym      = action.symbol
        analysis = analysis_map.get(sym)
        cause    = cause_map.get(sym)

        dna_cov        = analysis.dna_coverage if analysis else 0
        move_pct       = analysis.stock_move.daily_return_pct if analysis else 0.0
        evidence_count = len(cause.evidence) if cause else 0
        is_scanned     = analysis is not None and analysis.iios_signal is not None
        primary_cause  = cause.primary_cause if cause else "Unknown"

        conf = score_confidence(
            category=action.category,
            dna_coverage=dna_cov,
            move_pct=move_pct,
            evidence_count=evidence_count,
            is_scanned=is_scanned,
            primary_cause=primary_cause,
        )
        confidences.append(conf)

    conf_summary = {
        LearningConfidence.HIGH:         confidences.count(LearningConfidence.HIGH),
        LearningConfidence.MEDIUM:       confidences.count(LearningConfidence.MEDIUM),
        LearningConfidence.LOW:          confidences.count(LearningConfidence.LOW),
        LearningConfidence.EXPERIMENTAL: confidences.count(LearningConfidence.EXPERIMENTAL),
    }
    log.info("[ILC] Phase 5 Confidence: %s", conf_summary)
    return confidences
