"""iios/investment/portfolio/allocation/portfolio_allocation_engine.py

PortfolioAllocationEngine — main orchestrator for the Institutional Portfolio
Allocation Engine.

Responsibility: allocate portfolio capital among validated holdings from a
PortfolioBlueprint while respecting institutional constraints.

Does NOT:
  • Optimise portfolios
  • Rebalance portfolios
  • Execute trades
  • Fetch market data
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_health import (
    AllocationHealthMonitor,
    AllocationHealthReport,
)
from iios.investment.portfolio.allocation.allocation_history import AllocationHistory
from iios.investment.portfolio.allocation.allocation_metrics import (
    AllocationMetrics,
    compute_allocation_metrics,
)
from iios.investment.portfolio.allocation.allocation_plan import (
    AllocationPlan,
    AllocationRequest,
    AllocationResult,
    CashAllocation,
    PositionAllocation,
)
from iios.investment.portfolio.allocation.allocation_policy import (
    BALANCED_POLICY,
    AllocationPolicy,
)
from iios.investment.portfolio.allocation.allocation_quality import (
    AllocationQualityAssessor,
    AllocationQualityReport,
)
from iios.investment.portfolio.allocation.allocation_readiness import (
    AllocationReadinessAssessment,
    AllocationReadinessValidator,
)
from iios.investment.portfolio.allocation.allocation_rules import AllocationRule
from iios.investment.portfolio.allocation.allocation_score import (
    AllocationScore,
    AllocationScoreCalculator,
    AllocationScoreHistory,
)
from iios.investment.portfolio.allocation.allocation_snapshot import (
    AllocationHolding,
    AllocationSnapshot,
)
from iios.investment.portfolio.allocation.allocation_statistics import (
    AllocationRunMetric,
    AllocationStatistics,
    AllocationStatisticsSnapshot,
)
from iios.investment.portfolio.allocation.allocation_types import (
    AllocationDirection,
    AllocationMethod,
    AllocationRunStatus,
    CapitalDistributionStatus,
)
from iios.investment.portfolio.allocation.allocation_validator import (
    AllocationValidationReport,
    AllocationValidator,
)
from iios.investment.portfolio.allocation.cash_manager import CashManager, CashPosition
from iios.investment.portfolio.allocation.exposure_limits import ExposureCheck, ExposureLimitChecker
from iios.investment.portfolio.allocation.position_allocator import PositionAllocator


# ---------------------------------------------------------------------------
# Integration reference container
# ---------------------------------------------------------------------------

@dataclass
class AllocationIntegrationRefs:
    """
    Soft references to upstream/peer intelligence layers.
    All fields are Optional[Any] — the engine never requires them and
    always falls back gracefully.
    """

    decision_intelligence:  Optional[Any] = None
    market_intelligence:    Optional[Any] = None
    company_intelligence:   Optional[Any] = None
    strategy_intelligence:  Optional[Any] = None
    construction_engine:    Optional[Any] = None
    historical_framework:   Optional[Any] = None
    knowledge_layer:        Optional[Any] = None
    audit_framework:        Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: (v is not None) for k, v in self.__dict__.items()}


# ---------------------------------------------------------------------------
# Per-portfolio state
# ---------------------------------------------------------------------------

@dataclass
class _PortfolioAllocationState:
    portfolio_id:  str
    history:       AllocationHistory
    score_history: AllocationScoreHistory
    version:       int = 0
    registered_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PortfolioAllocationEngine:
    """
    Institutional Portfolio Allocation Engine.

    Thread-safe.  A single instance can serve multiple portfolios.

    Usage
    -----
    engine = PortfolioAllocationEngine()
    engine.start()
    result = engine.allocate(portfolio_id, blueprint, request)
    engine.stop()
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        *,
        policy:          Optional[AllocationPolicy]       = None,
        position_allocator: Optional[PositionAllocator]   = None,
        allocation_validator: Optional[AllocationValidator] = None,
        quality_assessor: Optional[AllocationQualityAssessor] = None,
        score_calculator: Optional[AllocationScoreCalculator] = None,
        extra_rules:     Optional[List[AllocationRule]]   = None,
        max_history:     int                              = 200,
        event_callback:  Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._policy    = policy or BALANCED_POLICY
        self._allocator = position_allocator or PositionAllocator(rules=extra_rules)
        self._validator = allocation_validator or AllocationValidator()
        self._quality   = quality_assessor or AllocationQualityAssessor()
        self._scorer    = score_calculator or AllocationScoreCalculator()
        self._cash_mgr  = CashManager()
        self._exp_check = ExposureLimitChecker()
        self._readiness = AllocationReadinessValidator()
        self._health    = AllocationHealthMonitor()
        self._stats     = AllocationStatistics()
        self._max_history = max_history
        self._callback  = event_callback

        self._portfolios: Dict[str, _PortfolioAllocationState] = {}
        self._lock       = threading.RLock()
        self._running    = False
        self._started_at: Optional[float] = None
        self._integrations: Optional[AllocationIntegrationRefs] = None

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

    def configure_integrations(self, refs: AllocationIntegrationRefs) -> None:
        self._integrations = refs

    # ------------------------------------------------------------------
    # Portfolio registration
    # ------------------------------------------------------------------

    def register_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            if portfolio_id not in self._portfolios:
                self._portfolios[portfolio_id] = _PortfolioAllocationState(
                    portfolio_id  = portfolio_id,
                    history       = AllocationHistory(portfolio_id, max_snapshots=self._max_history),
                    score_history = AllocationScoreHistory(portfolio_id),
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

    def allocate(
        self,
        portfolio_id:  str,
        blueprint:     Any,            # PortfolioBlueprint
        request:       AllocationRequest,
        *,
        auto_register: bool = True,
    ) -> AllocationResult:
        """
        Allocate capital from *request.total_capital* across *blueprint* slots.

        Returns AllocationResult regardless of success/failure.
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
            result = self._run_allocation(portfolio_id, blueprint, request, state, t0)
        except Exception as exc:  # pylint: disable=broad-except
            result = self._fail(request, portfolio_id, f"Unexpected error: {exc}", t0)

        # -- Record stats / health ---------------------------------------
        dur = (time.time() - t0) * 1000
        self._stats.record(AllocationRunMetric(
            portfolio_id     = portfolio_id,
            succeeded        = result.succeeded,
            positions_out    = result.positions_allocated,
            total_capital    = request.total_capital,
            utilisation_rate = result.plan.utilisation_rate if result.plan else 0.0,
            quality_score    = result.quality_summary.get("overall_score", 0.0),
            duration_ms      = dur,
        ))
        self._health.record_run(succeeded=result.succeeded, duration_ms=dur)

        return result

    # ------------------------------------------------------------------

    def _run_allocation(
        self,
        portfolio_id: str,
        blueprint:    Any,
        request:      AllocationRequest,
        state:        _PortfolioAllocationState,
        t0:           float,
    ) -> AllocationResult:
        warnings: List[str] = []

        # ---- 1. Position allocation ----------------------------------
        allocations: Tuple[PositionAllocation, ...] = self._allocator.allocate(blueprint, request)

        # ---- 2. Cash position ----------------------------------------
        invested      = sum(a.abs_capital for a in allocations)
        cash_position: CashPosition = self._cash_mgr.compute(
            total_capital    = request.total_capital,
            invested_capital = invested,
            request          = request,
            max_cash_pct     = self._policy.cash.max_cash_pct,
        )
        warnings.extend(cash_position.notes)

        # ---- 3. Exposure maps (fractions) ----------------------------
        total = request.total_capital
        sector_frac: Dict[str, float] = {}
        ac_frac:     Dict[str, float] = {}
        ind_frac:    Dict[str, float] = {}
        sec_dollars: Dict[str, float] = {}
        ac_dollars:  Dict[str, float] = {}
        ind_dollars: Dict[str, float] = {}

        for a in allocations:
            cap = a.abs_capital
            sec_dollars[a.sector]      = sec_dollars.get(a.sector, 0.0) + cap
            ac_dollars[a.asset_class]  = ac_dollars.get(a.asset_class, 0.0) + cap
            ind_dollars[a.industry]    = ind_dollars.get(a.industry, 0.0) + cap

        if total > 0:
            sector_frac = {k: v / total for k, v in sec_dollars.items()}
            ac_frac     = {k: v / total for k, v in ac_dollars.items()}
            ind_frac    = {k: v / total for k, v in ind_dollars.items()}

        # ---- 4. Exposure checks --------------------------------------
        exposure_checks: List[ExposureCheck] = self._exp_check.check_all(
            sector_weights       = sector_frac,
            asset_class_weights  = ac_frac,
            max_sector_pct       = self._policy.exposure.max_sector_weight,
            max_asset_class_pct  = self._policy.exposure.max_asset_class_weight,
            industry_weights     = ind_frac,
            max_industry_pct     = self._policy.exposure.max_industry_weight,
        )

        # ---- 5. Distribution status ----------------------------------
        util = invested / total if total > 0 else 0.0
        dist = _capital_dist_status(util, cash_position.cash_pct)

        # ---- 6. Assemble plan ----------------------------------------
        with self._lock:
            state.version += 1
            version = state.version

        plan = AllocationPlan(
            portfolio_id      = portfolio_id,
            blueprint_id      = request.blueprint_id,
            blueprint_version = int(getattr(blueprint, "version", 1)),
            request_id        = request.request_id,
            version           = version,
            method            = request.method,
            currency          = request.currency,
            total_capital     = request.total_capital,
            invested_capital  = round(invested, 2),
            short_capital     = round(sum(a.abs_capital for a in allocations if a.is_short), 2),
            net_invested      = round(sum(
                a.allocated_capital for a in allocations
            ), 2),
            cash_capital      = cash_position.cash_capital,
            utilisation_rate  = round(util, 6),
            allocations       = allocations,
            cash              = cash_position.to_cash_allocation(),
            sector_exposure   = sec_dollars,
            asset_class_exposure = ac_dollars,
            industry_exposure = ind_dollars,
            distribution_status = dist,
        )

        # ---- 7. Validate --------------------------------------------
        val_report: AllocationValidationReport = self._validator.validate(plan)

        # ---- 8. Quality assessment ----------------------------------
        q_report: AllocationQualityReport = self._quality.assess(
            plan, val_report, exposure_checks
        )

        # ---- 9. Score -----------------------------------------------
        prev_score = state.score_history.latest()
        score: AllocationScore = self._scorer.calculate(q_report, prev_score)
        state.score_history.record(score)

        # ---- 10. Readiness ------------------------------------------
        readiness: AllocationReadinessAssessment = self._readiness.validate(
            plan, val_report, exposure_checks
        )

        # ---- 11. Snapshot + history ---------------------------------
        holdings = tuple(
            AllocationHolding(
                symbol            = a.symbol,
                direction         = a.direction.value,
                allocated_capital = a.allocated_capital,
                allocated_weight  = a.allocated_weight,
                sector            = a.sector,
                asset_class       = a.asset_class,
                recommendation_id = a.recommendation_id,
            )
            for a in allocations
        )

        snapshot = AllocationSnapshot(
            portfolio_id        = portfolio_id,
            plan_id             = plan.plan_id,
            blueprint_id        = plan.blueprint_id,
            plan_version        = plan.version,
            result_id           = "",    # will be set on result creation below
            total_capital       = request.total_capital,
            invested_capital    = plan.invested_capital,
            cash_capital        = plan.cash_capital,
            utilisation_rate    = plan.utilisation_rate,
            currency            = request.currency,
            holdings            = holdings,
            sector_weights      = sector_frac,
            asset_class_weights = ac_frac,
            distribution_status = dist,
            method              = request.method,
            quality_score       = score.overall,
            is_valid            = val_report.is_valid,
            is_ready            = readiness.is_ready,
        )
        state.history.record(snapshot, status="completed", quality_score=score.overall)

        # ---- 12. Assemble result ------------------------------------
        dur_ms = (time.time() - t0) * 1000
        result = AllocationResult(
            request_id          = request.request_id,
            portfolio_id        = portfolio_id,
            status              = AllocationRunStatus.COMPLETED,
            plan                = plan,
            positions_in        = len(list(getattr(blueprint, "slots", []))),
            positions_allocated = len(allocations),
            validation_summary  = {
                "is_valid":  val_report.is_valid,
                "total":     val_report.total,
                "passed":    val_report.passed,
                "warnings":  val_report.warnings,
                "failures":  val_report.failures,
            },
            quality_summary = {
                "overall_score": score.overall,
                "grade":         score.grade.value,
                "is_acceptable": score.is_acceptable,
                "gate_passed":   score.gate_passed,
            },
            exposure_summary = {
                "checks":     len(exposure_checks),
                "violations": sum(1 for c in exposure_checks if c.outcome.value == "violated"),
                "warnings":   sum(1 for c in exposure_checks if c.outcome.value == "warning"),
            },
            warnings    = tuple(warnings + list(readiness.warnings)),
            errors      = (),
            duration_ms = dur_ms,
        )

        self._emit("allocation_completed", {
            "portfolio_id":      portfolio_id,
            "plan_id":           plan.plan_id,
            "positions":         len(allocations),
            "utilisation_rate":  util,
            "quality_score":     score.overall,
            "is_ready":          readiness.is_ready,
        })
        return result

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------

    def current_allocation(self, portfolio_id: str) -> Optional[AllocationSnapshot]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.latest() if state else None

    def allocation_history(self, portfolio_id: str, n: int = 10) -> List[AllocationSnapshot]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.history.recent(n) if state else []

    def quality_score(self, portfolio_id: str) -> Optional[AllocationScore]:
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        return state.score_history.latest() if state else None

    def allocation_metrics(self, portfolio_id: str) -> Optional[AllocationMetrics]:
        snap = self.current_allocation(portfolio_id)
        if snap is None:
            return None
        with self._lock:
            state = self._portfolios.get(portfolio_id)
        if state is None:
            return None
        rec = state.history.latest_record()
        if rec is None:
            return None
        # Build a stub plan from snapshot for metrics computation
        # (full plan not cached; metrics computed from snapshot summary)
        return None   # Metrics live in AllocationResult.plan if caller retains it

    def statistics_snapshot(self) -> AllocationStatisticsSnapshot:
        return self._stats.snapshot()

    def health(self) -> AllocationHealthReport:
        return self._health.check(active_portfolios=self.portfolio_count())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fail(
        self,
        request:      AllocationRequest,
        portfolio_id: str,
        reason:       str,
        t0:           float,
    ) -> AllocationResult:
        dur_ms = (time.time() - t0) * 1000
        self._emit("allocation_failed", {
            "portfolio_id": portfolio_id,
            "reason":       reason,
        })
        return AllocationResult(
            request_id   = request.request_id,
            portfolio_id = portfolio_id,
            status       = AllocationRunStatus.FAILED,
            plan         = None,
            errors       = (reason,),
            duration_ms  = dur_ms,
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

def _capital_dist_status(utilisation: float, cash_pct: float) -> CapitalDistributionStatus:
    if utilisation > 1.02:
        return CapitalDistributionStatus.OVER_ALLOCATED
    if cash_pct > 0.30:
        return CapitalDistributionStatus.CASH_HEAVY
    if utilisation >= 0.95:
        return CapitalDistributionStatus.FULLY_INVESTED
    if utilisation >= 0.50:
        return CapitalDistributionStatus.PARTIALLY_INVESTED
    return CapitalDistributionStatus.UNDER_INVESTED
