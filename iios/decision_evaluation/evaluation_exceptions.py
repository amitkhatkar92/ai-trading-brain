"""iios/decision_evaluation/evaluation_exceptions.py — Error hierarchy. Prefix: EE-"""
from __future__ import annotations


class EvaluationEngineError(Exception):
    code: str = "EE-000"

    def __init__(self, message: str, code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Evaluation ────────────────────────────────────────────────────────────────

class EvaluationError(EvaluationEngineError):
    code = "EE-010"

class EvaluationNotFoundError(EvaluationError):
    code = "EE-011"
    def __init__(self, eval_id: str) -> None:
        super().__init__(f"Evaluation not found: {eval_id!r}", self.code)

class EvaluationAlreadyExistsError(EvaluationError):
    code = "EE-012"
    def __init__(self, eval_id: str) -> None:
        super().__init__(f"Evaluation already exists: {eval_id!r}", self.code)

class EvaluationFailedError(EvaluationError):
    code = "EE-013"


# ── Criteria ──────────────────────────────────────────────────────────────────

class CriterionError(EvaluationEngineError):
    code = "EE-020"

class CriterionNotFoundError(CriterionError):
    code = "EE-021"
    def __init__(self, criterion_id: str) -> None:
        super().__init__(f"Criterion not found: {criterion_id!r}", self.code)

class CriterionAlreadyExistsError(CriterionError):
    code = "EE-022"
    def __init__(self, criterion_id: str) -> None:
        super().__init__(f"Criterion already exists: {criterion_id!r}", self.code)

class InvalidCriterionError(CriterionError):
    code = "EE-023"

class CriterionScoringError(CriterionError):
    code = "EE-024"
    def __init__(self, criterion_id: str, reason: str) -> None:
        super().__init__(f"Criterion {criterion_id!r} scoring failed: {reason}", self.code)


# ── Scoring ───────────────────────────────────────────────────────────────────

class ScoringError(EvaluationEngineError):
    code = "EE-030"

class NormalizationError(ScoringError):
    code = "EE-031"

class AggregationError(ScoringError):
    code = "EE-032"

class InsufficientDataError(ScoringError):
    code = "EE-033"
    def __init__(self, reason: str) -> None:
        super().__init__(f"Insufficient data: {reason}", self.code)


# ── Ranking ───────────────────────────────────────────────────────────────────

class RankingError(EvaluationEngineError):
    code = "EE-040"

class RankingAlgorithmNotFoundError(RankingError):
    code = "EE-041"
    def __init__(self, name: str) -> None:
        super().__init__(f"Ranking algorithm not found: {name!r}", self.code)

class RankingFailedError(RankingError):
    code = "EE-042"


# ── Trade-off ─────────────────────────────────────────────────────────────────

class TradeoffError(EvaluationEngineError):
    code = "EE-050"

class TradeoffAnalysisFailedError(TradeoffError):
    code = "EE-051"

class UtilityFunctionError(TradeoffError):
    code = "EE-052"


# ── Weights ───────────────────────────────────────────────────────────────────

class WeightError(EvaluationEngineError):
    code = "EE-060"

class InvalidWeightError(WeightError):
    code = "EE-061"
    def __init__(self, criterion_id: str, weight: float) -> None:
        super().__init__(f"Invalid weight {weight} for criterion {criterion_id!r}", self.code)

class WeightSumError(WeightError):
    code = "EE-062"
    def __init__(self, total: float) -> None:
        super().__init__(f"Weights sum to {total:.4f}, expected 1.0", self.code)


# ── Alternatives ──────────────────────────────────────────────────────────────

class AlternativeError(EvaluationEngineError):
    code = "EE-070"

class AlternativeNotFoundError(AlternativeError):
    code = "EE-071"
    def __init__(self, alt_id: str) -> None:
        super().__init__(f"Alternative not found: {alt_id!r}", self.code)

class InsufficientAlternativesError(AlternativeError):
    code = "EE-072"
    def __init__(self, found: int, required: int = 1) -> None:
        super().__init__(f"Need >= {required} alternative(s), found {found}", self.code)


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class EngineLifecycleError(EvaluationEngineError):
    code = "EE-080"

class EngineNotInitializedError(EngineLifecycleError):
    code = "EE-081"
    def __init__(self) -> None:
        super().__init__("Evaluation engine is not initialized", self.code)

class EngineAlreadyRunningError(EngineLifecycleError):
    code = "EE-082"
    def __init__(self) -> None:
        super().__init__("Evaluation engine is already running", self.code)


# ── Registry ──────────────────────────────────────────────────────────────────

class RegistryError(EvaluationEngineError):
    code = "EE-090"

class RegistryOverflowError(RegistryError):
    code = "EE-091"
    def __init__(self, limit: int) -> None:
        super().__init__(f"Registry limit exceeded: {limit}", self.code)
