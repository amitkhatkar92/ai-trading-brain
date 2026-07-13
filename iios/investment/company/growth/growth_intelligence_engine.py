"""iios/investment/company/growth/growth_intelligence_engine.py
PRIMARY ENGINE — Institutional Growth Intelligence Engine.

Consumes from:
  • FinancialSnapshot   (iios.investment.company.financials)
  • EarningsSnapshot    (iios.investment.company.earnings)
  • BusinessQualitySnapshot (iios.investment.company.business_quality)
  • ValuationSnapshot   (iios.investment.company.valuation) [optional]

Produces:
  • GrowthSnapshot

Does NOT:
  • Fetch or parse raw financial data
  • Make buy/sell/hold recommendations
  • Rank companies against each other
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.company.growth.growth_snapshot import GrowthSnapshot
from iios.investment.company.growth.growth_profile import (
    GrowthTrend, GrowthIntelligenceScore,
)
from iios.investment.company.growth.growth_history import GrowthHistory
from iios.investment.company.growth.revenue_growth import RevenueGrowthEngine
from iios.investment.company.growth.earnings_growth import EarningsGrowthEngine
from iios.investment.company.growth.margin_growth import MarginGrowthEngine
from iios.investment.company.growth.cashflow_growth import CashflowGrowthEngine
from iios.investment.company.growth.growth_driver_engine import GrowthDriverEngine
from iios.investment.company.growth.growth_sustainability import GrowthSustainabilityEngine
from iios.investment.company.growth.forecast_engine import ForecastEngine
from iios.investment.company.growth.forecast_assumptions import ForecastAssumptions
from iios.investment.company.growth.growth_quality import assess_growth_quality
from iios.investment.company.growth.growth_confidence import compute_overall_confidence
from iios.investment.company.growth.growth_score import compute_growth_score
from iios.investment.company.growth.driver_registry import DriverPlugin, DriverRegistry
from iios.investment.company.growth.organic_growth import estimate_organic_revenue_growth


class GrowthIntelligenceEngine:
    """
    Thread-safe growth intelligence engine.
    One instance should exist per IIOS deployment (singleton pattern encouraged).
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._history = GrowthHistory()

        self._revenue_engine       = RevenueGrowthEngine()
        self._earnings_engine      = EarningsGrowthEngine()
        self._margin_engine        = MarginGrowthEngine()
        self._cashflow_engine      = CashflowGrowthEngine()
        self._registry             = DriverRegistry()
        self._driver_engine        = GrowthDriverEngine(registry=self._registry)
        self._sustainability_engine = GrowthSustainabilityEngine()
        self._forecast_engine      = ForecastEngine()

    # ── Public API ───────────────────────────────────────────────────────────────

    def ingest(
        self,
        ticker:              str,
        financial_snapshot:  Any,                    # FinancialSnapshot
        earnings_snapshot:   Any,                    # EarningsSnapshot
        business_quality:    Any,                    # BusinessQualitySnapshot
        valuation_snapshot:  Any = None,             # Optional[ValuationSnapshot]
        revenue_series:      Optional[List[float]] = None,  # chronological, oldest first
        eps_series:          Optional[List[float]] = None,
        fcf_series:          Optional[List[float]] = None,
        forecast_assumptions: Optional[ForecastAssumptions] = None,
    ) -> GrowthSnapshot:
        """
        Compute and store a GrowthSnapshot for the given ticker.
        All snapshot arguments MUST be the outputs of their respective engines.
        Returns the GrowthSnapshot (also accessible via get_snapshot()).
        """
        inputs = self._extract_inputs(
            ticker=ticker,
            financial_snapshot=financial_snapshot,
            earnings_snapshot=earnings_snapshot,
            business_quality=business_quality,
            revenue_series=revenue_series,
            eps_series=eps_series,
            fcf_series=fcf_series,
        )

        snapshot = self._build_snapshot(ticker, inputs, forecast_assumptions)

        with self._lock:
            self._history.push(ticker, snapshot)

        return snapshot

    def get_snapshot(self, ticker: str) -> Optional[GrowthSnapshot]:
        with self._lock:
            return self._history.get_latest(ticker)

    def get_revenue_cagr(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.revenue.cagr.best_available if s else None

    def get_eps_cagr(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.earnings.eps_cagr.best_available if s else None

    def get_sustainability_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.sustainability.sustainability_score if s else None

    def get_growth_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.growth_score.overall_score if s else None

    def get_forecast(self, ticker: str):
        s = self.get_snapshot(ticker)
        return s.forecast if s else None

    def known_tickers(self) -> List[str]:
        with self._lock:
            return self._history.all_tickers()

    def register_driver_plugin(self, plugin: DriverPlugin) -> None:
        """Register a custom DriverPlugin for growth driver analysis."""
        self._registry.register(plugin)

    # ── Internal: input extraction ────────────────────────────────────────────

    def _extract_inputs(
        self,
        ticker:             str,
        financial_snapshot: Any,
        earnings_snapshot:  Any,
        business_quality:   Any,
        revenue_series:     Optional[List[float]],
        eps_series:         Optional[List[float]],
        fcf_series:         Optional[List[float]],
    ) -> Dict[str, Any]:
        """
        Extract all required inputs from upstream snapshots.
        Uses getattr(…, default) throughout to handle partial snapshots gracefully.
        """
        inp: Dict[str, Any] = {}
        inp["ticker"] = ticker

        # ── From FinancialSnapshot ────────────────────────────────────────────
        inp["current_revenue"] = getattr(financial_snapshot, "revenue", None)
        _cf = getattr(financial_snapshot, "cashflow_metrics", None)
        inp["current_fcf"] = getattr(_cf, "free_cash_flow", None)
        inp["current_ocf"] = getattr(_cf, "operating_cash_flow", None)
        _im = getattr(financial_snapshot, "income_metrics", None)
        inp["net_income"]   = getattr(_im, "net_income", None)
        _ratios             = getattr(financial_snapshot, "ratios", {}) or {}
        inp["ebitda"]       = _ratios.get("ebitda") if isinstance(_ratios, dict) else None

        # ── From EarningsSnapshot ─────────────────────────────────────────────
        _trend        = getattr(earnings_snapshot, "trend", None)
        inp["cagr_eps"]          = getattr(_trend, "cagr_eps", None)
        inp["eps_direction"]     = getattr(_trend, "eps_direction", None)
        inp["revenue_direction"] = getattr(_trend, "revenue_direction", None)

        _prof = getattr(earnings_snapshot, "profitability", None)
        inp["avg_net_margin"]   = getattr(_prof, "avg_net_margin", None)
        inp["net_margin"]       = getattr(_prof, "net_margin", None)
        inp["avg_gross_margin"] = getattr(_prof, "avg_gross_margin", None)
        inp["avg_fcf_margin"]   = getattr(_prof, "avg_fcf_margin", None)
        inp["avg_roe"]          = getattr(_prof, "avg_roe", None)
        inp["roe"]              = getattr(_prof, "roe", None)
        inp["avg_roic"]         = getattr(_prof, "avg_roic", None)
        inp["roic"]             = getattr(_prof, "roic", None)

        _risk = getattr(earnings_snapshot, "risk", None)
        inp["eps_volatility"]       = getattr(_risk, "eps_volatility", None)
        inp["revenue_volatility"]   = getattr(_risk, "revenue_volatility", None)
        inp["margin_volatility"]    = getattr(_risk, "margin_volatility", None)
        inp["earnings_stability"]   = getattr(_risk, "earnings_stability_score", None)
        inp["is_cyclical"]          = getattr(_risk, "is_cyclical", None)
        inp["loss_rate"]            = getattr(_risk, "loss_rate", None)

        _qual = getattr(earnings_snapshot, "quality", None)
        inp["consistency_score"] = getattr(_qual, "consistency_score", None)

        inp["history_depth"] = getattr(earnings_snapshot, "history_depth", 0) or 0

        # ── From BusinessQualitySnapshot ──────────────────────────────────────
        _moat = getattr(business_quality, "moat", None)
        inp["moat_score"]   = getattr(_moat, "moat_score", None)
        inp["moat_types"]   = getattr(_moat, "detected_moat_types", None) or []
        inp["bq_avg_roic"]  = getattr(_moat, "avg_roic", None)

        _ops = getattr(business_quality, "operational", None)
        inp["operational_quality"] = getattr(_ops, "operational_quality_score", None)

        _res = getattr(business_quality, "resilience", None)
        inp["resilience_score"] = getattr(_res, "resilience_score", None)

        # ── Optional explicit time series ──────────────────────────────────────
        inp["revenue_series"] = revenue_series
        inp["eps_series"]     = eps_series
        inp["fcf_series"]     = fcf_series

        return inp

    # ── Internal: snapshot assembly ───────────────────────────────────────────

    def _build_snapshot(
        self,
        ticker:       str,
        inp:          Dict[str, Any],
        assumptions:  Optional[ForecastAssumptions],
    ) -> GrowthSnapshot:

        # ── Revenue growth ───────────────────────────────────────────────────
        revenue_profile = self._revenue_engine.compute(
            revenue_series=inp.get("revenue_series"),
            current_revenue=inp.get("current_revenue"),
            revenue_direction=inp.get("revenue_direction"),
            revenue_volatility=inp.get("revenue_volatility"),
            history_depth=inp.get("history_depth", 0),
        )

        # Organic estimate
        revenue_profile.organic_estimate = estimate_organic_revenue_growth(
            reported_revenue_growth=revenue_profile.cagr.best_available,
            margin_expansion_bps=None,   # will be filled after margin computation
            avg_roic=inp.get("bq_avg_roic") or inp.get("avg_roic"),
            operational_quality=inp.get("operational_quality"),
        )

        # ── Earnings growth ───────────────────────────────────────────────────
        earnings_profile = self._earnings_engine.compute(
            cagr_eps=inp.get("cagr_eps"),
            eps_direction=inp.get("eps_direction"),
            avg_net_margin=inp.get("avg_net_margin"),
            net_margin=inp.get("net_margin"),
            eps_volatility=inp.get("eps_volatility"),
            net_income=inp.get("net_income"),
            current_revenue=inp.get("current_revenue"),
            eps_series=inp.get("eps_series"),
            history_depth=inp.get("history_depth", 0),
        )

        # ── Margin growth ─────────────────────────────────────────────────────
        margin_profile = self._margin_engine.compute(
            current_net_margin=inp.get("net_margin"),
            avg_net_margin=inp.get("avg_net_margin"),
            current_gross_margin=inp.get("avg_gross_margin"),  # use avg as proxy for current
            avg_gross_margin=inp.get("avg_gross_margin"),
            margin_volatility=inp.get("margin_volatility"),
            history_depth=inp.get("history_depth", 0),
        )

        # Backfill organic estimate with margin data
        revenue_profile.organic_estimate = estimate_organic_revenue_growth(
            reported_revenue_growth=revenue_profile.cagr.best_available,
            margin_expansion_bps=margin_profile.net_margin_expansion_bps,
            avg_roic=inp.get("bq_avg_roic") or inp.get("avg_roic"),
            operational_quality=inp.get("operational_quality"),
        )

        # ── Cashflow growth ───────────────────────────────────────────────────
        cashflow_profile = self._cashflow_engine.compute(
            current_revenue=inp.get("current_revenue"),
            current_fcf=inp.get("current_fcf"),
            current_ocf=inp.get("current_ocf"),
            avg_fcf_margin=inp.get("avg_fcf_margin"),
            fcf_series=inp.get("fcf_series"),
            history_depth=inp.get("history_depth", 0),
        )

        # ── Growth drivers ────────────────────────────────────────────────────
        drivers_profile = self._driver_engine.compute(
            avg_net_margin=inp.get("avg_net_margin"),
            current_net_margin=inp.get("net_margin"),
            revenue_cagr=revenue_profile.cagr.best_available,
            eps_cagr=earnings_profile.eps_cagr.best_available,
            moat_score=inp.get("moat_score"),
            moat_types=inp.get("moat_types"),
            gross_margin_exp=margin_profile.gross_margin_expansion_bps,
            avg_gross_margin=inp.get("avg_gross_margin"),
            operational_quality=inp.get("operational_quality"),
            resilience_score=inp.get("resilience_score"),
            avg_roic=inp.get("bq_avg_roic") or inp.get("avg_roic"),
            revenue_trend=revenue_profile.trend.value,
            earnings_trend=earnings_profile.trend.value,
            margin_expanding=margin_profile.is_expanding,
            is_cyclical=inp.get("is_cyclical"),
            history_depth=inp.get("history_depth", 0),
        )

        # ── Sustainability ────────────────────────────────────────────────────
        sustainability_profile = self._sustainability_engine.compute(
            eps_volatility=inp.get("eps_volatility"),
            revenue_volatility=inp.get("revenue_volatility"),
            margin_volatility=inp.get("margin_volatility"),
            consistency_score=inp.get("consistency_score"),
            loss_rate=inp.get("loss_rate"),
            is_cyclical=inp.get("is_cyclical"),
            avg_fcf_margin=inp.get("avg_fcf_margin"),
            net_margin=inp.get("net_margin"),
            avg_net_margin=inp.get("avg_net_margin"),
            earnings_stability=inp.get("earnings_stability"),
            moat_score=inp.get("moat_score"),
            resilience_score=inp.get("resilience_score"),
            history_depth=inp.get("history_depth", 0),
        )

        # ── Forecast ──────────────────────────────────────────────────────────
        forecast_profile = self._forecast_engine.compute(
            revenue_cagr=revenue_profile.cagr.best_available,
            eps_cagr=earnings_profile.eps_cagr.best_available,
            sustainability=sustainability_profile.sustainability_score,
            eps_volatility=inp.get("eps_volatility"),
            revenue_volatility=inp.get("revenue_volatility"),
            history_depth=inp.get("history_depth", 0),
            assumptions=assumptions,
        )

        # ── Quality ───────────────────────────────────────────────────────────
        quality = assess_growth_quality(
            has_eps_cagr=earnings_profile.eps_cagr.best_available is not None,
            has_revenue_cagr=revenue_profile.cagr.best_available is not None,
            has_fcf_data=cashflow_profile.fcf_cagr.best_available is not None
                         or cashflow_profile.avg_fcf_margin is not None,
            has_margin_data=margin_profile.current_net_margin is not None,
            history_depth=inp.get("history_depth", 0),
            eps_volatility=inp.get("eps_volatility"),
            loss_rate=inp.get("loss_rate"),
        )

        # ── Score ─────────────────────────────────────────────────────────────
        growth_score = compute_growth_score(
            revenue_cagr=revenue_profile.cagr.best_available,
            eps_cagr=earnings_profile.eps_cagr.best_available,
            ni_cagr=earnings_profile.net_income_cagr.best_available,
            fcf_cagr=cashflow_profile.fcf_cagr.best_available,
            sustainability=sustainability_profile.sustainability_score,
            forecast_confidence=forecast_profile.forecast_confidence,
        )

        # ── Overall confidence ────────────────────────────────────────────────
        confidence = compute_overall_confidence(
            history_depth=inp.get("history_depth", 0),
            has_eps_cagr=earnings_profile.eps_cagr.best_available is not None,
            has_revenue_cagr=revenue_profile.cagr.best_available is not None,
            has_fcf_data=cashflow_profile.avg_fcf_margin is not None,
            quality_label=quality.quality_label,
            sustainability=sustainability_profile.sustainability_score,
            eps_volatility=inp.get("eps_volatility"),
        )

        return GrowthSnapshot(
            ticker=ticker,
            revenue=revenue_profile,
            earnings=earnings_profile,
            margin=margin_profile,
            cashflow=cashflow_profile,
            drivers=drivers_profile,
            sustainability=sustainability_profile,
            forecast=forecast_profile,
            quality=quality,
            growth_score=growth_score,
            confidence=confidence,
            history_depth=inp.get("history_depth", 0),
        )
