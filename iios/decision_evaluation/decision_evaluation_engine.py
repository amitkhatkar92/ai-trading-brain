"""iios/decision_evaluation/decision_evaluation_engine.py — Top-level gateway."""
from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING

from .evaluation_constants import EVALUATION_ENGINE_SYSTEM_ID, EVALUATION_ENGINE_VERSION
from .evaluation_exceptions import EngineAlreadyRunningError, EngineNotInitializedError
from .evaluation_manager import (
    EvaluationManager,
    EvaluationRequest,
    EvaluationResult,
    get_evaluation_manager,
    reset_evaluation_manager,
)
from .evaluation_context import Alternative
from .criteria.criterion import Criterion
from .criteria.criteria_registry import get_criteria_registry
from .ranking.ranking_algorithm import RankingAlgorithm
from .ranking.ranking_registry import get_ranking_registry

if TYPE_CHECKING:
    pass


class DecisionEvaluationEngine:
    """
    Top-level gateway for the Multi-Criteria Decision Evaluation Engine.
    Must be initialized before use; thread-safe singleton.
    """

    VERSION   = EVALUATION_ENGINE_VERSION
    SYSTEM_ID = EVALUATION_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._running = False
        self._manager: EvaluationManager | None = None
        self._lock    = threading.Lock()

    def initialize(self, manager: EvaluationManager | None = None) -> None:
        with self._lock:
            if self._running:
                raise EngineAlreadyRunningError()
            self._manager = manager or get_evaluation_manager()
            self._running = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._manager = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Criterion/algorithm registration ──────────────────────────────────

    def register_criterion(
        self,
        criterion: Criterion,
        *,
        overwrite: bool = False,
    ) -> None:
        get_criteria_registry().register(criterion, overwrite=overwrite)

    def register_algorithm(self, algorithm: RankingAlgorithm) -> None:
        get_ranking_registry().register(algorithm)

    # ── Evaluation ────────────────────────────────────────────────────────

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        if not self._running:
            raise EngineNotInitializedError()
        return self._manager.evaluate(request)  # type: ignore[union-attr]

    async def evaluate_async(self, request: EvaluationRequest) -> EvaluationResult:
        if not self._running:
            raise EngineNotInitializedError()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._manager.evaluate(request))  # type: ignore[union-attr]

    def recommend(
        self,
        alternatives: list[Alternative],
        criteria:     list[Criterion],
        weights:      dict[str, float] | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Shortcut: build a request and evaluate in one call."""
        req = EvaluationRequest(
            alternatives = alternatives,
            criteria     = criteria,
            weights      = weights or {},
            **kwargs,
        )
        return self.evaluate(req)

    # ── Health / stats ────────────────────────────────────────────────────

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

_engine: DecisionEvaluationEngine | None = None
_lock   = threading.Lock()


def get_decision_evaluation_engine() -> DecisionEvaluationEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = DecisionEvaluationEngine()
    return _engine


def reset_decision_evaluation_engine() -> None:
    global _engine
    with _lock:
        if _engine is not None:
            _engine.shutdown()
        _engine = None
