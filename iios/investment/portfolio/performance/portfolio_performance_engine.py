"""iios/investment/portfolio/performance/portfolio_performance_engine.py

Portfolio Performance Engine — main orchestrator.

Responsibility: measure, evaluate, explain, attribute, benchmark, forecast,
and monitor portfolio performance throughout its lifecycle.

Does NOT: optimize portfolios, rebalance portfolios, execute trades.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.investment.portfolio.performance.benchmark_comparison import BenchmarkComparison
from iios.investment.portfolio.performance.benchmark_engine import BenchmarkEngine, BenchmarkReport
from iios.investment.portfolio.performance.benchmark_statistics import BenchmarkStatistics
from iios.investment.portfolio.performance.performance_attribution import (
    AttributionResult, PortfolioAttributionEngine,
)
from iios.investment.portfolio.performance.performance_confidence import (
    PerformanceConfidenceReport, compute_performance_confidence,
)
from iios.investment.portfolio.performance.performance_forecast import (
    PerformanceForecast, forecast_performance,
)
from iios.investment.portfolio.performance.performance_health import (
    PerformanceHealthMonitor, PerformanceHealthReport,
)
from iios.investment.portfolio.performance.performance_history import PortfolioPerformanceHistory
from iios.investment.portfolio.performance.performance_profile import PerformanceProfile
from iios.investment.portfolio.performance.performance_quality import (
    PerformanceQualityAssessor, PerformanceQualityReport,
)
from iios.investment.portfolio.performance.performance_ratios import (
    PerformanceRatios, compute_all_ratios,
)
from iios.investment.portfolio.performance.performance_score import (
    PerformanceScore, PerformanceScoreCalculator, PerformanceScoreHistory,
)
from iios.investment.portfolio.performance.performance_snapshot import (
    PerformanceHistory, PerformanceRecord,
)
from iios.investment.portfolio.performance.performance_statistics import (
    PerformanceRunMetric, PerformanceStatisticsSnapshot, PortfolioPerformanceStatistics,
)
from iios.investment.portfolio.performance.performance_types import (
    PerformanceTrend, PerformancePosition, positions_from_plan,
    portfolio_return as calc_portfolio_return,
    portfolio_vol_proxy,
    RISK_FREE_RATE_ANNUAL,
)
from iios.investment.portfolio.performance.return_analysis import (
    ReturnAnalysis, analyze_returns,
)
from iios.investment.portfolio.performance.risk_adjusted_returns import (
    RiskAdjustedReturns, compute_risk_adjusted_returns,
)


@dataclass
class PerformanceIntegrationRefs:
    """Optional upstream engine references (loose coupling)."""

    portfolio_framework:     Optional[Any] = None
    construction_engine:     Optional[Any] = None
    allocation_engine:       Optional[Any] = None
    optimization_engine:     Optional[Any] = None
    diversification_engine:  Optional[Any] = None
    risk_engine:             Optional[Any] = None
    decision_intelligence:   Optional[Any] = None
    market_intelligence:     Optional[Any] = None
    company_intelligence:    Optional[Any] = None
    strategy_intelligence:   Optional[Any] = None


class PortfolioPerformanceEngine:
    """
    Institutional Portfolio Performance Engine.

    Thread-safe. Start/stop lifecycle. All evaluation is synchronous.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        *,
        quality_assessor:  Optional[PerformanceQualityAssessor] = None,
        score_calculator:  Optional[PerformanceScoreCalculator] = None,
        max_history:       int = 200,
        event_callback:    Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._lock              = threading.RLock()
        self._running           = False
        self._refs              = PerformanceIntegrationRefs()
        self._registered:       Dict[str, bool] = {}
        self._event_cb          = event_callback

        # Sub-components
        self._quality_assessor  = quality_assessor or PerformanceQualityAssessor()
        self._score_calc        = score_calculator or PerformanceScoreCalculator()
        self._attribution_engine= PortfolioAttributionEngine()
        self._benchmark_engine  = BenchmarkEngine()
        self._benchmark_stats   = BenchmarkStatistics()
        self._health_monitor    = PerformanceHealthMonitor()
        self._statistics        = PortfolioPerformanceStatistics()
        self._profile_history   = PortfolioPerformanceHistory(max_history)

        # Per-portfolio score histories
        self._score_histories:  Dict[str, PerformanceScoreHistory] = {}
        # Per-portfolio lightweight snapshot histories
        self._snap_histories:   Dict[str, PerformanceHistory] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            self._running = True

    def stop(self) -> None:
        with self._lock:
            self._running = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ------------------------------------------------------------------
    # Integration refs
    # ------------------------------------------------------------------

    def configure_integrations(self, refs: PerformanceIntegrationRefs) -> None:
        with self._lock:
            self._refs = refs

    # ------------------------------------------------------------------
    # Portfolio registration
    # ------------------------------------------------------------------

    def register_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            if portfolio_id not in self._registered:
                self._registered[portfolio_id] = True
                self._score_histories[portfolio_id] = PerformanceScoreHistory(portfolio_id)
                self._snap_histories[portfolio_id]  = PerformanceHistory(portfolio_id)

    def deregister_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            self._registered.pop(portfolio_id, None)

    def is_registered(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._registered

    # ------------------------------------------------------------------
    # Core evaluate
    # ------------------------------------------------------------------

    def evaluate(
        self,
        portfolio_id:  str,
        plan:          Any,
        *,
        period_years:  float = 1.0,
        benchmark_id:  str   = "nifty50",
        nav_series:    Optional[List[float]] = None,
        return_series: Optional[List[float]] = None,
        auto_register: bool  = True,
    ) -> PerformanceProfile:
        """
        Full performance evaluation for a portfolio.

        ``plan`` may be:
        - A list of PerformancePosition objects
        - A duck-typed plan object with .positions or .allocations
        """
        t_start = time.monotonic()
        succeeded = False

        try:
            if auto_register and not self.is_registered(portfolio_id):
                self.register_portfolio(portfolio_id)

            positions = positions_from_plan(plan)

            # Previous score for trend
            with self._lock:
                score_hist = self._score_histories.get(portfolio_id)
            prev_score_val: Optional[float] = None
            if score_hist:
                latest = score_hist.latest()
                if latest:
                    prev_score_val = latest.overall

            profile = self._build_profile(
                portfolio_id  = portfolio_id,
                positions     = positions,
                period_years  = period_years,
                benchmark_id  = benchmark_id,
                nav_series    = nav_series,
                return_series = return_series,
                prev_score    = prev_score_val,
            )

            # Persist
            self._profile_history.add(portfolio_id, profile)
            if score_hist:
                score = self._score_calc.calculate(
                    sharpe           = profile.sharpe_ratio,
                    alpha            = profile.alpha,
                    sortino          = profile.sortino_ratio,
                    calmar           = profile.calmar_ratio,
                    information_ratio= profile.information_ratio,
                    portfolio_id     = portfolio_id,
                    previous_score   = prev_score_val,
                )
                score_hist.add(score)

            # Lightweight snapshot
            with self._lock:
                snap_hist = self._snap_histories.get(portfolio_id)
            if snap_hist:
                rec = PerformanceRecord(
                    portfolio_id    = portfolio_id,
                    portfolio_return= profile.annualized_return,
                    sharpe_ratio    = profile.sharpe_ratio,
                    alpha           = profile.alpha,
                    overall_score   = profile.overall_performance_score,
                    grade           = profile.performance_grade,
                    level           = profile.performance_level,
                    is_acceptable   = profile.is_acceptable,
                    n_positions     = profile.n_positions,
                    benchmark_id    = benchmark_id,
                )
                snap_hist.add(rec)

            succeeded = True
            return profile

        finally:
            duration_ms = (time.monotonic() - t_start) * 1000
            self._health_monitor.record_run(succeeded, duration_ms)
            self._statistics.record(PerformanceRunMetric(
                portfolio_id  = portfolio_id,
                succeeded     = succeeded,
                duration_ms   = round(duration_ms, 2),
                n_positions   = len(positions_from_plan(plan)) if succeeded else 0,
                overall_score = 0.0,
            ))

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def current_profile(self, portfolio_id: str) -> Optional[PerformanceProfile]:
        return self._profile_history.latest(portfolio_id)

    def history(self, portfolio_id: str, n: int = 10) -> List[Any]:
        return self._profile_history.recent(portfolio_id, n)

    def best_profile(self, portfolio_id: str) -> Optional[Any]:
        return self._profile_history.best(portfolio_id)

    def quality_score(self, portfolio_id: str) -> Optional[float]:
        profile = self.current_profile(portfolio_id)
        return profile.overall_performance_score if profile else None

    def statistics_snapshot(self) -> PerformanceStatisticsSnapshot:
        return self._statistics.snapshot()

    def health(self) -> PerformanceHealthReport:
        active = len(self._registered)
        return self._health_monitor.check(active)

    # ------------------------------------------------------------------
    # Monitoring shortcut
    # ------------------------------------------------------------------

    def monitor_portfolio(
        self,
        portfolio_id:  str,
        plan:          Any,
        *,
        period_years:  float = 1.0,
        benchmark_id:  str   = "nifty50",
        nav_series:    Optional[List[float]] = None,
        return_series: Optional[List[float]] = None,
    ) -> PerformanceHealthReport:
        """Evaluate and return health report (convenience method)."""
        self.evaluate(
            portfolio_id  = portfolio_id,
            plan          = plan,
            period_years  = period_years,
            benchmark_id  = benchmark_id,
            nav_series    = nav_series,
            return_series = return_series,
        )
        return self.health()

    # ------------------------------------------------------------------
    # Internal builder
    # ------------------------------------------------------------------

    def _build_profile(
        self,
        portfolio_id:  str,
        positions:     List[PerformancePosition],
        period_years:  float,
        benchmark_id:  str,
        nav_series:    Optional[List[float]],
        return_series: Optional[List[float]],
        prev_score:    Optional[float],
    ) -> PerformanceProfile:

        n = len(positions)

        # 1. Return analysis
        ret_analysis: ReturnAnalysis = analyze_returns(
            positions    = positions,
            portfolio_id = portfolio_id,
            period       = _period_label(period_years),
            period_years = period_years,
            nav_series   = nav_series,
        )
        ann_return = ret_analysis.annualized_return

        # 2. Benchmark comparison
        bmk_report: BenchmarkReport = self._benchmark_engine.run_all(
            positions        = positions,
            portfolio_return = ann_return,
            portfolio_id     = portfolio_id,
            benchmark_ids    = [benchmark_id],
            period_years     = period_years,
        )
        bmk_comp: Optional[BenchmarkComparison] = bmk_report.primary
        if bmk_comp:
            self._benchmark_stats.record(bmk_comp)

        # 3. Attribution
        attribution: AttributionResult = self._attribution_engine.analyze(
            positions            = positions,
            benchmark_comparison = bmk_comp,
            portfolio_id         = portfolio_id,
        )

        # 4. Vol proxy
        vol = portfolio_vol_proxy(positions)

        # 5. Risk-adjusted returns
        beta     = bmk_comp.beta if bmk_comp else 1.0
        max_dd   = vol * 2.0 * period_years   # rough proxy; 2σ drawdown estimate
        rar: RiskAdjustedReturns = compute_risk_adjusted_returns(
            positions        = positions,
            portfolio_return = ann_return,
            portfolio_vol    = vol,
            beta             = beta,
            max_drawdown     = max_dd,
            portfolio_id     = portfolio_id,
            return_series    = return_series,
        )

        # 6. Extended ratios
        bmk_vol = 0.16  # nifty50 proxy default
        te      = bmk_comp.tracking_error if bmk_comp else 0.05
        bmk_ret = bmk_comp.benchmark_return if bmk_comp else 0.12
        ratios: PerformanceRatios = compute_all_ratios(
            risk_adjusted    = rar,
            benchmark_return = bmk_ret,
            benchmark_vol    = bmk_vol,
            tracking_error   = te,
            return_series    = return_series,
        )

        # 7. Score
        alpha = bmk_comp.alpha if bmk_comp else (ann_return - RISK_FREE_RATE_ANNUAL)
        score: PerformanceScore = self._score_calc.calculate(
            sharpe           = rar.sharpe_ratio,
            alpha            = alpha,
            sortino          = rar.sortino_ratio,
            calmar           = rar.calmar_ratio,
            information_ratio= ratios.information_ratio,
            portfolio_id     = portfolio_id,
            previous_score   = prev_score,
        )

        # 8. Quality
        quality: PerformanceQualityReport = self._quality_assessor.assess(
            overall_score    = score.overall,
            sharpe           = rar.sharpe_ratio,
            sortino          = rar.sortino_ratio,
            calmar           = rar.calmar_ratio,
            information_ratio= ratios.information_ratio,
            alpha            = alpha,
            max_drawdown     = max_dd,
            portfolio_id     = portfolio_id,
        )

        # 9. Confidence
        confidence: PerformanceConfidenceReport = compute_performance_confidence(
            positions       = positions,
            has_nav_series  = nav_series is not None,
            analysis_complete = True,
            portfolio_id    = portfolio_id,
        )

        # 10. Forecast
        forecast: PerformanceForecast = forecast_performance(
            positions       = positions,
            current_sharpe  = rar.sharpe_ratio,
            portfolio_vol   = vol,
            portfolio_id    = portfolio_id,
        )

        # Alerts count
        n_alerts = len(quality.warnings) + len(confidence.limitations)

        top_sector = ""
        if attribution.sector_attribution:
            top_sector = attribution.sector_attribution.top_sector
        dominant_factor = ""
        if attribution.factor_attribution:
            dominant_factor = attribution.factor_attribution.dominant_factor
        best_strategy = ""
        if attribution.strategy_attribution:
            best_strategy = attribution.strategy_attribution.best_strategy

        return PerformanceProfile(
            portfolio_id           = portfolio_id,
            n_positions            = n,
            period_years           = period_years,
            total_period_return    = ret_analysis.total_period_return,
            annualized_return      = ann_return,
            excess_return          = ret_analysis.excess_return,
            expected_return        = ret_analysis.expected_return,
            benchmark_id           = bmk_comp.benchmark_id if bmk_comp else benchmark_id,
            benchmark_return       = bmk_comp.benchmark_return if bmk_comp else 0.0,
            active_return          = bmk_comp.active_return if bmk_comp else 0.0,
            alpha                  = alpha,
            beta                   = beta,
            tracking_error         = te,
            information_ratio      = ratios.information_ratio,
            outperforms_benchmark  = bmk_comp.outperforms if bmk_comp else False,
            allocation_effect      = attribution.allocation_effect,
            selection_effect       = attribution.selection_effect,
            interaction_effect     = attribution.interaction_effect,
            top_sector             = top_sector,
            dominant_factor        = dominant_factor,
            best_strategy          = best_strategy,
            annual_vol             = vol,
            sharpe_ratio           = rar.sharpe_ratio,
            sortino_ratio          = rar.sortino_ratio,
            treynor_ratio          = rar.treynor_ratio,
            calmar_ratio           = rar.calmar_ratio,
            omega_ratio            = rar.omega_ratio,
            max_drawdown_proxy     = max_dd,
            modigliani_ratio       = ratios.modigliani_ratio,
            upside_potential_ratio = ratios.upside_potential_ratio,
            overall_performance_score = score.overall,
            performance_grade      = score.grade,
            performance_level      = score.level,
            performance_trend      = score.trend,
            is_acceptable          = score.is_acceptable,
            primary_weakness       = quality.primary_weakness,
            recommendation         = quality.recommendation,
            expected_return_1y     = forecast.expected_return_1y,
            prob_positive_1y       = forecast.prob_positive_1y,
            confidence_score       = confidence.confidence_score,
            n_alerts               = n_alerts,
        )


def _period_label(period_years: float) -> str:
    if period_years <= 0.1:
        return "1m"
    if period_years <= 0.3:
        return "3m"
    if period_years <= 0.6:
        return "6m"
    if period_years <= 1.1:
        return "1y"
    if period_years <= 3.1:
        return "3y"
    return "inception"
