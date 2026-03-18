"""
Global Intelligence Layer — Global Sentiment AI
=================================================
Combines macro signals and correlation analysis into a single global
sentiment score that expresses the net directional bias for Indian equities.

Weighting scheme
----------------
  US equity move          40%   (strongest predictor of Nifty gap)
  Asian market move       20%   (overnight proxy for EM risk)
  Currency                20%   (DXY/INR = FII flow proxy)
  Bond yields             10%   (liquidity conditions)
  Commodities             10%   (crude inflation risk for India)

Score interpretation
--------------------
  Score ≥ +0.50   → BULLISH      (strong global tailwind for Nifty)
  0 ≤ score < 0.50 → NEUTRAL-BULLISH
  −0.50 ≤ score < 0 → NEUTRAL-BEARISH
  Score < −0.50   → BEARISH      (significant global headwind)

Output: GlobalSentimentScore dataclass consumed by PremarketBiasAI
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from utils import get_logger
from .global_data_ai    import GlobalSnapshot
from .macro_signal_ai   import MacroSignals, RiskSentiment
from .correlation_engine import CorrelationResult

log = get_logger(__name__)


class SentimentLabel(str, Enum):
    STRONGLY_BULLISH  = "strongly_bullish"
    BULLISH           = "bullish"
    NEUTRAL_BULLISH   = "neutral_bullish"
    NEUTRAL           = "neutral"
    NEUTRAL_BEARISH   = "neutral_bearish"
    BEARISH           = "bearish"
    STRONGLY_BEARISH  = "strongly_bearish"


@dataclass
class GlobalSentimentScore:
    """
    Composite sentiment for Indian equity markets based on overnight
    global signals.

    Attributes
    ----------
    score           : weighted composite in [−1, +1]
    label           : human-readable SentimentLabel
    component_scores: breakdown by input category
    confidence      : 0–1, how strongly signals agree with each other
    headline        : one-sentence natural language summary
    """
    score:             float
    label:             SentimentLabel
    component_scores:  Dict[str, float] = field(default_factory=dict)
    confidence:        float = 0.5
    headline:          str   = ""

    def is_bullish(self) -> bool:
        return self.score > 0.0

    def is_bearish(self) -> bool:
        return self.score < 0.0

    def summary(self) -> str:
        return (
            f"GlobalSentiment={self.label.value}  Score={self.score:+.3f}  "
            f"Confidence={self.confidence:.0%}  |  {self.headline}"
        )


class GlobalSentimentAI:
    """
    Synthesises GlobalSnapshot + MacroSignals + CorrelationResult into
    a single GlobalSentimentScore.

    Input weights are calibrated to empirical Nifty predictability:
      US equities (40%) > currency (20%) = Asian (20%) > bonds/commodities (10% each)
    """

    _WEIGHTS = {
        "us_equity":   0.40,
        "asian":       0.20,
        "currency":    0.20,
        "bonds":       0.10,
        "commodities": 0.10,
    }

    def __init__(self):
        log.info("[GlobalSentimentAI] Initialised. Weights: %s", self._WEIGHTS)

    def score(
        self,
        snap:       GlobalSnapshot,
        macro:      MacroSignals,
        corr:       CorrelationResult,
    ) -> GlobalSentimentScore:
        """
        Compute GlobalSentimentScore from all three upstream inputs.

        The macro score and correlation bias_score are combined using
        a simple equal blend, then weighted by category.
        """
        w = self._WEIGHTS

        # ── Per-category scores from correlation engine ────────────────
        inf = corr.influence_scores
        us_raw   = inf.get("us_equity",   0.0)
        asia_raw = inf.get("asian",       0.0)
        curr_raw = inf.get("currency",    0.0)
        bond_raw = inf.get("bonds",       0.0)
        comm_raw = inf.get("commodities", 0.0)

        # ── Blend correlation score with macro signal nudge ────────────
        macro_nudge = macro.macro_score * 0.25   # 25% weight to macro overlay

        us_score   = us_raw   * 0.75 + macro_nudge
        asia_score = asia_raw * 0.75 + macro_nudge * 0.5
        curr_score = curr_raw * 0.75 - (0.10 if macro.rupee_stress else 0.0)
        bond_score = bond_raw * 0.75 - (0.10 if macro.yield_pressure else 0.0)
        comm_score = comm_raw * 0.75

        # ── Weighted aggregate ─────────────────────────────────────────
        composite = (
            us_score   * w["us_equity"] +
            asia_score * w["asian"] +
            curr_score * w["currency"] +
            bond_score * w["bonds"] +
            comm_score * w["commodities"]
        )
        composite = round(max(-1.0, min(1.0, composite)), 4)

        # ── Confidence: how closely all categories agree ───────────────
        component_values = [us_score, asia_score, curr_score, bond_score, comm_score]
        agrees = sum(1 for v in component_values if (v > 0) == (composite > 0))
        confidence = round(agrees / len(component_values), 2)

        label    = self._classify(composite)
        headline = self._headline(composite, snap, macro)

        result = GlobalSentimentScore(
            score=composite,
            label=label,
            component_scores={
                "us_equity":   round(us_score, 4),
                "asian":       round(asia_score, 4),
                "currency":    round(curr_score, 4),
                "bonds":       round(bond_score, 4),
                "commodities": round(comm_score, 4),
            },
            confidence=confidence,
            headline=headline,
        )
        log.info("[GlobalSentimentAI] %s", result.summary())
        return result

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _classify(score: float) -> SentimentLabel:
        if score >= +0.60:
            return SentimentLabel.STRONGLY_BULLISH
        if score >= +0.30:
            return SentimentLabel.BULLISH
        if score >= +0.08:
            return SentimentLabel.NEUTRAL_BULLISH
        if score >= -0.08:
            return SentimentLabel.NEUTRAL
        if score >= -0.30:
            return SentimentLabel.NEUTRAL_BEARISH
        if score >= -0.60:
            return SentimentLabel.BEARISH
        return SentimentLabel.STRONGLY_BEARISH

    @staticmethod
    def _headline(score: float, snap: GlobalSnapshot, macro: MacroSignals) -> str:
        """Generate a concise natural-language summary of the dominant signal."""
        parts = []
        if abs(snap.sp500_change) >= 0.8:
            direction = "rally" if snap.sp500_change > 0 else "selloff"
            parts.append(f"S&P500 {direction} {snap.sp500_change:+.1f}%")
        if abs(snap.sgx_nifty_change) >= 0.5:
            direction = "positive" if snap.sgx_nifty_change > 0 else "negative"
            parts.append(f"SGX Nifty {direction} {snap.sgx_nifty_change:+.1f}%")
        if abs(snap.usdinr_change) >= 0.3:
            direction = "weakens" if snap.usdinr_change > 0 else "strengthens"
            parts.append(f"Rupee {direction} {snap.usdinr_change:+.2f}%")
        if macro.yield_pressure:
            parts.append(f"US yields rise {snap.us10y_change_bps:+.0f}bps (FII risk)")
        if snap.crude_brent_change >= 2.5:
            parts.append(f"Crude spike {snap.crude_brent_change:+.1f}% (inflation risk)")

        if not parts:
            parts.append("mixed global signals — no dominant driver")
        return "; ".join(parts)
