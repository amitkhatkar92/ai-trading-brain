"""iios/execution/planning/planning_exceptions.py
Exception hierarchy for the Execution Planning & Smart Routing Engine.
All codes carry the EP- prefix.
"""
from __future__ import annotations


class PlanningIntelligenceError(Exception):
    """Root exception — EP-000."""

    code = "EP-000"

    def __init__(self, message: str = "Planning error", code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Plan (EP-010) ─────────────────────────────────────────────────────────────

class PlanError(PlanningIntelligenceError):
    code = "EP-010"


class PlanNotFoundError(PlanError):
    code = "EP-011"

    def __init__(self, message: str = "", *, plan_id: str = "") -> None:
        self.plan_id = plan_id
        super().__init__(message or f"Execution plan not found: {plan_id!r}")


class PlanAlreadyExistsError(PlanError):
    code = "EP-012"

    def __init__(self, message: str = "", *, plan_id: str = "") -> None:
        self.plan_id = plan_id
        super().__init__(message or f"Execution plan already exists: {plan_id!r}")


class PlanTerminalError(PlanError):
    code = "EP-013"

    def __init__(self, message: str = "", *, plan_id: str = "", status: str = "") -> None:
        self.plan_id = plan_id
        self.status  = status
        super().__init__(message or f"Plan {plan_id!r} is terminal (status={status!r})")


class PlanInvalidError(PlanError):
    code = "EP-014"

    def __init__(self, message: str = "", detail: str = "") -> None:
        super().__init__(message or f"Invalid execution plan: {detail}")


# ── Routing (EP-020) ──────────────────────────────────────────────────────────

class RoutingError(PlanningIntelligenceError):
    code = "EP-020"


class RouteNotFoundError(RoutingError):
    code = "EP-021"

    def __init__(self, message: str = "", *, route_id: str = "") -> None:
        self.route_id = route_id
        super().__init__(message or f"Route not found: {route_id!r}")


class RoutingFailedError(RoutingError):
    code = "EP-022"

    def __init__(self, message: str = "", reason: str = "") -> None:
        super().__init__(message or f"Routing failed: {reason}")


class NoSuitableVenueError(RoutingError):
    code = "EP-023"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "No suitable execution venue found")


# ── Policy (EP-030) ───────────────────────────────────────────────────────────

class PolicyError(PlanningIntelligenceError):
    code = "EP-030"


class PolicyViolationError(PolicyError):
    code = "EP-031"

    def __init__(self, message: str = "", *, policy_name: str = "") -> None:
        self.policy_name = policy_name
        super().__init__(message or f"Policy violation: {policy_name!r}")


class PolicyNotFoundError(PolicyError):
    code = "EP-032"

    def __init__(self, message: str = "", *, policy_id: str = "") -> None:
        self.policy_id = policy_id
        super().__init__(message or f"Policy not found: {policy_id!r}")


# ── Constraint (EP-040) ───────────────────────────────────────────────────────

class ConstraintError(PlanningIntelligenceError):
    code = "EP-040"


class ConstraintViolationError(ConstraintError):
    code = "EP-041"

    def __init__(self, message: str = "", *, constraint: str = "", value: float = 0.0) -> None:
        self.constraint = constraint
        self.value      = value
        super().__init__(message or f"Constraint {constraint!r} violated: {value:.4f}")


# ── Engine lifecycle (EP-050) ─────────────────────────────────────────────────

class PlanningEngineError(PlanningIntelligenceError):
    code = "EP-050"


class PlanningEngineNotInitializedError(PlanningEngineError):
    code = "EP-051"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Planning Engine is not initialized")


class PlanningEngineAlreadyRunningError(PlanningEngineError):
    code = "EP-052"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Planning Engine is already running")


# ── Registry (EP-060) ─────────────────────────────────────────────────────────

class PlanningRegistryError(PlanningIntelligenceError):
    code = "EP-060"


class PlanningRegistryOverflowError(PlanningRegistryError):
    code = "EP-061"

    def __init__(self, message: str = "", *, capacity: int = 0, current: int = 0) -> None:
        self.capacity = capacity
        self.current  = current
        super().__init__(message or f"Planning registry full (max={capacity})")


class PlanningRegistryItemNotFoundError(PlanningRegistryError):
    code = "EP-062"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        self.item_id = item_id
        super().__init__(message or f"Registry item not found: {item_id!r}")
