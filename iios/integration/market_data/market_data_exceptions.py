"""iios/integration/market_data/market_data_exceptions.py

Exception hierarchy for the Market Data Provider Framework.
Error code prefix: MD-
"""
from __future__ import annotations


class MarketDataError(Exception):
    """Root exception for all Market Data Framework errors. [MD-000]"""

    def __init__(self, message: str, code: str = "MD-000") -> None:
        super().__init__(message)
        self.code    = code
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self.message})"


# ── Provider errors ───────────────────────────────────────────────────────────

class ProviderConnectionError(MarketDataError):
    """Cannot establish connection to provider. [MD-011]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-011")


class ProviderAuthenticationError(MarketDataError):
    """Provider authentication failed. [MD-012]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-012")


class ProviderNotConnectedError(MarketDataError):
    """Operation attempted before provider is connected. [MD-013]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-013")


class ProviderAlreadyConnectedError(MarketDataError):
    """Provider is already connected. [MD-014]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-014")


class MarketDataProviderNotFoundError(MarketDataError):
    """Provider not registered. [MD-015]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-015")


class MarketDataProviderAlreadyRegisteredError(MarketDataError):
    """Provider already registered under the same ID. [MD-016]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-016")


class NoProviderForSymbolError(MarketDataError):
    """No active provider can supply data for the requested symbol. [MD-017]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-017")


# ── Subscription errors ───────────────────────────────────────────────────────

class SubscriptionError(MarketDataError):
    """Base class for subscription errors. [MD-020]"""
    def __init__(self, message: str, code: str = "MD-020") -> None:
        super().__init__(message, code)


class SubscriptionNotFoundError(SubscriptionError):
    """Subscription not found. [MD-021]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-021")


class SubscriptionLimitExceededError(SubscriptionError):
    """Maximum subscriptions per provider reached. [MD-022]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-022")


class SubscriptionCapacityError(SubscriptionError):
    """Global subscription capacity exhausted. [MD-023]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-023")


# ── Streaming errors ──────────────────────────────────────────────────────────

class StreamError(MarketDataError):
    """Base class for streaming errors. [MD-030]"""
    def __init__(self, message: str, code: str = "MD-030") -> None:
        super().__init__(message, code)


class StreamBufferOverflowError(StreamError):
    """Stream buffer is full — producer is too fast for consumer. [MD-031]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-031")


class StreamNotActiveError(StreamError):
    """No active stream for the requested symbol/type. [MD-032]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-032")


# ── Data errors ───────────────────────────────────────────────────────────────

class MarketDataValidationError(MarketDataError):
    """Market data record failed validation. [MD-040]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-040")


class InstrumentNotFoundError(MarketDataError):
    """Symbol / instrument not found in this provider. [MD-041]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-041")


class HistoricalDataNotAvailableError(MarketDataError):
    """Historical data for the requested period is unavailable. [MD-042]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-042")


# ── Engine errors ─────────────────────────────────────────────────────────────

class MarketDataEngineNotRunningError(MarketDataError):
    """Engine called before start(). [MD-050]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-050")


class MarketDataEngineAlreadyRunningError(MarketDataError):
    """Engine.start() called while already running. [MD-051]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-051")


class MarketDataRegistryError(MarketDataError):
    """Registry inconsistency. [MD-060]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "MD-060")
