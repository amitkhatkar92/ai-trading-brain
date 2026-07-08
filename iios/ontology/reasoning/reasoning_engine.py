"""
iios/ontology/reasoning/reasoning_engine.py
===========================================
ReasoningEngine — single entry point for all IIOS ontology reasoning.

Wraps ReasoningManager with an initialisation guard, rule management
delegation to InferenceRegistry, and a simplified public API.

Singleton: get_reasoning_engine() / reset_reasoning_engine()
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from .reasoning_constants   import ReasoningType, ExplanationType
from .reasoning_exceptions  import ReasoningNotInitializedError
from .reasoning_factory     import ReasoningRequest, ReasoningResponse
from .reasoning_result      import InferredFact, ReasoningResult
from .reasoning_session     import ReasoningSession
from .reasoning_manager     import ReasoningManager, get_reasoning_manager
from .inference.inference_registry import InferenceRegistry, get_inference_registry
from .inference.inference_rule     import InferenceRule

__all__ = [
    "ReasoningEngine",
    "get_reasoning_engine",
    "reset_reasoning_engine",
]


class ReasoningEngine:
    """
    Master facade for the IIOS Ontology Reasoning Engine.

    Usage
    -----
    engine = get_reasoning_engine()
    engine.initialize()            # binds the ontology registry

    response = engine.reason(request)
    result   = engine.check_consistency()
    text     = engine.explain(session_id)

    engine.forward_chain("iios.core.Entity")
    engine.infer_all()

    engine.register_rule(my_rule)
    engine.enable_rule("my.rule.id")
    engine.disable_rule("my.rule.id")

    session = engine.get_session(session_id)
    print(engine.stats())
    print(engine.health())
    """

    def __init__(
        self,
        manager:  Optional[ReasoningManager]  = None,
        registry: Optional[InferenceRegistry] = None,
    ) -> None:
        self._manager  = manager  or get_reasoning_manager()
        self._registry = registry or get_inference_registry()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self, mgr: Optional[Any] = None) -> "ReasoningEngine":
        self._manager.initialize(mgr)
        return self

    @property
    def is_initialized(self) -> bool:
        return self._manager.is_initialized

    # ── Core reasoning ────────────────────────────────────────────────────────

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        return self._manager.reason(request)

    def check_consistency(self, target_uri: str = "*") -> ReasoningResult:
        return self._manager.check_consistency(target_uri)

    def explain(self, session_id: str) -> dict:
        return self._manager.explain(session_id)

    def forward_chain(self, target_uri: str) -> ReasoningResponse:
        return self._manager.reason_forward(target_uri)

    def backward_chain(self, goal_uri: str) -> ReasoningResponse:
        return self._manager.reason_backward(goal_uri)

    def infer_all(self) -> ReasoningResponse:
        return self._manager.reason_all()

    def infer_for_type(self, type_uri: str) -> list[InferredFact]:
        return self._manager.infer_relationships(type_uri)

    # ── Rule management ───────────────────────────────────────────────────────

    def register_rule(self, rule: InferenceRule) -> None:
        self._registry.register(rule)

    def enable_rule(self, rule_id: str) -> None:
        self._registry.enable(rule_id)

    def disable_rule(self, rule_id: str) -> None:
        self._registry.disable(rule_id)

    def list_rules(self) -> list[InferenceRule]:
        return self._registry.all_rules()

    # ── Session access ────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> ReasoningSession:
        return self._manager._sessions.get(session_id)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return self._manager.stats()

    def health(self) -> dict:
        return self._manager.health()


# ── Singleton ─────────────────────────────────────────────────────────────────

_eng_lock = threading.Lock()
_eng_inst: Optional[ReasoningEngine] = None


def get_reasoning_engine() -> ReasoningEngine:
    global _eng_inst
    if _eng_inst is None:
        with _eng_lock:
            if _eng_inst is None:
                _eng_inst = ReasoningEngine()
    return _eng_inst


def reset_reasoning_engine() -> None:
    global _eng_inst
    with _eng_lock:
        _eng_inst = None
