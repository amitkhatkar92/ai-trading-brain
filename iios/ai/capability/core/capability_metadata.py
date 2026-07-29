"""
capability_metadata.py -- iios.ai.capability.core
===================================================
:class:`CapabilityVersion`  — semantic version with compatibility check.
:class:`CapabilityMetadata` — immutable metadata header for a capability.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Tuple


# ── CapabilityVersion ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapabilityVersion:
    """Semantic version (major.minor.patch)."""

    major: int
    minor: int
    patch: int

    # ── factories ─────────────────────────────────────────────────────────────

    @classmethod
    def parse(cls, version_str: str) -> "CapabilityVersion":
        """Parse 'major.minor.patch' string."""
        parts = version_str.strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version string: {version_str!r}")
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))

    @classmethod
    def create(cls, major: int = 1, minor: int = 0, patch: int = 0) -> "CapabilityVersion":
        return cls(major=major, minor=minor, patch=patch)

    # ── helpers ───────────────────────────────────────────────────────────────

    def is_compatible_with(self, other: "CapabilityVersion") -> bool:
        """Two versions are compatible when they share the same major version."""
        return self.major == other.major

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "CapabilityVersion") -> bool:  # type: ignore[override]
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "CapabilityVersion") -> bool:  # type: ignore[override]
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)


# ── CapabilityMetadata ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapabilityMetadata:
    """Immutable metadata header attached to every :class:`CapabilityDescriptor`."""

    metadata_id:  str
    name:         str
    description:  str
    author:       str
    tags:         FrozenSet[str]
    created_at:   float
    updated_at:   float

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:        str,
        description: str  = "",
        author:      str  = "",
        tags:        Optional[FrozenSet[str]] = None,
    ) -> "CapabilityMetadata":
        now = time.time()
        return cls(
            metadata_id = str(uuid.uuid4()),
            name        = name,
            description = description,
            author      = author,
            tags        = tags if tags is not None else frozenset(),
            created_at  = now,
            updated_at  = now,
        )
