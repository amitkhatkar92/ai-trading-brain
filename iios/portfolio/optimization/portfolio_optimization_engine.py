"""
portfolio_optimization_engine.py — iios.portfolio.optimization
===============================================================
Primary public interface for the Portfolio Optimization Framework.

PortfolioOptimizationEngine is the single entry point used by external
callers.  It wraps the manager in a lifecycle-managed facade that
accepts requests, manages strategy and candidate registries, and
exposes health, statistics, and history.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    OPTIMIZATION_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    PortfolioOptimizationNotRunningError,
    PortfolioOptimizationStrategyError,
)
from .portfolio_candidate import PortfolioCandidate
from .portfolio_candidate_registry import PortfolioCandidateRegistry
from .portfolio_optimization_factory import PortfolioOptimizationFactory
from .portfolio_optimization_history import PortfolioOptimizationHistory
from .portfolio_optimization_manager import PortfolioOptimizationManager
from .portfolio_optimization_registry import PortfolioOptimizationRegistry
from .portfolio_optimization_request import PortfolioOptimizationRequest
from .portfolio_optimization_response import PortfolioOptimizationResponse
from .portfolio_optimization_statistics import PortfolioOptimizationStatistics
from .portfolio_optimization_strategy import PortfolioOptimizationStrategy
from .portfolio_optimizer import PortfolioOptimizer
from .portfolio_strategy_registry import PortfolioStrategyRegistry

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=OPTIMIZATION_SYSTEM_ID)


# ---------------------------------------------------------------------------
# Status value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationEngineStatus:
    """Point-in-time status snapshot of the optimization engine."""
    lifecycle_state:          str
    registered_strategies:    int
    active_strategies:        int
    registered_candidates:    int
    optimizations_total:      int
    optimizations_successful: int
    optimizations_failed:     int
    is_healthy:               bool
    uptime_s:                 float
    captured_at:              float
    framework_version:        str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lifecycle_state":           self.lifecycle_state,
            "registered_strategies":     self.registered_strategies,
            "active_strategies":         self.active_strategies,
            "registered_candidates":     self.registered_candidates,
            "optimizations_total":       self.optimizations_total,
            "optimizations_successful":  self.optimizations_successful,
            "optimizations_failed":      self.optimizations_failed,
            "is_healthy":                self.is_healthy,
            "uptime_s":                  self.uptime_s,
            "captured_at":               self.captured_at,
            "framework_version":         self.framework_version,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PortfolioOptimizationEngine(LifecycleAwareMixin):
    """
    Primary public interface for the Portfolio Optimization Framework.

    Usage
    -----
    ::

        engine = PortfolioOptimizationEngine()
        engine.start()

        # Register a strategy
        engine.register_strategy(strategy)

        # Optimize
        response = engine.optimize(portfolio_id, candidates=candidates)

        engine.stop()

    The engine performs NO policy evaluation, NO trade execution, and
    NO broker communication.
    """

    def __init__(self) -> None:
        super().__init__()
        self._strategy_registry  = PortfolioStrategyRegistry()
        self._candidate_registry = PortfolioCandidateRegistry()
        self._opt_registry       = PortfolioOptimizationRegistry()
        self._statistics         = PortfolioOptimizationStatistics()
        self._history            = PortfolioOptimizationHistory()
        self._optimizer          = PortfolioOptimizer()
        self._manager            = PortfolioOptimizationManager(
            optimizer             = self._optimizer,
            strategy_registry     = self._strategy_registry,
            candidate_registry    = self._candidate_registry,
            optimization_registry = self._opt_registry,
            statistics            = self._statistics,
            history               = self._history,
        )
        self._started_at: Optional[float] = None

        # Register the built-in default strategy
        default_strategy = PortfolioOptimizationFactory.create_default_strategy()
        self._strategy_registry.register(default_strategy)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        super().start()
        self._started_at = time.monotonic()
        _audit.log_lifecycle_event(
            engine_id  = OPTIMIZATION_SYSTEM_ID,
            from_state = "STOPPED",
            to_state   = "RUNNING",
            version    = VERSION,
            actor      = ACTOR_ENGINE,
        )
        _log.info(f"PortfolioOptimizationEngine started (version={VERSION})")

    def stop(self) -> None:
        super().stop()
        _audit.log_lifecycle_event(
            engine_id  = OPTIMIZATION_SYSTEM_ID,
            from_state = "RUNNING",
            to_state   = "STOPPED",
            version    = VERSION,
            actor      = ACTOR_ENGINE,
        )
        _log.info("PortfolioOptimizationEngine stopped")

    # ------------------------------------------------------------------
    # Strategy management
    # ------------------------------------------------------------------

    def register_strategy(self, strategy: PortfolioOptimizationStrategy) -> None:
        """Register an optimization strategy."""
        self._assert_running()
        self._strategy_registry.register(strategy)
        _log.debug(f"strategy registered: name={strategy.name!r}")

    def get_strategy(self, strategy_id: str) -> Optional[PortfolioOptimizationStrategy]:
        self._assert_running()
        return self._strategy_registry.get(strategy_id)

    def list_strategies(self) -> List[PortfolioOptimizationStrategy]:
        self._assert_running()
        return self._strategy_registry.all()

    # ------------------------------------------------------------------
    # Candidate management
    # ------------------------------------------------------------------

    def register_candidate(self, candidate: PortfolioCandidate) -> None:
        """Register a portfolio candidate in the engine's registry."""
        self._assert_running()
        self._candidate_registry.register(candidate)

    def get_candidate(self, candidate_id: str) -> Optional[PortfolioCandidate]:
        self._assert_running()
        return self._candidate_registry.get(candidate_id)

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    def submit(
        self, request: PortfolioOptimizationRequest
    ) -> PortfolioOptimizationResponse:
        """Submit a fully-formed optimization request."""
        self._assert_running()
        _log.debug(
            f"submit: optimization_id={request.optimization_id!r}, "
            f"portfolio_id={request.portfolio_id!r}, "
            f"candidates={request.candidate_count}"
        )
        return self._manager.optimize_portfolio(request)

    def optimize(
        self,
        portfolio_id:    str,
        *,
        candidates:      Optional[List[PortfolioCandidate]] = None,
        strategy_name:   str = "",
        inputs:          Optional[Dict[str, Any]] = None,
        optimization_id: str = "",
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> PortfolioOptimizationResponse:
        """
        Convenience method — builds and submits an optimization request.

        Parameters
        ----------
        portfolio_id :    Portfolio to optimize.
        candidates :      Candidates (optional — registry is also consulted).
        strategy_name :   Strategy to use (default: "default").
        inputs :          Input snapshots.
        optimization_id : Pre-assigned run ID (auto-generated if omitted).
        """
        self._assert_running()
        request = PortfolioOptimizationFactory.create_request(
            portfolio_id    = portfolio_id,
            strategy_name   = strategy_name or "default",
            candidates      = candidates,
            inputs          = inputs,
            optimization_id = optimization_id,
            metadata        = metadata,
        )
        return self.submit(request)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def validate(self, request: PortfolioOptimizationRequest) -> Dict[str, Any]:
        """Validate a request without running the optimization pipeline."""
        self._assert_running()
        checks: Dict[str, bool] = {
            "request_id_non_empty":    bool(request.request_id),
            "portfolio_id_non_empty":  bool(request.portfolio_id),
            "optimization_id_non_empty": bool(request.optimization_id),
            "has_candidates":          request.candidate_count > 0,
            "strategy_name_non_empty": bool(request.strategy_name),
        }
        is_valid = all(checks.values())
        return {"is_valid": is_valid, "checks": checks}

    def status(self) -> OptimizationEngineStatus:
        """Return a point-in-time engine status snapshot."""
        snap    = self._statistics.snapshot()
        uptime  = (
            time.monotonic() - self._started_at
            if self._started_at is not None
            else 0.0
        )
        return OptimizationEngineStatus(
            lifecycle_state           = self.lifecycle_state().value,
            registered_strategies     = self._strategy_registry.count,
            active_strategies         = self._strategy_registry.active_count,
            registered_candidates     = self._candidate_registry.count,
            optimizations_total       = snap.total_optimizations,
            optimizations_successful  = snap.successful,
            optimizations_failed      = snap.failed,
            is_healthy                = self.lifecycle_state().value == "running",
            uptime_s                  = uptime,
            captured_at               = time.time(),
        )

    def statistics(self) -> Dict[str, Any]:
        """Return raw statistics as a plain dict."""
        return self._statistics.snapshot().to_dict()

    def health(self) -> Dict[str, Any]:
        """Return a compact health dict."""
        st = self.status()
        return {
            "is_healthy":      st.is_healthy,
            "lifecycle_state": st.lifecycle_state,
            "uptime_s":        st.uptime_s,
        }

    def history(self) -> Dict[str, Any]:
        """Return history summary plus recent events."""
        return {
            **self._history.summary(),
            "recent_events": [
                e.to_dict() for e in self._history.recent_events(10)
            ],
        }

    # ------------------------------------------------------------------
    # Event bus delegation
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        """Subscribe to OptimizationEngineEvent notifications."""
        self._manager.add_listener(fn)

    def remove_listener(self, fn: Callable) -> None:
        self._manager.remove_listener(fn)

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise PortfolioOptimizationNotRunningError()
