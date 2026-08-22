"""iios/execution/core/execution_metadata.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.execution_constants import (
    EXECUTION_ENGINE_VERSION,
    ExecutionMode,
)


@dataclass
class ExecutionMetadata:
    """
    Rich provenance metadata attached to an execution lifecycle.

    Tracks where the execution originated, what environment it ran in,
    version information, and any free-form tags or context.
    """

    execution_id: str = ""

    # ── Provenance ─────────────────────────────────────────────────────────────
    source:       str = ""       # "DecisionLayer", "Manual", "Scheduler", …
    environment:  str = ""       # "paper", "live", "simulation"
    version:      str = EXECUTION_ENGINE_VERSION
    schema_version: str = "1.0"

    # ── Classification ─────────────────────────────────────────────────────────
    tags:        list[str]      = field(default_factory=list)
    labels:      dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    # ── Tracing / correlation ──────────────────────────────────────────────────
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id:       str = ""
    span_id:        str = ""

    # ── Context bag (arbitrary runtime data) ──────────────────────────────────
    context: dict[str, Any] = field(default_factory=dict)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at:  float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)
        self.modified_at = time.time()

    def remove_tag(self, tag: str) -> None:
        self.tags = [t for t in self.tags if t != tag]
        self.modified_at = time.time()

    def set_label(self, key: str, value: str) -> None:
        self.labels[key] = value
        self.modified_at = time.time()

    def set_context(self, key: str, value: Any) -> None:
        self.context[key] = value
        self.modified_at = time.time()

    @classmethod
    def for_execution(
        cls,
        execution_id: str,
        *,
        source: str = "ExecutionEngine",
        mode: ExecutionMode = ExecutionMode.PAPER,
    ) -> "ExecutionMetadata":
        return cls(
            execution_id=execution_id,
            source=source,
            environment=mode.value,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id":   self.execution_id,
            "source":         self.source,
            "environment":    self.environment,
            "version":        self.version,
            "schema_version": self.schema_version,
            "tags":           list(self.tags),
            "labels":         dict(self.labels),
            "annotations":    dict(self.annotations),
            "correlation_id": self.correlation_id,
            "trace_id":       self.trace_id,
            "span_id":        self.span_id,
            "context":        dict(self.context),
            "created_at":     self.created_at,
            "modified_at":    self.modified_at,
        }
