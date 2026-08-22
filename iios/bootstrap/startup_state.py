"""
iios/bootstrap/startup_state.py
================================
State definitions for the IIOS Bootstrap Engine.

All enumerations, result types, and stage descriptors used throughout the
bootstrap pipeline are defined here. No external IIOS dependencies.

Architecture Reference: IIOS-BSS-001 §2.1 State Model
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

__all__ = [
    "SystemPhase",
    "StageStatus",
    "StartupStageResult",
    "BootstrapStage",
    "BootstrapError",
    "ValidationSeverity",
    "ValidationFinding",
    "is_valid_transition",
]


# ---------------------------------------------------------------------------
# System Lifecycle Phases
# ---------------------------------------------------------------------------


class SystemPhase(Enum):
    """Lifecycle phases of the IIOS platform.

    The platform moves through these phases in order during normal operation.
    Abnormal transitions (e.g. FAILED, RECOVERY) are permitted from multiple
    phases. See ``is_valid_transition`` for the full transition graph.
    """

    UNINITIALIZED = "uninitialized"
    INITIALIZING  = "initializing"
    INITIALIZED   = "initialized"
    STARTING      = "starting"
    RUNNING       = "running"
    CERTIFIED     = "certified"     # Paper-trade performance criteria met
    PAUSING       = "pausing"
    PAUSED        = "paused"
    RESUMING      = "resuming"
    STOPPING      = "stopping"
    STOPPED       = "stopped"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN      = "shutdown"
    MAINTENANCE   = "maintenance"
    RECOVERY      = "recovery"
    FAILED        = "failed"

    @property
    def is_terminal(self) -> bool:
        """Return True if the phase is a terminal (no further transitions)."""
        return self in (SystemPhase.SHUTDOWN,)

    @property
    def is_active(self) -> bool:
        """Return True if the system is actively processing in this phase."""
        return self in (SystemPhase.RUNNING, SystemPhase.CERTIFIED)

    @property
    def is_transitioning(self) -> bool:
        """Return True if the system is mid-transition in this phase."""
        return self in (
            SystemPhase.INITIALIZING,
            SystemPhase.STARTING,
            SystemPhase.PAUSING,
            SystemPhase.RESUMING,
            SystemPhase.STOPPING,
            SystemPhase.SHUTTING_DOWN,
            SystemPhase.RECOVERY,
        )


# Valid lifecycle transitions: phase → set of allowed next phases
_TRANSITIONS: dict[SystemPhase, frozenset[SystemPhase]] = {
    SystemPhase.UNINITIALIZED: frozenset({SystemPhase.INITIALIZING}),
    SystemPhase.INITIALIZING:  frozenset({SystemPhase.INITIALIZED, SystemPhase.FAILED}),
    SystemPhase.INITIALIZED:   frozenset({SystemPhase.STARTING, SystemPhase.SHUTTING_DOWN}),
    SystemPhase.STARTING:      frozenset({SystemPhase.RUNNING, SystemPhase.FAILED}),
    SystemPhase.RUNNING:       frozenset({
        SystemPhase.PAUSING,
        SystemPhase.STOPPING,
        SystemPhase.CERTIFIED,
        SystemPhase.MAINTENANCE,
        SystemPhase.FAILED,
    }),
    SystemPhase.CERTIFIED:     frozenset({
        SystemPhase.RUNNING,
        SystemPhase.PAUSING,
        SystemPhase.STOPPING,
        SystemPhase.MAINTENANCE,
        SystemPhase.FAILED,
    }),
    SystemPhase.PAUSING:       frozenset({SystemPhase.PAUSED, SystemPhase.FAILED}),
    SystemPhase.PAUSED:        frozenset({
        SystemPhase.RESUMING,
        SystemPhase.STOPPING,
        SystemPhase.SHUTTING_DOWN,
    }),
    SystemPhase.RESUMING:      frozenset({SystemPhase.RUNNING, SystemPhase.FAILED}),
    SystemPhase.STOPPING:      frozenset({SystemPhase.STOPPED, SystemPhase.FAILED}),
    SystemPhase.STOPPED:       frozenset({SystemPhase.SHUTTING_DOWN, SystemPhase.STARTING}),
    SystemPhase.SHUTTING_DOWN: frozenset({SystemPhase.SHUTDOWN}),
    SystemPhase.SHUTDOWN:      frozenset(),  # terminal
    SystemPhase.MAINTENANCE:   frozenset({
        SystemPhase.RUNNING,
        SystemPhase.STOPPING,
        SystemPhase.FAILED,
    }),
    SystemPhase.RECOVERY:      frozenset({
        SystemPhase.INITIALIZING,
        SystemPhase.RUNNING,
        SystemPhase.FAILED,
    }),
    SystemPhase.FAILED:        frozenset({SystemPhase.RECOVERY, SystemPhase.SHUTTING_DOWN}),
}


def is_valid_transition(from_phase: SystemPhase, to_phase: SystemPhase) -> bool:
    """Return True if the lifecycle transition is permitted."""
    return to_phase in _TRANSITIONS.get(from_phase, frozenset())


def allowed_transitions(from_phase: SystemPhase) -> frozenset[SystemPhase]:
    """Return the set of phases reachable from ``from_phase``."""
    return _TRANSITIONS.get(from_phase, frozenset())


# ---------------------------------------------------------------------------
# Stage Execution Status
# ---------------------------------------------------------------------------


class StageStatus(Enum):
    """Execution status of a single bootstrap stage."""

    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    SKIPPED   = "skipped"
    FAILED    = "failed"
    RETRYING  = "retrying"


# ---------------------------------------------------------------------------
# Validation Findings
# ---------------------------------------------------------------------------


class ValidationSeverity(Enum):
    """Severity level of a validation finding."""

    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


@dataclass
class ValidationFinding:
    """A single finding from a startup validation check."""

    check_name: str
    severity: ValidationSeverity
    message: str
    detail: str = ""
    remediation: str = ""

    @property
    def blocks_startup(self) -> bool:
        return self.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)

    def __str__(self) -> str:
        base = f"[{self.severity.value.upper()}] {self.check_name}: {self.message}"
        if self.detail:
            base += f" — {self.detail}"
        return base


# ---------------------------------------------------------------------------
# Stage Result
# ---------------------------------------------------------------------------


@dataclass
class StartupStageResult:
    """Outcome of executing a single bootstrap stage."""

    stage_number: int
    stage_name: str
    status: StageStatus
    started_at: float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None
    error: Optional[Exception] = None
    error_message: Optional[str] = None
    attempt: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_completed(self) -> None:
        self.status = StageStatus.COMPLETED
        self.completed_at = time.monotonic()

    def mark_failed(self, error: Exception, message: str | None = None) -> None:
        self.status = StageStatus.FAILED
        self.completed_at = time.monotonic()
        self.error = error
        self.error_message = message or str(error)

    def mark_skipped(self, reason: str = "") -> None:
        self.status = StageStatus.SKIPPED
        self.completed_at = time.monotonic()
        if reason:
            self.metadata["skip_reason"] = reason

    @property
    def duration_ms(self) -> float:
        end = self.completed_at if self.completed_at is not None else time.monotonic()
        return (end - self.started_at) * 1000.0

    @property
    def succeeded(self) -> bool:
        return self.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)


# ---------------------------------------------------------------------------
# Stage Descriptor
# ---------------------------------------------------------------------------


@dataclass
class BootstrapStage:
    """Descriptor for a single bootstrap stage.

    ``handler`` is called with ``(context: StartupContext)`` at execution time.
    ``dependencies`` lists stage numbers that must have completed successfully
    before this stage can run.
    """

    number: int
    name: str
    description: str
    handler: Callable[..., None]
    dependencies: list[int] = field(default_factory=list)
    optional: bool = False
    can_retry: bool = True
    max_retries: int = 3
    timeout_seconds: float = 30.0
    tags: frozenset[str] = field(default_factory=frozenset)

    def __hash__(self) -> int:
        return hash(self.number)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BootstrapStage):
            return NotImplemented
        return self.number == other.number

    def __repr__(self) -> str:
        return f"BootstrapStage(number={self.number}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Bootstrap Error
# ---------------------------------------------------------------------------


class BootstrapError(RuntimeError):
    """Raised when the bootstrap engine encounters an unrecoverable error."""

    def __init__(
        self,
        message: str,
        stage_number: Optional[int] = None,
        stage_name: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.stage_number = stage_number
        self.stage_name = stage_name
        self.cause = cause

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.stage_number is not None:
            parts.append(f"[stage={self.stage_number}:{self.stage_name}]")
        if self.cause is not None:
            parts.append(f"[cause={type(self.cause).__name__}: {self.cause}]")
        return " ".join(parts)


class ShutdownError(RuntimeError):
    """Raised when the shutdown sequence encounters an unrecoverable error."""
