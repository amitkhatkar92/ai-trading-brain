"""
iios/infrastructure/cache/cache_exceptions.py
==============================================
Exception hierarchy for the IIOS Distributed Caching Framework.
Extends the base CacheError from infrastructure_exceptions.
"""

from __future__ import annotations

from typing import Any, Optional

from ..infrastructure_exceptions import CacheError

__all__ = [
    "CacheError",
    "CacheMissError",
    "CacheFullError",
    "CacheExpiredError",
    "CacheSerializationError",
    "CacheDeserializationError",
    "CacheCompressionError",
    "CacheProviderError",
    "CacheProviderUnavailableError",
    "CacheSyncError",
    "CacheRegionError",
    "CacheRegionNotFoundError",
    "CacheKeyError",
    "CacheKeyTooLongError",
    "CacheConfigError",
    "CacheBulkError",
    "CacheInvalidationError",
    "CacheVersionConflictError",
]


class CacheMissError(CacheError):
    """Key does not exist in any cache level."""

    def __init__(self, key: str, region: str = "") -> None:
        msg = f"Cache miss: '{key}'" + (f" in region '{region}'" if region else "")
        super().__init__(msg, code="CACHE-001", context={"key": key, "region": region})
        self.key = key
        self.region = region


class CacheFullError(CacheError):
    """Cache capacity exceeded and eviction could not free space."""

    def __init__(self, region: str = "", capacity: int = 0) -> None:
        super().__init__(
            f"Cache full: region='{region}' capacity={capacity}",
            code="CACHE-002",
            context={"region": region, "capacity": capacity},
        )


class CacheExpiredError(CacheError):
    """Entry exists but has expired (for callers that need to distinguish miss vs expired)."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Cache entry expired: '{key}'", code="CACHE-003", context={"key": key})
        self.key = key


class CacheSerializationError(CacheError):
    """Failed to serialize a cache value."""

    def __init__(self, key: str, reason: str = "") -> None:
        super().__init__(
            f"Serialization failed for '{key}': {reason}",
            code="CACHE-004",
            context={"key": key, "reason": reason},
        )


class CacheDeserializationError(CacheError):
    """Failed to deserialize a cached value."""

    def __init__(self, key: str, reason: str = "") -> None:
        super().__init__(
            f"Deserialization failed for '{key}': {reason}",
            code="CACHE-005",
            context={"key": key, "reason": reason},
        )


class CacheCompressionError(CacheError):
    """Compression or decompression failed."""

    def __init__(self, key: str, reason: str = "") -> None:
        super().__init__(
            f"Compression error for '{key}': {reason}",
            code="CACHE-006",
            context={"key": key},
        )


class CacheProviderError(CacheError):
    """A cache provider encountered a runtime error."""

    def __init__(self, provider: str, reason: str = "") -> None:
        super().__init__(
            f"Provider '{provider}' error: {reason}",
            code="CACHE-007",
            context={"provider": provider},
        )


class CacheProviderUnavailableError(CacheProviderError):
    """Cache provider is temporarily unavailable (e.g., Redis down)."""


class CacheSyncError(CacheError):
    """Cross-level or distributed synchronization failed."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Cache sync failed: {reason}", code="CACHE-008")


class CacheRegionError(CacheError):
    """Generic region-related error."""


class CacheRegionNotFoundError(CacheRegionError):
    """Named cache region is not registered."""

    def __init__(self, region: str) -> None:
        super().__init__(
            f"Cache region not found: '{region}'",
            code="CACHE-009",
            context={"region": region},
        )
        self.region = region


class CacheKeyError(CacheError):
    """Invalid cache key format."""


class CacheKeyTooLongError(CacheKeyError):
    """Cache key exceeds maximum allowed length."""

    def __init__(self, key: str, max_len: int) -> None:
        super().__init__(
            f"Key length {len(key)} exceeds maximum {max_len}",
            code="CACHE-010",
            context={"key_len": len(key), "max_len": max_len},
        )


class CacheConfigError(CacheError):
    """Invalid cache configuration."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid cache config: {reason}", code="CACHE-011")


class CacheBulkError(CacheError):
    """One or more bulk operations failed."""

    def __init__(self, total: int, failed: int, errors: list[str]) -> None:
        super().__init__(
            f"Bulk cache error: {failed}/{total} failed",
            code="CACHE-012",
            context={"total": total, "failed": failed, "errors": errors},
        )
        self.total = total
        self.failed = failed
        self.errors = errors


class CacheInvalidationError(CacheError):
    """Cache invalidation failed for one or more keys."""

    def __init__(self, tag: str, reason: str = "") -> None:
        super().__init__(
            f"Invalidation failed for tag '{tag}': {reason}",
            code="CACHE-013",
            context={"tag": tag},
        )


class CacheVersionConflictError(CacheError):
    """Optimistic concurrency conflict — version mismatch on update."""

    def __init__(self, key: str, expected: int, actual: int) -> None:
        super().__init__(
            f"Version conflict for '{key}': expected {expected}, got {actual}",
            code="CACHE-014",
            context={"key": key, "expected": expected, "actual": actual},
        )
        self.key = key
        self.expected = expected
        self.actual = actual
