"""
iios/ontology/compiler/compiler_registry.py
=============================================
Registry of all compilation results and their metadata.

Tracks:
- Every compiled ontology artefact
- Its CompilationMetadata
- Its compilation status
- Compile-attempt history (for diagnostics)

Separate from OntologyRegistryManager (which tracks live runtime types).
This registry tracks the *compilation process* itself.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .compiler_constants import LoadPhase
from .compiler_exceptions import CompilerRegistryError, DuplicateCompilationError
from .metadata_generator  import CompilationMetadata
from ..runtime.runtime_object import CompiledOntology

__all__ = [
    "CompilationRecord",
    "CompilerRegistry",
    "get_compiler_registry",
    "reset_compiler_registry",
]

_LOG  = logging.getLogger("iios.ontology.compiler.registry")
_lock = threading.Lock()
_reg: Optional["CompilerRegistry"] = None


# ── Compilation record ────────────────────────────────────────────────────────

@dataclass
class CompilationRecord:
    """A single entry in the compiler registry."""
    name:       str
    phase:      LoadPhase
    compiled:   Optional[CompiledOntology]  = None
    metadata:   Optional[CompilationMetadata] = None
    error:      Optional[str]               = None
    attempt:    int                         = 1
    started_at: float                       = field(default_factory=time.time)
    finished_at: Optional[float]            = None
    duration_ms: float                      = 0.0

    @property
    def succeeded(self) -> bool:
        return self.compiled is not None and self.error is None

    @property
    def failed(self) -> bool:
        return self.error is not None

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "phase":       self.phase.value,
            "succeeded":   self.succeeded,
            "error":       self.error,
            "attempt":     self.attempt,
            "duration_ms": round(self.duration_ms, 3),
            "build_id":    self.metadata.build_id if self.metadata else None,
            "type_count":  self.metadata.type_count if self.metadata else 0,
        }


# ── Registry ──────────────────────────────────────────────────────────────────

class CompilerRegistry:
    """
    Registry of all compilation results.

    Thread-safe. Maintains history of all compilation attempts,
    allowing diagnostics to report what was compiled, when, and
    whether it succeeded.
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._records: dict[str, CompilationRecord] = {}
        self._history: list[CompilationRecord]      = []

    # ── Registration ──────────────────────────────────────────────────────────

    def register_start(self, name: str) -> CompilationRecord:
        """Record the start of a compilation attempt."""
        with self._lock:
            record = CompilationRecord(
                name       = name,
                phase      = LoadPhase.COMPILING,
                started_at = time.time(),
            )
            existing = self._records.get(name)
            if existing:
                record.attempt = existing.attempt + 1
            self._records[name] = record
            return record

    def register_success(
        self,
        name:       str,
        compiled:   CompiledOntology,
        metadata:   CompilationMetadata,
        duration_ms: float = 0.0,
    ) -> CompilationRecord:
        """Record a successful compilation."""
        with self._lock:
            record = self._records.get(name)
            if record is None:
                record = CompilationRecord(name=name, phase=LoadPhase.COMPLETE)
                self._records[name] = record

            record.compiled    = compiled
            record.metadata    = metadata
            record.phase       = LoadPhase.COMPLETE
            record.finished_at = time.time()
            record.duration_ms = duration_ms
            record.error       = None
            self._history.append(record)
            _LOG.debug("Compilation record: %s succeeded in %.1fms", name, duration_ms)
            return record

    def register_failure(
        self,
        name:    str,
        error:   str,
        duration_ms: float = 0.0,
    ) -> CompilationRecord:
        """Record a failed compilation."""
        with self._lock:
            record = self._records.get(name)
            if record is None:
                record = CompilationRecord(name=name, phase=LoadPhase.FAILED)
                self._records[name] = record

            record.error       = error
            record.phase       = LoadPhase.FAILED
            record.finished_at = time.time()
            record.duration_ms = duration_ms
            self._history.append(record)
            _LOG.warning("Compilation record: %s FAILED: %s", name, error)
            return record

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[CompilationRecord]:
        with self._lock:
            return self._records.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._records

    def is_compiled(self, name: str) -> bool:
        with self._lock:
            r = self._records.get(name)
            return r is not None and r.succeeded

    def get_metadata(self, name: str) -> Optional[CompilationMetadata]:
        with self._lock:
            r = self._records.get(name)
            return r.metadata if r else None

    def all_names(self) -> list[str]:
        with self._lock:
            return list(self._records.keys())

    def successful_names(self) -> list[str]:
        with self._lock:
            return [n for n, r in self._records.items() if r.succeeded]

    def failed_names(self) -> list[str]:
        with self._lock:
            return [n for n, r in self._records.items() if r.failed]

    def history(self) -> list[CompilationRecord]:
        with self._lock:
            return list(self._history)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            total     = len(self._records)
            succeeded = sum(1 for r in self._records.values() if r.succeeded)
            failed    = sum(1 for r in self._records.values() if r.failed)
            avg_ms    = 0.0
            if succeeded > 0:
                durations = [r.duration_ms for r in self._records.values() if r.succeeded]
                avg_ms    = sum(durations) / len(durations)
            return {
                "total_registered": total,
                "succeeded":        succeeded,
                "failed":           failed,
                "avg_duration_ms":  round(avg_ms, 2),
                "history_entries":  len(self._history),
            }

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._history.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_compiler_registry() -> CompilerRegistry:
    global _reg
    if _reg is None:
        with _lock:
            if _reg is None:
                _reg = CompilerRegistry()
    return _reg


def reset_compiler_registry() -> None:
    global _reg
    with _lock:
        _reg = None
