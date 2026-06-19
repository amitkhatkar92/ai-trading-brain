"""
analysis/option_regime_classifier.py
=====================================
OPTIONS_AUDIT_001 — Market Regime Classification

No live trading. No execution influence. Analysis only.

Classifies market conditions into regimes that determine
which option strategies are structurally advantaged.

Regime taxonomy:
  HIGH_VOL  — VIX > 22, elevated fear, wide bid-ask, premium expansion
  TRENDING  — VIX ≤ 22, trend_strength > 0.70, directional momentum
  RANGING   — VIX ≤ 22, trend_strength ≤ 0.70, mean-reversion conditions

Sub-regimes (compound classification):
  HIGH_VOL_TRENDING, HIGH_VOL_RANGING, TRENDING_BULLISH,
  TRENDING_BEARISH, RANGING_TIGHT, RANGING_WIDE
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


# ── Regime Enums ──────────────────────────────────────────────────────────────

class Regime(str, Enum):
    HIGH_VOL  = "HIGH_VOL"
    TRENDING  = "TRENDING"
    RANGING   = "RANGING"
    UNKNOWN   = "UNKNOWN"


class SubRegime(str, Enum):
    HIGH_VOL_TRENDING = "HIGH_VOL_TRENDING"
    HIGH_VOL_RANGING  = "HIGH_VOL_RANGING"
    TRENDING_BULLISH  = "TRENDING_BULLISH"
    TRENDING_BEARISH  = "TRENDING_BEARISH"
    RANGING_TIGHT     = "RANGING_TIGHT"    # VIX < 14
    RANGING_WIDE      = "RANGING_WIDE"     # VIX 14-22
    UNKNOWN           = "UNKNOWN"


# Regime thresholds (configurable)
VIX_HIGH_THRESHOLD      = 22.0   # above this = HIGH_VOL regime
TREND_STRENGTH_THRESHOLD = 0.70   # above this (in normal VIX) = TRENDING regime
VIX_TIGHT_UPPER          = 14.0   # below this = RANGING_TIGHT


# ── Core Classifiers ──────────────────────────────────────────────────────────

def classify_regime(vix: float, trend_strength: float) -> Regime:
    """
    Primary regime classifier.

    Parameters
    ----------
    vix            : India VIX (^INDIAVIX) or NIFTY VIX level
    trend_strength : 0–1 score (e.g. ADX/100, or momentum z-score normalised).
                     0 = pure mean-reversion / choppy
                     1 = strong directional trend

    Returns
    -------
    Regime enum: HIGH_VOL | TRENDING | RANGING

    Decision rules
    --------------
    VIX > 22                     → HIGH_VOL
        (elevated fear = premium buyers dominate; selling spreads is risky)
    VIX ≤ 22 AND strength > 0.70 → TRENDING
        (directional strategies outperform; spread strategies underperform)
    VIX ≤ 22 AND strength ≤ 0.70 → RANGING
        (mean-reversion + premium decay strategies optimal)
    """
    if vix > VIX_HIGH_THRESHOLD:
        return Regime.HIGH_VOL
    if trend_strength > TREND_STRENGTH_THRESHOLD:
        return Regime.TRENDING
    return Regime.RANGING


def classify_sub_regime(
    vix:            float,
    trend_strength: float,
    direction:      Optional[float] = None,   # +1 bullish, -1 bearish, 0 neutral
) -> SubRegime:
    """
    Extended sub-regime classifier for fine-grained strategy selection.

    Parameters
    ----------
    direction : Optional signed float. Positive = bullish bias, negative = bearish.
    """
    regime = classify_regime(vix, trend_strength)

    if regime == Regime.HIGH_VOL:
        return (SubRegime.HIGH_VOL_TRENDING if trend_strength > TREND_STRENGTH_THRESHOLD
                else SubRegime.HIGH_VOL_RANGING)

    if regime == Regime.TRENDING:
        if direction is None or direction == 0:
            return SubRegime.TRENDING_BULLISH  # default
        return SubRegime.TRENDING_BULLISH if direction > 0 else SubRegime.TRENDING_BEARISH

    # RANGING
    return SubRegime.RANGING_TIGHT if vix < VIX_TIGHT_UPPER else SubRegime.RANGING_WIDE


# ── Strategy Suitability Map ──────────────────────────────────────────────────

# For each regime, which strategies are PREFERRED / NEUTRAL / AVOID
# Based on structural options theory (IV expansion/contraction dynamics)
REGIME_STRATEGY_SUITABILITY = {
    Regime.HIGH_VOL: {
        "PREFERRED": ["LONG_STRADDLE", "LONG_STRANGLE", "BULL_PUT_SPREAD", "BEAR_CALL_SPREAD"],
        "NEUTRAL":   ["IRON_CONDOR", "IRON_BUTTERFLY"],
        "AVOID":     ["SHORT_STRANGLE", "SHORT_STRADDLE", "COVERED_CALL"],
        "rationale": "IV elevated; premium buying favoured. Selling naked premium is dangerous.",
    },
    Regime.TRENDING: {
        "PREFERRED": ["BULL_PUT_SPREAD", "BEAR_CALL_SPREAD", "COVERED_CALL", "PROTECTIVE_PUT"],
        "NEUTRAL":   ["LONG_STRADDLE", "IRON_CONDOR"],
        "AVOID":     ["SHORT_STRANGLE", "IRON_BUTTERFLY"],
        "rationale": "Directional; defined-risk spreads aligned with trend outperform.",
    },
    Regime.RANGING: {
        "PREFERRED": ["SHORT_STRANGLE", "IRON_CONDOR", "IRON_BUTTERFLY", "SHORT_STRADDLE"],
        "NEUTRAL":   ["BULL_PUT_SPREAD", "BEAR_CALL_SPREAD"],
        "AVOID":     ["LONG_STRADDLE", "LONG_STRANGLE", "PROTECTIVE_PUT"],
        "rationale": "Theta decay maximised; premium selling structurally advantaged.",
    },
}


def get_preferred_strategies(
    vix:            float,
    trend_strength: float,
) -> dict:
    """
    Return strategy suitability dict for the current regime.

    Returns
    -------
    dict with keys: regime, PREFERRED, NEUTRAL, AVOID, rationale
    """
    regime = classify_regime(vix, trend_strength)
    suitability = REGIME_STRATEGY_SUITABILITY.get(regime, {})
    return {"regime": regime.value, **suitability}


# ── Regime Series Analyser ────────────────────────────────────────────────────

@dataclass
class RegimeRecord:
    date:           str
    vix:            float
    trend_strength: float
    regime:         str
    sub_regime:     str


def classify_series(
    dates:            List[str],
    vix_values:       List[float],
    trend_strengths:  List[float],
    directions:       Optional[List[float]] = None,
) -> List[RegimeRecord]:
    """
    Classify a time series of (date, vix, trend_strength) into regime records.

    Parameters
    ----------
    directions : Optional list of direction floats (same length as dates).
    """
    n = min(len(dates), len(vix_values), len(trend_strengths))
    dirs = directions if directions and len(directions) == n else [0.0] * n

    return [
        RegimeRecord(
            date           = dates[i],
            vix            = vix_values[i],
            trend_strength = trend_strengths[i],
            regime         = classify_regime(vix_values[i], trend_strengths[i]).value,
            sub_regime     = classify_sub_regime(vix_values[i], trend_strengths[i], dirs[i]).value,
        )
        for i in range(n)
    ]


def regime_distribution(records: List[RegimeRecord]) -> dict:
    """Count how many days fell into each regime."""
    from collections import Counter
    counts = Counter(r.regime for r in records)
    total  = len(records) or 1
    return {
        regime: {"count": n, "pct": round(n / total * 100, 1)}
        for regime, n in counts.most_common()
    }
