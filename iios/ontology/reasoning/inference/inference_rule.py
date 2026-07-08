"""
iios/ontology/reasoning/inference/inference_rule.py
====================================================
Inference rule model for the IIOS Reasoning Engine.

An InferenceRule combines a callable condition with a callable action:
  - condition(FactStore, registry_manager) -> bool
  - action(FactStore, registry_manager) -> list[InferredFact | ConsistencyIssue]

Rules are data objects registered in InferenceRegistry and executed
by InferenceExecutor.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..reasoning_constants import RuleType, CONFIDENCE_HIGH
from ..reasoning_result    import InferredFact, ConsistencyIssue, FactStore

__all__ = [
    "RuleCondition",
    "RuleAction",
    "InferenceRule",
]

# Type aliases
RuleCondition = Callable[[FactStore, Any], bool]
RuleAction    = Callable[[FactStore, Any], list[InferredFact | ConsistencyIssue]]


@dataclass
class InferenceRule:
    """
    A single inference or constraint rule.

    Parameters
    ----------
    rule_id:     Unique identifier (e.g. "builtin.subtype_transitivity")
    name:        Human-readable name
    description: What the rule does
    rule_type:   Kind of reasoning (IMPLICATION, CONSTRAINT, DEDUCTION…)
    priority:    Execution order within a session (lower = runs first)
    confidence:  Default confidence for facts produced by this rule
    enabled:     Rules can be toggled at runtime
    condition:   callable(facts, mgr) -> bool — True means rule should fire
    action:      callable(facts, mgr) -> [InferredFact | ConsistencyIssue]
    tags:        Arbitrary string tags for grouping
    """
    rule_id:     str
    name:        str
    description: str
    rule_type:   RuleType
    priority:    int                   = 100
    confidence:  float                 = CONFIDENCE_HIGH
    enabled:     bool                  = True
    condition:   RuleCondition         = field(default=lambda f, m: True, repr=False)
    action:      RuleAction            = field(default=lambda f, m: [], repr=False)
    tags:        list[str]             = field(default_factory=list)
    builtin:     bool                  = False
    metadata:    dict[str, Any]        = field(default_factory=dict)

    def execute(
        self,
        facts: FactStore,
        mgr:   Any,
    ) -> list[InferredFact | ConsistencyIssue]:
        """
        Execute this rule against *facts* and *mgr* (OntologyRegistryManager).

        Returns new InferredFacts or ConsistencyIssues.
        Never raises — exceptions are caught and returned as empty list.
        """
        try:
            if not self.enabled:
                return []
            if not self.condition(facts, mgr):
                return []
            return self.action(facts, mgr)
        except Exception:
            return []

    def to_dict(self) -> dict:
        return {
            "rule_id":     self.rule_id,
            "name":        self.name,
            "description": self.description,
            "rule_type":   self.rule_type.value,
            "priority":    self.priority,
            "confidence":  self.confidence,
            "enabled":     self.enabled,
            "builtin":     self.builtin,
            "tags":        self.tags,
        }
