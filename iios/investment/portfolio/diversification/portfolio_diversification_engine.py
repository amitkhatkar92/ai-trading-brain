"""iios/investment/portfolio/diversification/portfolio_diversification_engine.py

PortfolioDiversificationEngine — authoritative diversification intelligence
for the Institutional Investment Intelligence Operating System (IIOS).

Responsibility:
    Evaluate, measure, explain, monitor, and improve portfolio diversification
    while respecting institutional investment policies.

Does NOT:
  • Optimize portfolios
  • Rebalance portfolios
  • Execute trades
  • Independently analyze markets, companies, or strategies
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.concentration_engine import ConcentrationEngine
from iios.investment.portfolio.diversification.correlation_engine import CorrelationEngine
from iios.investment.portfolio.diversification.diversification_alerts import (
    AlertThresholds,
    DiversificationAlert,
    DiversificationAlerter,
)
from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalysis,
    DiversificationAnalyzer,
)
from iios.investment.portfolio.diversification.diversification_health import (
    DiversificationHealthMonitor,
    DiversificationHealthReport,
)
from iios.investment.portfolio.diversification.diversification_metrics import (
    DiversificationMetrics,
    compute_diversification_metrics,
)
from iios.investment.portfolio.diversification.diversification_monitor import (
    DiversificationMonitor,
    MonitoringReport,
)
from iios.investment.portfolio.diversification.diversification_profile import DiversificationProfile
from iios.investment.portfolio.diversification.diversification_quality import (
    DiversificationQualityAssessor,
    DiversificationQualityReport,
)
from iios.investment.portfolio.diversification.diversification_score import (
    DiversificationScore,
    DiversificationScoreCalculator,
    DiversificationScoreHistory,
)
from iios.investment.portfolio.diversification.diversification_snapshot import (
    DiversificationHistory,
    DiversificationRecord,
)
from iios.investment.portfolio.diversification.diversification_statistics import (
    DiversificationRunMetric,
    DiversificationStatistics,
    DiversificationStatisticsSnapshot,
)
from iios.investment.portfolio.diversification.diversification_trends import (
    TrendAnalyzer,
    TrendsReport,
)
from iios.investment.portfolio.diversification.diversification_types import (
    DiversificationGrade,
    DiversificationStatus,
    PositionData,
    positions_from_plan,
)


# ---------------------------------------------------------------------------
# Integration references
# ---------------------------------------------------------------------------

@dataclass
class DiversificationIntegrationRefs:
    """Soft references to upstream/peer intelligence layers (all optional)."""

    decision_intelligence:   Optional[Any] = None
    market_intelligence:     Optional[Any] = None
    company_intelligence:    Optional[Any] = None
    strategy_intelligence:   Optional[Any] = None
    construction_engine:     Optional[Any] = None
    allocation_engine:       Optional[Any] = None
    optimization_engine:     Optional[Any] = None
    historical_framework:    Optional[Any] = None
    knowledge_layer:         Optional[Any] = None
    audit_framework:         Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: (v is not None) for k, v in self.__dict__.items()}


# ---------------------------------------------------------------------------
# Per-portfolio state
# ---------------------------------------------------------------------------

@dataclass
class _PortfolioDiversificationState:
    portfolio_id:  str
    history:       DiversificationHistory
    score_history: DiversificationScoreHistory
    version:       int   = 0
    registered_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PortfolioDiversificationEngine:
    """
    Institutional Portfolio Diversification Engine.

    Thread-safe.  One instance serves multiple portfolios.

    Usage
    -----
    engine = PortfolioDiversificationEngine()
    engine.start()
    profile = engine.evaluate(portfolio_id, plan)
    engine.stop()
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        *,
        quality_assessor:     Optional[DiversificationQualityAssessor]  = None,
        score_calculator:     Optional[DiversificationScoreCalculator]   = None,
        concentration_engine: Optional[ConcentrationEngine]              = None,
        correlation_engine:   Optional[CorrelationEngine]                = None,
        thresholds:           Optional[AlertThresholds]                  = None,
        max_history:          int                                         = 200,
        event_callback:       Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._quality    = quality_assessor  or DiversificationQualityAssessor()
        self._scorer     = score_calculator  or DiversificationScoreCalculator()
        self._analyzer   = DiversificationAnalyzer(
            concentration_engine = concentration_engine or ConcentrationEngine(),
            correlation_engine   = correlation_engine   or CorrelationEngine(),
        )
        self._monitor    = DiversificationMonitor(thresholds=thresholds)
        self._alerter    = DiversificationAlerter()
        self._health     = DiversificationHealthMonitor()
        self._stats      = DiversificationStatistics()
        self._trends     = TrendAnalyzer()
        self._thresholds = thresholds
        self._max_history= max_history
        self._callback   = event_callback

        self._portfolios: Dict[str, _PortfolioDiversificationState] = {}
        self._lock       = threading.RLock()
        self._running    = False
        self._started_at: Optional[float] = None
        self._integrations: Optional[DiversificationIntegrationRefs] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running    = True
            self._started_at = time.time()
        self._emit("engine_started", {"version": self.VERSION})

    def stop(self) -> None:
        with self._lock:
            self._running = False
        self._emit("engine_stopped", {})

    @property
    def is_running(self) -> bool:
        return self._running

    def configure_integrations(self, refs: DiversificationIntegrationRefs) -> None:
        self._integrations = refs

    # ------------------------------------------------------------------
    # Portfolio registration
    # ------------------------------------------------------------------

    def register_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            if portfolio_id not in self._portfolios:
                self._portfolios[portfolio_id] = _PortfolioDiversificationState(
                    portfolio_id  = portfolio_id,
                    history       = DiversificationHistory(portfolio_id, self._max_history),
                    score_history = DiversificationScoreHistory(portfolio_id),
                )

    def deregister_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            self._portfolios.pop(portfolio_id, None)

    def is_registered(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._portfolios

    def list_portfolios(self) -> List[str]:
        with self._lock:
            return list(self._portfolios)

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._portfolios)

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------

    def evaluate(
        self,
        portfolio_id: str,
        plan:         Any,              # OptimizationPlan or AllocationPlan (duck-typed)
        *,
        auto_register:bool = True,
        total_capital:float = 0.0,
        currency:     str  = "INR",
    ) -> DiversificationProfile:
        """
        Evaluate portfolio diversification.

        Parameters
        ----------
        plan:
            An OptimizationPlan or AllocationPlan exposing .positions or .allocations.
        total_capital:
            Portfolio total capital; extracted from plan if not provided.
        """
        t0 = time.time()

        if auto_register:
            self.register_portfolio(portfolio_id)

        if not self.is_running:
            return self._empty_profile(portfolio_id, "Engine is not running")

        with self._lock:
            state = self._portfolios.get(portfolio_id)

        if state is None:
            return self._empty_profile(portfolio_id, "Portfolio not registered")

        try:
            profile = self._run_evaluation(
                portfolio_id, plan, state, t0, total_capital, currency
            )
            succeeded = True
        except Exception as exc:  # pylint: disable=broad-except
            profile   = self._empty_profile(portfolio_id, f"Error: {exc}")
            succeeded = False

        dur_ms = (time.time() - t0) * 1000
        self._stats.record(DiversificationRunMetric(
            portfolio_id         = portfolio_id,
            succeeded            = succeeded,
            n_positions          = profile.n_positions,
            hhi                  = profile.hhi,
            effective_n          = profile.effective_n,
            entropy_ratio        = profile.entropy_ratio,
            avg_correlation      = profile.avg_correlation,
            diversification_ratio= profile.diversification_ratio,
            overall_score        = profile.overall_score,
            n_alerts             = profile.n_alerts,
            duration_ms          = dur_ms,
        ))
        self._health.record_run(succeeded=succeeded, duration_ms=dur_ms)
        return profile

    # ------------------------------------------------------------------

    def _run_evaluation(
        self,
        portfolio_id: str,
        plan:         Any,
        state:        _PortfolioDiversificationState,
        t0:           float,
        total_capital:float,
        currency:     str,
    ) -> DiversificationProfile:
        # 1. Extract positions
        positions = positions_from_plan(plan)
        if not positions:
            return self._empty_profile(portfolio_id, "Plan has no positions")

        tc = total_capital or float(getattr(plan, "total_capital", 0.0))

        # 2. Analyse
        plan_id   = str(getattr(plan, "plan_id", ""))
        analysis  = self._analyzer.analyze(positions, portfolio_id, plan_id)

        # 3. Quality + score
        q_report  = self._quality.assess(analysis)
        prev_score= state.score_history.latest()
        score     = self._scorer.calculate(q_report, prev_score)
        state.score_history.record(score)

        # 4. Alerts
        alerts    = self._alerter.generate(analysis, self._thresholds)
        n_crit    = sum(1 for a in alerts if a.severity.value == "critical")

        # 5. Increment version
        with self._lock:
            state.version += 1
            version = state.version

        # 6. Assemble profile
        pos_c  = analysis.concentration.position
        sec_c  = analysis.concentration.sector.sector
        corr_a = analysis.correlation.analysis
        ovlp   = analysis.correlation.overlap
        fac    = analysis.concentration.factor

        profile = DiversificationProfile(
            portfolio_id         = portfolio_id,
            plan_id              = plan_id,
            allocation_plan_id   = str(getattr(plan, "allocation_plan_id", "")),
            blueprint_id         = str(getattr(plan, "blueprint_id", "")),
            version              = version,
            total_capital        = tc,
            currency             = currency,
            n_positions          = analysis.n_positions,
            effective_n          = analysis.effective_n,
            hhi                  = analysis.hhi,
            entropy              = analysis.entropy,
            entropy_ratio        = analysis.entropy_ratio,
            top1_weight          = pos_c.top1_weight,
            top5_weight          = pos_c.top5_weight,
            top10_weight         = pos_c.top10_weight,
            top1_symbol          = pos_c.top1_symbol,
            n_sectors            = analysis.n_sectors,
            top_sector_weight    = analysis.top_sector_weight,
            top_sector_name      = sec_c.top1_bucket,
            sector_hhi           = analysis.sector_hhi,
            sector_entropy_ratio = analysis.sector_entropy_ratio,
            avg_correlation      = corr_a.avg_correlation,
            diversification_ratio= analysis.diversification_ratio,
            portfolio_risk_proxy = corr_a.portfolio_risk,
            n_high_corr_pairs    = corr_a.n_high_pairs,
            sector_overlap       = ovlp.sector_overlap,
            thematic_overlap     = ovlp.thematic_overlap,
            quality_tilt         = fac.quality_tilt,
            volatility_tilt      = fac.volatility_tilt,
            momentum_tilt        = fac.momentum_tilt,
            overall_score        = score.overall,
            position_score       = score.position,
            sector_score         = score.sector,
            correlation_score    = score.correlation,
            concentration_score  = score.concentration,
            resilience_score     = score.resilience,
            grade                = score.grade,
            is_acceptable        = score.is_acceptable,
            has_concentration_risk = analysis.has_concentration_risk,
            has_correlation_risk   = analysis.has_correlation_risk,
            n_alerts             = len(alerts),
            n_critical_alerts    = n_crit,
            concentration_level  = pos_c.concentration_level,
        )

        # 7. Record to history
        state.history.record(profile)

        self._emit("evaluation_completed", {
            "portfolio_id":  portfolio_id,
            "profile_id":    profile.profile_id,
            "overall_score": profile.overall_score,
            "grade":         profile.grade.value,
            "n_alerts":      len(alerts),
        })
        return profile

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------

    def current_profile(self, portfolio_id: str) -> Optional[DiversificationProfile]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.latest() if state else None

    def history(self, portfolio_id: str, n: int = 10) -> List[DiversificationProfile]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.recent(n) if state else []

    def best_profile(self, portfolio_id: str) -> Optional[DiversificationProfile]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.best() if state else None

    def quality_score(self, portfolio_id: str) -> Optional[DiversificationScore]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.score_history.latest() if state else None

    def monitor_portfolio(
        self,
        portfolio_id: str,
        plan:         Any,
        *,
        auto_register:bool = True,
    ) -> MonitoringReport:
        """Evaluate + monitor in one call."""
        if auto_register:
            self.register_portfolio(portfolio_id)
        profile = self.evaluate(portfolio_id, plan, auto_register=False)
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        analysis = self._analyzer.analyze(
            positions_from_plan(plan), portfolio_id, str(getattr(plan, "plan_id", ""))
        )
        hist = state.history if state else None
        return self._monitor.monitor(analysis, hist, portfolio_id)

    def trends(
        self,
        portfolio_id: str,
        metrics:      Optional[List[str]] = None,
    ) -> TrendsReport:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        if state is None:
            return TrendsReport(portfolio_id=portfolio_id)
        key_metrics = metrics or [
            "overall_score", "hhi", "entropy_ratio",
            "avg_correlation", "effective_n", "top_sector_weight",
        ]
        series = {m: state.history.metric_series(m) for m in key_metrics}
        return self._trends.analyze(series, portfolio_id)

    def metrics(self, portfolio_id: str) -> Optional[DiversificationMetrics]:
        """Compute metrics from the latest profile."""
        profile = self.current_profile(portfolio_id)
        if profile is None:
            return None
        score = self.quality_score(portfolio_id)
        # Reconstruct a minimal analysis-like object from the profile for metrics
        # We use a lightweight wrapper since the full analysis is not stored
        return _metrics_from_profile(profile, score)

    def statistics_snapshot(self) -> DiversificationStatisticsSnapshot:
        return self._stats.snapshot()

    def health(self) -> DiversificationHealthReport:
        return self._health.check(active_portfolios=self.portfolio_count())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_profile(self, portfolio_id: str, reason: str = "") -> DiversificationProfile:
        self._emit("evaluation_failed", {"portfolio_id": portfolio_id, "reason": reason})
        return DiversificationProfile(
            portfolio_id  = portfolio_id,
            is_acceptable = False,
            grade         = DiversificationGrade.F,
        )

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        if self._callback:
            try:
                self._callback(event, data)
            except Exception:  # pylint: disable=broad-except
                pass


