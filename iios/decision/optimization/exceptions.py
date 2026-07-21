"""
exceptions.py — iios.decision.optimization
============================================
Exception hierarchy for the Decision Optimization Framework.

Error codes: DO-000 through DO-009

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class DecisionOptimizationError(IIOSError):
    """Base exception for all optimization errors.  DO-000"""
    error_code = "DO-000"

    def __init__(self, message: str = "Decision optimization error", **_kw: object) -> None:
        super().__init__(message, code=self.error_code)


class OptimizationEngineNotRunningError(DecisionOptimizationError):
    """Raised when operating on a stopped engine.  DO-001"""
    error_code = "DO-001"

    def __init__(self, message: str = "Decision optimization engine is not running") -> None:
        super().__init__(message)


class NoCandidatesError(DecisionOptimizationError):
    """Raised when no candidates are provided for optimization.  DO-002"""
    error_code = "DO-002"

    def __init__(self, message: str = "No candidates available for optimization") -> None:
        super().__init__(message)


class NoFeasibleSolutionError(DecisionOptimizationError):
    """Raised when all candidates violate hard constraints.  DO-003"""
    error_code = "DO-003"

    def __init__(self, message: str = "No feasible solution found") -> None:
        super().__init__(message)


class ObjectiveNotFoundError(DecisionOptimizationError):
    """Raised when a referenced objective is not registered.  DO-004"""
    error_code = "DO-004"

    def __init__(self, objective_id: str = "") -> None:
        self.objective_id = objective_id
        super().__init__(f"Objective not found: {objective_id!r}")


class ConstraintNotFoundError(DecisionOptimizationError):
    """Raised when a referenced constraint is not registered.  DO-005"""
    error_code = "DO-005"

    def __init__(self, constraint_id: str = "") -> None:
        self.constraint_id = constraint_id
        super().__init__(f"Constraint not found: {constraint_id!r}")


class StrategyNotFoundError(DecisionOptimizationError):
    """Raised when a requested strategy is not registered.  DO-006"""
    error_code = "DO-006"

    def __init__(self, strategy_id: str = "") -> None:
        self.strategy_id = strategy_id
        super().__init__(f"Optimization strategy not found: {strategy_id!r}")


class OptimizationValidationError(DecisionOptimizationError):
    """Raised when optimization validation fails.  DO-007"""
    error_code = "DO-007"

    def __init__(
        self,
        message:      str          = "Optimization validation failed",
        failed_checks: tuple[str, ...] = (),
    ) -> None:
        self.failed_checks = tuple(failed_checks)
        super().__init__(message)


class CandidateRegistryError(DecisionOptimizationError):
    """Raised on candidate registry failures.  DO-008"""
    error_code = "DO-008"

    def __init__(self, message: str = "Candidate registry error") -> None:
        super().__init__(message)


class OptimizationConfigurationError(DecisionOptimizationError):
    """Raised when an objective, constraint, or strategy is misconfigured.  DO-009"""
    error_code = "DO-009"

    def __init__(self, message: str = "Optimization configuration error") -> None:
        super().__init__(message)
