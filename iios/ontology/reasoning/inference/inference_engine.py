"""
iios/ontology/reasoning/inference/inference_engine.py
=====================================================
Orchestrator for all inference operations in a single reasoning session.

The InferenceEngine ties together:
  - InferenceExecutor  (forward/backward chaining)
  - InferenceRegistry  (rule catalogue)
  - InferenceGraph     (result graph construction)
  - ReasoningTrace     (audit trail)

Returns a (FactStore, ReasoningTrace) pair so the caller (ReasoningManager)
can wrap it into a full ReasoningResult.

Singleton: get_inference_engine_instance() / reset_inference_engine_instance()
  (Named *_instance* to avoid a name clash with QueryEngine's get_*_engine.)
"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from ..reasoning_constants   import (
    ReasoningType,
    InferenceStatus,
    MAX_FIXPOINT_ITERATIONS,
    MAX_INFERENCE_DEPTH,
    PRED_TRANSITIVE_SUBTYPE,
    PRED_INHERITS_PROPERTY,
    PRED_INVERSE_RELATED,
)
from ..reasoning_result      import FactStore, ConsistencyIssue
from ..reasoning_trace       import ReasoningTrace
from ..reasoning_factory     import ReasoningRequest
from .inference_executor     import InferenceExecutor, get_inference_executor
from .inference_registry     import InferenceRegistry, get_inference_registry
from .inference_graph        import (
    InferenceGraph,
    InferenceNode,
    InferenceEdge,
)

__all__ = [
    "InferenceEngine",
    "get_inference_engine_instance",
    "reset_inference_engine_instance",
]


class InferenceEngine:
    """
    Coordinates forward/backward chaining and graph construction.

    Methods
    -------
    run(request, mgr)
        Full pipeline for one reasoning session.
        Returns (FactStore, list[ConsistencyIssue], ReasoningTrace).

    forward_chain_all(mgr)
        Run all enabled implication/deduction rules and return the fact store.

    infer_for_type(type_uri, mgr, depth)
        Multi-hop inference anchored at one type URI.
    """

    def __init__(
        self,
        executor: Optional[InferenceExecutor] = None,
        registry: Optional[InferenceRegistry] = None,
    ) -> None:
        self._executor = executor or get_inference_executor()
        self._registry = registry or get_inference_registry()

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        request: ReasoningRequest,
        mgr:     Any,
    ) -> tuple[FactStore, list[ConsistencyIssue], ReasoningTrace]:
        """Execute the full inference pipeline for *request*."""
        trace       = ReasoningTrace(session_id=request.request_id)
        t_start     = time.perf_counter()

        # Seed ground truth
        facts = self._executor.load_ground_truth(mgr)

        # Forward-chain all inference rules
        facts = self._executor.forward_chain(
            facts    = facts,
            mgr      = mgr,
            rule_ids = request.rule_ids or None,
            max_iter = MAX_FIXPOINT_ITERATIONS,
            trace    = trace,
        )

        # Collect consistency issues (constraint rules only)
        issues = self._executor.collect_issues(
            facts    = facts,
            mgr      = mgr,
            rule_ids = request.rule_ids or None,
        )

        trace.finalise()
        return facts, issues, trace

    def forward_chain_all(self, mgr: Any) -> FactStore:
        """Run all enabled rules starting from ground truth."""
        facts = self._executor.load_ground_truth(mgr)
        return self._executor.forward_chain(facts, mgr)

    def infer_for_type(
        self,
        type_uri: str,
        mgr:      Any,
        depth:    int = MAX_INFERENCE_DEPTH,
    ) -> list:
        """All facts inferred about *type_uri* within *depth* hops."""
        return self._executor.multi_hop_inference(type_uri, mgr, max_depth=depth)

    def build_graph(self, facts: FactStore, mgr: Any) -> InferenceGraph:
        """Construct an InferenceGraph from a FactStore."""
        graph = InferenceGraph()

        # Add all known types as nodes
        for td in mgr.list_all_types():
            graph.add_node(InferenceNode(
                uri           = td.uri,
                name          = td.name,
                namespace_uri = td.namespace_uri,
                abstract      = td.abstract,
                confidence    = 1.0,
            ))

        # Add edges from inferred transitive-subtype and inverse-related facts
        for fact in facts.all_facts():
            if fact.predicate in (
                PRED_TRANSITIVE_SUBTYPE,
                PRED_INHERITS_PROPERTY,
                PRED_INVERSE_RELATED,
            ):
                graph.add_edge(InferenceEdge(
                    source     = fact.subject_uri,
                    target     = str(fact.object_value),
                    relation   = fact.predicate,
                    confidence = fact.confidence,
                    rule_id    = fact.rule_ids[0] if fact.rule_ids else "",
                    inferred   = fact.inferred,
                ))

        return graph


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_lock = threading.Lock()
_engine_inst: Optional[InferenceEngine] = None


def get_inference_engine_instance() -> InferenceEngine:
    global _engine_inst
    if _engine_inst is None:
        with _engine_lock:
            if _engine_inst is None:
                _engine_inst = InferenceEngine()
    return _engine_inst


def reset_inference_engine_instance() -> None:
    global _engine_inst
    with _engine_lock:
        _engine_inst = None
