"""
iios/ontology/compiler/compiler_context.py
=============================================
Thread-local execution context for the Ontology Compiler pipeline.

Tracks the current compilation pass, active ontology name, actor,
operation-id, and accumulated diagnostics for a single compilation run.
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from .compiler_constants import CompilationPass, LoadPhase, COMPILER_NAMESPACE

__all__ = [
    "CompilationDiagnostic",
    "CompilerContext",
    "get_compiler_context",
    "reset_compiler_context",
    "compiler_compilation",
    "DiagnosticLevel",
]


# ── Diagnostics ───────────────────────────────────────────────────────────────

class DiagnosticLevel(str):
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"


@dataclass
class CompilationDiagnostic:
    """A single diagnostic message generated during compilation."""
    level:       str
    pass_name:   str
    ont_name:    str
    message:     str
    timestamp:   float = field(default_factory=time.time)
    context:     dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level":     self.level,
            "pass":      self.pass_name,
            "ontology":  self.ont_name,
            "message":   self.message,
            "timestamp": self.timestamp,
            "context":   self.context,
        }


# ── Context ───────────────────────────────────────────────────────────────────

class CompilerContext:
    """
    Thread-local context for the compiler pipeline.

    Holds per-compilation state: current pass, diagnostics, timings.
    One instance is the module-level singleton; state is per-thread.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    # ── Thread-local state helpers ────────────────────────────────────────────

    @property
    def operation_id(self) -> Optional[str]:
        return getattr(self._local, "operation_id", None)

    @property
    def actor(self) -> str:
        return getattr(self._local, "actor", COMPILER_NAMESPACE)

    @property
    def current_ontology(self) -> Optional[str]:
        return getattr(self._local, "current_ontology", None)

    @property
    def current_pass(self) -> Optional[str]:
        return getattr(self._local, "current_pass", None)

    @property
    def current_phase(self) -> Optional[str]:
        return getattr(self._local, "current_phase", None)

    @property
    def started_at(self) -> Optional[float]:
        return getattr(self._local, "started_at", None)

    @property
    def diagnostics(self) -> list[CompilationDiagnostic]:
        if not hasattr(self._local, "diagnostics"):
            self._local.diagnostics = []
        return self._local.diagnostics

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        diag = CompilationDiagnostic(
            level     = level,
            pass_name = self.current_pass or "",
            ont_name  = self.current_ontology or "",
            message   = message,
            context   = context or {},
        )
        self.diagnostics.append(diag)

    def warnings(self) -> list[str]:
        return [d.message for d in self.diagnostics if d.level == DiagnosticLevel.WARNING]

    def errors(self) -> list[str]:
        return [d.message for d in self.diagnostics if d.level == DiagnosticLevel.ERROR]

    def elapsed_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        return (time.perf_counter() - self.started_at) * 1_000.0

    # ── Context managers ──────────────────────────────────────────────────────

    @contextmanager
    def compilation(
        self,
        ont_name:     str,
        actor:        Optional[str]  = None,
        operation_id: Optional[str]  = None,
    ) -> Generator[None, None, None]:
        """
        Scope a full compilation run for one ontology document.
        Resets diagnostics and sets the active ontology name.
        """
        prev_ont  = self._local.__dict__.get("current_ontology")
        prev_id   = self._local.__dict__.get("operation_id")
        prev_actor = self._local.__dict__.get("actor")
        prev_diag = self._local.__dict__.get("diagnostics")

        self._local.current_ontology = ont_name
        self._local.operation_id     = operation_id or str(uuid.uuid4())
        self._local.actor            = actor or COMPILER_NAMESPACE
        self._local.diagnostics      = []
        self._local.started_at       = time.perf_counter()

        try:
            yield
        finally:
            self._local.current_ontology = prev_ont
            self._local.operation_id     = prev_id
            self._local.actor            = prev_actor
            self._local.diagnostics      = prev_diag if prev_diag is not None else []

    @contextmanager
    def pass_(self, pass_name: str) -> Generator[None, None, None]:
        """Scope a single compilation pass."""
        prev_pass  = self._local.__dict__.get("current_pass")
        prev_phase = self._local.__dict__.get("current_phase")
        self._local.current_pass  = pass_name
        self._local.current_phase = pass_name
        try:
            yield
        finally:
            self._local.current_pass  = prev_pass
            self._local.current_phase = prev_phase

    @contextmanager
    def phase(self, phase: LoadPhase) -> Generator[None, None, None]:
        """Scope a load phase."""
        prev = self._local.__dict__.get("current_phase")
        self._local.current_phase = phase.value
        try:
            yield
        finally:
            self._local.current_phase = prev


# ── Singleton ─────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_ctx: Optional[CompilerContext] = None


def get_compiler_context() -> CompilerContext:
    global _ctx
    if _ctx is None:
        with _lock:
            if _ctx is None:
                _ctx = CompilerContext()
    return _ctx


def reset_compiler_context() -> None:
    global _ctx
    with _lock:
        _ctx = None


# ── Module-level convenience ──────────────────────────────────────────────────

@contextmanager
def compiler_compilation(
    ont_name:     str,
    actor:        Optional[str] = None,
    operation_id: Optional[str] = None,
) -> Generator[None, None, None]:
    with get_compiler_context().compilation(ont_name, actor=actor, operation_id=operation_id):
        yield
