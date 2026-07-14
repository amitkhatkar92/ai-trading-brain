"""iios/investment/portfolio/optimization/portfolio_optimization_engine.py

PortfolioOptimizationEngine — main orchestrator for the Institutional Portfolio
Optimization Engine (IPOE).

Responsibility:
    Receive a validated AllocationPlan and optimize its position weights using
    configurable algorithms, objective functions, and constraint solvers.

Does NOT:
  • Construct portfolios
  • Generate investment recommendations
  • Execute trades
  • Rebalance portfolios
  • Independently analyze markets, companies, or strategies
"""
from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.constraint_solver import (
    ConstraintSolution,
    ConstraintSolver,
)
from iios.investment.portfolio.optimization.constraint_validator import (
    ConstraintValidationReport,
    ConstraintValidator,
)
from iios.investment.portfolio.optimization.objective_engine import (
    ObjectiveEvaluation,
    ObjectiveEvaluator,
)
from iios.investment.portfolio.optimization.optimization_constraints import (
    OptimizationConstraintSet,
    default_constraint_set,
)
from iios.investment.portfolio.optimization.optimization_engine import AssetProxy
from iios.investment.portfolio.optimization.optimization_health import (
    OptimizationHealthMonitor,
    OptimizationHealthReport,
)
from iios.investment.portfolio.optimization.optimization_snapshot import (
    OptimizationHistory,
    OptimizationRecord,
    OptimizationSnapshot,
    OptimizedHolding,
)
from iios.investment.portfolio.optimization.optimization_metrics import (
    OptimizationMetrics,
    compute_optimization_metrics,
)
from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationPlan,
    OptimizationRequest,
    OptimizationResult,
    OptimizedPosition,
)
from iios.investment.portfolio.optimization.optimization_policy import (
    BALANCED_OPTIMIZATION_POLICY,
    OptimizationPolicy,
)
from iios.investment.portfolio.optimization.optimization_quality import (
    OptimizationQualityAssessor,
    OptimizationQualityReport,
)
from iios.investment.portfolio.optimization.optimization_readiness import (
    OptimizationReadinessAssessment,
    OptimizationReadinessValidator,
)
from iios.investment.portfolio.optimization.optimization_registry import (
    OptimizationRegistry,
    get_default_registry,
)
from iios.investment.portfolio.optimization.optimization_score import (
    OptimizationScore,
    OptimizationScoreCalculator,
    OptimizationScoreHistory,
)
from iios.investment.portfolio.optimization.optimization_statistics import (
    OptimizationRunMetric,
    OptimizationStatistics,
    OptimizationStatisticsSnapshot,
)
from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    ObjectiveType,
    OptimizationMethod,
    OptimizationQualityGrade,
    OptimizationRunStatus,
    WeightChangeStatus,
)
from iios.investment.portfolio.optimization.optimization_validator import (
    OptimizationValidationReport,
    OptimizationValidator,
)


# ---------------------------------------------------------------------------
# Integration references
# ---------------------------------------------------------------------------

@dataclass
class OptimizationIntegrationRefs:
    """
    Soft references to upstream/peer intelligence layers.
    The engine never requires them — all fields are optional.
    """

    decision_intelligence:   Optional[Any] = None
    market_intelligence:     Optional[Any] = None
    company_intelligence:    Optional[Any] = None
    strategy_intelligence:   Optional[Any] = None
    construction_engine:     Optional[Any] = None
    allocation_engine:       Optional[Any] = None
    historical_framework:    Optional[Any] = None
    knowledge_layer:         Optional[Any] = None
    audit_framework:         Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: (v is not None) for k, v in self.__dict__.items()}


# ---------------------------------------------------------------------------
# Per-portfolio state
# ---------------------------------------------------------------------------

