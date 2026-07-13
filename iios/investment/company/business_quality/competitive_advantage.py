"""iios/investment/company/business_quality/competitive_advantage.py
Competitive advantage signal detection from financial patterns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.business_quality.economic_moat import MoatType, MoatSignal
from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.quality_statistics import (
    safe_mean, safe_stdev, clamp,
)


# Moat detection thresholds
_HIGH_ROIC_PCT       = 15.0   # ROIC threshold for capital moat signal
_PREMIUM_MARGIN_PCT  = 40.0   # Gross margin threshold for brand/pricing signal
_WIDE_MARGIN_PCT     = 55.0   # Strong brand signal
_FCF_CONVERSION_MIN  = 0.85   # OCF/NI for earnings quality signal
_LOW_CAPEX_PCT       = 5.0    # CapEx < 5% → asset-light moat
_ASSET_TURNOVER_LOW  = 0.5    # Very low → regulated/network asset
_HIGH_ROIC_WIDE      = 20.0   # ROIC for wide moat classification


class CompetitiveAdvantageDetector:
    """
    Detects competitive advantage signals from financial metrics.
    Returns a list of MoatSignal objects.
    """

    def detect(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals: List[MoatSignal] = []
        signals.extend(self._detect_brand(ctx))
        signals.extend(self._detect_cost_advantage(ctx))
        signals.extend(self._detect_switching_costs(ctx))
        signals.extend(self._detect_scale(ctx))
        signals.extend(self._detect_ip(ctx))
        signals.extend(self._detect_network(ctx))
        signals.extend(self._detect_distribution(ctx))
        return signals

    # ── Brand / Pricing power ──────────────────────────────────────────────────
    def _detect_brand(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals = []
        gm  = ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")
        nm  = ctx.income_metric("net_margin")   or ctx.ratio("net_margin")

        avg_gm: Optional[float] = None
        if ctx.earnings_snapshot:
            try:
                avg_gm = ctx.earnings_snapshot.profitability.avg_gross_margin
            except Exception:
                pass

        ref_gm = avg_gm or gm
        if ref_gm is not None:
            if ref_gm >= _WIDE_MARGIN_PCT:
                signals.append(MoatSignal(
                    moat_type=MoatType.BRAND,
                    strength=min(1.0, (ref_gm - _WIDE_MARGIN_PCT) / 30 + 0.65),
                    evidence=[f"avg_gross_margin={ref_gm:.1f}% (>55%)"],
                ))
            elif ref_gm >= _PREMIUM_MARGIN_PCT:
                signals.append(MoatSignal(
                    moat_type=MoatType.BRAND,
                    strength=0.40,
                    evidence=[f"avg_gross_margin={ref_gm:.1f}% (>40%)"],
                ))
        return signals

    # ── Cost advantage ─────────────────────────────────────────────────────────
    def _detect_cost_advantage(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals = []
        roic = ctx.ratio("roic") or ctx.ratio("return_on_invested_capital")
        avg_roic: Optional[float] = None
        if ctx.earnings_snapshot:
            try:
                avg_roic = ctx.earnings_snapshot.profitability.avg_roic
            except Exception:
                pass

        ref = avg_roic or roic
        if ref is not None and ref >= _HIGH_ROIC_PCT:
            strength = clamp((ref - _HIGH_ROIC_PCT) / 20, 0, 1)
            signals.append(MoatSignal(
                moat_type=MoatType.COST_ADVANTAGE,
                strength=strength,
                evidence=[f"avg_roic={ref:.1f}% (>15%)"],
            ))
        return signals

    # ── Switching costs (sticky revenue) ──────────────────────────────────────
    def _detect_switching_costs(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals = []
        rec_days = ctx.ratio("receivable_turnover_days") or ctx.ratio("dso")
        nm = ctx.income_metric("net_margin") or ctx.ratio("net_margin")

        # High margins + low receivables days → customers pay fast = sticky
        if nm is not None and rec_days is not None:
            if nm >= 15 and rec_days < 45:
                signals.append(MoatSignal(
                    moat_type=MoatType.SWITCHING_COSTS,
                    strength=0.45,
                    evidence=[f"net_margin={nm:.1f}%, rec_days={rec_days:.0f}"],
                ))
        return signals

    # ── Scale advantage ────────────────────────────────────────────────────────
    def _detect_scale(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals = []
        revenue = ctx.fs_metric("revenue")
        at      = ctx.ratio("asset_turnover")

        # High asset turnover → scale efficiency
        if at is not None and at >= 1.5:
            signals.append(MoatSignal(
                moat_type=MoatType.SCALE_ADVANTAGE,
                strength=min(1.0, (at - 1.5) / 2.0 + 0.35),
                evidence=[f"asset_turnover={at:.2f}"],
            ))
        return signals

    # ── Intellectual Property (R&D driven) ────────────────────────────────────
    def _detect_ip(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals = []
        rd_pct  = ctx.ratio("rd_pct") or ctx.income_metric("rd_pct")
        gm      = ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")

        if rd_pct is not None and rd_pct >= 5.0 and (gm is None or gm >= 40.0):
            strength = min(1.0, (rd_pct - 5.0) / 15.0 + 0.35)
            signals.append(MoatSignal(
                moat_type=MoatType.INTELLECTUAL_PROPERTY,
                strength=strength,
                evidence=[f"rd_pct={rd_pct:.1f}%"],
            ))
        return signals

    # ── Network effect (asset-light + high margins) ───────────────────────────
    def _detect_network(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals = []
        capex_pct = ctx.cashflow_metric("capex_pct") or ctx.ratio("capex_pct")
        gm        = ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")

        if capex_pct is not None and gm is not None:
            if capex_pct < _LOW_CAPEX_PCT and gm >= 55.0:
                signals.append(MoatSignal(
                    moat_type=MoatType.NETWORK_EFFECT,
                    strength=0.50,
                    evidence=[f"capex_pct={capex_pct:.1f}%, gm={gm:.1f}%"],
                ))
        return signals

    # ── Distribution strength ─────────────────────────────────────────────────
    def _detect_distribution(self, ctx: AssessmentContext) -> List[MoatSignal]:
        signals = []
        sga_pct = ctx.income_metric("sga_pct") or ctx.ratio("sga_pct")
        gm      = ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")

        # High SGA + high gross margin → investment in distribution moat
        if sga_pct is not None and gm is not None:
            if sga_pct >= 20.0 and gm >= 50.0:
                signals.append(MoatSignal(
                    moat_type=MoatType.DISTRIBUTION,
                    strength=0.35,
                    evidence=[f"sga_pct={sga_pct:.1f}%, gm={gm:.1f}%"],
                ))
        return signals
