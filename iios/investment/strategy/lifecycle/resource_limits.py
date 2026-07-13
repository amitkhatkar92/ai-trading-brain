"""iios/investment/strategy/lifecycle/resource_limits.py
Resource ceiling definitions for the strategy runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResourceProfile(str, Enum):
    """Pre-defined resource limit profiles for common deployment scenarios."""

    MINIMAL    = "minimal"
    STANDARD   = "standard"
    AGGRESSIVE = "aggressive"
    UNLIMITED  = "unlimited"


@dataclass(frozen=True)
class ResourceLimits:
    """
    Immutable resource ceiling configuration.

    A zero (0 / 0.0) value means "unlimited" for all numeric limits.
    """

    max_concurrent_strategies: int = 32
    max_thread_pool_workers: int = 64
    max_queue_depth: int = 10_000
    max_memory_mb: int = 0             # 0 = unlimited
    cpu_weight_limit: float = 0.0      # 0.0 = unlimited; 1.0 = 100% of one core
    max_execution_time_s: float = 300.0  # per-strategy wall-clock timeout
    max_retries_per_strategy: int = 3
    max_restarts_per_strategy: int = 5

    # Admission control: reject new strategies above this utilisation fraction
    admission_threshold: float = 0.90   # 90 %

    # ── Named profiles ────────────────────────────────────────────────────────

    @classmethod
    def minimal(cls) -> "ResourceLimits":
        return cls(
            max_concurrent_strategies=4,
            max_thread_pool_workers=8,
            max_queue_depth=100,
            max_execution_time_s=60.0,
        )

    @classmethod
    def standard(cls) -> "ResourceLimits":
        return cls()

    @classmethod
    def aggressive(cls) -> "ResourceLimits":
        return cls(
            max_concurrent_strategies=256,
            max_thread_pool_workers=512,
            max_queue_depth=50_000,
            max_execution_time_s=600.0,
            max_retries_per_strategy=5,
            max_restarts_per_strategy=10,
        )

    @classmethod
    def unlimited(cls) -> "ResourceLimits":
        return cls(
            max_concurrent_strategies=0,
            max_thread_pool_workers=0,
            max_queue_depth=0,
            max_memory_mb=0,
            cpu_weight_limit=0.0,
            max_execution_time_s=0.0,
        )

    def is_unlimited_field(self, value: float) -> bool:
        """True if the given field value represents "no limit"."""
        return value == 0 or value == 0.0
