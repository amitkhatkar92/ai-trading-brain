"""
analysis/rejection_classifier.py
====================================
REJECTION_AUDIT_001 — Pure classification functions.

No database. No IO. No live-system imports.
All functions are deterministic and unit-testable.

Core question answered by this module:
    "Was the rejection correct?"

Terminology
-----------
CORRECT_REJECTION  : price moved adversely — the rejection saved a loss.
FALSE_REJECTION    : price moved favourably — the rejection caused a missed winner.
NEUTRAL            : move too small to classify (<= MIN_MOVE_PCT in either direction).
PENDING            : follow-through price data not yet available.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class RejectionReason(str, Enum):
    """Why a trade candidate was rejected by the system."""
    LOW_DECISION_SCORE  = "LOW_DECISION_SCORE"   # score < threshold
    LOW_QUALITY_SCORE   = "LOW_QUALITY_SCORE"    # composite quality < gate
    LOW_SFT             = "LOW_SFT"              # symbol SFT class = LOW
    HIGH_VOL_REGIME     = "HIGH_VOL_REGIME"      # regime not suitable for strategy
    MAX_POSITIONS       = "MAX_POSITIONS"        # position count cap hit
    DAILY_LOSS_LIMIT    = "DAILY_LOSS_LIMIT"     # daily loss limit reached
    CORRELATED_POSITION = "CORRELATED_POSITION"  # already holding correlated symbol
    LOW_CONVICTION      = "LOW_CONVICTION"       # margin above threshold too thin
    MANUAL_OVERRIDE     = "MANUAL_OVERRIDE"      # manually rejected
    UNKNOWN             = "UNKNOWN"


class RejectionOutcome(str, Enum):
    CORRECT_REJECTION = "CORRECT_REJECTION"  # saved a loss  ✅
    FALSE_REJECTION   = "FALSE_REJECTION"    # missed a winner  ❌
    NEUTRAL           = "NEUTRAL"            # move too small to judge
    PENDING           = "PENDING"            # no follow-through data yet


# Minimum absolute price move (%) before we classify the rejection as meaningful
MIN_MOVE_PCT: float = 2.0

# Reason-level expected accuracy benchmarks (theoretical)
# Used to colour-code underperforming rejection reasons in the report.
REASON_EXPECTED_ACCURACY: Dict[str, float] = {
    RejectionReason.LOW_SFT:             0.75,  # strongest signal
    RejectionReason.HIGH_VOL_REGIME:     0.72,
    RejectionReason.LOW_DECISION_SCORE:  0.65,
    RejectionReason.LOW_QUALITY_SCORE:   0.65,
    RejectionReason.LOW_CONVICTION:      0.60,
    RejectionReason.CORRELATED_POSITION: 0.58,
    RejectionReason.MAX_POSITIONS:       0.50,  # capacity constraint — weakest signal
    RejectionReason.DAILY_LOSS_LIMIT:    0.50,
    RejectionReason.MANUAL_OVERRIDE:     0.55,
    RejectionReason.UNKNOWN:             0.50,
}


# ── Core outcome classification ───────────────────────────────────────────────

def classify_outcome(
    price_at_rejection: float,
    price_after:        float,
    direction:          str,            # "LONG" or "SHORT"
    min_move_pct:       float = MIN_MOVE_PCT,
) -> RejectionOutcome:
    """
    Classify a rejection as CORRECT, FALSE, or NEUTRAL.

    For a LONG trade that was rejected:
        price goes UP   → FALSE_REJECTION   (we missed a winner)
        price goes DOWN → CORRECT_REJECTION (we saved a loss)

    For a SHORT trade that was rejected:
        price goes DOWN → FALSE_REJECTION
        price goes UP   → CORRECT_REJECTION

    Args:
        price_at_rejection: price when the trade was rejected.
        price_after:        price N days later (use 5d for primary classification).
        direction:          "LONG" or "SHORT".
        min_move_pct:       minimum move to consider meaningful.

    Returns:
        RejectionOutcome enum value.
    """
    if price_at_rejection <= 0 or price_after <= 0:
        return RejectionOutcome.NEUTRAL

    move_pct = (price_after - price_at_rejection) / price_at_rejection * 100

    if abs(move_pct) <= min_move_pct:
        return RejectionOutcome.NEUTRAL

    if direction.upper() == "LONG":
        return (RejectionOutcome.FALSE_REJECTION   if move_pct > 0
                else RejectionOutcome.CORRECT_REJECTION)
    else:  # SHORT
        return (RejectionOutcome.FALSE_REJECTION   if move_pct < 0
                else RejectionOutcome.CORRECT_REJECTION)


def favorable_move_pct(
    price_at_rejection: float,
    price_after:        float,
    direction:          str,
) -> float:
    """
    Signed percentage move in the trade's favour.

    LONG: positive = favourable  (price went up)
    SHORT: positive = favourable (price went down)
    """
    if price_at_rejection <= 0:
        return 0.0
    raw = (price_after - price_at_rejection) / price_at_rejection * 100
    return round(raw if direction.upper() == "LONG" else -raw, 3)


# ── Batch statistics ──────────────────────────────────────────────────────────

def compute_accuracy_stats(records: List[dict]) -> dict:
    """
    Overall rejection accuracy across all classified records.

    Args:
        records: list of dicts, each must have "rejection_outcome" key.
                 PENDING records are excluded from accuracy calculation.

    Returns:
        Dict with: total, pending, classified, correct, false, neutral,
                   accuracy_pct, false_negative_pct
    """
    total    = len(records)
    pending  = [r for r in records if r.get("rejection_outcome") == "PENDING"]
    closed   = [r for r in records if r.get("rejection_outcome") != "PENDING"]
    correct  = [r for r in closed if r.get("rejection_outcome") == "CORRECT_REJECTION"]
    false_r  = [r for r in closed if r.get("rejection_outcome") == "FALSE_REJECTION"]
    neutral  = [r for r in closed if r.get("rejection_outcome") == "NEUTRAL"]

    classified = len(correct) + len(false_r)  # neutral excluded from accuracy

    accuracy = (
        round(len(correct) / classified * 100, 1)
        if classified > 0 else 0.0
    )
    false_negative_pct = (
        round(len(false_r) / classified * 100, 1)
        if classified > 0 else 0.0
    )

    return {
        "total":              total,
        "pending":            len(pending),
        "classified":         len(closed),
        "correct":            len(correct),
        "false_rejections":   len(false_r),
        "neutral":            len(neutral),
        "accuracy_pct":       accuracy,
        "false_negative_pct": false_negative_pct,
    }


def accuracy_by_reason(records: List[dict]) -> Dict[str, dict]:
    """
    Per-reason rejection accuracy.

    Returns dict keyed by rejected_reason, each with accuracy stats.
    """
    buckets: Dict[str, list] = defaultdict(list)
    for r in records:
        reason = r.get("rejected_reason", "UNKNOWN")
        buckets[reason].append(r)

    result = {}
    for reason, recs in buckets.items():
        stats = compute_accuracy_stats(recs)
        expected = REASON_EXPECTED_ACCURACY.get(reason, 0.50)
        actual   = stats["accuracy_pct"] / 100

        if stats["classified"] < 5:
            verdict = "INSUFFICIENT_DATA"
        elif actual >= expected + 0.10:
            verdict = "OUTPERFORMING"
        elif actual >= expected - 0.05:
            verdict = "ON_TARGET"
        elif actual >= expected - 0.15:
            verdict = "UNDERPERFORMING"
        else:
            verdict = "BROKEN"

        result[reason] = {**stats, "expected_pct": round(expected * 100, 1), "verdict": verdict}

    return result


def accuracy_by_quality_tier(records: List[dict]) -> Dict[str, dict]:
    """
    Per quality-tier rejection accuracy.

    Insight: if we are rejecting PREMIUM-quality trades at high accuracy,
    the rejection system is working. If PREMIUM rejections have low accuracy
    (many false negatives), the rejection criteria are too aggressive.
    """
    buckets: Dict[str, list] = defaultdict(list)
    for r in records:
        tier = r.get("quality_tier", "UNKNOWN")
        buckets[tier].append(r)

    return {tier: compute_accuracy_stats(recs) for tier, recs in buckets.items()}


def missed_winner_analysis(records: List[dict]) -> dict:
    """
    Deep analysis of FALSE_REJECTION (missed winners).

    Returns:
        - count and avg quality_score of missed winners
        - avg favorable_move_pct of missed winners (how much we left on the table)
        - breakdown by rejection reason
    """
    missed = [
        r for r in records
        if r.get("rejection_outcome") == "FALSE_REJECTION"
    ]
    if not missed:
        return {"count": 0}

    moves = [
        r.get("max_favorable_move") or r.get("move_5d_pct") or 0.0
        for r in missed
        if r.get("max_favorable_move") or r.get("move_5d_pct")
    ]
    qualities = [r["quality_score"] for r in missed if r.get("quality_score")]
    reasons: Dict[str, int] = defaultdict(int)
    for r in missed:
        reasons[r.get("rejected_reason", "UNKNOWN")] += 1

    return {
        "count":        len(missed),
        "avg_quality":  round(statistics.mean(qualities), 2) if qualities else 0.0,
        "avg_move_pct": round(statistics.mean(moves), 2)     if moves     else 0.0,
        "max_move_pct": round(max(moves), 2)                 if moves     else 0.0,
        "by_reason":    dict(reasons),
    }


def hypothetical_pnl(
    price_at_rejection: float,
    price_after:        float,
    direction:          str,
    lot_size:           int   = 50,
    lot_count:          int   = 1,
) -> float:
    """
    Estimate PnL had we taken the trade instead of rejecting.

    Positive = we would have profited.
    Negative = rejection correctly saved a loss.
    """
    if price_at_rejection <= 0:
        return 0.0
    move = price_after - price_at_rejection
    sign = 1.0 if direction.upper() == "LONG" else -1.0
    return round(sign * move * lot_size * lot_count, 0)