@dataclass
class _PortfolioOptimizationState:
    portfolio_id:  str
    history:       OptimizationHistory
    score_history: OptimizationScoreHistory
    version:       int  = 0
    registered_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PortfolioOptimizationEngine:
    """
    Institutional Portfolio Optimization Engine.

    Thread-safe.  One instance serves multiple portfolios.

    Usage
    -----
    engine = PortfolioOptimizationEngine()
    engine.start()
    result = engine.optimize(portfolio_id, allocation_plan, request)
    engine.stop()
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        *,
        policy:               Optional[OptimizationPolicy]        = None,
        registry:             Optional[OptimizationRegistry]       = None,
        constraint_solver:    Optional[ConstraintSolver]           = None,
        constraint_validator: Optional[ConstraintValidator]        = None,
        validation_validator: Optional[OptimizationValidator]      = None,
        quality_assessor:     Optional[OptimizationQualityAssessor]= None,
        score_calculator:     Optional[OptimizationScoreCalculator]= None,
        max_history:          int                                   = 200,
        event_callback:       Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._policy    = policy or BALANCED_OPTIMIZATION_POLICY
        self._registry  = registry or get_default_registry()
        self._c_solver  = constraint_solver or ConstraintSolver()
        self._c_valid   = constraint_validator or ConstraintValidator()
        self._validator = validation_validator or OptimizationValidator()
        self._quality   = quality_assessor or OptimizationQualityAssessor()
        self._scorer    = score_calculator or OptimizationScoreCalculator()
        self._obj_eval  = ObjectiveEvaluator()
        self._readiness = OptimizationReadinessValidator()
        self._health    = OptimizationHealthMonitor()
        self._stats     = OptimizationStatistics()
        self._max_history = max_history
        self._callback  = event_callback

        self._portfolios: Dict[str, _PortfolioOptimizationState] = {}
        self._lock       = threading.RLock()
        self._running    = False
        self._started_at: Optional[float] = None
        self._integrations: Optional[OptimizationIntegrationRefs] = None

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

    def configure_integrations(self, refs: OptimizationIntegrationRefs) -> None:
        self._integrations = refs

    # ------------------------------------------------------------------
    # Portfolio registration
    # ------------------------------------------------------------------

    def register_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            if portfolio_id not in self._portfolios:
                self._portfolios[portfolio_id] = _PortfolioOptimizationState(
                    portfolio_id  = portfolio_id,
                    history       = OptimizationHistory(portfolio_id, max_snapshots=self._max_history),
                    score_history = OptimizationScoreHistory(portfolio_id),
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

    def optimize(
        self,
        portfolio_id:    str,
        allocation_plan: Any,           # AllocationPlan (duck-typed)
        request:         OptimizationRequest,
        *,
        auto_register:   bool = True,
        constraints:     Optional[OptimizationConstraintSet] = None,
    ) -> OptimizationResult:
        """
        Optimize the weights of *allocation_plan* for *portfolio_id*.

        Parameters
        ----------
        allocation_plan:
            An AllocationPlan from the Portfolio Allocation Engine.
            Must expose: .allocations (iterable of PositionAllocation-like objects),
            .total_capital, .portfolio_id, .plan_id, .blueprint_id, .version.
        request:
            OptimizationRequest controlling method, constraints, convergence.
        constraints:
            Optional explicit constraint set. If None, one is built from request.
        """
        t0 = time.time()

        if auto_register:
            self.register_portfolio(portfolio_id)

        if not self.is_running:
            return self._fail(request, portfolio_id, "Engine is not running", t0)

        with self._lock:
            state = self._portfolios.get(portfolio_id)

        if state is None:
            return self._fail(request, portfolio_id, "Portfolio not registered", t0)

        try:
            result = self._run_optimization(
                portfolio_id, allocation_plan, request, state, t0, constraints
            )
        except Exception as exc:  # pylint: disable=broad-except
            result = self._fail(request, portfolio_id, f"Unexpected error: {exc}", t0)

        # Record stats + health
        dur = (time.time() - t0) * 1000
        self._stats.record(OptimizationRunMetric(
            portfolio_id          = portfolio_id,
            succeeded             = result.succeeded,
            positions_optimized   = len(result.plan.positions) if result.plan else 0,
            total_capital         = request.total_capital,
            utilisation_rate      = result.plan.utilisation_rate if result.plan else 0.0,
            objective_improvement = result.plan.objective_improvement if result.plan else 0.0,
            sharpe_proxy          = result.plan.sharpe_proxy if result.plan else 0.0,
            quality_score         = result.quality_summary.get("overall_score", 0.0),
            total_turnover        = result.plan.total_turnover if result.plan else 0.0,
            duration_ms           = dur,
        ))
        self._health.record_run(succeeded=result.succeeded, duration_ms=dur)
        return result

    # ------------------------------------------------------------------

    def _run_optimization(
        self,
        portfolio_id:    str,
        allocation_plan: Any,
        request:         OptimizationRequest,
        state:           _PortfolioOptimizationState,
        t0:              float,
        explicit_cs:     Optional[OptimizationConstraintSet],
    ) -> OptimizationResult:
        warnings: List[str] = []

        allocations = list(getattr(allocation_plan, "allocations", []))
        if not allocations:
            return self._fail(request, portfolio_id, "AllocationPlan has no positions", t0)

        total_capital = request.total_capital or float(getattr(allocation_plan, "total_capital", 0.0))
        if total_capital <= 0:
            return self._fail(request, portfolio_id, "total_capital must be > 0", t0)

        investable = total_capital * (1.0 - request.cash_reserve_pct)

        # -- 1. Build AssetProxy list ------------------------------------
        assets: List[AssetProxy] = _build_asset_proxies(allocations, investable)

        # Filter excluded / allowed symbols
        if request.symbols_excluded:
            assets = [a for a in assets if a.symbol not in request.symbols_excluded]
        if request.symbols_allowed:
            assets = [a for a in assets if a.symbol in request.symbols_allowed]

        if not assets:
            return self._fail(request, portfolio_id, "No assets remain after symbol filters", t0)

        # -- 2. Evaluate prior objective ---------------------------------
        prior_weights = {a.symbol: max(0.0, a.prior_weight) for a in assets}
        # Renormalize prior
        prior_sum = sum(prior_weights.values())
        if prior_sum > 0:
            prior_weights = {s: w / prior_sum for s, w in prior_weights.items()}

        obj_type = request.objective.primary
        prior_eval = self._obj_eval.evaluate(prior_weights, assets, obj_type,
                                              request.risk_aversion)

        # -- 3. Run optimization algorithm -------------------------------
        algo = self._registry.get(request.method)
        raw_weights, conv_result = algo.optimize(
            assets,
            min_weight    = request.min_weight,
            max_weight    = request.max_weight,
            risk_aversion = request.risk_aversion,
            max_iter      = request.max_iterations,
            tol           = request.convergence_tol,
            lr            = request.learning_rate,
        )

        # -- 4. Build / apply constraint set -----------------------------
        constraint_set = explicit_cs or default_constraint_set(
            portfolio_id = portfolio_id,
            min_weight   = request.min_weight,
            max_weight   = request.max_weight,
            max_sector   = request.max_sector_weight,
            max_leverage = request.max_gross_leverage,
        )

        solution: ConstraintSolution = self._c_solver.solve(
            weights             = raw_weights,
            assets              = assets,
            constraints         = constraint_set,
            request_min_weight  = request.min_weight,
            request_max_weight  = request.max_weight,
        )
        opt_weights = solution.weights
        warnings.extend(solution.warnings)

        # -- 5. Evaluate optimized objective ----------------------------
        opt_eval = self._obj_eval.evaluate(opt_weights, assets, obj_type, request.risk_aversion)
        obj_improvement = opt_eval.value - prior_eval.value

        # -- 6. Build OptimizedPosition list ----------------------------
        with self._lock:
            state.version += 1
            version = state.version

        positions = _build_positions(
            assets, opt_weights, prior_weights, total_capital, investable,
            opt_eval, prior_eval,
            allocation_plan_id = getattr(allocation_plan, "plan_id", ""),
        )

        # -- 7. Exposure summaries (optimized weights) ------------------
        sector_w:    Dict[str, float] = {}
        ac_w:        Dict[str, float] = {}
        industry_w:  Dict[str, float] = {}
        for p in positions:
            sector_w[p.sector]      = sector_w.get(p.sector, 0.0) + p.optimized_weight
            ac_w[p.asset_class]     = ac_w.get(p.asset_class, 0.0) + p.optimized_weight
            industry_w[p.industry]  = industry_w.get(p.industry, 0.0) + p.optimized_weight

        # -- 8. Weight change status ------------------------------------
        max_delta  = max((abs(p.weight_change) for p in positions), default=0.0)
        turnover   = sum(abs(p.weight_change) for p in positions)
        wc_status  = _weight_change_status(max_delta)

        # -- 9. Capital summary -----------------------------------------
        opt_invested = sum(p.optimized_capital for p in positions)
        cash_cap     = max(0.0, total_capital - opt_invested)
        utilisation  = opt_invested / total_capital if total_capital > 0 else 0.0

        # -- 10. Assemble plan ------------------------------------------
        plan = OptimizationPlan(
            portfolio_id            = portfolio_id,
            allocation_plan_id      = getattr(allocation_plan, "plan_id", ""),
            blueprint_id            = getattr(allocation_plan, "blueprint_id", ""),
            request_id              = request.request_id,
            version                 = version,
            method                  = request.method,
            objective_type          = obj_type,
            currency                = request.currency,
            total_capital           = total_capital,
            investable_capital      = investable,
            optimized_invested      = round(opt_invested, 2),
            cash_capital            = round(cash_cap, 2),
            utilisation_rate        = round(utilisation, 6),
            positions               = positions,
            convergence             = conv_result.status,
            iterations              = conv_result.iterations,
            final_gradient_norm     = conv_result.final_gradient_norm,
            converged               = conv_result.status in (
                ConvergenceStatus.CONVERGED, ConvergenceStatus.ANALYTICAL, ConvergenceStatus.TRIVIAL
            ),
            prior_objective_value   = prior_eval.value,
            optimized_objective_value = opt_eval.value,
            objective_improvement   = obj_improvement,
            weight_change_status    = wc_status,
            max_weight_change       = max_delta,
            total_turnover          = turnover,
            sector_weights          = sector_w,
            asset_class_weights     = ac_w,
            industry_weights        = industry_w,
            expected_return         = opt_eval.expected_return,
            portfolio_risk          = opt_eval.portfolio_risk,
            sharpe_proxy            = opt_eval.sharpe_proxy,
            diversification_ratio   = opt_eval.diversification_ratio,
            hhi                     = sum(p.optimized_weight ** 2 for p in positions),
        )

        # -- 11. Validate -----------------------------------------------
        val_report: OptimizationValidationReport = self._validator.validate(plan)

        # -- 12. Constraint validation ----------------------------------
        c_report: ConstraintValidationReport = self._c_valid.validate(plan, constraint_set)

        # -- 13. Quality ------------------------------------------------
        q_report: OptimizationQualityReport = self._quality.assess(plan, val_report, c_report)

        # -- 14. Score --------------------------------------------------
        prev_score = state.score_history.latest()
        score: OptimizationScore = self._scorer.calculate(q_report, prev_score)
        state.score_history.record(score)

        # -- 15. Readiness ----------------------------------------------
        readiness: OptimizationReadinessAssessment = self._readiness.validate(
            plan, val_report, c_report
        )

        # -- 16. Snapshot + history ------------------------------------
        snapshot = OptimizationSnapshot(
            portfolio_id            = portfolio_id,
            plan_id                 = plan.plan_id,
            allocation_plan_id      = plan.allocation_plan_id,
            blueprint_id            = plan.blueprint_id,
            plan_version            = plan.version,
            total_capital           = total_capital,
            optimized_invested      = plan.optimized_invested,
            cash_capital            = plan.cash_capital,
            utilisation_rate        = utilisation,
            currency                = request.currency,
            holdings                = tuple(
                OptimizedHolding(
                    symbol           = p.symbol,
                    prior_weight     = p.prior_weight,
                    optimized_weight = p.optimized_weight,
                    weight_change    = p.weight_change,
                    sector           = p.sector,
                    asset_class      = p.asset_class,
                )
                for p in positions
            ),
            method                  = request.method,
            prior_objective_value   = prior_eval.value,
            optimized_objective_value = opt_eval.value,
            objective_improvement   = obj_improvement,
            sharpe_proxy            = opt_eval.sharpe_proxy,
            diversification_ratio   = opt_eval.diversification_ratio,
            total_turnover          = turnover,
            quality_score           = score.overall,
            is_valid                = val_report.is_valid,
            is_ready                = readiness.is_ready,
        )
        state.history.record(snapshot, status="converged", quality_score=score.overall)

        # -- 17. Assemble result ----------------------------------------
        dur_ms   = (time.time() - t0) * 1000
        status   = (
            OptimizationRunStatus.CONVERGED
            if plan.converged and val_report.is_valid
            else OptimizationRunStatus.PARTIAL
        )

        result = OptimizationResult(
            request_id          = request.request_id,
            portfolio_id        = portfolio_id,
            allocation_plan_id  = plan.allocation_plan_id,
            status              = status,
            plan                = plan,
            validation_summary  = {
                "is_valid":  val_report.is_valid,
                "total":     val_report.total,
                "passed":    val_report.passed,
                "failures":  val_report.failures,
            },
            quality_summary     = {
                "overall_score": score.overall,
                "grade":         score.grade.value,
                "is_acceptable": score.is_acceptable,
                "gate_passed":   score.gate_passed,
            },
            constraint_summary  = {
                "total":       c_report.total,
                "satisfied":   c_report.satisfied,
                "violations":  c_report.violations,
                "is_feasible": c_report.is_feasible,
            },
            warnings    = tuple(warnings + list(readiness.warnings)),
            errors      = (),
            duration_ms = dur_ms,
        )

        self._emit("optimization_completed", {
            "portfolio_id":        portfolio_id,
            "plan_id":             plan.plan_id,
            "method":              request.method.value,
            "positions":           len(positions),
            "objective_improvement": obj_improvement,
            "quality_score":       score.overall,
            "is_ready":            readiness.is_ready,
        })
        return result

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------

    def current_optimization(self, portfolio_id: str) -> Optional[OptimizationSnapshot]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.latest() if state else None

    def optimization_history(self, portfolio_id: str, n: int = 10) -> List[OptimizationSnapshot]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.recent(n) if state else []

    def best_optimization(self, portfolio_id: str) -> Optional[OptimizationSnapshot]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.best() if state else None

    def quality_score(self, portfolio_id: str) -> Optional[OptimizationScore]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.score_history.latest() if state else None

    def statistics_snapshot(self) -> OptimizationStatisticsSnapshot:
        return self._stats.snapshot()

    def health(self) -> OptimizationHealthReport:
        return self._health.check(active_portfolios=self.portfolio_count())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fail(
        self,
        request:      OptimizationRequest,
        portfolio_id: str,
        reason:       str,
        t0:           float,
    ) -> OptimizationResult:
        dur_ms = (time.time() - t0) * 1000
        self._emit("optimization_failed", {"portfolio_id": portfolio_id, "reason": reason})
        return OptimizationResult(
            request_id         = request.request_id,
            portfolio_id       = portfolio_id,
            allocation_plan_id = request.allocation_plan_id,
            status             = OptimizationRunStatus.FAILED,
            plan               = None,
            errors             = (reason,),
            duration_ms        = dur_ms,
        )

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        if self._callback:
            try:
                self._callback(event, data)
            except Exception:  # pylint: disable=broad-except
                pass


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_asset_proxies(
    allocations: list,
    investable:  float,
) -> List[AssetProxy]:
    proxies: List[AssetProxy] = []
    # Compute weight sum for normalization
    total_alloc = sum(abs(float(getattr(a, "allocated_capital", 0.0))) for a in allocations)
    for a in allocations:
        cap  = abs(float(getattr(a, "allocated_capital", 0.0)))
        w    = cap / total_alloc if total_alloc > 0 else 0.0
        proxies.append(AssetProxy(
            symbol          = str(getattr(a, "symbol", "")),
            expected_return = float(getattr(a, "conviction", 0.5)),
            risk            = float(getattr(a, "risk_score", 0.5)),
            confidence      = float(getattr(a, "confidence", 0.5)),
            prior_weight    = w,
            sector          = str(getattr(a, "sector", "unknown")),
            industry        = str(getattr(a, "industry", "unknown")),
            asset_class     = str(getattr(getattr(a, "asset_class", None), "value",
                                         getattr(a, "asset_class", "equity"))),
        ))
    return proxies


def _build_positions(
    assets:            List[AssetProxy],
    opt_weights:       Dict[str, float],
    prior_weights:     Dict[str, float],
    total_capital:     float,
    investable:        float,
    opt_eval:          ObjectiveEvaluation,
    prior_eval:        ObjectiveEvaluation,
    allocation_plan_id:str = "",
) -> Tuple[OptimizedPosition, ...]:
    """Convert weight maps + asset proxies into OptimizedPosition tuple."""
    positions: List[OptimizedPosition] = []

    # Compute per-position objective contribution (Sharpe contribution proxy)
    total_contribution = max(1e-10, sum(
        abs(opt_weights.get(a.symbol, 0.0) * a.expected_return)
        for a in assets
    ))

    for rank, a in enumerate(
        sorted(assets, key=lambda x: opt_weights.get(x.symbol, 0.0), reverse=True),
        start=1,
    ):
        sym      = a.symbol
        opt_w    = opt_weights.get(sym, 0.0)
        prior_w  = prior_weights.get(sym, 0.0)
        delta_w  = opt_w - prior_w

        opt_cap  = round(opt_w * investable, 2)
        prior_cap= round(prior_w * investable, 2)

        risk_adj = a.expected_return / max(1e-8, a.risk)
        obj_contrib = (opt_w * a.expected_return) / total_contribution

        positions.append(OptimizedPosition(
            symbol                = sym,
            name                  = sym,
            prior_weight          = prior_w,
            optimized_weight      = opt_w,
            weight_change         = delta_w,
            prior_capital         = prior_cap,
            optimized_capital     = opt_cap,
            capital_change        = round(opt_cap - prior_cap, 2),
            expected_return_proxy = a.expected_return,
            risk_proxy            = a.risk,
            confidence_proxy      = a.confidence,
            sector                = a.sector,
            industry              = a.industry,
            asset_class           = a.asset_class,
            risk_adjusted_return  = risk_adj,
            objective_contribution= obj_contrib,
            allocation_plan_id    = allocation_plan_id,
            rank                  = rank,
        ))

    return tuple(positions)


def _weight_change_status(max_delta: float) -> WeightChangeStatus:
    if max_delta > 0.20:
        return WeightChangeStatus.LARGE
    if max_delta > 0.05:
        return WeightChangeStatus.MODERATE
    if max_delta > 0.01:
        return WeightChangeStatus.SMALL
    return WeightChangeStatus.MINIMAL
