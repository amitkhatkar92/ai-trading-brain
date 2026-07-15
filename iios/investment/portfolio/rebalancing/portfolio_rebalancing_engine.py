"""iios/investment/portfolio/rebalancing/portfolio_rebalancing_engine.py

Portfolio Rebalancing Engine — main orchestrator.

Responsibilities:
  - Consume drift analysis, policy evaluation, trade planning, validation, scoring
  - Generate deterministic, auditable RebalancePlan objects
  - Maintain per-portfolio history and run statistics

This engine does NOT execute trades.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift, compute_allocation_drift
from iios.investment.portfolio.rebalancing.cost_validator import CostValidator
from iios.investment.portfolio.rebalancing.drift_engine import DriftEngine, DriftReport
from iios.investment.portfolio.rebalancing.execution_estimator import ExecutionEstimate, ExecutionEstimator
from iios.investment.portfolio.rebalancing.policy_engine import PolicyEngine, PolicyEngineResult
from iios.investment.portfolio.rebalancing.policy_registry import PolicyRegistry
from iios.investment.portfolio.rebalancing.policy_validator import PolicyValidator
from iios.investment.portfolio.rebalancing.rebalance_forecast import (
    RebalanceForecast, forecast_rebalance_benefit,
)
from iios.investment.portfolio.rebalancing.rebalance_health import (
    RebalanceHealthMonitor, RebalanceHealthReport,
)
from iios.investment.portfolio.rebalancing.rebalance_history import PortfolioRebalanceHistory
from iios.investment.portfolio.rebalancing.rebalance_plan import RebalancePlan
from iios.investment.portfolio.rebalancing.rebalance_quality import (
    RebalanceQualityAssessor, RebalanceQualityReport,
)
from iios.investment.portfolio.rebalancing.rebalance_score import (
    RebalanceScore, RebalanceScoreCalculator,
)
from iios.investment.portfolio.rebalancing.rebalance_snapshot import RebalanceHistory, RebalanceRecord
from iios.investment.portfolio.rebalancing.rebalance_statistics import (
    PortfolioRebalanceStatistics, RebalanceRunMetric, RebalanceStatisticsSnapshot,
)
from iios.investment.portfolio.rebalancing.rebalance_validator import RebalanceValidator
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CurrentPosition, RebalanceGrade, RebalanceLevel, RebalanceStatus,
    RebalanceTrigger, TargetPosition, TradePriority,
    current_positions_from_any, target_positions_from_any, now_utc,
)
from iios.investment.portfolio.rebalancing.risk_drift import compute_risk_drift
from iios.investment.portfolio.rebalancing.trade_planner import TradePlan, TradePlanner


@dataclass
class RebalancingIntegrationRefs:
    """
    Optional references to upstream portfolio engines.
    The Rebalancing Engine NEVER invokes these directly — they are stored
    only for observability and metadata enrichment.
    """

    portfolio_framework:    Optional[Any] = None
    construction_engine:    Optional[Any] = None
    allocation_engine:      Optional[Any] = None
    optimization_engine:    Optional[Any] = None
    diversification_engine: Optional[Any] = None
    risk_engine:            Optional[Any] = None
    performance_engine:     Optional[Any] = None
    decision_engine:        Optional[Any] = None


class PortfolioRebalancingEngine:
    """
    Institutional Portfolio Rebalancing Engine.

    Determines WHEN, WHY, and HOW a portfolio should be rebalanced, subject to:
      - Institutional investment policies
      - Tax considerations (STCG / LTCG)
      - Transaction cost constraints
      - Liquidity constraints
      - Governance rules

    Does NOT execute trades.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        *,
        policy_registry:    Optional[PolicyRegistry]           = None,
        drift_engine:       Optional[DriftEngine]              = None,
        trade_planner:      Optional[TradePlanner]             = None,
        validator:          Optional[RebalanceValidator]        = None,
        score_calculator:   Optional[RebalanceScoreCalculator]  = None,
        quality_assessor:   Optional[RebalanceQualityAssessor]  = None,
        health_monitor:     Optional[RebalanceHealthMonitor]    = None,
        policy_engine:      Optional[PolicyEngine]              = None,
        max_history:        int = 50,
        event_callback:     Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        self._policy_reg  = policy_registry    or PolicyRegistry()
        self._drift_eng   = drift_engine       or DriftEngine()
        self._planner     = trade_planner      or TradePlanner()
        self._validator   = validator          or RebalanceValidator()
        self._scorer      = score_calculator   or RebalanceScoreCalculator()
        self._assessor    = quality_assessor   or RebalanceQualityAssessor()
        self._health      = health_monitor     or RebalanceHealthMonitor()
        self._pol_engine  = policy_engine      or PolicyEngine()
        self._max_history = max_history
        self._callback    = event_callback

        self._lock          = threading.RLock()
        self._running       = False
        self._portfolios:   Dict[str, RebalanceHistory]     = {}
        self._history       = PortfolioRebalanceHistory(max_per_portfolio=max_history)
        self._statistics    = PortfolioRebalanceStatistics()
        self._integrations: Optional[RebalancingIntegrationRefs] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Integration references (read-only metadata enrichment only)
    # ------------------------------------------------------------------ #

    def configure_integrations(self, refs: RebalancingIntegrationRefs) -> None:
        self._integrations = refs

    # ------------------------------------------------------------------ #
    # Portfolio registry
    # ------------------------------------------------------------------ #

    def register_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            if portfolio_id not in self._portfolios:
                self._portfolios[portfolio_id] = RebalanceHistory(portfolio_id)

    def deregister_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            self._portfolios.pop(portfolio_id, None)

    def is_registered(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._portfolios

    # ------------------------------------------------------------------ #
    # Core evaluation
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        portfolio_id:         str,
        current:              Any,   # List[CurrentPosition] or duck-typed
        target:               Any,   # List[TargetPosition]  or duck-typed
        *,
        policy_id:            Optional[str] = None,
        days_since_rebalance: float = 91.0,
        portfolio_value:      float = 10_000_000.0,
        portfolio_vol:        float = 0.15,
        net_cash_flow_pct:    float = 0.0,
        auto_register:        bool  = True,
    ) -> RebalancePlan:
        """
        Evaluate whether and how to rebalance a portfolio.

        Parameters
        ----------
        portfolio_id          : Unique portfolio identifier.
        current               : Current positions (List[CurrentPosition] or duck-typed list).
        target                : Target positions  (List[TargetPosition]  or duck-typed list).
        policy_id             : Policy to apply (uses registry default if None).
        days_since_rebalance  : Calendar days since the last rebalance.
        portfolio_value       : Total portfolio value in INR.
        portfolio_vol         : Current portfolio volatility (annualized fraction).
        net_cash_flow_pct     : Net cash flow as fraction of portfolio (+ = inflow).
        auto_register         : Register portfolio_id if not already registered.

        Returns
        -------
        RebalancePlan (frozen, deterministic, fully traceable)
        """
        t0 = time.monotonic()
        if auto_register:
            self.register_portfolio(portfolio_id)

        current_list = current_positions_from_any(current)
        target_list  = target_positions_from_any(target)

        policy = self._policy_reg.get_or_default(policy_id)

        succeeded = False
        plan: Optional[RebalancePlan] = None

        try:
            plan = self._build_plan(
                portfolio_id          = portfolio_id,
                current               = current_list,
                target                = target_list,
                policy                = policy,
                days_since_rebalance  = days_since_rebalance,
                portfolio_value       = portfolio_value,
                portfolio_vol         = portfolio_vol,
                net_cash_flow_pct     = net_cash_flow_pct,
            )
            succeeded = True
        except Exception:
            plan = RebalancePlan(
                portfolio_id = portfolio_id,
                policy_id    = policy.policy_id,
                policy_name  = policy.name,
                status       = RebalanceStatus.FAILED,
                is_valid     = False,
                primary_validation_failure = "Engine evaluation error",
            )
        finally:
            dur_ms = (time.monotonic() - t0) * 1000
            metric = RebalanceRunMetric(
                portfolio_id    = portfolio_id,
                succeeded       = succeeded,
                duration_ms     = dur_ms,
                n_trades        = plan.n_buys + plan.n_sells if plan else 0,
                rebalance_score = plan.rebalance_score if plan else 0.0,
                is_recommended  = plan.is_recommended if plan else False,
            )
            self._statistics.record(metric)
            self._health.record_run(succeeded, dur_ms, plan_created=succeeded)

            if plan and succeeded:
                record = self._build_record(plan)
                with self._lock:
                    if portfolio_id in self._portfolios:
                        self._portfolios[portfolio_id].add(record)
                self._history.add(portfolio_id, plan)

            if self._callback and plan:
                self._callback("plan_evaluated", plan)

        return plan  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Query APIs
    # ------------------------------------------------------------------ #

    def current_plan(self, portfolio_id: str) -> Optional[RebalancePlan]:
        return self._history.latest(portfolio_id)

    def plan_history(self, portfolio_id: str, n: int = 5) -> List[RebalancePlan]:
        return self._history.recent(portfolio_id, n)

    def best_plan(self, portfolio_id: str) -> Optional[RebalancePlan]:
        return self._history.best(portfolio_id)

    def drift_report(
        self,
        portfolio_id: str,
        current:      Any,
        target:       Any,
    ) -> DriftReport:
        """Run a drift-only analysis without full plan evaluation."""
        current_list = current_positions_from_any(current)
        target_list  = target_positions_from_any(target)
        return self._drift_eng.analyze(current_list, target_list, portfolio_id)

    def statistics_snapshot(self) -> RebalanceStatisticsSnapshot:
        return self._statistics.snapshot()

    def health(self) -> RebalanceHealthReport:
        n_active = len(self._portfolios)
        return self._health.check(n_active)

    # ------------------------------------------------------------------ #
    # Internal plan builder
    # ------------------------------------------------------------------ #

    def _build_plan(
        self,
        portfolio_id:         str,
        current:              List[CurrentPosition],
        target:               List[TargetPosition],
        policy:               Any,
        days_since_rebalance: float,
        portfolio_value:      float,
        portfolio_vol:        float,
        net_cash_flow_pct:    float,
    ) -> RebalancePlan:

        # 1. Drift analysis
        drift_report   = self._drift_eng.analyze(current, target, portfolio_id)
        alloc_drift    = drift_report.allocation
        risk_drift_obj = drift_report.risk
        exposure       = drift_report.exposure

        # 2. Policy evaluation
        pol_eval: PolicyEngineResult = self._pol_engine.evaluate(
            policy                = policy,
            allocation_drift      = alloc_drift,
            risk_drift            = risk_drift_obj,
            current_positions     = current,
            days_since_rebalance  = days_since_rebalance,
            portfolio_vol         = portfolio_vol,
            net_cash_flow_pct     = net_cash_flow_pct,
            estimated_cost        = 0.001,   # initial estimate (updated below)
            expected_benefit      = alloc_drift.total_abs_drift * 0.02,
        )

        # Determine trigger
        trigger = pol_eval.trigger if pol_eval.triggered else RebalanceTrigger.NONE
        status  = RebalanceStatus.RECOMMENDED if pol_eval.triggered else RebalanceStatus.NOT_REQUIRED

        # 3. Trade planning (always generate — score decides recommendation)
        trade_plan: TradePlan = self._planner.plan(
            current         = current,
            target          = target,
            policy          = policy,
            portfolio_id    = portfolio_id,
            portfolio_value = portfolio_value,
        )
        execution_est: ExecutionEstimate = trade_plan.execution_estimate

        # 4. Validation
        master_val = self._validator.validate(
            trade_plan    = trade_plan,
            policy        = policy,
            current       = current,
            target        = target,
            alloc_drift   = alloc_drift,
            execution_est = execution_est,
            portfolio_id  = portfolio_id,
        )

        # 5. Scoring
        score: RebalanceScore = self._scorer.calculate(
            alloc_drift    = alloc_drift,
            risk_drift     = risk_drift_obj,
            trade_plan     = trade_plan,
            execution_est  = execution_est,
            portfolio_id   = portfolio_id,
        )

        # 6. Quality
        quality: RebalanceQualityReport = self._assessor.assess(
            overall_score   = score.overall,
            drift_red_score = score.drift_red_score,
            cost_eff_score  = score.cost_eff_score,
            risk_imp_score  = score.risk_imp_score,
            div_score       = score.div_score,
            tax_eff_score   = score.tax_eff_score,
            total_cost_pct  = execution_est.total_cost_pct if execution_est else 0.0,
            total_turnover  = trade_plan.total_turnover,
            portfolio_id    = portfolio_id,
        )

        # 7. Forecast
        forecast: RebalanceForecast = forecast_rebalance_benefit(
            alloc_drift    = alloc_drift,
            trade_plan     = trade_plan,
            execution_est  = execution_est,
            portfolio_id   = portfolio_id,
        )

        # 8. Assemble final plan
        exec_est = execution_est
        is_recommended = (
            pol_eval.triggered
            and master_val.is_valid
            and quality.is_acceptable
        )

        plan = RebalancePlan(
            portfolio_id                = portfolio_id,
            policy_id                   = policy.policy_id,
            policy_name                 = policy.name,
            trigger                     = trigger,
            status                      = status if is_recommended else (
                RebalanceStatus.REJECTED if not master_val.is_valid else RebalanceStatus.NOT_REQUIRED
            ),

            n_positions_current         = alloc_drift.n_positions_current,
            n_positions_target          = alloc_drift.n_positions_target,

            n_buys                      = trade_plan.n_buys,
            n_sells                     = trade_plan.n_sells,
            total_turnover              = trade_plan.total_turnover,
            buy_turnover                = trade_plan.buy_turnover,
            sell_turnover               = trade_plan.sell_turnover,

            total_transaction_cost_pct  = exec_est.total_transaction_cost if exec_est else 0.0,
            total_market_impact_pct     = exec_est.total_market_impact if exec_est else 0.0,
            total_tax_cost_pct          = exec_est.total_tax_cost if exec_est else 0.0,
            total_cost_pct              = exec_est.total_cost_pct if exec_est else 0.0,

            pre_rebalance_drift         = alloc_drift.total_abs_drift,
            expected_post_drift         = forecast.expected_post_drift,
            expected_drift_reduction    = forecast.expected_drift_reduction_pct,

            expected_return_benefit     = forecast.expected_return_benefit,
            net_benefit_pct             = forecast.net_benefit_pct,
            months_to_breakeven         = forecast.months_to_breakeven,

            rebalance_score             = score.overall,
            performance_grade           = score.grade,
            performance_level           = score.level,
            is_recommended              = is_recommended,

            is_valid                    = master_val.is_valid,
            n_validation_warnings       = master_val.n_warnings,
            primary_validation_failure  = (
                master_val.blocking_issues[0] if master_val.blocking_issues else ""
            ),

            primary_drift_driver        = drift_report.primary_driver,
            most_drifted_position       = self._find_most_drifted(alloc_drift),
            most_drifted_sector         = getattr(exposure, "most_drifted_sector", ""),

            overall_priority            = trade_plan.overall_priority,
            forecast_confidence         = forecast.forecast_confidence,
        )

        return plan

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _find_most_drifted(alloc_drift: AllocationDrift) -> str:
        if not alloc_drift.position_drifts:
            return ""
        return max(alloc_drift.position_drifts, key=lambda pd: pd.abs_drift).symbol

    @staticmethod
    def _build_record(plan: RebalancePlan) -> RebalanceRecord:
        from iios.investment.portfolio.rebalancing.rebalance_snapshot import RebalanceRecord
        from iios.investment.portfolio.rebalancing.rebalancing_types import DriftLevel
        return RebalanceRecord(
            portfolio_id    = plan.portfolio_id,
            plan_id         = plan.plan_id,
            trigger         = plan.trigger,
            status          = plan.status,
            total_turnover  = plan.total_turnover,
            total_cost_pct  = plan.total_cost_pct,
            pre_drift       = plan.pre_rebalance_drift,
            post_drift      = plan.expected_post_drift,
            drift_reduction = plan.expected_drift_reduction,
            rebalance_score = plan.rebalance_score,
            grade           = plan.performance_grade,
            is_recommended  = plan.is_recommended,
            is_valid        = plan.is_valid,
            n_trades        = plan.n_buys + plan.n_sells,
            n_buys          = plan.n_buys,
            n_sells         = plan.n_sells,
            overall_priority= plan.overall_priority,
        )
