"""
Global Intelligence Layer — Macro Signal AI
=============================================
Interprets raw global data into macro-economic signals that affect
Indian equity markets.

Signals produced
----------------
  liquidity       : EASY / NEUTRAL / TIGHT
  inflation_risk  : LOW / MODERATE / HIGH
  risk_sentiment  : RISK_ON / NEUTRAL / RISK_OFF
  dollar_strength : STRONG / NEUTRAL / WEAK
  energy_pressure : HIGH / MODERATE / LOW    (crude-driven)
  safe_haven_demand: HIGH / MODERATE / LOW   (gold/bond-driven)

Macro interpretation logic
---------------------------
  Rising US 10Y yield  → tighter liquidity, pressure on EM equities
  Falling DXY          → weaker dollar → FII inflows → Nifty positive
  Crude spike > +3%    → inflation risk, PSU & auto sector drag
  Gold rally > +1%     → defensive / risk-off sentiment
  CBOE VIX > 25        → high fear, reduce equity exposure
  Strong US rally      → global risk-on → Nifty gap-up bias
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from utils import get_logger
from .global_data_ai import GlobalSnapshot

log = get_logger(__name__)


class LiquidityCondition(str, Enum):
    EASY    = "easy"
    NEUTRAL = "neutral"
    TIGHT   = "tight"


class InflationRisk(str, Enum):
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class RiskSentiment(str, Enum):
    RISK_ON  = "risk_on"
    NEUTRAL  = "neutral"
    RISK_OFF = "risk_off"


class DollarStrength(str, Enum):
    STRONG  = "strong"
    NEUTRAL = "neutral"
    WEAK    = "weak"


@dataclass
class MacroSignals:
    """
    Interpreted macro signals derived from GlobalSnapshot.

    Consumed by GlobalSentimentAI and PremarketBiasAI.
    """
    liquidity:         LiquidityCondition
    inflation_risk:    InflationRisk
    risk_sentiment:    RiskSentiment
    dollar_strength:   DollarStrength
    energy_pressure:   str          # "high" | "moderate" | "low"
    safe_haven_demand: str          # "high" | "moderate" | "low"
    yield_pressure:    bool         # True = yields rising, pressuring equities
    rupee_stress:      bool         # True = INR weakening, FII outflow risk

    # Numeric composite score: −1.0 (full bearish) → +1.0 (full bullish)
    macro_score: float = 0.0

    def summary(self) -> str:
        return (
            f"Liquidity={self.liquidity.value} | "
            f"Inflation={self.inflation_risk.value} | "
            f"RiskSentiment={self.risk_sentiment.value} | "
            f"Dollar={self.dollar_strength.value} | "
            f"MacroScore={self.macro_score:+.2f}"
        )


class MacroSignalAI:
    """
    Converts a GlobalSnapshot into interpretable MacroSignals.

    Thresholds are based on empirical relationships:
      • Bond yields impact Indian equity FII flows
      • Crude is a direct cost-push for Indian inflation
      • DXY inverse relationship with emerging-market inflows
      • CBOE VIX drives global risk appetite
    """

    # ── Interpretation thresholds ──────────────────────────────────────
    # Bond yields
    YLD_TIGHT_BPS     = +8.0    # > +8 bps move = tightening signal
    YLD_EASY_BPS      = -8.0    # < −8 bps = easing

    # Crude (% change)
    CRUDE_HIGH        = +3.0    # >+3% = energy pressure
    CRUDE_LOW         = -3.0    # <-3% = energy relief

    # DXY (% change)
    DXY_STRONG        = +0.5    # >+0.5% = strong dollar
    DXY_WEAK          = -0.5    # <-0.5% = weak dollar

    # Gold (% change)
    GOLD_SAFE_HAVEN   = +1.0    # >+1% = safe-haven demand
    GOLD_RISK_ON      = -0.5    # <-0.5% = risk-on (selling safe haven)

    # CBOE VIX
    VIX_FEAR          = 25.0    # > 25 = risk-off globally
    VIX_CALM          = 16.0    # < 16 = risk-on globally

    # USD/INR (% change)
    RUPEE_STRESS      = +0.3    # >+0.3% = rupee weakening

    def __init__(self):
        log.info("[MacroSignalAI] Initialised.")

    def analyse(self, snap: GlobalSnapshot) -> MacroSignals:
        """Interpret a GlobalSnapshot into MacroSignals."""

        liquidity       = self._liquidity(snap)
        inflation_risk  = self._inflation(snap)
        risk_sentiment  = self._risk_sentiment(snap)
        dollar_strength = self._dollar(snap)
        energy_pressure = self._energy(snap)
        safe_haven      = self._safe_haven(snap)
        yield_pressure  = snap.us10y_change_bps > self.YLD_TIGHT_BPS
        rupee_stress    = snap.usdinr_change > self.RUPEE_STRESS

        macro_score = self._composite_score(snap, risk_sentiment, dollar_strength,
                                            inflation_risk, liquidity)

        signals = MacroSignals(
            liquidity=liquidity,
            inflation_risk=inflation_risk,
            risk_sentiment=risk_sentiment,
            dollar_strength=dollar_strength,
            energy_pressure=energy_pressure,
            safe_haven_demand=safe_haven,
            yield_pressure=yield_pressure,
            rupee_stress=rupee_stress,
            macro_score=macro_score,
        )
        log.info("[MacroSignalAI] %s", signals.summary())
        return signals

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE CLASSIFIERS
    # ──────────────────────────────────────────────────────────────────

    def _liquidity(self, snap: GlobalSnapshot) -> LiquidityCondition:
        bps = snap.us10y_change_bps
        if bps > self.YLD_TIGHT_BPS:
            return LiquidityCondition.TIGHT
        if bps < self.YLD_EASY_BPS:
            return LiquidityCondition.EASY
        return LiquidityCondition.NEUTRAL

    def _inflation(self, snap: GlobalSnapshot) -> InflationRisk:
        crude_str = snap.crude_brent_change
        if crude_str > self.CRUDE_HIGH:
            return InflationRisk.HIGH
        if crude_str > 1.0:
            return InflationRisk.MODERATE
        return InflationRisk.LOW

    def _risk_sentiment(self, snap: GlobalSnapshot) -> RiskSentiment:
        vix = snap.cboe_vix
        us  = snap.sp500_change
        if vix > self.VIX_FEAR or us < -1.0:
            return RiskSentiment.RISK_OFF
        if vix < self.VIX_CALM and us > 0.5:
            return RiskSentiment.RISK_ON
        return RiskSentiment.NEUTRAL

    def _dollar(self, snap: GlobalSnapshot) -> DollarStrength:
        dxy = snap.dxy_change
        if dxy > self.DXY_STRONG:
            return DollarStrength.STRONG
        if dxy < self.DXY_WEAK:
            return DollarStrength.WEAK
        return DollarStrength.NEUTRAL

    def _energy(self, snap: GlobalSnapshot) -> str:
        c = snap.crude_brent_change
        if c > self.CRUDE_HIGH:
            return "high"
        if c < self.CRUDE_LOW:
            return "low"
        return "moderate"

    def _safe_haven(self, snap: GlobalSnapshot) -> str:
        g = snap.gold_change
        if g > self.GOLD_SAFE_HAVEN:
            return "high"
        if g < self.GOLD_RISK_ON:
            return "low"
        return "moderate"

    def _composite_score(
        self,
        snap: GlobalSnapshot,
        risk: RiskSentiment,
        dollar: DollarStrength,
        inflation: InflationRisk,
        liquidity: LiquidityCondition,
    ) -> float:
        """
        Weighted composite macro score in [−1, +1].

        Positive = macro-bullish for Indian equities.
        """
        score = 0.0

        # Risk sentiment (most impactful)
        if risk == RiskSentiment.RISK_ON:
            score += 0.35
        elif risk == RiskSentiment.RISK_OFF:
            score -= 0.35

        # USD strength: strong dollar → FII exits EM → bearish Nifty
        if dollar == DollarStrength.WEAK:
            score += 0.25
        elif dollar == DollarStrength.STRONG:
            score -= 0.25

        # Liquidity: easy money → equity positive
        if liquidity == LiquidityCondition.EASY:
            score += 0.20
        elif liquidity == LiquidityCondition.TIGHT:
            score -= 0.20

        # Inflation: high crude hurts India (oil importer)
        if inflation == InflationRisk.HIGH:
            score -= 0.15
        elif inflation == InflationRisk.LOW:
            score += 0.05

        # Rupee stability bonus
        if snap.usdinr_change < -0.2:     # rupee strengthening
            score += 0.05
        elif snap.usdinr_change > 0.5:    # rupee sharply weakening
            score -= 0.10

        return round(max(-1.0, min(1.0, score)), 4)
