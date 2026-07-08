"""
iios/ontology/reasoning/inference/inference_executor.py
=======================================================
Forward and backward chaining execution over a FactStore.

Key design choices:
  - Forward chaining:  iterate rules until no new facts are produced (fixpoint)
                       or MAX_FIXPOINT_ITERATIONS is reached.
  - Backward chaining: depth-limited goal-directed search.
  - Ground-truth load: seeds the FactStore with one fact per registered type
                       (its URI) so rules have something to match against.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from ..reasoning_constants import (
    MAX_FIXPOINT_ITERATIONS,
    MAX_INFERENCE_DEPTH,
    REASONING_TIMEOUT_MS,
    PRED_SUBTYPE_OF,
    PRED_HAS_NAMESPACE,
    CONFIDENCE_CERTAIN,
)
from ..reasoning_result     import InferredFact, FactStore
from ..reasoning_trace      import ReasoningTrace
from .inference_registry    import InferenceRegistry, get_inference_registry
from .inference_rule        import InferenceRule

__all__ = [
    "InferenceExecutor",
    "get_inference_executor",
    "reset_inference_executor",
]


class InferenceExecutor:
    """
    Executes inference rules via forward and backward chaining.

    Parameters
    ----------
    registry: InferenceRegistry (optional, defaults to global singleton)
    """

    def __init__(self, registry: Optional[InferenceRegistry] = None) -> None:
        self._registry = registry or get_inference_registry()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_ground_truth(self, mgr: Any) -> FactStore:
        """
        Seed a FactStore with one fact per registered type.

        The fact captures the type's URI (subject), IS_A predicate (predicate),
        and namespace URI (object).  These ground-truth facts allow rules to
        iterate over all types without special-case logic.
        """
        store = FactStore()
        for td in mgr.list_all_types():
            store.add(InferredFact(
                subject_uri  = td.uri,
                predicate    = PRED_SUBTYPE_OF,
                object_value = td.parent_uri or td.namespace_uri,
                confidence   = CONFIDENCE_CERTAIN,
                rule_ids     = ["ground_truth"],
                inferred     = False,
            ))
            store.add(InferredFact(
                subject_uri  = td.uri,
                predicate    = PRED_HAS_NAMESPACE,
                object_value = td.namespace_uri,
                confidence   = CONFIDENCE_CERTAIN,
                rule_ids     = ["ground_truth"],
                inferred     = False,
            ))
        return store

    def forward_chain(
        self,
        facts:     FactStore,
        mgr:       Any,
        rule_ids:  list[str] | None = None,
        max_iter:  int              = MAX_FIXPOINT_ITERATIONS,
        trace:     Optional[ReasoningTrace] = None,
    ) -> FactStore:
        """
        Saturate *facts* by repeatedly firing enabled rules until fixpoint.

        Returns the augmented FactStore.
        """
        rules = self._select_rules(rule_ids)
        for i in range(max_iter):
            changed = False
            for rule in rules:
                new_items = rule.execute(facts, mgr)
                step_facts   = [x for x in new_items if isinstance(x, InferredFact)]
                step_issues  = [x for x in new_items if not isinstance(x, InferredFact)]
                step_added   = 0
                for f in step_facts:
                    if facts.add(f):
                        changed = True
                        step_added += 1
                if trace is not None and (step_added or step_issues):
                    trace.add_step(
                        rule_id      = rule.rule_id,
                        rule_name    = rule.name,
                        input_facts  = [],
                        output_facts = [f.to_dict() for f in step_facts[:step_added]],
                        issues       = [iss.to_dict() for iss in step_issues],
                        confidence   = rule.confidence,
                    )
            if not changed:
                break
        return facts

    def collect_issues(
        self,
        facts:    FactStore,
        mgr:      Any,
        rule_ids: list[str] | None = None,
    ) -> list:
        """Run constraint rules and collect ConsistencyIssues without altering facts."""
        from ..reasoning_constants import RuleType
        rules = [
            r for r in self._select_rules(rule_ids)
            if r.rule_type == RuleType.CONSTRAINT
        ]
        issues: list = []
        for rule in rules:
            result = rule.execute(facts, mgr)
            for item in result:
                if not isinstance(item, InferredFact):
                    issues.append(item)
        return issues

    def backward_chain(
        self,
        goal:       InferredFact,
        facts:      FactStore,
        mgr:        Any,
        rule_ids:   list[str] | None = None,
        max_depth:  int              = MAX_INFERENCE_DEPTH,
    ) -> bool:
        """
        Attempt to prove *goal* fact by backward chaining.

        Returns True if the goal can be derived (exists in facts or can be
        inferred via forward chaining up to *max_depth*).
        """
        key = goal.key()
        if facts.has(*key):
            return True
        if max_depth <= 0:
            return False
        # Forward-chain and check again
        augmented = self.forward_chain(
            facts     = FactStore(),          # operate on a copy
            mgr       = mgr,
            rule_ids  = rule_ids,
            max_iter  = max_depth,
        )
        # Merge original facts into augmented
        for f in facts.all_facts():
            augmented.add(f)
        return augmented.has(*key)

    def multi_hop_inference(
        self,
        start_uri: str,
        mgr:       Any,
        max_depth: int = 4,
    ) -> list[InferredFact]:
        """
        Collect all facts reachable from *start_uri* within *max_depth* hops.
        """
        gt    = self.load_ground_truth(mgr)
        store = self.forward_chain(gt, mgr, max_iter=max_depth)
        return store.about(start_uri)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _select_rules(self, rule_ids: list[str] | None) -> list[InferenceRule]:
        if rule_ids:
            rules = []
            for rid in rule_ids:
                if self._registry.has(rid):
                    r = self._registry.get(rid)
                    if r.enabled:
                        rules.append(r)
            return sorted(rules, key=lambda r: r.priority)
        return self._registry.enabled_rules()


# ── Singleton ─────────────────────────────────────────────────────────────────

_exec_lock = threading.Lock()
_exec_inst: Optional[InferenceExecutor] = None


def get_inference_executor() -> InferenceExecutor:
    global _exec_inst
    if _exec_inst is None:
        with _exec_lock:
            if _exec_inst is None:
                _exec_inst = InferenceExecutor()
    return _exec_inst


def reset_inference_executor() -> None:
    global _exec_inst
    with _exec_lock:
        _exec_inst = None
