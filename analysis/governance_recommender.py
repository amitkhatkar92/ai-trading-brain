"""
analysis/governance_recommender.py
======================================
LEARNING_ENGINE_001 — Recommendation generator.

No database writes. No IO. No live-system imports.

Converts edge data into typed, prioritised recommendations.

SAFETY GUARANTEE
----------------
This module NEVER suggests modifying:
    decision_engine.py
    risk_control.py
    execution_engine.py
    risk_guardian.py
    Any protected module listed in copilot-instructions.md

All recommendations require human review before implementation.
The approval gate is enforced in recommendation_tracker.py.

Recommendation types
--------------------
INCREASE_WEIGHT   : Amplify the influence of a well-performing filter
DECREASE_WEIGHT   : Reduce the penalty of an underperforming filter
REMOVE_FILTER     : Candidate for disabling (strong negative edge, n >= 20)
KEEP_FILTER       : Explicit confirmation to keep a strong filter unchanged
INVESTIGATE       : Anomaly worth examining manually (e.g. impossible accuracy)
COLLECT_MORE_DATA : Not enough observations for a decision
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from analysis.edge_detector import Edge, EdgeDirection, EdgeStrength, MIN_OBS_FOR_EDGE, BASELINE


# ── Config ────────────────────────────────────────────────────────────────────

REMOVE_ACCURACY_THRESHOLD   = 0.45   # below this + n >= MIN_TO_REMOVE → REMOVE
MIN_TO_REMOVE               = 20     # must have this many obs to recommend removal
KEEP_ACCURACY_THRESHOLD     = 0.70   # above this → KEEP (no change needed)
INCREASE_WEIGHT_THRESHOLD   = 0.65   # above baseline + meaningful n → INCREASE_WEIGHT
DECREASE_WEIGHT_THRESHOLD   = 0.52   # below this → DECREASE_WEIGHT

CONFIDENCE_HIGH   = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW    = "LOW"


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class Recommendation:
    """A single governance recommendation produced by the learning engine."""
    rec_id:       str           # e.g. "REC-001"
    rec_type:     str           # INCREASE_WEIGHT / DECREASE_WEIGHT / REMOVE_FILTER / etc.
    target:       str           # filter / signal name
    category:     str           # REJECTION_FILTER / QUALITY_TIER / NEWS_SIGNAL / OPTIONS
    current_accuracy: float     # observed accuracy %
    n_obs:        int
    suggestion:   str           # concise human-readable action
    rationale:    str           # why (includes edge score and direction)
    confidence:   str           # HIGH / MEDIUM / LOW
    priority:     int           # 1 = highest
    generated_at: str

    # Safety gate — always displayed prominently
    requires_human_approval: bool = True
    safe_to_auto_apply:      bool = False


# ── Recommendation generation ─────────────────────────────────────────────────

def _confidence(n: int, edge_magnitude: float) -> str:
    """Map sample size and effect size to confidence level."""
    if n >= 50 and edge_magnitude >= 0.25:
        return CONFIDENCE_HIGH
    elif n >= 20 and edge_magnitude >= 0.12:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_recommendations(
    all_edges:  List[Edge],
    rec_id_start: int = 1,
) -> List[Recommendation]:
    """
    Convert detected edges into prioritised recommendations.

    Args:
        all_edges:    output of detect_*_edges() functions
        rec_id_start: starting number for REC-NNN labels

    Returns:
        List of Recommendation objects, sorted by priority ascending.
    """
    recs   : List[Recommendation] = []
    counter = rec_id_start
    ts      = _now()

    # Sort edges to process strongest first
    sorted_edges = sorted(all_edges, key=lambda e: abs(e.edge_score))

    for edge in sorted_edges:
        acc   = edge.accuracy * 100  # back to pct for display
        mag   = abs(edge.accuracy - 0.50)
        conf  = _confidence(edge.n_obs, mag)

        if edge.direction == EdgeDirection.COLLECTING:
            recs.append(Recommendation(
                rec_id            = f"REC-{counter:03d}",
                rec_type          = "COLLECT_MORE_DATA",
                target            = edge.name,
                category          = edge.category,
                current_accuracy  = round(acc, 1),
                n_obs             = edge.n_obs,
                suggestion        = (
                    f"Collect {max(0, MIN_OBS_FOR_EDGE - edge.n_obs)} more "
                    f"observations before deciding on {edge.name}"
                ),
                rationale         = f"Only {edge.n_obs} obs — below threshold of {MIN_OBS_FOR_EDGE}",
                confidence        = CONFIDENCE_LOW,
                priority          = 5,
                generated_at      = ts,
            ))
            counter += 1
            continue

        if (edge.direction == EdgeDirection.NEGATIVE
                and edge.n_obs >= MIN_TO_REMOVE
                and edge.accuracy < REMOVE_ACCURACY_THRESHOLD):
            recs.append(Recommendation(
                rec_id            = f"REC-{counter:03d}",
                rec_type          = "REMOVE_FILTER",
                target            = edge.name,
                category          = edge.category,
                current_accuracy  = round(acc, 1),
                n_obs             = edge.n_obs,
                suggestion        = (
                    f"Consider disabling {edge.name}. "
                    f"It is blocking more winners than losers "
                    f"({acc:.1f}% accuracy, n={edge.n_obs})."
                ),
                rationale         = (
                    f"Accuracy {acc:.1f}% is below REMOVE threshold "
                    f"{REMOVE_ACCURACY_THRESHOLD*100:.0f}% with {edge.n_obs} obs. "
                    f"Edge score: {edge.edge_score:+.2f}."
                ),
                confidence        = conf,
                priority          = 1,
                generated_at      = ts,
            ))
            counter += 1

        elif (edge.direction == EdgeDirection.NEGATIVE
              and edge.accuracy < DECREASE_WEIGHT_THRESHOLD):
            pct_reduce = min(40, int((BASELINE - edge.accuracy) * 200))
            recs.append(Recommendation(
                rec_id            = f"REC-{counter:03d}",
                rec_type          = "DECREASE_WEIGHT",
                target            = edge.name,
                category          = edge.category,
                current_accuracy  = round(acc, 1),
                n_obs             = edge.n_obs,
                suggestion        = (
                    f"Reduce the penalty/weight of {edge.name} by ~{pct_reduce}%. "
                    f"Current accuracy {acc:.1f}% suggests it is over-penalising."
                ),
                rationale         = (
                    f"Accuracy {acc:.1f}% is {(0.50 - edge.accuracy)*100:.1f}pp below "
                    f"baseline. Edge score: {edge.edge_score:+.2f}."
                ),
                confidence        = conf,
                priority          = 2,
                generated_at      = ts,
            ))
            counter += 1

        elif (edge.direction == EdgeDirection.POSITIVE
              and edge.accuracy >= KEEP_ACCURACY_THRESHOLD):
            recs.append(Recommendation(
                rec_id            = f"REC-{counter:03d}",
                rec_type          = "KEEP_FILTER",
                target            = edge.name,
                category          = edge.category,
                current_accuracy  = round(acc, 1),
                n_obs             = edge.n_obs,
                suggestion        = (
                    f"Maintain {edge.name} unchanged. "
                    f"Strong accuracy {acc:.1f}% across {edge.n_obs} observations."
                ),
                rationale         = (
                    f"Accuracy {acc:.1f}% exceeds KEEP threshold "
                    f"{KEEP_ACCURACY_THRESHOLD*100:.0f}%. "
                    f"Edge score: {edge.edge_score:+.2f}."
                ),
                confidence        = conf,
                priority          = 4,
                generated_at      = ts,
            ))
            counter += 1

        elif (edge.direction == EdgeDirection.POSITIVE
              and edge.accuracy >= INCREASE_WEIGHT_THRESHOLD):
            pct_increase = min(25, int((edge.accuracy - 0.50) * 100))
            recs.append(Recommendation(
                rec_id            = f"REC-{counter:03d}",
                rec_type          = "INCREASE_WEIGHT",
                target            = edge.name,
                category          = edge.category,
                current_accuracy  = round(acc, 1),
                n_obs             = edge.n_obs,
                suggestion        = (
                    f"Increase influence/weight of {edge.name} by ~{pct_increase}%. "
                    f"It is reliably discriminating at {acc:.1f}%."
                ),
                rationale         = (
                    f"Accuracy {acc:.1f}% is {(edge.accuracy - 0.50)*100:.1f}pp above "
                    f"baseline. Edge score: {edge.edge_score:+.2f}."
                ),
                confidence        = conf,
                priority          = 3,
                generated_at      = ts,
            ))
            counter += 1

    # Sort by priority then by confidence
    conf_rank = {CONFIDENCE_HIGH: 0, CONFIDENCE_MEDIUM: 1, CONFIDENCE_LOW: 2}
    recs.sort(key=lambda r: (r.priority, conf_rank.get(r.confidence, 9)))
    return recs


# ── Pattern-based recommendations ────────────────────────────────────────────

def recommend_from_pattern(
    pattern_description: str,
    win_rate:            float,
    n:                   int,
    baseline:            float,
    source:              str,
    rec_id:              str,
) -> Recommendation:
    """
    Generate a single recommendation from a discovered pattern.

    This is used by learning_engine.py to convert top mined patterns
    into actionable guidance.
    """
    edge   = win_rate - baseline
    conf   = _confidence(n, abs(edge))
    ts     = _now()

    if edge > 0.15 and n >= 10:
        rec_type   = "INCREASE_WEIGHT"
        suggestion = (
            f"Pattern '{pattern_description}' achieves {win_rate*100:.1f}% WR "
            f"(+{edge*100:.1f}pp above baseline). "
            f"Consider boosting trade approval when this combination is present."
        )
        priority   = 2
    elif edge < -0.15 and n >= 10:
        rec_type   = "DECREASE_WEIGHT"
        suggestion = (
            f"Pattern '{pattern_description}' achieves only {win_rate*100:.1f}% WR "
            f"({edge*100:.1f}pp below baseline). "
            f"Consider adding an avoidance rule for this combination."
        )
        priority   = 1
    else:
        rec_type   = "COLLECT_MORE_DATA"
        suggestion = (
            f"Pattern '{pattern_description}': {win_rate*100:.1f}% WR ({n} obs). "
            f"Edge is present but needs more data to be actionable."
        )
        priority   = 5

    return Recommendation(
        rec_id            = rec_id,
        rec_type          = rec_type,
        target            = pattern_description,
        category          = f"PATTERN_{source.upper()}",
        current_accuracy  = round(win_rate * 100, 1),
        n_obs             = n,
        suggestion        = suggestion,
        rationale         = (
            f"Mined from {source}. WR={win_rate*100:.1f}%, "
            f"baseline={baseline*100:.1f}%, n={n}"
        ),
        confidence        = conf,
        priority          = priority,
        generated_at      = ts,
    )
