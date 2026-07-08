"""
iios/decisions/decision_exceptions.py
======================================
Exception hierarchy for the Decision Engine Core.
Error-code prefix: DE-
"""
from __future__ import annotations


class DecisionEngineError(Exception):
    """Root exception for all Decision Engine errors.  DE-000"""
    code = "DE-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Decision errors (DE-01x) ──────────────────────────────────────────────────

class DecisionError(DecisionEngineError):
    """Base decision lifecycle error.  DE-010"""
    code = "DE-010"


class DecisionNotFoundError(DecisionError):
    """Decision not in registry.  DE-011"""
    code = "DE-011"

    def __init__(self, decision_id: str) -> None:
        super().__init__(f"Decision not found: {decision_id!r}")


class DecisionAlreadyExistsError(DecisionError):
    """Duplicate decision ID.  DE-012"""
    code = "DE-012"

    def __init__(self, decision_id: str) -> None:
        super().__init__(f"Decision already exists: {decision_id!r}")


class DecisionExpiredError(DecisionError):
    """Decision TTL exceeded.  DE-013"""
    code = "DE-013"

    def __init__(self, decision_id: str) -> None:
        super().__init__(f"Decision expired: {decision_id!r}")


class DecisionCancelledError(DecisionError):
    """Attempt to operate on a cancelled decision.  DE-014"""
    code = "DE-014"

    def __init__(self, decision_id: str) -> None:
        super().__init__(f"Decision cancelled: {decision_id!r}")


# ── Request errors (DE-02x) ───────────────────────────────────────────────────

class DecisionRequestError(DecisionEngineError):
    """Base request validation error.  DE-020"""
    code = "DE-020"


class InvalidDecisionRequestError(DecisionRequestError):
    """Request fails structural validation.  DE-021"""
    code = "DE-021"

    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid decision request: {reason}")


class MissingDecisionContextError(DecisionRequestError):
    """Required context is absent.  DE-022"""
    code = "DE-022"

    def __init__(self, field: str) -> None:
        super().__init__(f"Missing required context field: {field!r}")


# ── Policy errors (DE-03x) ────────────────────────────────────────────────────

class PolicyError(DecisionEngineError):
    """Base policy error.  DE-030"""
    code = "DE-030"


class PolicyViolationError(PolicyError):
    """A mandatory policy was violated.  DE-031"""
    code = "DE-031"

    def __init__(self, policy_name: str, reason: str = "") -> None:
        super().__init__(f"Policy {policy_name!r} violated: {reason}")


class NoPoliciesDefinedError(PolicyError):
    """No policies registered when at least one is required.  DE-032"""
    code = "DE-032"

    def __init__(self) -> None:
        super().__init__("No decision policies are registered")


class PolicyConflictError(PolicyError):
    """Policies produced contradictory outcomes.  DE-033"""
    code = "DE-033"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Policy conflict: {detail}")


# ── Evaluation errors (DE-04x) ────────────────────────────────────────────────

class EvaluationError(DecisionEngineError):
    """Base candidate evaluation error.  DE-040"""
    code = "DE-040"


class NoCandidatesError(EvaluationError):
    """No candidates generated from the request.  DE-041"""
    code = "DE-041"

    def __init__(self, request_id: str) -> None:
        super().__init__(f"No decision candidates for request {request_id!r}")


class EvaluationFailedError(EvaluationError):
    """Evaluation pipeline could not complete.  DE-042"""
    code = "DE-042"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Evaluation failed: {detail}")


class ScoringError(EvaluationError):
    """Score computation error.  DE-043"""
    code = "DE-043"

    def __init__(self, candidate_id: str, detail: str) -> None:
        super().__init__(f"Scoring failed for {candidate_id!r}: {detail}")


# ── Workflow errors (DE-05x) ──────────────────────────────────────────────────

class WorkflowError(DecisionEngineError):
    """Base workflow error.  DE-050"""
    code = "DE-050"


class WorkflowStageFailedError(WorkflowError):
    """A specific workflow stage failed.  DE-051"""
    code = "DE-051"

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"Workflow stage {stage!r} failed: {detail}")


class WorkflowAbortedError(WorkflowError):
    """Entire workflow was aborted.  DE-052"""
    code = "DE-052"

    def __init__(self, request_id: str, reason: str) -> None:
        super().__init__(f"Workflow aborted for {request_id!r}: {reason}")


# ── Registry errors (DE-06x) ──────────────────────────────────────────────────

class RegistryError(DecisionEngineError):
    """Base registry error.  DE-060"""
    code = "DE-060"


class RegistryOverflowError(RegistryError):
    """Registry capacity exceeded.  DE-061"""
    code = "DE-061"

    def __init__(self, limit: int) -> None:
        super().__init__(f"Decision registry capacity {limit} exceeded")


# ── Engine lifecycle errors (DE-07x) ─────────────────────────────────────────

class EngineLifecycleError(DecisionEngineError):
    """Base engine lifecycle error.  DE-070"""
    code = "DE-070"


class EngineNotInitializedError(EngineLifecycleError):
    """Engine called before initialize().  DE-071"""
    code = "DE-071"

    def __init__(self) -> None:
        super().__init__("Decision engine has not been initialized; call initialize() first")


class EngineAlreadyRunningError(EngineLifecycleError):
    """initialize() called while engine is already running.  DE-072"""
    code = "DE-072"

    def __init__(self) -> None:
        super().__init__("Decision engine is already running")
