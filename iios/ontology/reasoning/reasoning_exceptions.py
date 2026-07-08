"""
iios/ontology/reasoning/reasoning_exceptions.py
=================================================
Structured exception hierarchy for the IIOS Ontology Reasoning
Integration Engine.

Error-code prefix: RSN-
"""

from __future__ import annotations

__all__ = [
    "ReasoningError",
    # Inference
    "InferenceError",
    "InferenceTimeoutError",
    "InferenceDepthError",
    "InferenceCycleError",
    # Consistency
    "ConsistencyError",
    "OntologyInconsistencyError",
    "ReasoningConstraintError",
    "ConflictError",
    # Rule
    "RuleError",
    "DuplicateRuleError",
    "UnknownRuleError",
    "RuleExecutionError",
    # Explanation
    "ExplanationError",
    # Session
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    # Engine
    "ReasoningEngineError",
    "ReasoningNotInitializedError",
]


# ── Base ──────────────────────────────────────────────────────────────────────

class ReasoningError(RuntimeError):
    """RSN-000: Base exception for all reasoning engine errors."""
    code = "RSN-000"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Inference ─────────────────────────────────────────────────────────────────

class InferenceError(ReasoningError):
    """RSN-010: Base for inference failures."""
    code = "RSN-010"


class InferenceTimeoutError(InferenceError):
    """RSN-011: Inference exceeded the configured timeout."""
    code = "RSN-011"

    def __init__(self, elapsed_ms: float) -> None:
        super().__init__(f"Inference timed out after {elapsed_ms:.0f} ms")
        self.elapsed_ms = elapsed_ms


class InferenceDepthError(InferenceError):
    """RSN-012: Inference chain exceeded maximum depth."""
    code = "RSN-012"

    def __init__(self, depth: int, max_depth: int) -> None:
        super().__init__(
            f"Inference depth {depth} exceeds maximum {max_depth}"
        )
        self.depth     = depth
        self.max_depth = max_depth


class InferenceCycleError(InferenceError):
    """RSN-013: Cycle detected in inference chain."""
    code = "RSN-013"

    def __init__(self, cycle: list[str]) -> None:
        chain = " → ".join(cycle)
        super().__init__(f"Inference cycle detected: {chain}")
        self.cycle = cycle


# ── Consistency ───────────────────────────────────────────────────────────────

class ConsistencyError(ReasoningError):
    """RSN-020: Base for ontology consistency failures."""
    code = "RSN-020"


class OntologyInconsistencyError(ConsistencyError):
    """RSN-021: The ontology graph contains a structural inconsistency."""
    code = "RSN-021"

    def __init__(self, detail: str, affected_uris: list[str] | None = None) -> None:
        super().__init__(f"Ontology inconsistency: {detail}")
        self.affected_uris = affected_uris or []


class ReasoningConstraintError(ConsistencyError):
    """RSN-022: A reasoning constraint was violated."""
    code = "RSN-022"

    def __init__(self, rule_id: str, detail: str) -> None:
        super().__init__(f"Constraint {rule_id!r} violated: {detail}")
        self.rule_id = rule_id


class ConflictError(ConsistencyError):
    """RSN-023: Two or more facts are in direct conflict."""
    code = "RSN-023"

    def __init__(self, fact_a: str, fact_b: str) -> None:
        super().__init__(f"Fact conflict: {fact_a!r} ↔ {fact_b!r}")
        self.fact_a = fact_a
        self.fact_b = fact_b


# ── Rule ──────────────────────────────────────────────────────────────────────

class RuleError(ReasoningError):
    """RSN-030: Base for inference rule errors."""
    code = "RSN-030"


class DuplicateRuleError(RuleError):
    """RSN-031: A rule with the same ID is already registered."""
    code = "RSN-031"

    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Rule already registered: {rule_id!r}")
        self.rule_id = rule_id


class UnknownRuleError(RuleError):
    """RSN-032: No rule found with the given ID."""
    code = "RSN-032"

    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Unknown rule: {rule_id!r}")
        self.rule_id = rule_id


class RuleExecutionError(RuleError):
    """RSN-033: A rule raised an exception during execution."""
    code = "RSN-033"

    def __init__(self, rule_id: str, cause: str) -> None:
        super().__init__(f"Rule {rule_id!r} execution failed: {cause}")
        self.rule_id = rule_id


# ── Explanation ───────────────────────────────────────────────────────────────

class ExplanationError(ReasoningError):
    """RSN-040: Explanation generation failed."""
    code = "RSN-040"


# ── Session ───────────────────────────────────────────────────────────────────

class SessionError(ReasoningError):
    """RSN-050: Base for session management errors."""
    code = "RSN-050"


class SessionNotFoundError(SessionError):
    """RSN-051: No session found with the given ID."""
    code = "RSN-051"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id!r}")
        self.session_id = session_id


class SessionExpiredError(SessionError):
    """RSN-052: The requested session has expired."""
    code = "RSN-052"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session expired: {session_id!r}")
        self.session_id = session_id


# ── Engine ────────────────────────────────────────────────────────────────────

class ReasoningEngineError(ReasoningError):
    """RSN-060: Base for engine-level errors."""
    code = "RSN-060"


class ReasoningNotInitializedError(ReasoningEngineError):
    """RSN-061: Engine used before initialization."""
    code = "RSN-061"

    def __init__(self) -> None:
        super().__init__(
            "ReasoningEngine has not been initialized — call initialize() first"
        )
