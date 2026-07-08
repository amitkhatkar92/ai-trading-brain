"""
iios/ontology/reasoning/reasoning_constants.py
================================================
Enumerations and constants for the IIOS Ontology Reasoning
Integration Engine.

Error-code prefix: RSN-
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "ReasoningType",
    "InferenceStatus",
    "ConsistencyStatus",
    "ExplanationType",
    "RuleType",
    "ReasoningPhase",
    "IssueSeverity",
    "IssueType",
    # Confidence constants
    "CONFIDENCE_CERTAIN",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_MEDIUM",
    "CONFIDENCE_LOW",
    "CONFIDENCE_SPECULATIVE",
    # Well-known predicates
    "PRED_SUBTYPE_OF",
    "PRED_TRANSITIVE_SUBTYPE",
    "PRED_INHERITS_PROPERTY",
    "PRED_HAS_OWN_PROPERTY",
    "PRED_RELATED_TO",
    "PRED_INVERSE_RELATED",
    "PRED_IS_CONSISTENT",
    "PRED_HAS_NAMESPACE",
    "PRED_APPLIES_TO_SUBTYPE",
    # Limits
    "MAX_INFERENCE_DEPTH",
    "MAX_FIXPOINT_ITERATIONS",
    "MAX_RULES",
    "MAX_FACTS_PER_SESSION",
    "REASONING_TIMEOUT_MS",
    "SESSION_TTL_SECONDS",
    "MAX_SESSIONS",
    "EXPLANATION_MAX_DEPTH",
    "PROOF_MAX_STEPS",
    # Metadata
    "REASONING_ENGINE_VERSION",
    "SYSTEM_REASONING_ACTOR",
    # Built-in rule IDs
    "RULE_INHERITANCE_PROPAGATION",
    "RULE_SUBTYPE_TRANSITIVITY",
    "RULE_SYMMETRIC_RELATIONSHIP",
    "RULE_TYPE_CONSISTENCY",
    "RULE_NAMESPACE_CONSISTENCY",
    "RULE_REFERENCE_VALIDITY",
    "RULE_ABSTRACT_TYPE_CHECK",
    "RULE_ORPHAN_TYPE_CHECK",
    "RULE_REL_ENDPOINT_CHECK",
]


# ── Reasoning type ────────────────────────────────────────────────────────────

class ReasoningType(str, Enum):
    """Kind of reasoning operation to perform."""
    FORWARD_CHAINING  = "forward_chaining"
    BACKWARD_CHAINING = "backward_chaining"
    FORWARD_CHAIN     = "forward_chain"       # short alias used by the engine facade
    BACKWARD_CHAIN    = "backward_chain"      # short alias used by the engine facade
    FULL_INFERENCE    = "full_inference"       # run all inference rules to fixpoint
    CONSISTENCY_CHECK = "consistency_check"   # constraint-only pass
    RULE_BASED        = "rule_based"
    CONSTRAINT        = "constraint"
    ONTOLOGY          = "ontology"
    GRAPH             = "graph"
    DEPENDENCY        = "dependency"
    TEMPORAL          = "temporal"
    PROBABILISTIC     = "probabilistic"
    HYBRID            = "hybrid"


# ── Inference status ──────────────────────────────────────────────────────────

class InferenceStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    TIMEOUT   = "timeout"
    CACHED    = "cached"
    SKIPPED   = "skipped"


# ── Consistency status ────────────────────────────────────────────────────────

class ConsistencyStatus(str, Enum):
    CONSISTENT   = "consistent"
    INCONSISTENT = "inconsistent"
    UNKNOWN      = "unknown"
    PARTIAL      = "partial"


# ── Explanation type ──────────────────────────────────────────────────────────

class ExplanationType(str, Enum):
    RULE_TRACE       = "rule_trace"
    PROOF            = "proof"
    EVIDENCE_CHAIN   = "evidence_chain"
    DEPENDENCY_TRACE = "dependency_trace"
    HUMAN_READABLE   = "human_readable"
    MACHINE_READABLE = "machine_readable"


# ── Rule type ─────────────────────────────────────────────────────────────────

class RuleType(str, Enum):
    IMPLICATION = "implication"   # If X then Y
    CONSTRAINT  = "constraint"    # X must hold
    DEDUCTION   = "deduction"     # Derive new facts from existing
    INDUCTION   = "induction"     # Generalise from examples
    ABDUCTION   = "abduction"     # Hypothesis generation


# ── Reasoning phase ───────────────────────────────────────────────────────────

class ReasoningPhase(str, Enum):
    INITIALIZATION    = "initialization"
    RULE_LOADING      = "rule_loading"
    FACT_LOADING      = "fact_loading"
    INFERENCE         = "inference"
    CONSISTENCY_CHECK = "consistency_check"
    EXPLANATION       = "explanation"
    FINALIZATION      = "finalization"


# ── Issue severity ────────────────────────────────────────────────────────────

class IssueSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


# ── Issue type ────────────────────────────────────────────────────────────────

class IssueType(str, Enum):
    CIRCULAR_INHERITANCE   = "circular_inheritance"
    BROKEN_PARENT_REF      = "broken_parent_ref"
    BROKEN_PROPERTY_REF    = "broken_property_ref"
    PROPERTY_TYPE_CONFLICT = "property_type_conflict"
    MISSING_REQUIRED_PROP  = "missing_required_property"
    ORPHAN_TYPE            = "orphan_type"
    ABSTRACT_NO_CHILDREN   = "abstract_no_children"
    NAMESPACE_NOT_FOUND    = "namespace_not_found"
    DUPLICATE_PROPERTY     = "duplicate_property"
    CONSTRAINT_VIOLATION   = "constraint_violation"
    RELATIONSHIP_BROKEN    = "relationship_broken"
    TEMPORAL_CONFLICT      = "temporal_conflict"


# ── Confidence levels ─────────────────────────────────────────────────────────

CONFIDENCE_CERTAIN:     Final[float] = 1.0
CONFIDENCE_HIGH:        Final[float] = 0.9
CONFIDENCE_MEDIUM:      Final[float] = 0.7
CONFIDENCE_LOW:         Final[float] = 0.5
CONFIDENCE_SPECULATIVE: Final[float] = 0.3


# ── Well-known predicates ─────────────────────────────────────────────────────

PRED_SUBTYPE_OF:         Final[str] = "subtype_of"
PRED_TRANSITIVE_SUBTYPE: Final[str] = "transitive_subtype_of"
PRED_INHERITS_PROPERTY:  Final[str] = "inherits_property"
PRED_HAS_OWN_PROPERTY:   Final[str] = "has_own_property"
PRED_RELATED_TO:         Final[str] = "related_to"
PRED_INVERSE_RELATED:    Final[str] = "inverse_related_to"
PRED_IS_CONSISTENT:      Final[str] = "is_consistent"
PRED_HAS_NAMESPACE:      Final[str] = "has_namespace"
PRED_APPLIES_TO_SUBTYPE: Final[str] = "applies_to_subtype"


# ── Limits ────────────────────────────────────────────────────────────────────

MAX_INFERENCE_DEPTH:     Final[int]   = 32
MAX_FIXPOINT_ITERATIONS: Final[int]   = 100
MAX_RULES:               Final[int]   = 1_024
MAX_FACTS_PER_SESSION:   Final[int]   = 50_000
REASONING_TIMEOUT_MS:    Final[float] = 30_000.0
SESSION_TTL_SECONDS:     Final[int]   = 3_600   # 1 hour
MAX_SESSIONS:            Final[int]   = 256
EXPLANATION_MAX_DEPTH:   Final[int]   = 16
PROOF_MAX_STEPS:         Final[int]   = 64


# ── Metadata ──────────────────────────────────────────────────────────────────

REASONING_ENGINE_VERSION: Final[str] = "1.0.0"
SYSTEM_REASONING_ACTOR:   Final[str] = "iios:reasoning:system"


# ── Built-in rule IDs ─────────────────────────────────────────────────────────

RULE_INHERITANCE_PROPAGATION: Final[str] = "builtin.inheritance_propagation"
RULE_SUBTYPE_TRANSITIVITY:    Final[str] = "builtin.subtype_transitivity"
RULE_SYMMETRIC_RELATIONSHIP:  Final[str] = "builtin.symmetric_relationship"
RULE_TYPE_CONSISTENCY:        Final[str] = "builtin.type_consistency"
RULE_NAMESPACE_CONSISTENCY:   Final[str] = "builtin.namespace_consistency"
RULE_REFERENCE_VALIDITY:      Final[str] = "builtin.reference_validity"
RULE_ABSTRACT_TYPE_CHECK:     Final[str] = "builtin.abstract_type_check"
RULE_ORPHAN_TYPE_CHECK:       Final[str] = "builtin.orphan_type_check"
RULE_REL_ENDPOINT_CHECK:      Final[str] = "builtin.rel_endpoint_check"
