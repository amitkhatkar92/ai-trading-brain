"""
iios/ontology/reasoning/reasoning_manager.py
=============================================
ReasoningManager — coordinator for all reasoning operations.

Orchestrates:
  - SessionManager           (session lifecycle)
  - InferenceEngine          (forward/backward chaining)
  - ExplanationEngine        (human/machine explanations)
  - ReasoningStatistics      (metrics recording)
  - ReasoningFactory         (request/response construction)

Public API
----------
reason(request)                        -> ReasoningResponse
check_consistency(target_uri)          -> ReasoningResult
explain(session_id)                    -> dict
infer_relationships(type_uri)          -> list[InferredFact]
reason_forward(target_uri)             -> ReasoningResponse
reason_backward(goal_uri)              -> ReasoningResponse
reason_all()                           -> ReasoningResponse
stats()                                -> dict
health()                               -> dict

Singleton: get_reasoning_manager() / reset_reasoning_manager()
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Optional

from .reasoning_constants   import (
    ReasoningType,
    InferenceStatus,
    ConsistencyStatus,
    SYSTEM_REASONING_ACTOR,
    PRED_TRANSITIVE_SUBTYPE,
)
from .reasoning_exceptions  import (
    ReasoningNotInitializedError,
    SessionNotFoundError,
)
from .reasoning_factory     import ReasoningFactory, ReasoningRequest, ReasoningResponse, get_reasoning_factory
from .reasoning_result      import ReasoningResult, FactStore, ConsistencyIssue
from .reasoning_session     import SessionManager, get_session_manager
from .reasoning_statistics  import ReasoningStats, get_reasoning_statistics
from .reasoning_trace       import ReasoningTrace
from .inference.inference_engine  import InferenceEngine, get_inference_engine_instance
from .explanation.explanation_engine import ExplanationEngine, get_explanation_engine

__all__ = [
    "ReasoningManager",
    "get_reasoning_manager",
    "reset_reasoning_manager",
]


class ReasoningManager:
    """
    Central coordinator for the IIOS Ontology Reasoning Engine.

    Must be initialised before use (is_initialized property).
    Initialisation is deferred so that the registry manager is ready.
    """

    def __init__(
        self,
        factory:     Optional[ReasoningFactory]  = None,
        sessions:    Optional[SessionManager]    = None,
        stats:       Optional[ReasoningStats]    = None,
        inf_engine:  Optional[InferenceEngine]   = None,
        expl_engine: Optional[ExplanationEngine] = None,
    ) -> None:
        self._factory     = factory     or get_reasoning_factory()
        self._sessions    = sessions    or get_session_manager()
        self._stats       = stats       or get_reasoning_statistics()
        self._inf_engine  = inf_engine  or get_inference_engine_instance()
        self._expl_engine = expl_engine or get_explanation_engine()
        self._mgr: Optional[Any] = None  # OntologyRegistryManager — injected at init
        self._lock         = threading.RLock()
        self._initialized  = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self, mgr: Optional[Any] = None) -> None:
        """
        Bind the OntologyRegistryManager and mark the engine as ready.

        If *mgr* is not provided, imports the global singleton.
        """
        with self._lock:
            if mgr is None:
                from iios.ontology.registry.ontology_registry_manager import (
                    get_registry_manager,
                )
                mgr = get_registry_manager()
            self._mgr         = mgr
            self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _require_init(self) -> Any:
        if not self._initialized or self._mgr is None:
            raise ReasoningNotInitializedError()
        return self._mgr

    # ── Core reasoning operations ─────────────────────────────────────────────

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        """
        Execute a full reasoning session and return the response.
        """
        mgr     = self._require_init()
        session = self._sessions.create(request)
        t0      = time.perf_counter()
        try:
            facts, issues, trace = self._inf_engine.run(request, mgr)
            duration_ms           = (time.perf_counter() - t0) * 1_000.0
            consistency_status    = (
                ConsistencyStatus.CONSISTENT
                if not any(i.is_error for i in issues)
                else ConsistencyStatus.INCONSISTENT
            )
            result = ReasoningResult(
                session_id         = session.session_id,
                reasoning_type     = request.reasoning_type,
                status             = InferenceStatus.COMPLETED,
                consistency_status = consistency_status,
                inferred_facts     = facts.all_facts(),
                consistency_issues = issues,
                duration_ms        = duration_ms,
                iterations         = trace.step_count,
                rule_fire_count    = trace.step_count,
            )
            session.complete(result, trace)
            self._stats.record(
                reasoning_type = request.reasoning_type,
                fact_count     = result.fact_count,
                issue_count    = result.issue_count,
                rule_fires     = result.rule_fire_count,
                duration_ms    = duration_ms,
                iterations     = result.iterations,
            )
            response = self._factory.make_response(request, result, trace)
            return response
        except Exception as exc:
            session.fail(str(exc))
            raise

    def check_consistency(
        self,
        target_uri: str = "*",
    ) -> ReasoningResult:
        """Run all constraint rules and return a consistency report."""
        mgr     = self._require_init()
        request = self._factory.make_request(
            reasoning_type = ReasoningType.CONSISTENCY_CHECK,
            target_uri     = target_uri,
        )
        response = self.reason(request)
        return response.result

    def explain(self, session_id: str) -> dict:
        """Return a machine-readable explanation of a completed session."""
        session = self._sessions.get(session_id)
        if session.result is None or session.trace is None:
            raise SessionNotFoundError(session_id)
        return self._expl_engine.explain(
            result           = session.result,
            trace            = session.trace,
            explanation_type = __import__(
                "iios.ontology.reasoning.reasoning_constants",
                fromlist=["ExplanationType"],
            ).ExplanationType.MACHINE_READABLE,
        )

    def infer_relationships(self, type_uri: str) -> list:
        """Return all inferred relationship facts for *type_uri*."""
        mgr = self._require_init()
        all_facts = self._inf_engine.forward_chain_all(mgr)
        return [
            f for f in all_facts.about(type_uri)
            if f.predicate == PRED_TRANSITIVE_SUBTYPE
        ]

    def reason_forward(self, target_uri: str) -> ReasoningResponse:
        request = self._factory.make_request(
            reasoning_type = ReasoningType.FORWARD_CHAIN,
            target_uri     = target_uri,
        )
        return self.reason(request)

    def reason_backward(self, goal_uri: str) -> ReasoningResponse:
        request = self._factory.make_request(
            reasoning_type = ReasoningType.BACKWARD_CHAIN,
            target_uri     = goal_uri,
        )
        return self.reason(request)

    def reason_all(self) -> ReasoningResponse:
        request = self._factory.make_request(
            reasoning_type = ReasoningType.FULL_INFERENCE,
            target_uri     = "*",
        )
        return self.reason(request)

    # ── Health and diagnostics ────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "initialized": self._initialized,
            "sessions":    self._sessions.stats(),
            "reasoning":   self._stats.snapshot(),
        }

    def health(self) -> dict:
        status = "healthy" if self._initialized else "not_initialized"
        return {
            "status":      status,
            "initialized": self._initialized,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_man_lock = threading.Lock()
_man_inst: Optional[ReasoningManager] = None


def get_reasoning_manager() -> ReasoningManager:
    global _man_inst
    if _man_inst is None:
        with _man_lock:
            if _man_inst is None:
                _man_inst = ReasoningManager()
    return _man_inst


def reset_reasoning_manager() -> None:
    global _man_inst
    with _man_lock:
        _man_inst = None
