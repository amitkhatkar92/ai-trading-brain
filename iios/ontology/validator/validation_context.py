"""
iios/ontology/validator/validation_context.py
==============================================
Thread-local validation context.

Tracks the current validation operation (operation_id, mode, phase,
target) within one thread.  Used by all validators and constraint
evaluators to avoid threading parameter pollution.
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .validation_constants import (
    SYSTEM_VALIDATOR_ACTOR,
    ValidationMode,
    ValidationPhase,
    ValidationScope,
)

__all__ = [
    "ValidationContext",
    "get_validation_context",
    "reset_validation_context",
    "DiagnosticLevel",
    "ValidationDiagnostic",
]

# ── Diagnostic helpers ────────────────────────────────────────────────────────

class DiagnosticLevel:
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"


from dataclasses import dataclass, field


@dataclass
class ValidationDiagnostic:
    """A single diagnostic note produced during validation."""
    level:       str
    scope:       str
    target:      str
    message:     str
    timestamp:   float = field(default_factory=time.time)
    context_data: dict[str, Any] = field(default_factory=dict)


# ── Thread-local context ──────────────────────────────────────────────────────

class _ThreadLocalState(threading.local):
    """Thread-local storage for the validation context stack."""

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[dict[str, Any]] = []

    def push(self, frame: dict[str, Any]) -> None:
        self._stack.append(frame)

    def pop(self) -> dict[str, Any]:
        return self._stack.pop() if self._stack else {}

    @property
    def current(self) -> Optional[dict[str, Any]]:
        return self._stack[-1] if self._stack else None

    @property
    def depth(self) -> int:
        return len(self._stack)


class ValidationContext:
    """
    Thread-local validation context.

    Stores the current operation's identity (operation_id, actor),
    the active mode/phase, and per-thread diagnostics.

    Context managers automatically push/pop frames so nested validations
    each see their own isolated state.
    """

    def __init__(self) -> None:
        self._tls  = _ThreadLocalState()
        self._lock = threading.Lock()

    # ── Current-frame accessors ───────────────────────────────────────────────

    @property
    def operation_id(self) -> Optional[str]:
        f = self._tls.current
        return f["operation_id"] if f else None

    @property
    def actor(self) -> str:
        f = self._tls.current
        return f["actor"] if f else SYSTEM_VALIDATOR_ACTOR

    @property
    def mode(self) -> ValidationMode:
        f = self._tls.current
        return f["mode"] if f else ValidationMode.STANDARD

    @property
    def phase(self) -> ValidationPhase:
        f = self._tls.current
        return f["phase"] if f else ValidationPhase.ON_DEMAND

    @property
    def current_target(self) -> Optional[str]:
        f = self._tls.current
        return f.get("target") if f else None

    @property
    def current_scope(self) -> Optional[ValidationScope]:
        f = self._tls.current
        return f.get("scope") if f else None

    @property
    def started_at(self) -> Optional[float]:
        f = self._tls.current
        return f.get("started_at") if f else None

    def elapsed_ms(self) -> float:
        """Milliseconds since the innermost context was entered."""
        sa = self.started_at
        return (time.time() - sa) * 1_000.0 if sa is not None else 0.0

    @property
    def diagnostics(self) -> list[ValidationDiagnostic]:
        f = self._tls.current
        return f["diagnostics"] if f else []

    def add_diagnostic(
        self,
        level:        str,
        message:      str,
        scope:        str  = "",
        target:       str  = "",
        **extra: Any,
    ) -> None:
        f = self._tls.current
        if f is None:
            return
        f["diagnostics"].append(
            ValidationDiagnostic(
                level        = level,
                scope        = scope or (self.current_scope.value if self.current_scope else ""),
                target       = target or (self.current_target or ""),
                message      = message,
                context_data = extra,
            )
        )

    def warnings(self) -> list[ValidationDiagnostic]:
        return [d for d in self.diagnostics if d.level == DiagnosticLevel.WARNING]

    def errors(self) -> list[ValidationDiagnostic]:
        return [d for d in self.diagnostics if d.level == DiagnosticLevel.ERROR]

    # ── Context managers ──────────────────────────────────────────────────────

    @contextmanager
    def validation(
        self,
        target:       str,
        actor:        str              = SYSTEM_VALIDATOR_ACTOR,
        mode:         ValidationMode   = ValidationMode.STANDARD,
        phase:        ValidationPhase  = ValidationPhase.ON_DEMAND,
        operation_id: Optional[str]    = None,
        scope:        Optional[ValidationScope] = None,
    ) -> Generator[None, None, None]:
        """Enter a validation context frame for *target*."""
        frame: dict[str, Any] = {
            "operation_id": operation_id or str(uuid.uuid4()),
            "actor":        actor,
            "mode":         mode,
            "phase":        phase,
            "target":       target,
            "scope":        scope,
            "started_at":   time.time(),
            "diagnostics":  [],
        }
        self._tls.push(frame)
        try:
            yield
        finally:
            self._tls.pop()

    @contextmanager
    def target(
        self,
        target: str,
        scope:  Optional[ValidationScope] = None,
    ) -> Generator[None, None, None]:
        """
        Nested context for a specific sub-target inside an outer validation.
        Inherits operation_id / actor / mode / phase from the parent frame.
        """
        parent = self._tls.current or {}
        frame: dict[str, Any] = {
            "operation_id": parent.get("operation_id", str(uuid.uuid4())),
            "actor":        parent.get("actor", SYSTEM_VALIDATOR_ACTOR),
            "mode":         parent.get("mode", ValidationMode.STANDARD),
            "phase":        parent.get("phase", ValidationPhase.ON_DEMAND),
            "target":       target,
            "scope":        scope or parent.get("scope"),
            "started_at":   time.time(),
            "diagnostics":  [],
        }
        self._tls.push(frame)
        try:
            yield
        finally:
            self._tls.pop()

    @property
    def depth(self) -> int:
        return self._tls.depth


# ── Singleton ─────────────────────────────────────────────────────────────────

_lock:    threading.Lock              = threading.Lock()
_context: Optional[ValidationContext] = None


def get_validation_context() -> ValidationContext:
    global _context
    if _context is None:
        with _lock:
            if _context is None:
                _context = ValidationContext()
    return _context


def reset_validation_context() -> None:
    global _context
    with _lock:
        _context = None
