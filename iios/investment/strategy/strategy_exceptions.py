"""iios/investment/strategy/strategy_exceptions.py
Exception hierarchy for the Strategy Intelligence Engine.
All error codes carry the SI- prefix.
"""
from __future__ import annotations


class StrategyIntelligenceError(Exception):
    """Root exception — SI-000."""

    code = "SI-000"

    def __init__(
        self,
        message: str = "Strategy intelligence error",
        code: str | None = None,
    ) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Strategy (SI-010) ─────────────────────────────────────────────────────────

class StrategyError(StrategyIntelligenceError):
    code = "SI-010"


class StrategyNotFoundError(StrategyError):
    code = "SI-011"

    def __init__(self, message: str = "", *, strategy_id: str = "") -> None:
        self.strategy_id = strategy_id
        super().__init__(message or f"Strategy not found: {strategy_id!r}")


class StrategyAlreadyExistsError(StrategyError):
    code = "SI-012"

    def __init__(self, message: str = "", *, strategy_id: str = "") -> None:
        self.strategy_id = strategy_id
        super().__init__(message or f"Strategy already registered: {strategy_id!r}")


class StrategyInvalidError(StrategyError):
    code = "SI-013"

    def __init__(self, message: str = "", detail: str = "") -> None:
        super().__init__(message or f"Invalid strategy: {detail}")


# ── Registry (SI-020) ─────────────────────────────────────────────────────────

class StrategyRegistryError(StrategyIntelligenceError):
    code = "SI-020"


class StrategyRegistryOverflowError(StrategyRegistryError):
    code = "SI-021"

    def __init__(self, message: str = "", *, capacity: int = 0, current: int = 0) -> None:
        self.capacity = capacity
        self.current  = current
        super().__init__(message or f"Strategy registry full (max={capacity})")


class StrategyRegistryItemNotFoundError(StrategyRegistryError):
    code = "SI-022"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        self.item_id = item_id
        super().__init__(message or f"Registry item not found: {item_id!r}")


class StrategyRegistryItemAlreadyExistsError(StrategyRegistryError):
    code = "SI-023"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        self.item_id = item_id
        super().__init__(message or f"Registry item already exists: {item_id!r}")


# ── Evaluation (SI-030) ───────────────────────────────────────────────────────

class StrategyEvaluationError(StrategyIntelligenceError):
    code = "SI-030"


class StrategyEvaluationDataInsufficientError(StrategyEvaluationError):
    code = "SI-031"

    def __init__(self, message: str = "", *, required: int = 0, actual: int = 0) -> None:
        self.required = required
        self.actual   = actual
        super().__init__(message or f"Insufficient data for evaluation (required={required}, actual={actual})")


class StrategyEvaluationFailedError(StrategyEvaluationError):
    code = "SI-032"

    def __init__(self, message: str = "", reason: str = "") -> None:
        super().__init__(message or f"Strategy evaluation failed: {reason}")


# ── Selection (SI-040) ────────────────────────────────────────────────────────

class StrategySelectionError(StrategyIntelligenceError):
    code = "SI-040"


class NoStrategiesAvailableError(StrategySelectionError):
    code = "SI-041"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "No strategies available for selection")


class StrategySelectionFailedError(StrategySelectionError):
    code = "SI-042"

    def __init__(self, message: str = "", reason: str = "") -> None:
        super().__init__(message or f"Strategy selection failed: {reason}")


# ── Adaptation (SI-050) ───────────────────────────────────────────────────────

class StrategyAdaptationError(StrategyIntelligenceError):
    code = "SI-050"


class StrategyAdaptationFailedError(StrategyAdaptationError):
    code = "SI-051"

    def __init__(self, message: str = "", reason: str = "") -> None:
        super().__init__(message or f"Strategy adaptation failed: {reason}")


# ── Lifecycle (SI-060) ────────────────────────────────────────────────────────

class StrategyLifecycleError(StrategyIntelligenceError):
    code = "SI-060"


class StrategyLifecycleInvalidTransitionError(StrategyLifecycleError):
    code = "SI-061"

    def __init__(
        self,
        message: str = "",
        *,
        from_status: str = "",
        to_status: str = "",
    ) -> None:
        self.from_status = from_status
        self.to_status   = to_status
        super().__init__(
            message or f"Invalid lifecycle transition: {from_status!r} → {to_status!r}"
        )


class StrategyLifecycleBlockedError(StrategyLifecycleError):
    code = "SI-062"

    def __init__(self, message: str = "", reason: str = "") -> None:
        super().__init__(message or f"Lifecycle transition blocked: {reason}")


# ── Engine (SI-070) ───────────────────────────────────────────────────────────

class StrategyEngineError(StrategyIntelligenceError):
    code = "SI-070"


class StrategyEngineNotInitializedError(StrategyEngineError):
    code = "SI-071"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Strategy Intelligence Engine is not initialized")


class StrategyEngineAlreadyRunningError(StrategyEngineError):
    code = "SI-072"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Strategy Intelligence Engine is already running")
