"""
Market Regime AI — Layer 2 Agent 2
====================================
Classifies the current market state so that downstream strategy agents
can select the appropriate playbook.

Output classes:
  BULL_TREND   → momentum / breakout strategies
  RANGE_MARKET → mean reversion strategies
  BEAR_MARKET  → hedging / short strategies
  VOLATILE     → reduce size, prefer options hedges
"""

from __future__ import annotations
from typing import Any, Dict

from models.market_data  import RegimeLabel, VolatilityLevel
from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)

# ── Thresholds (tune with your own data) ────────────────────────────────────
VIX_MEDIUM_HIGH  = 18.0
VIX_HIGH         = 22.0
ADV_DECLINE_BULL = 0.60     # breadth > 60% → bullish
ADV_DECLINE_BEAR = 0.40     # breadth < 40% → bearish
PCR_BEARISH      = 1.2      # high PCR → fear


class MarketRegimeAI:
    """
    Classifies market regime using VIX, PCR, breadth, and index trend filters.
    """

    def __init__(self):
        log.info("[MarketRegimeAI] Initialised.")

    # ─────────────────────────────────────────────
    # PUBLIC INTERFACE
    # ─────────────────────────────────────────────

    def classify(self, raw_data: Dict[str, Any],
                 global_bias: str = "neutral",
                 global_sentiment_score: float = 0.0) -> AgentOutput:
        """
        Args:
            raw_data               : dict produced by MarketDataAI.fetch()
            global_bias            : "bullish" | "neutral" | "bearish" from GMIL
            global_sentiment_score : −1→+1 from GlobalSentimentAI
        Returns:
            AgentOutput with data = {"regime": RegimeLabel, "volatility": VolatilityLevel}
        """
        vix     = raw_data.get("vix", 15.0)
        pcr     = raw_data.get("pcr", 1.0)
        breadth = raw_data.get("breadth", 0.5)
        nifty   = raw_data.get("indices", {}).get("NIFTY 50", {})
        nifty_chg = nifty.get("change_pct", 0.0) if nifty else 0.0

        regime     = self._classify_regime(vix, pcr, breadth, nifty_chg,
                                           global_bias, global_sentiment_score)
        volatility = self._classify_volatility(vix)

        summary = (
            f"Regime: {regime.value} | "
            f"Volatility: {volatility.value} | "
            f"VIX: {vix:.1f} | PCR: {pcr:.2f} | Breadth: {breadth:.0%} | "
            f"GlobalBias: {global_bias}"
        )
        log.info("[MarketRegimeAI] %s", summary)

        return AgentOutput(
            agent_name = "MarketRegimeAI",
            status     = "ok",
            summary    = summary,
            confidence = 8.5,
            data       = {"regime": regime, "volatility": volatility,
                          "vix": vix, "pcr": pcr, "breadth": breadth},
        )

    # ─────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────

    def _classify_regime(self, vix: float, pcr: float,
                         breadth: float, nifty_chg: float,
                         global_bias: str = "neutral",
                         global_sentiment_score: float = 0.0) -> RegimeLabel:
        # Extreme volatility first — global context can't override real panic
        if vix >= VIX_HIGH:
            return RegimeLabel.VOLATILE

        # Global context nudges: strong global signal can flip a borderline regime
        # A strong bullish global sentiment (+0.40) adds +0.6% to nifty_chg perception
        # A strong bearish signal (−0.40) subtracts the same
        adjusted_chg = nifty_chg + global_sentiment_score * 1.5
        adjusted_breadth = min(1.0, max(0.0, breadth + global_sentiment_score * 0.15))

        # Bear signals: high VIX + bearish breadth + negative nifty
        if (vix >= VIX_MEDIUM_HIGH and adjusted_breadth < ADV_DECLINE_BEAR
                and adjusted_chg < -0.5):
            return RegimeLabel.BEAR_MARKET

        # Global bearish override: strong global headwind can push to bear
        if global_bias == "bearish" and global_sentiment_score <= -0.45:
            if adjusted_breadth < 0.50:
                return RegimeLabel.BEAR_MARKET

        # Bull signals: low VIX + positive breadth + positive nifty
        if (adjusted_breadth >= ADV_DECLINE_BULL and adjusted_chg > 0.3
                and vix < VIX_MEDIUM_HIGH):
            return RegimeLabel.BULL_TREND

        # Global bullish override: strong tailwind can push range → bull
        if (global_bias == "bullish" and global_sentiment_score >= 0.45
                and adjusted_breadth >= 0.50 and vix < VIX_MEDIUM_HIGH):
            return RegimeLabel.BULL_TREND

        # Default: range / sideways market
        return RegimeLabel.RANGE_MARKET

    def _classify_volatility(self, vix: float) -> VolatilityLevel:
        if vix >= VIX_HIGH:
            return VolatilityLevel.EXTREME
        elif vix >= VIX_MEDIUM_HIGH:
            return VolatilityLevel.HIGH
        elif vix >= 14.0:
            return VolatilityLevel.MEDIUM
        else:
            return VolatilityLevel.LOW
