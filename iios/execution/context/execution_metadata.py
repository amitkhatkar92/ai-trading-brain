"""iios/execution/context/execution_metadata.py
==================================================
ExecutionMetadata — immutable administrative metadata attached
to every ExecutionContext.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.context.constants import ExecutionEnvironment, ExecutionMode, VERSION

ACTOR_SYSTEM_DEFAULT = "iios:system"


@dataclass(frozen=True)
class ExecutionMetadata:
    """
    Administrative metadata for a single execution context.

    Carries identity, versioning, lineage, and timing information.
    All fields are set at construction and never mutated.
    """

    metadata_id:     str                = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version:  str                = VERSION

    # Lineage
    created_by:      str                = ACTOR_SYSTEM_DEFAULT
    created_at:      float              = field(default_factory=time.time)
    source_system:   str                = "iios:execution:context"

    # Mode / environment
    execution_mode:  ExecutionMode      = ExecutionMode.PAPER
    environment:     ExecutionEnvironment = ExecutionEnvironment.PRODUCTION

    # Tags and labels
    tags:            frozenset[str]     = field(default_factory=frozenset)
    labels:          dict[str, str]     = field(default_factory=dict)

    # Extra
    notes:           str                = ""
    metadata:        dict[str, Any]     = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata_id":    self.metadata_id,
            "schema_version": self.schema_version,
            "created_by":     self.created_by,
            "created_at":     self.created_at,
            "source_system":  self.source_system,
            "execution_mode": self.execution_mode.value,
            "environment":    self.environment.value,
            "tags":           sorted(self.tags),
            "labels":         dict(self.labels),
            "notes":          self.notes,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionMetadata("
            f"mode={self.execution_mode.value}, "
            f"env={self.environment.value})"
        )


ACTOR_SYSTEM_DEFAULT = "iios:system"
