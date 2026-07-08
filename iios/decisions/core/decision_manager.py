"""
iios/decisions/core/decision_manager.py
========================================
DecisionManager — orchestrates the full decision lifecycle:
create → run workflow → persist → monitor.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from ..decision_constants import (
    DECISION_ENGINE_SYSTEM_ID,
    DecisionPriority,
    DecisionType,
)
from ..decision_exceptions import (
    DecisionNotFoundError,
    NoCandidatesError,
)
from ..evaluation.decision_evaluator import DecisionEvaluator
from ..evaluation.decision_ranker import DecisionRanker
from ..models.decision import Decision
from ..models.decision_option import DecisionOption
from ..models.decision_request import DecisionRequest
from ..models.decision_result import DecisionResult
from ..models.decision_statistics import DecisionStatistics
from ..monitoring.decision_monitor import DecisionMonitor, get_decision_monitor
from ..policies.decision_policy import DecisionPolicy, MinConfidencePolicy, MaxRiskPolicy
from ..registry.decision_registry import DecisionRegistry, get_decision_registry
from ..workflow.decision_factory import DecisionFactory
from ..workflow.decision_workflow import DecisionWorkflow


class DecisionManager:
    """
    Single-entry orchestrator for the Decision Engine subsystem.

    Lifecycle
    ---------
    1. Caller submits a DecisionRequest via ``decide()``.
    2. Manager runs the 10-stage DecisionWorkflow.
    3. Decision is persisted in the registry.
    4. Result is forwarded to the monitor.
    5. Completed Decision is returned to the caller.
    """

    _DEFAULT_POLICIES: list[DecisionPolicy] = [
        MinConfidencePolicy(),
        MaxRiskPolicy(),
    ]

    def __init__(self) -> None:
        self._registry:  DecisionRegistry  = get_decision_registry()
        self._monitor:   DecisionMonitor   = get_decision_monitor()
        self._evaluator: DecisionEvaluator = DecisionEvaluator()
        self._ranker:    DecisionRanker    = DecisionRanker()
        self._factory:   DecisionFactory   = DecisionFactory()
        self._policies:  list[DecisionPolicy] = list(self._DEFAULT_POLICIES)
        self._lock:      threading.RLock   = threading.RLock()
        self._workflow:  DecisionWorkflow  = self._build_workflow()

    # -- Policy management ────────────────────────────────────────────────────

    def register_policy(self, policy: DecisionPolicy) -> None:
        with self._lock:
            self._policies.append(policy)
            self._workflow = self._build_workflow()

    def clear_policies(self) -> None:
        with self._lock:
            self._policies = list(self._DEFAULT_POLICIES)
            self._workflow = self._build_workflow()

    def policy_names(self) -> list[str]:
        with self._lock:
            return [p.name for p in self._policies]

    # -- Decision lifecycle ────────────────────────────────────────────────────

    def decide(self, request: DecisionRequest) -> DecisionResult:
        """
        Run the full 10-stage workflow for ``request`` and return a DecisionResult.
        The resulting Decision is also stored in the registry.
        """
        with self._lock:
            wf = self._workflow

        result = wf.run(request)
        self._persist(result)
        self._monitor.record(result, source_id=request.source_id)
        return result

    def get(self, decision_id: str) -> Decision:
        return self._registry.get(decision_id)

    def cancel(self, decision_id: str) -> None:
        self._registry.cancel(decision_id)

    def expire(self, decision_id: str) -> None:
        self._registry.expire(decision_id)

    def expire_stale(self, ttl_s: float) -> list[str]:
        return self._registry.expire_stale(ttl_s)

    # -- Query ─────────────────────────────────────────────────────────────────

    def for_source(self, source_id: str) -> list[Decision]:
        return self._registry.for_source(source_id)

    def for_request(self, request_id: str) -> list[Decision]:
        return self._registry.for_request(request_id)

    def recent(self, n: int = 20) -> list[Decision]:
        return self._registry.recent(n)

    def statistics(self, source_id: str | None = None) -> DecisionStatistics:
        return self._registry.statistics(source_id=source_id)

    # -- Health ────────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        h = self._monitor.health()
        h["registry"] = self._registry.stats()
        return h

    def stats(self) -> dict[str, Any]:
        return {
            "registry":  self._registry.stats(),
            "monitor":   self._monitor.stats(),
            "policies":  len(self._policies),
        }

    # -- Internal ──────────────────────────────────────────────────────────────

    def _persist(self, result: DecisionResult) -> None:
        if result.decision and result.decision.decision_id:
            try:
                self._registry.register(result.decision)
            except Exception:
                # Best-effort — never crash the caller
                pass

    def _build_workflow(self) -> DecisionWorkflow:
        return DecisionWorkflow(
            evaluator  = self._evaluator,
            ranker     = self._ranker,
            factory    = self._factory,
            policies   = list(self._policies),
            on_publish = None,   # registry persistence handled in _persist
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock           = threading.Lock()
_MANAGER: DecisionManager | None  = None


def get_decision_manager() -> DecisionManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = DecisionManager()
    return _MANAGER


def reset_decision_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