# ---------------------------------------------------------------------------
# Lightweight metrics from a stored profile
# ---------------------------------------------------------------------------

def _metrics_from_profile(
    profile: DiversificationProfile,
    score:   Optional[DiversificationScore],
) -> DiversificationMetrics:
    from iios.investment.portfolio.diversification.diversification_metrics import DiversificationMetrics
    return DiversificationMetrics(
        portfolio_id          = profile.portfolio_id,
        n_positions           = profile.n_positions,
        effective_n           = profile.effective_n,
        hhi                   = profile.hhi,
        entropy               = profile.entropy,
        entropy_ratio         = profile.entropy_ratio,
        top1_weight           = profile.top1_weight,
        top5_weight           = profile.top5_weight,
        top10_weight          = profile.top10_weight,
        n_sectors             = profile.n_sectors,
        sector_hhi            = profile.sector_hhi,
        sector_entropy_ratio  = profile.sector_entropy_ratio,
        top_sector_weight     = profile.top_sector_weight,
        avg_correlation       = profile.avg_correlation,
        diversification_ratio = profile.diversification_ratio,
        n_high_corr_pairs     = profile.n_high_corr_pairs,
        portfolio_risk_proxy  = profile.portfolio_risk_proxy,
        sector_overlap        = profile.sector_overlap,
        industry_overlap      = 0.0,
        quality_tilt          = profile.quality_tilt,
        volatility_tilt       = profile.volatility_tilt,
        momentum_tilt         = profile.momentum_tilt,
        overall_score         = profile.overall_score,
        grade                 = profile.grade.value,
        is_acceptable         = profile.is_acceptable,
    )
