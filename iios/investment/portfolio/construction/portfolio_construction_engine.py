"""iios/investment/portfolio/construction/portfolio_construction_engine.py

PortfolioConstructionEngine — the authoritative orchestrator for all
portfolio construction operations in IIOS.

Responsibilities:
  • Accept validated InvestmentRecommendations
  • Orchestrate the full construction pipeline per portfolio
  • Maintain construction history and snapshots
  • Publish construction events (via optional callback)
  • Provide rich query APIs

Pipeline (deterministic):
  SecuritySelector  →  ConstructionEngine  →  ConstraintEngine
  →  PortfolioValidator  →  ConstructionValidator  →  ReadinessValidator
  →  ConstructionQualityAssessor  →  ScoreCalculator
  →  PortfolioConstructionHistory  →  ConstructionResult

This engine NEVER:
  • Analyses markets, companies, or strategies independently
  • Optimises portfolio weights
  • Rebalances portfolios
  • Executes trades
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.constraint_engine import ConstraintEngine
from iios.investment.portfolio.construction.constraint_registry import ConstraintRegistry
from iios.investment.portfolio.construction.construction_engine import ConstructionEngine
from iios.investment.portfolio.construction.construction_health import ConstructionHealthMonitor
from iios.investment.portfolio.construction.construction_quality import ConstructionQualityAssessor
from iios.investment.portfolio.construction.construction_score import ScoreCalculator, ScoreHistory
from iios.investment.portfolio.construction.construction_statistics import (
    ConstructionStatistics,
    RunMetric,
)
from iios.investment.portfolio.construction.construction_types import (
    ConstructionStatus,
    HealthStatus,
)
from iios.investment.portfolio.construction.construction_validator import ConstructionValidator
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    ConstructionResult,
)
from iios.investment.portfolio.construction.portfolio_history import (
    PortfolioConstructionHistory,
)
from iios.investment.portfolio.construction.portfolio_snapshot import (
    HoldingRecord,
    PortfolioConstructionSnapshot,
)
from iios.investment.portfolio.construction.portfolio_statistics import compute_statistics
from iios.investment.portfolio.construction.portfolio_validator import PortfolioValidator
from iios.investment.portfolio.construction.readiness_validator import ReadinessValidator
from iios.investment.portfolio.construction.security_selector import SecuritySelector
from iios.investment.portfolio.construction.selection_policy import SelectionPolicy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Integration references
# ---------------------------------------------------------------------------

@dataclass
class ConstructionIntegrationRefs:
    """
    Optional references to upstream IIOS engines.
    The construction engine NEVER calls these to analyse markets or strategies —
    they are passed through for traceability only.
    """

    decision_intelligence:  Optional[Any] = None
    market_intelligence:    Optional[Any] = None
    company_intelligence:   Optional[Any] = None
    strategy_intelligence:  Optional[Any] = None
    historical_framework:   Optional[Any] = None
    knowledge_layer:        Optional[Any] = None
    audit_framework:        Optional[Any] = None

    def to_dict(self) -> Dict[str, bool]:
        return {
            "decision_intelligence":  self.decision_intelligence is not None,
            "market_intelligence":    self.market_intelligence is not None,
            "company_intelligence":   self.company_intelligence is not None,
            "strategy_intelligence":  self.strategy_intelligence is not None,
            "historical_framework":   self.historical_framework is not None,
            "knowledge_layer":        self.knowledge_layer is not None,
            "audit_framework":        self.audit_framework is not None,
        }


# ---------------------------------------------------------------------------
# PortfolioState (per-portfolio internal book-keeping)
# ---------------------------------------------------------------------------

@dataclass
class _PortfolioState:
    """Internal state for a single registered portfolio."""

    portfolio_id:   str
    history:        PortfolioConstructionHistory
    score_history:  ScoreHistory
    version:        int = 0
    last_result_id: str = ""
    registered_at:  float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# PortfolioConstructionEngine
# ---------------------------------------------------------------------------

class PortfolioConstructionEngine:
    """
    Authoritative portfolio construction engine.

    Usage::

        engine = PortfolioConstructionEngine()
        engine.start()
        engine.register_portfolio("PF-001")
        result = engine.construct("PF-001", recommendations, request)
        engine.stop()

    Thread-safety: all public methods are thread-safe.
    """

    _CONSTRUCTION_VERSION = "1.0.0"

    def __init__(
        self,
        *,
        selector:        Optional[SecuritySelector]           = None,
        construction_engine: Optional[ConstructionEngine]     = None,
        constraint_registry: Optional[ConstraintRegistry]     = None,
        constraint_engine:   Optional[ConstraintEngine]       = None,
        portfolio_validator: Optional[PortfolioValidator]     = None,
        construction_validator: Optional[ConstructionValidator] = None,
        readiness_validator: Optional[ReadinessValidator]     = None,
        quality_assessor:    Optional[ConstructionQualityAssessor] = None,
        score_calculator:    Optional[ScoreCalculator]        = None,
        selection_policy:    Optional[SelectionPolicy]        = None,
        environment:         str                              = "paper",
        event_callback:      Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        self._selector       = selector or SecuritySelector(policy=selection_policy)
        self._engine         = construction_engine or ConstructionEngine()
        self._con_registry   = constraint_registry or ConstraintRegistry()
        self._con_engine     = constraint_engine or ConstraintEngine(self._con_registry)
        self._pv             = portfolio_validator or PortfolioValidator()
        self._cv             = construction_validator or ConstructionValidator()
        self._rv             = readiness_validator or ReadinessValidator()
        self._qa             = quality_assessor or ConstructionQualityAssessor()
        self._sc             = score_calculator or ScoreCalculator()

        self._environment    = environment
        self._event_callback = event_callback

        self._portfolios: Dict[str, _PortfolioState] = {}
        self._stats          = ConstructionStatistics()
        self._health_monitor = ConstructionHealthMonitor()

        self._lock           = threading.RLock()
        self._running        = False
        self._started_at: Optional[float] = None
        self._integrations   = ConstructionIntegrationRefs()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running    = True
            self._started_at = time.time()
        logger.info("PortfolioConstructionEngine started [env=%s]", self._environment)
        self._emit("engine_started", {"environment": self._environment})

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
        logger.info("PortfolioConstructionEngine stopped")
        self._emit("engine_stopped", {})

    @property
    def is_running(self) -> bool:
        return self._running

    def configure_integrations(self, refs: ConstructionIntegrationRefs) -> None:
        with self._lock:
            self._integrations = refs

    # ------------------------------------------------------------------
    # Portfolio registration
    # ------------------------------------------------------------------

    def register_portfolio(self, portfolio_id: str) -> None:
        """Register a portfolio so the engine can track its construction history."""
        self._assert_running()
        with self._lock:
            if portfolio_id not in self._portfolios:
                self._portfolios[portfolio_id] = _PortfolioState(
                    portfolio_id  = portfolio_id,
                    history       = PortfolioConstructionHistory(portfolio_id),
                    score_history = ScoreHistory(portfolio_id),
                )
        logger.debug("Registered portfolio %s", portfolio_id)

    def deregister_portfolio(self, portfolio_id: str) -> bool:
        """Remove a portfolio from tracking.  Returns True if it existed."""
        with self._lock:
            return self._portfolios.pop(portfolio_id, None) is not None

    def is_registered(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._portfolios

    # ------------------------------------------------------------------
    # Main construction entry point
    # ------------------------------------------------------------------

    def construct(
        self,
        portfolio_id: str,
        recommendations: List[Any],
        request: Optional[ConstructionRequest] = None,
        *,
        auto_register: bool = True,
    ) -> ConstructionResult:
        """
        Construct a portfolio blueprint from validated recommendations.

        Args:
            portfolio_id:    Target portfolio identifier.
            recommendations: Validated InvestmentRecommendations from upstream pipelines.
            request:         Construction parameters.  A sensible default is used if None.
            auto_register:   If True, register the portfolio if not already known.

        Returns:
            ConstructionResult — always returned (never raises on business failures).
        """
        self._assert_running()
        t0 = time.monotonic()

        if request is None:
            request = ConstructionRequest(portfolio_id=portfolio_id)

        if auto_register and not self.is_registered(portfolio_id):
            self.register_portfolio(portfolio_id)

        result = self._run_pipeline(portfolio_id, recommendations, request, t0)

        # Record run metric
        duration_ms = (time.monotonic() - t0) * 1000.0
        quality     = result.quality_summary.get("overall_score", 0.0)
        metric      = RunMetric(
            portfolio_id  = portfolio_id,
            succeeded     = result.succeeded,
            slots_built   = result.recommendations_selected,
            duration_ms   = duration_ms,
            quality_score = quality,
        )
        self._stats.record(metric)
        self._health_monitor.record_run(success=result.succeeded, duration_ms=duration_ms)

        return result

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(
        self,
        portfolio_id: str,
        recommendations: List[Any],
        request: ConstructionRequest,
        t0: float,
    ) -> ConstructionResult:
        warnings:  List[str] = []
        errors:    List[str] = []
        blueprint             = None
        quality_summary: Dict = {}
        constraint_summary: Dict = {}
        validation_summary: Dict = {}

        try:
            # Step 1: Security selection
            state    = self._get_state(portfolio_id)
            sel_policy = SelectionPolicy(
                min_conviction   = request.min_conviction,
                min_confidence   = request.min_confidence,
                max_risk_score   = request.max_risk_score,
                max_long_holdings= request.max_holdings,
                max_short_holdings=request.max_holdings if request.allow_short else 0,
            )
            sel_result = self._selector.select(
                recommendations, request, policy=sel_policy
            )

            if sel_result.count == 0:
                errors.append("Security selection returned 0 eligible recommendations")
                return self._fail_result(
                    request, recommendations, errors, time.monotonic() - t0
                )

            # Step 2: Build blueprint
            version   = (state.version + 1) if state else 1
            blueprint = self._engine.build_blueprint(
                list(sel_result.selected), request, version=version
            )

            # Step 3: Constraint evaluation
            constraint_report  = self._con_engine.evaluate(blueprint)
            constraint_summary = {
                "is_compliant":  constraint_report.is_compliant,
                "hard_violated": constraint_report.hard_violated,
                "total_checked": constraint_report.total_checked,
                "compliance_rate": round(constraint_report.compliance_rate, 4),
            }
            if not constraint_report.is_compliant:
                for v in constraint_report.violations:
                    warnings.append(f"Constraint [{v.constraint_name}]: {v.message}")

            # Step 4: Portfolio validation
            portfolio_report = self._pv.validate(blueprint)

            # Step 5: Construction validation
            construction_report = self._cv.validate(blueprint, request)

            # Step 6: Readiness assessment
            readiness = self._rv.validate(
                blueprint, constraint_report,
                portfolio_report, construction_report
            )

            validation_summary = {
                "portfolio_valid":    portfolio_report.is_valid,
                "construction_valid": construction_report.is_valid,
                "is_ready":           readiness.is_ready,
                "blocking_count":     len(readiness.blocking_reasons),
            }

            # Step 7: Quality assessment
            stats = compute_statistics(blueprint)
            quality_report = self._qa.assess(
                blueprint, portfolio_report, construction_report,
                constraint_report, readiness, stats=stats,
            )
            quality_summary = {
                "overall_score":  quality_report.overall_score,
                "health_status":  quality_report.health_status.value,
                "is_acceptable":  quality_report.is_acceptable,
                "grade":          "",   # filled below
            }

            # Step 8: Score
            prev_score = state.score_history.latest() if state else None
            score      = self._sc.calculate(quality_report, prev_score)
            quality_summary["grade"] = score.grade

            # Step 9: Update state
            if state:
                with self._lock:
                    state.version += 1
                    state.score_history.record(score)

            # Step 10: Record in history
            self._record_to_history(portfolio_id, blueprint, request, quality_report)

            duration_ms = (time.monotonic() - t0) * 1000.0
            logger.info(
                "Construction completed portfolio=%s slots=%d quality=%.3f in %.1f ms",
                portfolio_id, blueprint.total_slots, quality_report.overall_score, duration_ms,
            )
            self._emit("construction_completed", {
                "portfolio_id": portfolio_id,
                "blueprint_id": blueprint.blueprint_id,
                "quality":      quality_report.overall_score,
            })

            return ConstructionResult(
                request_id               = request.request_id,
                portfolio_id             = portfolio_id,
                status                   = ConstructionStatus.COMPLETED,
                blueprint                = blueprint,
                recommendations_in       = len(recommendations),
                recommendations_selected = sel_result.count,
                validation_summary       = validation_summary,
                constraint_summary       = constraint_summary,
                quality_summary          = quality_summary,
                warnings                 = tuple(warnings),
                errors                   = tuple(errors),
                duration_ms              = (time.monotonic() - t0) * 1000.0,
                construction_version     = self._CONSTRUCTION_VERSION,
            )

        except Exception as exc:
            logger.exception("Construction failed for portfolio %s: %s", portfolio_id, exc)
            errors.append(str(exc))
            self._emit("construction_failed", {
                "portfolio_id": portfolio_id,
                "error": str(exc),
            })
            return self._fail_result(request, recommendations, errors, time.monotonic() - t0)

    def _fail_result(
        self,
        request: ConstructionRequest,
        recommendations: List[Any],
        errors: List[str],
        elapsed: float,
    ) -> ConstructionResult:
        return ConstructionResult(
            request_id           = request.request_id,
            portfolio_id         = request.portfolio_id,
            status               = ConstructionStatus.FAILED,
            blueprint            = None,
            recommendations_in   = len(recommendations),
            errors               = tuple(errors),
            duration_ms          = elapsed * 1000.0,
            construction_version = self._CONSTRUCTION_VERSION,
        )

    # ------------------------------------------------------------------
    # History recording
    # ------------------------------------------------------------------

    def _record_to_history(
        self,
        portfolio_id: str,
        blueprint: Any,
        request: ConstructionRequest,
        quality_report: Any,
    ) -> None:
        state = self._get_state(portfolio_id)
        if state is None:
            return

        snapshot = _blueprint_to_snapshot(blueprint, quality_report)
        state.history.record(
            snapshot,
            status            = ConstructionStatus.COMPLETED.value,
            construction_type = blueprint.construction_type.value,
            weighting_method  = blueprint.weighting_method.value,
            quality_score     = quality_report.overall_score,
        )

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------

    def current_blueprint(self, portfolio_id: str) -> Optional[Any]:
        """Return the most recent PortfolioConstructionSnapshot for a portfolio, or None."""
        state = self._get_state(portfolio_id)
        return state.history.latest() if state else None

    def construction_history(self, portfolio_id: str, n: int = 20) -> List[Dict]:
        """Return the n most recent blueprint records for a portfolio."""
        state = self._get_state(portfolio_id)
        if state is None:
            return []
        return [r.to_dict() for r in state.history.all_records()[-n:]]

    def constraint_report(self, portfolio_id: str) -> Optional[Dict]:
        """Return constraint summary for the latest run."""
        state = self._get_state(portfolio_id)
        if state is None:
            return None
        latest = state.history.latest_record()
        if latest is None:
            return None
        return latest.to_dict()

    def quality_score(self, portfolio_id: str) -> Optional[float]:
        """Return the latest overall quality score for a portfolio."""
        state = self._get_state(portfolio_id)
        if state is None:
            return None
        s = state.score_history.latest()
        return s.overall if s else None

    def portfolio_statistics(self, portfolio_id: str) -> Optional[Dict]:
        """Return latest blueprint composition statistics as a dict."""
        snap = self.current_blueprint(portfolio_id)
        return snap.to_dict() if snap else None

    def statistics_snapshot(self) -> Dict:
        """Return engine-level aggregated statistics."""
        return self._stats.snapshot().to_dict()

    def health(self) -> Dict:
        """Return current engine health report as a dict."""
        return self._health_monitor.check(
            active_portfolios=self.portfolio_count()
        ).to_dict()

    def list_portfolios(self) -> List[str]:
        with self._lock:
            return list(self._portfolios.keys())

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._portfolios)

    # ------------------------------------------------------------------
    # Constraint management
    # ------------------------------------------------------------------

    @property
    def constraint_registry(self) -> ConstraintRegistry:
        return self._con_registry

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_state(self, portfolio_id: str) -> Optional[_PortfolioState]:
        with self._lock:
            return self._portfolios.get(portfolio_id)

    def _assert_running(self) -> None:
        if not self._running:
            raise RuntimeError(
                "PortfolioConstructionEngine is not running. Call start() first."
            )

    def _emit(self, event: str, payload: Dict) -> None:
        if self._event_callback:
            try:
                self._event_callback(event, payload)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Snapshot helper
# ---------------------------------------------------------------------------

def _blueprint_to_snapshot(blueprint: Any, quality_report: Any) -> PortfolioConstructionSnapshot:
    """Convert a PortfolioBlueprint to a PortfolioConstructionSnapshot."""
    holdings = tuple(
        HoldingRecord(
            symbol              = s.symbol,
            name                = s.name,
            direction           = s.direction,
            target_weight       = s.target_weight,
            sector              = s.sector,
            asset_class         = s.asset_class,
            market_cap_category = s.market_cap_category,
            recommendation_id   = s.recommendation_id,
            conviction          = s.conviction,
            confidence          = s.confidence,
            risk_score          = s.risk_score,
        )
        for s in blueprint.slots
    )

    return PortfolioConstructionSnapshot(
        portfolio_id       = blueprint.portfolio_id,
        blueprint_id       = blueprint.blueprint_id,
        blueprint_version  = blueprint.version,
        holdings           = holdings,
        cash_weight        = blueprint.cash_weight,
        long_count         = blueprint.long_count,
        short_count        = blueprint.short_count,
        long_weight_sum    = blueprint.long_weight_sum,
        short_weight_sum   = blueprint.short_weight_sum,
        net_exposure       = blueprint.net_exposure,
        gross_exposure     = blueprint.gross_exposure,
        sector_weights     = dict(blueprint.sector_weights),
        asset_class_weights= dict(blueprint.asset_class_weights),
        quality_score      = getattr(quality_report, "overall_score", 0.0),
        is_valid           = True,
        is_ready           = True,
    )
