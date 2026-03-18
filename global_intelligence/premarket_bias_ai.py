"""
Global Intelligence Layer — Premarket Bias AI
===============================================
Converts global sentiment + macro signals into a concrete pre-market
bias for Indian equities, including:

  • Expected Nifty open direction and magnitude
  • Gap-up / gap-down probability
  • Sector-level tailwind / headwind signals
  • Global confidence adjustment for MarketRegimeAI

This is the final output of the Global Intelligence Layer, consumed
directly by MarketRegimeAI to bias regime classification and by the
orchestrator to print the pre-market report.

Sector logic
------------
  IT          ← strongly driven by Nasdaq / US tech
  Banks       ← rate sensitivity (US10Y yield), FII flows
  PSU Banks   ← rate sensitivity, slightly less FII-driven
  Auto        ← crude oil cost-push (inverse)
  Pharma      ← defensive; tends to outperform in risk-off
  Metal       ← global growth proxy (China / Hang Seng)
  Oil & Gas   ← crude price direct
  FMCG        ← defensive; relatively insulated from global
  Realty      ← rate-sensitive (inverse bond yield)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from utils import get_logger
from .global_data_ai       import GlobalSnapshot
from .macro_signal_ai      import MacroSignals, RiskSentiment, DollarStrength, LiquidityCondition
from .global_sentiment_ai  import GlobalSentimentScore, SentimentLabel

log = get_logger(__name__)


class NiftyBias(str, Enum):
    STRONGLY_BULLISH = "strongly_bullish"
    BULLISH          = "bullish"
    SLIGHTLY_BULLISH = "slightly_bullish"
    NEUTRAL          = "neutral"
    SLIGHTLY_BEARISH = "slightly_bearish"
    BEARISH          = "bearish"
    STRONGLY_BEARISH = "strongly_bearish"


@dataclass
class PremarketBias:
    """
    Output of the Global Intelligence Layer — consumed by MarketRegimeAI.

    Attributes
    ----------
    nifty_bias          : directional enum
    bias_score          : numeric −1 → +1 (same scale as sentiment score)
    gap_up_probability  : 0–1 probability of gap-up open
    gap_down_probability: 0–1 probability of gap-down open
    expected_gap_pct    : estimated gap magnitude in %
    sector_outlook      : dict {sector: "positive" | "neutral" | "negative"}
    regime_nudge        : "bullish" | "neutral" | "bearish" — for MarketRegimeAI
    confidence          : 0–1 from sentiment layer
    summary_lines       : list of key-insight strings for the report
    """
    nifty_bias:           NiftyBias
    bias_score:           float
    gap_up_probability:   float
    gap_down_probability: float
    expected_gap_pct:     float
    sector_outlook:       Dict[str, str] = field(default_factory=dict)
    regime_nudge:         str = "neutral"     # fed into MarketRegimeAI
    confidence:           float = 0.5
    summary_lines:        list = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"NiftyBias={self.nifty_bias.value}  "
            f"Score={self.bias_score:+.3f}  "
            f"GapUp={self.gap_up_probability:.0%}  "
            f"GapDown={self.gap_down_probability:.0%}  "
            f"ExpectedGap={self.expected_gap_pct:+.2f}%"
        )


class PremarketBiasAI:
    """
    Synthesises the full Global Intelligence pipeline into a
    pre-market actionable bias statement for Indian equity markets.
    """

    # Gap-up/-down thresholds on sentiment score
    _GAP_UP_THRESHOLD   = +0.25
    _GAP_DOWN_THRESHOLD = -0.25

    # Probability calibration: each unit of |score| maps to ~45% base probability
    _PROB_SCALE = 0.45

    def __init__(self):
        log.info("[PremarketBiasAI] Initialised.")

    def compute(
        self,
        snap:      GlobalSnapshot,
        macro:     MacroSignals,
        sentiment: GlobalSentimentScore,
    ) -> PremarketBias:
        """
        Compute the full PremarketBias from upstream Global Intelligence outputs.
        """
        score = sentiment.score

        nifty_bias  = self._classify_bias(score)
        gap_up_prob = self._gap_prob(score, direction="up")
        gap_dn_prob = self._gap_prob(score, direction="down")
        expected_gap = self._expected_gap(score, snap)
        sectors      = self._sector_outlook(snap, macro)
        regime_nudge = self._regime_nudge(score)
        lines        = self._build_summary_lines(snap, macro, sentiment, sectors)

        bias = PremarketBias(
            nifty_bias=nifty_bias,
            bias_score=score,
            gap_up_probability=gap_up_prob,
            gap_down_probability=gap_dn_prob,
            expected_gap_pct=expected_gap,
            sector_outlook=sectors,
            regime_nudge=regime_nudge,
            confidence=sentiment.confidence,
            summary_lines=lines,
        )
        log.info("[PremarketBiasAI] %s", bias.summary())
        return bias

    def print_premarket_report(self, snap: GlobalSnapshot,
                                bias: PremarketBias) -> None:
        """
        Print a formatted pre-market intelligence report to the log.
        Called by the orchestrator at the start of each cycle.
        """
        sep  = "═" * 76
        thin = "─" * 76
        log.info(sep)
        log.info("  AI GLOBAL MARKET REPORT  |  %s",
                 snap.timestamp.strftime("%Y-%m-%d %H:%M"))
        log.info(thin)

        # Global markets table
        log.info("  %-22s  %-14s  %s", "Asset", "Level", "Change")
        log.info("  %s", "─" * 60)
        rows = [
            ("S&P 500",    f"{snap.sp500_level:>10,.0f}", f"{snap.sp500_change:>+.2f}%"),
            ("Nasdaq",     f"{snap.nasdaq_level:>10,.0f}", f"{snap.nasdaq_change:>+.2f}%"),
            ("Dow Jones",  f"{snap.dow_level:>10,.0f}", f"{snap.dow_change:>+.2f}%"),
            ("Nikkei 225", f"{snap.nikkei_level:>10,.0f}", f"{snap.nikkei_change:>+.2f}%"),
            ("Hang Seng",  f"{snap.hangseng_level:>10,.0f}", f"{snap.hangseng_change:>+.2f}%"),
            ("SGX Nifty",  f"{snap.sgx_nifty_level:>10,.0f}", f"{snap.sgx_nifty_change:>+.2f}%"),
            ("US 10Y Yield", f"{snap.us10y_yield:>10.2f}%", f"{snap.us10y_change_bps:>+.0f} bps"),
            ("Brent Crude", f"${snap.crude_brent:>9.2f}", f"{snap.crude_brent_change:>+.2f}%"),
            ("Gold",       f"${snap.gold_price:>9,.0f}", f"{snap.gold_change:>+.2f}%"),
            ("USD/INR",    f"{snap.usdinr_rate:>10.4f}", f"{snap.usdinr_change:>+.2f}%"),
            ("DXY",        f"{snap.dxy_level:>10.2f}", f"{snap.dxy_change:>+.2f}%"),
            ("CBOE VIX",   f"{snap.cboe_vix:>10.1f}", ""),
        ]
        for name, level, change in rows:
            log.info("  %-22s  %-14s  %s", name, level, change)

        log.info("  %s", "─" * 60)
        log.info("  Global Sentiment Score : %+.3f  →  %s",
                 bias.bias_score, bias.nifty_bias.value.replace("_", " ").upper())
        log.info("  Confidence             : %.0f%%", bias.confidence * 100)
        log.info("  Gap-Up Probability     : %.0f%%  |  Gap-Down: %.0f%%",
                 bias.gap_up_probability * 100, bias.gap_down_probability * 100)
        log.info("  Expected Move          : %+.2f%%", bias.expected_gap_pct)

        # Sector outlook
        log.info(thin)
        log.info("  SECTOR OUTLOOK")
        for sector, outlook in bias.sector_outlook.items():
            icon = "↑" if outlook == "positive" else ("↓" if outlook == "negative" else "→")
            log.info("  %-22s  %s %s", sector, icon, outlook.upper())

        # Key insights
        if bias.summary_lines:
            log.info(thin)
            log.info("  KEY INSIGHTS")
            for line in bias.summary_lines:
                log.info("  • %s", line)

        log.info(sep)

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────────────────────────

    def _classify_bias(self, score: float) -> NiftyBias:
        if score >= +0.55:
            return NiftyBias.STRONGLY_BULLISH
        if score >= +0.28:
            return NiftyBias.BULLISH
        if score >= +0.08:
            return NiftyBias.SLIGHTLY_BULLISH
        if score >= -0.08:
            return NiftyBias.NEUTRAL
        if score >= -0.28:
            return NiftyBias.SLIGHTLY_BEARISH
        if score >= -0.55:
            return NiftyBias.BEARISH
        return NiftyBias.STRONGLY_BEARISH

    def _gap_prob(self, score: float, direction: str) -> float:
        """
        Estimate gap probability in a given direction.
        Base = 50%; shifted by sentiment score.
        """
        base = 0.50
        shift = abs(score) * self._PROB_SCALE
        if direction == "up":
            return round(min(0.90, max(0.05,
                base + shift if score > 0 else base - shift)), 3)
        else:
            return round(min(0.90, max(0.05,
                base + shift if score < 0 else base - shift)), 3)

    @staticmethod
    def _expected_gap(score: float, snap: GlobalSnapshot) -> float:
        """
        Estimate expected Nifty gap % based on SGX Nifty change
        and the sentiment score as a blended signal.
        """
        sgx_contribution = snap.sgx_nifty_change * 0.60
        sentiment_pct    = score * 0.50              # 50 bps per unit of score
        return round((sgx_contribution + sentiment_pct) / 2, 3)

    @staticmethod
    def _sector_outlook(snap: GlobalSnapshot, macro: MacroSignals) -> Dict[str, str]:
        """
        Rule-based sector outlook from global signals.

        IT       — Nasdaq-driven (US tech sentiment)
        Banks    — US yield driven + FII
        Auto     — crude cost-push (inverse)
        Pharma   — defensive (gold / safe-haven proxy)
        Metal    — global growth / Asian markets
        Oil&Gas  — crude direct
        FMCG     — defensive baseline
        Realty   — bond yield inverse
        """
        def t(v: float, pos: float, neg: float) -> str:
            if v >= pos:
                return "positive"
            if v <= neg:
                return "negative"
            return "neutral"

        it_outlook    = t(snap.nasdaq_change, +0.8, -0.8)
        bank_factor   = snap.sp500_change * 0.5 - snap.us10y_change_bps * 0.03
        banks         = t(bank_factor, +0.3, -0.3)
        auto          = t(-snap.crude_brent_change, +1.0, -1.0)   # crude inverse
        pharma        = "positive" if macro.risk_sentiment == RiskSentiment.RISK_OFF else "neutral"
        metal_factor  = (snap.hangseng_change + snap.nikkei_change) / 2
        metal         = t(metal_factor, +0.5, -0.5)
        oil_gas       = t(snap.crude_brent_change, +1.5, -1.5)
        fmcg          = "neutral"                                   # structural defensive
        realty        = t(-snap.us10y_change_bps, +5, -5)          # inverse yield

        return {
            "IT":          it_outlook,
            "Banks":       banks,
            "Auto":        auto,
            "Pharma":      pharma,
            "Metal":       metal,
            "Oil & Gas":   oil_gas,
            "FMCG":        fmcg,
            "Realty":      realty,
        }

    @staticmethod
    def _regime_nudge(score: float) -> str:
        """Map sentiment score to a regime nudge fed to MarketRegimeAI."""
        if score >= +0.30:
            return "bullish"
        if score <= -0.30:
            return "bearish"
        return "neutral"

    @staticmethod
    def _build_summary_lines(
        snap:      GlobalSnapshot,
        macro:     MacroSignals,
        sentiment: GlobalSentimentScore,
        sectors:   Dict[str, str],
    ) -> list:
        lines = []

        if abs(snap.sp500_change) >= 1.0:
            lines.append(
                f"Strong US session: S&P500 {snap.sp500_change:+.1f}% — "
                f"expect gap-{'up' if snap.sp500_change > 0 else 'down'} open"
            )
        if abs(snap.sgx_nifty_change) >= 0.6:
            lines.append(
                f"SGX Nifty futures {snap.sgx_nifty_change:+.2f}% — "
                f"direct pre-market signal for Nifty open"
            )
        if macro.yield_pressure:
            lines.append(
                f"US 10Y yield rising +{snap.us10y_change_bps:.0f} bps — "
                f"FII equity exit risk; banks / realty under pressure"
            )
        if macro.rupee_stress:
            lines.append(
                f"USD/INR {snap.usdinr_change:+.2f}% — rupee weakening; "
                f"FII outflow risk amplified"
            )
        if snap.crude_brent_change >= 2.5:
            lines.append(
                f"Crude spike +{snap.crude_brent_change:.1f}% — auto & FMCG margin "
                f"pressure; Oil & Gas positive"
            )
        if snap.gold_change >= 1.0:
            lines.append(
                f"Gold +{snap.gold_change:.1f}% — safe-haven demand; "
                f"defensive posture recommended"
            )
        if sectors.get("IT") == "positive":
            lines.append(
                f"Nasdaq {snap.nasdaq_change:+.1f}% tailwind — IT sector likely outperformer"
            )
        return lines
