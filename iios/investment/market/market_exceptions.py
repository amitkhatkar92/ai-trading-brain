"""iios/investment/market/market_exceptions.py
Exception hierarchy for the Market Intelligence Engine.
All codes carry the MI- prefix.
"""
from __future__ import annotations


class MarketIntelligenceError(Exception):
    """Root exception — MI-000."""

    code = "MI-000"

    def __init__(
        self,
        message: str = "Market intelligence error",
        code: str | None = None,
    ) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Market State (MI-010) ─────────────────────────────────────────────────────

class MarketStateError(MarketIntelligenceError):
    code = "MI-010"


class MarketStateNotFoundError(MarketStateError):
    code = "MI-011"

    def __init__(self, market_id: str = "") -> None:
        super().__init__(f"Market state not found: {market_id!r}")


class MarketStateAlreadyExistsError(MarketStateError):
    code = "MI-012"

    def __init__(self, market_id: str = "") -> None:
        super().__init__(f"Market state already exists: {market_id!r}")


class MarketStateTransitionError(MarketStateError):
    code = "MI-013"

    def __init__(self, from_status: str = "", to_status: str = "") -> None:
        super().__init__(f"Invalid state transition: {from_status!r} → {to_status!r}")


# ── Regime (MI-020) ───────────────────────────────────────────────────────────

class RegimeError(MarketIntelligenceError):
    code = "MI-020"


class RegimeNotFoundError(RegimeError):
    code = "MI-021"

    def __init__(self, market_id: str = "") -> None:
        super().__init__(f"Regime not found for market: {market_id!r}")


class RegimeInvalidError(RegimeError):
    code = "MI-022"

    def __init__(self, regime: str = "") -> None:
        super().__init__(f"Invalid regime: {regime!r}")


class RegimeTransitionError(RegimeError):
    code = "MI-023"

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Regime transition error: {detail}")


# ── Snapshot (MI-030) ─────────────────────────────────────────────────────────

class SnapshotError(MarketIntelligenceError):
    code = "MI-030"


class SnapshotNotFoundError(SnapshotError):
    code = "MI-031"

    def __init__(self, key: str = "") -> None:
        super().__init__(f"Snapshot not found: {key!r}")


class SnapshotStaleError(SnapshotError):
    code = "MI-032"

    def __init__(self, age_sec: float = 0.0) -> None:
        super().__init__(f"Snapshot is stale (age={age_sec:.1f}s)")


class SnapshotInvalidError(SnapshotError):
    code = "MI-033"

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Invalid snapshot: {detail}")


# ── Analysis (MI-040) ─────────────────────────────────────────────────────────

class MarketAnalysisError(MarketIntelligenceError):
    code = "MI-040"


class MarketAnalysisFailedError(MarketAnalysisError):
    code = "MI-041"

    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Market analysis failed: {reason}")


class MarketAnalysisTimeoutError(MarketAnalysisError):
    code = "MI-042"

    def __init__(self, timeout_sec: float = 0.0) -> None:
        super().__init__(f"Market analysis timed out after {timeout_sec:.1f}s")


# ── Engine Lifecycle (MI-050) ─────────────────────────────────────────────────

class MarketEngineError(MarketIntelligenceError):
    code = "MI-050"


class MarketEngineNotInitializedError(MarketEngineError):
    code = "MI-051"

    def __init__(self) -> None:
        super().__init__("Market Intelligence Engine is not initialized")


class MarketEngineAlreadyRunningError(MarketEngineError):
    code = "MI-052"

    def __init__(self) -> None:
        super().__init__("Market Intelligence Engine is already running")


# ── Registry (MI-060) ─────────────────────────────────────────────────────────

class MarketRegistryError(MarketIntelligenceError):
    code = "MI-060"


class MarketRegistryItemNotFoundError(MarketRegistryError):
    code = "MI-061"

    def __init__(self, key: str = "") -> None:
        super().__init__(f"Registry item not found: {key!r}")


class MarketRegistryItemAlreadyExistsError(MarketRegistryError):
    code = "MI-062"

    def __init__(self, key: str = "") -> None:
        super().__init__(f"Registry item already exists: {key!r}")


class MarketRegistryOverflowError(MarketRegistryError):
    code = "MI-063"

    def __init__(self, max_size: int = 0) -> None:
        super().__init__(f"Registry capacity exceeded (max={max_size})")


# ── Data (MI-070) ─────────────────────────────────────────────────────────────

class MarketDataError(MarketIntelligenceError):
    code = "MI-070"


class MarketDataMissingError(MarketDataError):
    code = "MI-071"

    def __init__(self, field: str = "") -> None:
        super().__init__(f"Market data missing: {field!r}")


class MarketDataInvalidError(MarketDataError):
    code = "MI-072"

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Invalid market data: {detail}")


class MarketDataStaleError(MarketDataError):
    code = "MI-073"

    def __init__(self, age_sec: float = 0.0) -> None:
        super().__init__(f"Market data is stale (age={age_sec:.1f}s)")
