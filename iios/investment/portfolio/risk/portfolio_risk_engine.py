"""iios/investment/portfolio/risk/portfolio_risk_engine.py

Institutional Portfolio Risk Engine — main orchestrator.

Responsibility: continuously evaluate, monitor, explain, forecast, and manage
portfolio risk. It consumes ONLY:
  - Portfolio Framework Core
  - Portfolio Construction Engine
  - Portfolio Allocation Engine
  - Portfolio Optimization Engine
  - Portfolio Diversification Engine
  - Decision/Market/Company/Strategy Intelligence Integration Engines

It does NOT optimize portfolios, rebalance them, or execute trades.
"""
from __future__ import annotations

import datetime
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from iios.investment.portfolio.risk.concentration_risk import (
    ConcentrationRiskResult, analyze_concentration_risk,
)
from iios.investment.portfolio.risk.credit_risk import (
    CreditRiskResult, analyze_credit_risk,
)
from iios.investment.portfolio.risk.currency_risk import (
    CurrencyRiskResult, analyze_currency_risk,
)
from iios.investment.portfolio.risk.drawdown_analysis import (
    DrawdownAnalysisResult, analyze_drawdown,
)
from iios.investment.portfolio.risk.interest_rate_risk import (
    InterestRateRiskResult, analyze_interest_rate_risk,
)
from iios.investment.portfolio.risk.liquidity_risk import (
    LiquidityRiskResult, analyze_liquidity_risk,
)
from iios.investment.portfolio.risk.market_risk import (
    MarketRiskResult, analyze_market_risk,
)
from iios.investment.portfolio.risk.portfolio_exposure import (
    PortfolioExposureAnalyzer, PortfolioExposureReport,
)
from iios.investment.portfolio.risk.portfolio_risk_history import PortfolioRiskHistory
from iios.investment.portfolio.risk.portfolio_risk_profile import PortfolioRiskProfile
from iios.investment.portfolio.risk.portfolio_risk_score import (
    RiskScore, RiskScoreCalculator, RiskScoreHistory,
)
from iios.investment.portfolio.risk.portfolio_risk_snapshot import RiskHistory
from iios.investment.portfolio.risk.portfolio_risk_statistics import (
    PortfolioRiskStatistics, RiskStatisticsSnapshot,
)
from iios.investment.portfolio.risk.risk_confidence import (
    RiskConfidenceReport, compute_risk_confidence,
)
from iios.investment.portfolio.risk.risk_health import RiskHealthMonitor, RiskHealthReport
from iios.investment.portfolio.risk.risk_quality import (
    RiskQualityAssessor, RiskQualityReport,
)
from iios.investment.portfolio.risk.risk_types import (
    RiskLevel, RiskPosition, positions_from_plan,
)
from iios.investment.portfolio.risk.stress_testing import StressTestEngine, StressTestReport
from iios.investment.portfolio.risk.tail_risk import TailRiskResult, analyze_tail_risk


@dataclass
class RiskIntegrationRefs:
    """References to upstream engine APIs consumed by the Risk Engine."""

    portfolio_framework:    Optional[Any] = None   # PortfolioFrameworkCore
    construction_engine:    Optional[Any] = None   # PortfolioConstructionEngine
    allocation_engine:      Optional[Any] = None   # PortfolioAllocationEngine
    optimization_engine:    Optional[Any] = None   # PortfolioOptimizationEngine
    diversification_engine: Optional[Any] = None   # PortfolioDiversificationEngine
    decision_engine:        Optional[Any] = None   # DecisionIntelligenceIntegration
    market_engine:          Optional[Any] = None   # MarketIntelligenceIntegration
    company_engine:         Optional[Any] = None   # CompanyIntelligenceIntegration
    strategy_engine:        Optional[Any] = None   # StrategyIntelligenceIntegration


@dataclass(frozen=True)
class MonitoringReport:
    """Lightweight monitoring report for a portfolio."""
    report_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str   = ""
    is_healthy:         bool  = True
    overall_risk_score: float = 0.0
    risk_level:         str   = "moderate"
    is_acceptable:      bool  = True
    n_alerts:           int   = 0
    n_critical_alerts:  int   = 0
    message:            str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":       self.portfolio_id,
            "is_healthy":         self.is_healthy,
            "overall_risk_score": round(self.overall_risk_score, 4),
            "risk_level":         self.risk_level,
            "is_acceptable":      self.is_acceptable,
            "n_alerts":           self.n_alerts,
        }


