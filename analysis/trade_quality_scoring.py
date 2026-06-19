"""
analysis/trade_quality_scoring.py
===================================
TRADE_QUALITY_AUDIT_001 — Pure scoring functions.

No database. No IO. No live-system imports.
All functions are deterministic and unit-testable.

Composite quality score formula
--------------------------------
quality_score = (
    decision_score  * 0.40 +
    technical_score * 0.25 +
    macro_score     * 0.15 +
    sentiment_score * 0.10 +
    risk_score      * 0.10
)

Quality tiers
-------------
PREMIUM  >= 8.0
HIGH     >= 7.0
MEDIUM   >= 6.0
LOW      <  6.0
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ── Quality tier ──────────────────────────────────────────────────────────────

class QualityTier(str, Enum):
    PREMIUM = "PREMIUM"   # composite >= 8.0
    HIGH    = "HIGH"      # composite >= 7.0
    MEDIUM  = "MEDIUM"    # composite >= 6.0
    LOW     = "LOW"       # composite <  6.0
    UNKNOWN = "UNKNOWN"   # not computed


TIER_THRESHOLDS: Dict[QualityTier, float] = {
    QualityTier.PREMIUM: 8.0,
    QualityTier.HIGH:    7.0,
    QualityTier.MEDIUM:  6.0,
}

# Expected win rates per tier (theoretical benchmark)
TIER_EXPECTED_WIN_RATES: Dict[str, float] = {
    "PREMIUM": 0.80,
    "HIGH":    0.63,
    "MEDIUM":  0.38,
    "LOW":     0.20,
}

# Score component weights (must sum to 1.0)
QUALITY_WEIGHTS: Dict[str, float] = {
    "decision_score":  0.40,
    "technical_score": 0.25,
    "macro_score":     0.15,
    "sentiment_score": 0.10,
    "risk_score":      0.10,
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class TradeScores:
    """Input scores for a single trade. All on a 0–10 scale."""
    decision_score:      float
    effective_threshold: float
    technical_score:     float
    macro_score:         float
    sentiment_score:     float
    risk_score:          float
    sft_class:           str   = "UNKNOWN"
    sft_score:           float = 0.0


@dataclass
class QualityResult:
    """Output of compute_quality_score()."""
    quality_score:       float
    quality_tier:        QualityTier
    margin:              float   # decision_score − effective_threshold
    is_high_conviction:  bool    # quality >= 7.5 AND margin > 0.5
    component_scores:    Dict[str, float] = field(default_factory=dict)


@dataclass
class OutcomeComparison:
    """
    Head-to-head score averages: winning trades vs losing trades.
    The key learning output — if quality_edge >= 1.0 the scoring is working.
    """
    n_wins:              int
    n_losses:            int

    win_avg_quality:     float
    loss_avg_quality:    float

    win_avg_decision:    float
    loss_avg_decision:   float

    win_avg_technical:   float
    loss_avg_technical:  float

    win_avg_macro:       float
    loss_avg_macro:      float

    win_sft_high_pct:    float   # % of wins where SFT class was HIGH
    loss_sft_high_pct:   float   # % of losses where SFT class was HIGH

    quality_edge:        float   # win_avg_quality − loss_avg_quality
    verdict:             str     # "QUALITY PREDICTS OUTCOME" / "MARGINAL SIGNAL" / "INCONCLUSIVE"


# ── Core scoring functions ────────────────────────────────────────────────────

def compute_quality_score(scores: TradeScores) -> QualityResult:
    """
    Compute composite quality score and classify tier.

    Args:
        scores: TradeScores with all component scores on 0–10 scale.

    Returns:
        QualityResult with score, tier, margin, and conviction flag.
    """
    components = {
        "decision_score":  scores.decision_score,
        "technical_score": scores.technical_score,
        "macro_score":     scores.macro_score,
        "sentiment_score": scores.sentiment_score,
        "risk_score":      scores.risk_score,
    }
    quality_score = round(
        sum(components[k] * QUALITY_WEIGHTS[k] for k in QUALITY_WEIGHTS),
        3,
    )
    tier           = classify_tier(quality_score)
    margin         = round(scores.decision_score - scores.effective_threshold, 3)
    high_conviction = quality_score >= 7.5 and margin > 0.5

    return QualityResult(
        quality_score      = quality_score,
        quality_tier       = tier,
        margin             = margin,
        is_high_conviction = high_conviction,
        component_scores   = components,
    )


def classify_tier(quality_score: float) -> QualityTier:
    """Classify a quality score into a tier."""
    if quality_score >= TIER_THRESHOLDS[QualityTier.PREMIUM]:
        return QualityTier.PREMIUM
    elif quality_score >= TIER_THRESHOLDS[QualityTier.HIGH]:
        return QualityTier.HIGH
    elif quality_score >= TIER_THRESHOLDS[QualityTier.MEDIUM]:
        return QualityTier.MEDIUM
    return QualityTier.LOW


# ── Comparison / analysis functions ──────────────────────────────────────────

def compare_win_loss(trade_records: List[dict]) -> Optional[OutcomeComparison]:
    """
    Compare score averages between winning and losing trades.

    Args:
        trade_records: list of dicts with keys:
            outcome (WIN/LOSS), quality_score, decision_score,
            technical_score, macro_score, sentiment_score, sft_class

    Returns:
        OutcomeComparison, or None if insufficient data (< 1 win or < 1 loss).
    """
    wins   = [r for r in trade_records if r.get("outcome") == "WIN"]
    losses = [r for r in trade_records if r.get("outcome") == "LOSS"]

    if not wins or not losses:
        return None

    def _avg(records: list, key: str) -> float:
        vals = [r[key] for r in records if r.get(key) is not None]
        return round(statistics.mean(vals), 3) if vals else 0.0

    def _sft_high_pct(records: list) -> float:
        if not records:
            return 0.0
        highs = sum(1 for r in records if r.get("sft_class") in ("HIGH", "PREMIUM"))
        return round(highs / len(records) * 100, 1)

    win_avg_q  = _avg(wins,   "quality_score")
    loss_avg_q = _avg(losses, "quality_score")
    edge       = round(win_avg_q - loss_avg_q, 3)

    if edge >= 1.0:
        verdict = "QUALITY PREDICTS OUTCOME"
    elif edge >= 0.5:
        verdict = "MARGINAL SIGNAL"
    else:
        verdict = "INCONCLUSIVE"

    return OutcomeComparison(
        n_wins             = len(wins),
        n_losses           = len(losses),
        win_avg_quality    = win_avg_q,
        loss_avg_quality   = loss_avg_q,
        win_avg_decision   = _avg(wins,   "decision_score"),
        loss_avg_decision  = _avg(losses, "decision_score"),
        win_avg_technical  = _avg(wins,   "technical_score"),
        loss_avg_technical = _avg(losses, "technical_score"),
        win_avg_macro      = _avg(wins,   "macro_score"),
        loss_avg_macro     = _avg(losses, "macro_score"),
        win_sft_high_pct   = _sft_high_pct(wins),
        loss_sft_high_pct  = _sft_high_pct(losses),
        quality_edge       = edge,
        verdict            = verdict,
    )


def tier_win_rates(trade_records: List[dict]) -> Dict[str, dict]:
    """
    Compute win rate and avg PnL for each quality tier.

    Args:
        trade_records: list of dicts with keys: quality_tier, outcome, pnl

    Returns:
        Dict keyed by tier name with stats: total, closed, wins, win_rate, avg_pnl
    """
    buckets: Dict[str, list] = defaultdict(list)
    for r in trade_records:
        tier = r.get("quality_tier", "UNKNOWN")
        buckets[tier].append(r)

    result = {}
    for tier, records in buckets.items():
        closed = [r for r in records if r.get("outcome") in ("WIN", "LOSS", "BREAKEVEN")]
        wins   = [r for r in closed if r.get("outcome") == "WIN"]
        pnls   = [r["pnl"] for r in closed if r.get("pnl") is not None]
        result[tier] = {
            "total":    len(records),
            "closed":   len(closed),
            "wins":     len(wins),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
            "avg_pnl":  round(sum(pnls) / len(pnls), 0)         if pnls   else 0.0,
        }
    return result


def score_distribution(trade_records: List[dict]) -> dict:
    """
    Descriptive statistics for quality_score across all closed trades.

    Returns dict with: mean, median, stdev, min, max, percentile_25, percentile_75
    """
    scores = [r["quality_score"] for r in trade_records if r.get("quality_score") is not None]
    if not scores:
        return {}
    scores_sorted = sorted(scores)
    n = len(scores_sorted)
    return {
        "n":             n,
        "mean":          round(statistics.mean(scores_sorted), 3),
        "median":        round(statistics.median(scores_sorted), 3),
        "stdev":         round(statistics.stdev(scores_sorted), 3) if n > 1 else 0.0,
        "min":           round(scores_sorted[0], 3),
        "max":           round(scores_sorted[-1], 3),
        "percentile_25": round(scores_sorted[n // 4], 3),
        "percentile_75": round(scores_sorted[3 * n // 4], 3),
    }
