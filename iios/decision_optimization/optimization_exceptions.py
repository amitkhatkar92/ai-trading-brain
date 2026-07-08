"""iios/decision_optimization/optimization_exceptions.py — Error hierarchy. Prefix: OE-"""
from __future__ import annotations


class OptimizationEngineError(Exception):
    code: str = "OE-000"

    def __init__(self, message: str, code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Optimization ──────────────────────────────────────────────────────────────

class OptimizationError(OptimizationEngineError):
    code = "OE-010"

class OptimizationNotFoundError(OptimizationError):
    code = "OE-011"
    def __init__(self, opt_id: str) -> None:
        super().__init__(f"Optimization not found: {opt_id!r}", self.code)

class OptimizationAlreadyExistsError(OptimizationError):
    code = "OE-012"
    def __init__(self, opt_id: str) -> None:
        super().__init__(f"Optimization already exists: {opt_id!r}", self.code)

class OptimizationFailedError(OptimizationError):
    code = "OE-013"


# ── Objectives ────────────────────────────────────────────────────────────────

class ObjectiveError(OptimizationEngineError):
    code = "OE-020"

class ObjectiveNotFoundError(ObjectiveError):
    code = "OE-021"
    def __init__(self, objective_id: str) -> None:
        super().__init__(f"Objective not found: {objective_id!r}", self.code)

class ObjectiveAlreadyExistsError(ObjectiveError):
    code = "OE-022"
    def __init__(self, objective_id: str) -> None:
        super().__init__(f"Objective already exists: {objective_id!r}", self.code)

class InvalidObjectiveError(ObjectiveError):
    code = "OE-023"

class ObjectiveEvaluationError(ObjectiveError):
    code = "OE-024"
    def __init__(self, objective_id: str, reason: str) -> None:
        super().__init__(f"Objective {objective_id!r} evaluation failed: {reason}", self.code)


# ── Constraints ───────────────────────────────────────────────────────────────

class ConstraintError(OptimizationEngineError):
    code = "OE-030"

class ConstraintNotFoundError(ConstraintError):
    code = "OE-031"
    def __init__(self, constraint_id: str) -> None:
        super().__init__(f"Constraint not found: {constraint_id!r}", self.code)

class ConstraintAlreadyExistsError(ConstraintError):
    code = "OE-032"
    def __init__(self, constraint_id: str) -> None:
        super().__init__(f"Constraint already exists: {constraint_id!r}", self.code)

class ConstraintViolationError(ConstraintError):
    code = "OE-033"
    def __init__(self, constraint_id: str, candidate_id: str) -> None:
        super().__init__(f"Constraint {constraint_id!r} violated by {candidate_id!r}", self.code)

class InfeasibleSolutionError(ConstraintError):
    code = "OE-034"
    def __init__(self, reason: str = "no feasible candidate") -> None:
        super().__init__(f"Infeasible: {reason}", self.code)


# ── Algorithms ────────────────────────────────────────────────────────────────

class AlgorithmError(OptimizationEngineError):
    code = "OE-040"

class AlgorithmNotFoundError(AlgorithmError):
    code = "OE-041"
    def __init__(self, algorithm_id: str) -> None:
        super().__init__(f"Algorithm not found: {algorithm_id!r}", self.code)

class AlgorithmExecutionError(AlgorithmError):
    code = "OE-042"

class UnsupportedAlgorithmError(AlgorithmError):
    code = "OE-043"
    def __init__(self, algorithm_type: str) -> None:
        super().__init__(f"Unsupported algorithm type: {algorithm_type!r}", self.code)


# ── Simulation ────────────────────────────────────────────────────────────────

class SimulationError(OptimizationEngineError):
    code = "OE-050"

class SimulationFailedError(SimulationError):
    code = "OE-051"

class ScenarioNotFoundError(SimulationError):
    code = "OE-052"
    def __init__(self, scenario_id: str) -> None:
        super().__init__(f"Scenario not found: {scenario_id!r}", self.code)


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class EngineLifecycleError(OptimizationEngineError):
    code = "OE-060"

class EngineNotInitializedError(EngineLifecycleError):
    code = "OE-061"
    def __init__(self) -> None:
        super().__init__("Optimization engine is not initialized", self.code)

class EngineAlreadyRunningError(EngineLifecycleError):
    code = "OE-062"
    def __init__(self) -> None:
        super().__init__("Optimization engine is already running", self.code)


# ── Registry ──────────────────────────────────────────────────────────────────

class RegistryError(OptimizationEngineError):
    code = "OE-070"

class RegistryOverflowError(RegistryError):
    code = "OE-071"
    def __init__(self, limit: int) -> None:
        super().__init__(f"Registry limit exceeded: {limit}", self.code)


# ── Candidates ────────────────────────────────────────────────────────────────

class CandidateError(OptimizationEngineError):
    code = "OE-080"

class CandidateNotFoundError(CandidateError):
    code = "OE-081"
    def __init__(self, candidate_id: str) -> None:
        super().__init__(f"Candidate not found: {candidate_id!r}", self.code)

class InsufficientCandidatesError(CandidateError):
    code = "OE-082"
    def __init__(self, found: int, required: int = 1) -> None:
        super().__init__(f"Need >= {required} candidate(s), found {found}", self.code)