class PortfolioRiskEngine:
    """
    Institutional Portfolio Risk Engine — evaluates, monitors, and explains
    portfolio risk across all dimensions.

    Thread-safe. All evaluate() calls acquire a per-portfolio lock to prevent
    concurrent evaluation of the same portfolio.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        *,
        quality_assessor:   Optional[RiskQualityAssessor]   = None,
        score_calculator:   Optional[RiskScoreCalculator]    = None,
        domestic_currency:  str                              = "INR",
        domestic_country:   str                              = "IN",
        max_history:        int                              = 100,
        event_callback:     Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        self._quality_assessor   = quality_assessor  or RiskQualityAssessor()
        self._score_calculator   = score_calculator  or RiskScoreCalculator()
        self._domestic_currency  = domestic_currency
        self._domestic_country   = domestic_country
        self._max_history        = max_history
        self._event_callback     = event_callback

        # Sub-engines
        self._stress_engine      = StressTestEngine()
        self._exposure_analyzer  = PortfolioExposureAnalyzer(
            domestic_currency=domestic_currency,
            domestic_country=domestic_country,
        )

        # State
        self._lock           = threading.RLock()
        self._portfolio_locks: Dict[str, threading.RLock] = {}
        self._registered:    Dict[str, bool] = {}
        self._history        = PortfolioRiskHistory(max_per_portfolio=max_history)
        self._snapshots:     Dict[str, RiskHistory] = {}
        self._score_history: Dict[str, RiskScoreHistory] = {}
        self._stats          = PortfolioRiskStatistics()
        self._health         = RiskHealthMonitor()
        self._running        = False
        self._integrations   = RiskIntegrationRefs()

    # ── Lifecycle ────────────────────────────────────────────────────────────

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

    def configure_integrations(self, refs: RiskIntegrationRefs) -> None:
        with self._lock:
            self._integrations = refs

    # ── Portfolio Registration ────────────────────────────────────────────────

    def register_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            if portfolio_id not in self._registered:
                self._registered[portfolio_id]    = True
                self._portfolio_locks[portfolio_id] = threading.RLock()

    def deregister_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            self._registered.pop(portfolio_id, None)
            self._portfolio_locks.pop(portfolio_id, None)

    def is_registered(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._registered

    # ── Core Evaluation ──────────────────────────────────────────────────────

    def evaluate(
        self,
        portfolio_id: str,
        plan:         Any,            # OptimizationPlan | AllocationPlan | Any duck-typed
        *,
        auto_register:bool = True,
    ) -> PortfolioRiskProfile:
        """
        Full risk evaluation pipeline for one portfolio plan.

        Returns a PortfolioRiskProfile (immutable frozen dataclass).
        """
        if auto_register:
            self.register_portfolio(portfolio_id)

        plock = self._portfolio_locks.get(portfolio_id, threading.RLock())
        t_start = time.perf_counter()
        succeeded = False
        profile: Optional[PortfolioRiskProfile] = None

        try:
            with plock:
                positions = positions_from_plan(plan)
                plan_id   = getattr(plan, "plan_id", getattr(plan, "allocation_id", ""))
                profile   = self._run_pipeline(
                    positions, portfolio_id, plan_id, plan
                )
                self._history.record(profile)
                self._get_snapshot_store(portfolio_id).record(profile)
                succeeded = True
                return profile
        except Exception:
            raise
        finally:
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            self._health.record_run(succeeded=succeeded, duration_ms=elapsed_ms)
            if profile is not None:
                self._stats.record(
                    portfolio_id  = portfolio_id,
                    succeeded     = succeeded,
                    duration_ms   = elapsed_ms,
                    overall_score = profile.overall_risk_score,
                    is_acceptable = profile.is_acceptable,
                    n_alerts      = profile.n_alerts,
                )
            if self._event_callback and profile is not None:
                try:
                    self._event_callback("risk_evaluated", profile)
                except Exception:
                    pass

    def _run_pipeline(
        self,
        positions:    List[RiskPosition],
        portfolio_id: str,
        plan_id:      str,
        plan:         Any,
    ) -> PortfolioRiskProfile:
        # 1. Market risk
        mr  = analyze_market_risk(positions, portfolio_id)
        # 2. Credit risk
        cr  = analyze_credit_risk(positions, portfolio_id)
        # 3. Liquidity risk
        lr  = analyze_liquidity_risk(positions, portfolio_id)
        # 4. Currency risk
        ccy = analyze_currency_risk(positions, self._domestic_currency, portfolio_id)
        # 5. Interest rate risk
        ir  = analyze_interest_rate_risk(positions, portfolio_id)
        # 6. Concentration risk
        cnc = analyze_concentration_risk(positions, portfolio_id)
        # 7. Tail risk
        tr  = analyze_tail_risk(positions, portfolio_id)
        # 8. Portfolio exposure
        exp = self._exposure_analyzer.analyze(positions, portfolio_id, plan_id)
        # 9. Drawdown
        dd  = analyze_drawdown(positions, portfolio_id)
        # 10. Stress tests
        st  = self._stress_engine.run_all(positions, portfolio_id=portfolio_id)
        # 11. Risk score
        score = self._compute_score(mr, cr, lr, ccy, ir, cnc, tr, portfolio_id)
        # 12. Quality
        quality = self._quality_assessor.assess(score)
        # 13. Confidence
        confidence = compute_risk_confidence(positions, True, portfolio_id)

        # Collect all warnings
        all_warnings = (
            mr.warnings + cr.warnings + lr.warnings
            + ccy.warnings + ir.warnings + cnc.warnings + tr.warnings
            + dd.warnings
        )
        n_critical = sum(
            1 for w in all_warnings
            if any(kw in w.lower() for kw in ("critical", "extreme", "black swan", "severe"))
        )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return PortfolioRiskProfile(
            portfolio_id          = portfolio_id,
            plan_id               = plan_id,
            created_at            = now,
            n_positions           = len(positions),

            # Market
            portfolio_vol_annual  = mr.portfolio_vol_annual,
            portfolio_vol_daily   = mr.portfolio_vol_daily,
            var_95_1d             = mr.var_95_1d,
            var_99_1d             = mr.var_99_1d,
            var_95_10d            = mr.var_95_10d,
            cvar_95_1d            = mr.cvar_95_1d,
            beta_proxy            = mr.beta_proxy,
            diversification_benefit = mr.diversification_benefit,
            market_risk_level     = mr.risk_level.value,

            # Credit
            avg_credit_quality    = cr.avg_credit_quality,
            default_prob_proxy    = cr.default_prob_proxy,
            junk_weight           = cr.junk_weight,
            credit_risk_level     = cr.risk_level.value,

            # Liquidity
            avg_liquidity_score   = lr.avg_liquidity_score,
            illiquid_weight       = lr.illiquid_weight,
            lvar_95_1d            = lr.lvar_95_1d,
            estimated_days_to_liq = lr.estimated_days_to_liquidate,
            liquidity_risk_level  = lr.risk_level.value,

            # Currency
            foreign_weight        = ccy.foreign_weight,
            n_currencies          = ccy.n_currencies,
            fx_shock_impact_15pct = ccy.fx_shock_impact_15pct,
            currency_risk_level   = ccy.risk_level.value,

            # Interest rate
            portfolio_duration_proxy = ir.portfolio_duration_proxy,
            impact_100bps         = ir.impact_100bps,
            ir_risk_level         = ir.risk_level.value,

            # Concentration
            position_hhi          = cnc.position_hhi,
            sector_hhi            = cnc.sector_hhi,
            top1_weight           = cnc.top1_weight,
            top_sector            = cnc.top_sector,
            top_sector_weight     = cnc.top_sector_weight,
            has_high_concentration= cnc.has_high_concentration,
            concentration_risk_level = cnc.risk_level.value,

            # Tail
            cvar_99_1d            = tr.cvar_99_1d,
            black_swan_1pct_loss  = tr.black_swan_1pct_loss,
            skewness_proxy        = tr.skewness_proxy,
            tail_risk_level       = tr.risk_level.value,

            # Drawdown
            max_drawdown_proxy    = dd.max_drawdown_proxy,
            expected_recovery_days= dd.expected_recovery_days,
            drawdown_level        = dd.drawdown_level.value,

            # Stress
            stress_worst_scenario = st.worst_scenario,
            stress_worst_loss     = st.worst_loss,
            stress_resilience_score= st.resilience_score,

            # Composite
            overall_risk_score    = score.overall,
            risk_grade            = score.grade.value,
            risk_level            = score.risk_level.value,
            is_acceptable         = score.is_acceptable,

            # Quality & Confidence
            quality_score         = quality.quality_score,
            confidence_score      = confidence.confidence_score,
            confidence_level      = confidence.confidence_level,

            n_alerts              = len(all_warnings),
            n_critical_alerts     = n_critical,
            all_warnings          = all_warnings,
        )

    def _compute_score(
        self,
        mr:  MarketRiskResult,
        cr:  CreditRiskResult,
        lr:  LiquidityRiskResult,
        ccy: CurrencyRiskResult,
        ir:  InterestRateRiskResult,
        cnc: ConcentrationRiskResult,
        tr:  TailRiskResult,
        portfolio_id: str,
    ) -> RiskScore:
        def _to_score(level: RiskLevel) -> float:
            mapping = {
                RiskLevel.VERY_LOW:  0.10,
                RiskLevel.LOW:       0.25,
                RiskLevel.MODERATE:  0.45,
                RiskLevel.HIGH:      0.65,
                RiskLevel.VERY_HIGH: 0.80,
                RiskLevel.CRITICAL:  0.95,
            }
            return mapping.get(level, 0.45)

        sh = self._score_history.get(portfolio_id)
        prev = sh.latest().overall if sh and sh.latest() else None

        score = self._score_calculator.calculate(
            market_score        = _to_score(mr.risk_level),
            credit_score        = _to_score(cr.risk_level),
            liquidity_score     = _to_score(lr.risk_level),
            concentration_score = cnc.concentration_score,
            tail_score          = _to_score(tr.risk_level),
            currency_score      = _to_score(ccy.risk_level),
            interest_rate_score = _to_score(ir.risk_level),
            portfolio_id        = portfolio_id,
            previous_overall    = prev,
        )

        if portfolio_id not in self._score_history:
            self._score_history[portfolio_id] = RiskScoreHistory(portfolio_id)
        self._score_history[portfolio_id].record(score)

        return score

    # ── Queries ──────────────────────────────────────────────────────────────

    def current_profile(self, portfolio_id: str) -> Optional[PortfolioRiskProfile]:
        return self._history.latest(portfolio_id)

    def history(
        self, portfolio_id: str, n: Optional[int] = None
    ) -> List[PortfolioRiskProfile]:
        return self._history.all(portfolio_id, n)

    def best_profile(self, portfolio_id: str) -> Optional[PortfolioRiskProfile]:
        return self._history.best(portfolio_id)

    def quality_score(self, portfolio_id: str) -> Optional[float]:
        p = self.current_profile(portfolio_id)
        return p.quality_score if p else None

    def statistics_snapshot(self) -> RiskStatisticsSnapshot:
        return self._stats.snapshot()

    def health(self) -> RiskHealthReport:
        return self._health.check(active_portfolios=len(self._registered))

    def monitor_portfolio(
        self, portfolio_id: str, plan: Any
    ) -> MonitoringReport:
        """Lightweight monitoring wrapper — calls evaluate() under the hood."""
        try:
            profile = self.evaluate(portfolio_id, plan, auto_register=True)
            return MonitoringReport(
                portfolio_id       = portfolio_id,
                is_healthy         = profile.is_acceptable,
                overall_risk_score = profile.overall_risk_score,
                risk_level         = profile.risk_level,
                is_acceptable      = profile.is_acceptable,
                n_alerts           = profile.n_alerts,
                n_critical_alerts  = profile.n_critical_alerts,
                message            = (
                    "RISK ACCEPTABLE" if profile.is_acceptable
                    else f"RISK ELEVATED: {profile.risk_level} (score={profile.overall_risk_score:.2f})"
                ),
            )
        except Exception as exc:
            return MonitoringReport(
                portfolio_id = portfolio_id,
                is_healthy   = False,
                message      = f"Risk evaluation failed: {exc}",
            )

    # ── Internals ────────────────────────────────────────────────────────────

    def _get_snapshot_store(self, portfolio_id: str) -> RiskHistory:
        if portfolio_id not in self._snapshots:
            self._snapshots[portfolio_id] = RiskHistory(portfolio_id)
        return self._snapshots[portfolio_id]
