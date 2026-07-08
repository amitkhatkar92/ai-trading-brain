"""iios/decision_optimization/decision_optimization_engine.py — Top-level gateway."""
from __future__ import annotations

import asyncio
import threading

from .optimization_constants import OPTIMIZATION_ENGINE_SYSTEM_ID, OPTIMIZATION_ENGINE_VERSION
from .optimization_exceptions import EngineAlreadyRunningError, EngineNotInitializedError
from .optimization_manager import (
    OptimizationManager,
    OptimizationRequest,
    OptimizationResult,
    get_optimization_manager,
    reset_optimization_manager,
)
from .optimization_context import Candidate
from .objectives.objective import Objective
from .objectives.objective_registry import get_objective_registry
from .constraints.constraint_checker import OptimizationConstraint
from .constraints.constraint_optimizer import get_constraint_optimizer
from .algorithms.optimization_algorithm import OptimizationAlgorithm
from .algorithms.algorithm_registry import get_algorithm_registry
from .optimization_constants import AlgorithmType


class DecisionOptimizationEngine:
    """
    Top-level gateway for the Decision Optimization Engine.
    Must be initialized before use.  Thread-safe singleton wrapper.
    """

    VERSION   = OPTIMIZATION_ENGINE_VERSION
    SYSTEM_ID = OPTIMIZATION_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._running  = False
        self._manager: OptimizationManager | None = None
        self._lock     = threading.Lock()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def initialize(self, manager: OptimizationManager | None = None) -> None:
        with self._lock:
            if self._running:
                raise EngineAlreadyRunningError()
            self._manager = manager or get_optimization_manager()
            self._running = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._manager = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Registration ───────────────────────────────────────────────────────

    def register_objective(
        self, objective: Objective, *, overwrite: bool = False
    ) -> None:
        get_objective_registry().register(objective, overwrite=overwrite)

    def register_constraint(
        self, constraint: OptimizationConstraint, *, overwrite: bool = False
    ) -> None:
        get_constraint_optimizer().register(constraint, overwrite=overwrite)

    def register_algorithm(self, algorithm: OptimizationAlgorithm) -> None:
        get_algorithm_registry().register(algorithm)

    # ── Optimization ───────────────────────────────────────────────────────

    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        if not self._running:
            raise EngineNotInitializedError()
        return self._manager.optimize(request)  # type: ignore[union-attr]

    async def optimize_async(self, request: OptimizationRequest) -> OptimizationResult:
        if not self._running:
            raise EngineNotInitializedError()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._manager.optimize(request)  # type: ignore[union-attr]
        )

    def recommend(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective] | None = None,
        constraints: list[OptimizationConstraint] | None = None,
        **kwargs,
    ) -> OptimizationResult:
        req = OptimizationRequest(
            candidates  = candidates,
            objectives  = objectives or [],
            constraints = constraints or [],
            **kwargs,
        )
        return self.optimize(req)

    # ── Analytics ──────────────────────────────────────────────────────────

    def sensitivity_analysis(
        self,
        request:      OptimizationRequest,
        objective_id: str,
        weight_range: tuple[float, float] = (0.0, 1.0),
        steps:        int = 10,
    ) -> dict:
        if not self._running:
            raise EngineNotInitializedError()
        return self._manager.sensitivity_analysis(  # type: ignore[union-attr]
            request, objective_id, weight_range, steps
        )

    def robustness(
        self,
        request:     OptimizationRequest,
        noise_level: float = 0.05,
        n_trials:    int   = 50,
    ) -> dict:
        if not self._running:
            raise EngineNotInitializedError()
        return self._manager.robustness(request, noise_level, n_trials)  # type: ignore[union-attr]

    # ── Health / stats ─────────────────────────────────────────────────────

    def health(self) -> dict:
        return {
            "running":   self._running,
            "version":   self.VERSION,
            "system_id": self.SYSTEM_ID,
        }

    def stats(self) -> dict:
        base = {
            "version":   self.VERSION,
            "system_id": self.SYSTEM_ID,
            "running":   self._running,
        }
        if self._manager is not None:
            base.update(self._manager.statistics())
        return base


# ── Module-level singleton ────────────────────────────────────────────────────

_engine: DecisionOptimizationEngine | None = None
_lock   = threading.Lock()


def get_decision_optimization_engine() -> DecisionOptimizationEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = DecisionOptimizationEngine()
    return _engine


def reset_decision_optimization_engine() -> None:
    global _engine
    with _lock:
        if _engine is not None:
            _engine.shutdown()
        _engine = None
