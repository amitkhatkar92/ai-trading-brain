"""
iios/decisions/core/decision_engine.py
=======================================
DecisionEngine — the mandatory gateway for every decision produced by IIOS.

Usage
-----
    from iios.decisions.core.decision_engine import get_decision_engine

    engine = get_decision_engine()
    engine.initialize()

    result = engine.decide(
        DecisionRequest(
            source_id   = "strategy_engine",
            options     = [accept_option, reject_option],
            priority    = DecisionPriority.HIGH,
        )
    )
    if result.succeeded:
        decision = result.decision
        ...
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from ..decision_constants import (
    DECISION_ENGINE_VERSION,
    DecisionPriority,
    DecisionType,
)
from ..decision_context import reset_decision_context
from ..decision_exceptions import (
    EngineAlreadyRunningError,
    EngineNotInitializedError,
)
from ..models.decision import Decision
from ..models.decision_option import DecisionOption
from ..models.decision_request import DecisionRequest
from ..models.decision_result import DecisionResult
from ..models.decision_statistics import DecisionStatistics
from ..monitoring.decision_monitor import get_decision_monitor, reset_decision_monitor
from ..policies.decision_policy import DecisionPolicy
from ..registry.decision_registry import get_decision_registry, reset_decision_registry
from .decision_manager import DecisionManager, get_decision_manager, reset_decision_manager


class DecisionEngine:
    """
    Top-level AI Decision Layer gateway.

    Wraps DecisionManager and enforces the initialize / shutdown lifecycle.

    Thread-safe.  Supports both synchronous and asynchronous invocation.
    """

    VERSION: str = DECISION_ENGINE_VERSION

    def __init__(self) -> None:
        self._manager: DecisionManager | None = None
        self._running: bool                   = False
        self._lock:    threading.RLock        = threading.RLock()

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            if self._running:
                raise EngineAlreadyRunningError()
            self._manager = get_decision_manager()
            self._running = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._manager = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _require_running(self) -> DecisionManager:
        with self._lock:
            if not self._running or self._manager is None:
                raise EngineNotInitializedError()
            return self._manager

    # -- Core API ──────────────────────────────────────────────────────────────

    def decide(self, request: DecisionRequest) -> DecisionResult:
        """
        Run the full 10-stage decision workflow.

        Returns a ``DecisionResult``.  Check ``result.succeeded`` and
        ``result.decision`` before acting.
        """
        mgr = self._require_running()
        return mgr.decide(request)

    async def decide_async(self, request: DecisionRequest) -> DecisionResult:
        """Async wrapper — runs the synchronous workflow in the default executor."""
        loop = asyncio.get_running_loop()
        mgr  = self._require_running()
        return await loop.run_in_executor(None, lambda: mgr.decide(request))

    # -- Convenience factory methods ──────────────────────────────────────────

    def make_request(
        self,
        options:              list[DecisionOption] | None = None,
        intelligence_payload: list[dict[str, Any]] | None = None,
        source_id:            str                          = "",
        decision_type:        DecisionType | None          = None,
        priority:             DecisionPriority             = DecisionPriority.MEDIUM,
        context:              dict[str, Any] | None        = None,
        constraints:          dict[str, Any] | None        = None,
        metadata:             dict[str, Any] | None        = None,
        ttl_s:                float                        = 3_600.0,
    ) -> DecisionRequest:
        return DecisionRequest(
            decision_type        = decision_type,
            source_id            = source_id,
            options              = list(options or []),
            intelligence_payload = list(intelligence_payload or []),
            context              = dict(context or {}),
            constraints          = dict(constraints or {}),
            priority             = priority,
            ttl_s                = ttl_s,
            metadata             = dict(metadata or {}),
        )

    # -- Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy: DecisionPolicy) -> None:
        mgr = self._require_running()
        mgr.register_policy(policy)

    def policy_names(self) -> list[str]:
        mgr = self._require_running()
        return mgr.policy_names()

    # -- Query ─────────────────────────────────────────────────────────────────

    def get(self, decision_id: str) -> Decision:
        mgr = self._require_running()
        return mgr.get(decision_id)

    def cancel(self, decision_id: str) -> None:
        mgr = self._require_running()
        mgr.cancel(decision_id)

    def recent(self, n: int = 20) -> list[Decision]:
        mgr = self._require_running()
        return mgr.recent(n)

    def for_source(self, source_id: str) -> list[Decision]:
        mgr = self._require_running()
        return mgr.for_source(source_id)

    def statistics(self, source_id: str | None = None) -> DecisionStatistics:
        mgr = self._require_running()
        return mgr.statistics(source_id=source_id)

    # -- Metrics ───────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        with self._lock:
            running = self._running
        if not running:
            return {"status": "stopped", "engine_version": self.VERSION}
        try:
            mgr = self._require_running()
            h   = mgr.health()
            h["engine_version"] = self.VERSION
            return h
        except Exception as exc:
            return {"status": "error", "error": str(exc), "engine_version": self.VERSION}

    def stats(self) -> dict[str, Any]:
        mgr = self._require_running()
        s   = mgr.stats()
        s["engine_version"] = self.VERSION
        return s


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock      = threading.Lock()
_ENGINE: DecisionEngine | None = None


def get_decision_engine() -> DecisionEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = DecisionEngine()
    return _ENGINE


def reset_decision_engine() -> None:
    global _ENGINE
    with _LOCK:
        if _ENGINE is not None:
            try:
                _ENGINE.shutdown()
            except Exception:
                pass
        _ENGINE = None
