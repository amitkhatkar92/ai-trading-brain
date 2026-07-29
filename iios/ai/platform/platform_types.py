"""
platform_types.py — iios.ai.platform
======================================
Domain types for the IIOS AI Platform Bootstrap.

Immutable frozen dataclasses throughout, consistent with the AI Platform
coding convention established in A1–A10.

F0.1 Critical Architecture Resolution — R-001 Platform Bootstrap
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Phase
# ─────────────────────────────────────────────────────────────────────────────

class PlatformPhase(str, Enum):
    """Lifecycle phase of a registered platform."""
    REGISTERED = "registered"
    STARTING   = "starting"
    RUNNING    = "running"
    STOPPING   = "stopping"
    STOPPED    = "stopped"
    FAILED     = "failed"

    def is_terminal(self) -> bool:
        """True if the platform has reached a final non-recoverable state."""
        return self in (PlatformPhase.STOPPED, PlatformPhase.FAILED)

    def is_active(self) -> bool:
        """True if the platform is currently serving requests."""
        return self == PlatformPhase.RUNNING


# ─────────────────────────────────────────────────────────────────────────────
# Dependency
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlatformDependency:
    """Explicit declaration that one platform depends on another."""
    dependent_id:  str   # platform that depends on another
    dependency_id: str   # platform that must be running first


# ─────────────────────────────────────────────────────────────────────────────
# Descriptor
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlatformDescriptor:
    """
    Immutable description of a platform or module that participates in
    bootstrap lifecycle management.

    Attributes
    ----------
    platform_id:
        Unique stable identifier.  Convention: ``"A1:foundation"``,
        ``"A2:model_management"``, etc.
    name:
        Human-readable display name.
    version:
        Module version string (semver).
    dependencies:
        Frozenset of ``platform_id`` values that must reach
        ``PlatformPhase.RUNNING`` before this platform starts.
    priority:
        Within a resolved dependency batch, platforms with higher
        priority start first.  Default 100.
    optional:
        If ``True``, startup failure is logged but does not abort
        dependent platforms or the overall bootstrap.
    metadata:
        Arbitrary key-value pairs for documentation or tooling.
    """
    platform_id:  str
    name:         str
    version:      str
    dependencies: FrozenSet[str]
    priority:     int
    optional:     bool
    metadata:     FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        platform_id:  str,
        name:         str              = "",
        version:      str              = "1.0.0",
        dependencies: FrozenSet[str]   = frozenset(),
        priority:     int              = 100,
        optional:     bool             = False,
        **metadata:   Any,
    ) -> "PlatformDescriptor":
        return cls(
            platform_id  = platform_id,
            name         = name or platform_id,
            version      = version,
            dependencies = frozenset(dependencies),
            priority     = priority,
            optional     = optional,
            metadata     = frozenset(metadata.items()),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Startup result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlatformStartupResult:
    """
    Immutable result of a single platform startup or shutdown operation.
    """
    platform_id:  str
    phase:        PlatformPhase
    elapsed_ms:   float
    error:        Optional[str]

    @property
    def succeeded(self) -> bool:
        return self.phase == PlatformPhase.RUNNING

    @property
    def failed(self) -> bool:
        return self.phase == PlatformPhase.FAILED

    # ── factories ─────────────────────────────────────────────────────────────

    @classmethod
    def success(
        cls, platform_id: str, elapsed_ms: float
    ) -> "PlatformStartupResult":
        return cls(
            platform_id=platform_id,
            phase=PlatformPhase.RUNNING,
            elapsed_ms=elapsed_ms,
            error=None,
        )

    @classmethod
    def failure(
        cls, platform_id: str, elapsed_ms: float, error: str
    ) -> "PlatformStartupResult":
        return cls(
            platform_id=platform_id,
            phase=PlatformPhase.FAILED,
            elapsed_ms=elapsed_ms,
            error=error,
        )

    @classmethod
    def stopped(
        cls, platform_id: str, elapsed_ms: float
    ) -> "PlatformStartupResult":
        return cls(
            platform_id=platform_id,
            phase=PlatformPhase.STOPPED,
            elapsed_ms=elapsed_ms,
            error=None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Startup order
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StartupOrder:
    """
    Resolved platform startup order produced by the :class:`StartupCoordinator`.

    ``batches`` is an ordered sequence of batches.  Platforms within the
    same batch have no dependency relationship with each other; all
    platforms in batch N must complete before batch N+1 begins.

    Within each batch, platforms are sorted by descending ``priority``.
    """
    batches:        Tuple[Tuple[str, ...], ...]  # outer = batches, inner = platform_ids
    platform_count: int

    def flat_order(self) -> Tuple[str, ...]:
        """All platform IDs in startup order, flattened."""
        return tuple(pid for batch in self.batches for pid in batch)


# ─────────────────────────────────────────────────────────────────────────────
# Platform status snapshot
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlatformStatus:
    """
    Immutable snapshot of the complete bootstrap state at a point in time.
    """
    snapshot_id:       str
    captured_at:       float
    total_platforms:   int
    running_platforms: int
    failed_platforms:  int
    stopped_platforms: int
    platform_phases:   FrozenSet[Tuple[str, str]]        # (platform_id, phase.value)
    startup_results:   Tuple[PlatformStartupResult, ...]

    @property
    def is_fully_operational(self) -> bool:
        """True when all registered platforms are running and none failed."""
        return (
            self.failed_platforms == 0
            and self.total_platforms > 0
            and self.running_platforms == self.total_platforms
        )

    @classmethod
    def create(
        cls,
        phases:  Dict[str, PlatformPhase],
        results: List[PlatformStartupResult],
    ) -> "PlatformStatus":
        running  = sum(1 for p in phases.values() if p == PlatformPhase.RUNNING)
        failed   = sum(1 for p in phases.values() if p == PlatformPhase.FAILED)
        stopped  = sum(1 for p in phases.values() if p == PlatformPhase.STOPPED)
        return cls(
            snapshot_id       = str(uuid.uuid4()),
            captured_at       = time.time(),
            total_platforms   = len(phases),
            running_platforms = running,
            failed_platforms  = failed,
            stopped_platforms = stopped,
            platform_phases   = frozenset((pid, ph.value) for pid, ph in phases.items()),
            startup_results   = tuple(results),
        )
