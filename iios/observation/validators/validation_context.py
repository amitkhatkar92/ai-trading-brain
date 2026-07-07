"""
iios/observation/validators/validation_context.py
==================================================
Thread-local validation context — tracks which observation and stage
is currently being validated in the calling thread.

Usage::

    with validation_operation("obs-123", ValidationStage.PRE):
        # inside here, current_obs_id() == "obs-123"
        ...
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from .validation_constants import SYSTEM_VALIDATOR, ValidationStage

__all__ = [
    "ValidationContext",
    "get_validation_context",
    "reset_validation_context",
    "validation_operation",
    "current_obs_id",
    "current_stage",
    "current_run_id",
]

_thread_local = threading.local()


@dataclass
class ValidationContext:
    """Per-thread validation state."""

    obs_id:          str             = ""
    run_id:          str             = ""
    stage:           Optional[ValidationStage] = None
    validator_name:  str             = SYSTEM_VALIDATOR
    started_at:      float           = field(default_factory=time.time)
    rule_count:      int             = 0
    violation_count: int             = 0
    warning_count:   int             = 0
    attributes:      dict[str, Any]  = field(default_factory=dict)

    def reset(self) -> None:
        self.obs_id         = ""
        self.run_id         = ""
        self.stage          = None
        self.validator_name = SYSTEM_VALIDATOR
        self.started_at     = time.time()
        self.rule_count     = 0
        self.violation_count = 0
        self.warning_count  = 0
        self.attributes.clear()

    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000.0

    @contextmanager
    def running(
        self,
        obs_id:         str,
        stage:          Optional[ValidationStage] = None,
        validator_name: str = SYSTEM_VALIDATOR,
    ) -> Generator[None, None, None]:
        """Context manager — set context for duration of a validation run."""
        prev_obs_id         = self.obs_id
        prev_run_id         = self.run_id
        prev_stage          = self.stage
        prev_validator_name = self.validator_name
        prev_started_at     = self.started_at

        self.obs_id         = obs_id
        self.run_id         = uuid.uuid4().hex
        self.stage          = stage
        self.validator_name = validator_name
        self.started_at     = time.time()
        try:
            yield
        finally:
            self.obs_id         = prev_obs_id
            self.run_id         = prev_run_id
            self.stage          = prev_stage
            self.validator_name = prev_validator_name
            self.started_at     = prev_started_at


# ── Thread-local accessor ─────────────────────────────────────────────────────

def get_validation_context() -> ValidationContext:
    """Return the per-thread ValidationContext, creating it if needed."""
    if not hasattr(_thread_local, "ctx"):
        _thread_local.ctx = ValidationContext()
    return _thread_local.ctx  # type: ignore[return-value]


def reset_validation_context() -> None:
    """Reset the context in the calling thread (useful for tests)."""
    if hasattr(_thread_local, "ctx"):
        _thread_local.ctx.reset()


# ── Module-level helpers ──────────────────────────────────────────────────────

@contextmanager
def validation_operation(
    obs_id:         str,
    stage:          Optional[ValidationStage] = None,
    validator_name: str = SYSTEM_VALIDATOR,
) -> Generator[None, None, None]:
    """Convenience context manager — delegates to the thread-local context."""
    ctx = get_validation_context()
    with ctx.running(obs_id, stage=stage, validator_name=validator_name):
        yield


def current_obs_id() -> str:
    return get_validation_context().obs_id


def current_stage() -> Optional[ValidationStage]:
    return get_validation_context().stage


def current_run_id() -> str:
    return get_validation_context().run_id
