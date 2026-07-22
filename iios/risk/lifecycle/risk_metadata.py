"""
risk_metadata.py — iios.risk.lifecycle
=========================================
Immutable supplementary metadata for a risk session.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION


@dataclass(frozen=True)
class RiskMetadata:
    """
    Immutable supplementary metadata attached to a risk session.

    Fields
    ------
    assessment_id :     Risk assessment correlation identifier.
    source :            System or component that initiated the session.
    tags :              Free-form key/value tags for filtering.
    notes :             Optional human-readable notes.
    framework_version : Framework version string.
    """
    assessment_id:     str            = ""
    source:            str            = ""
    tags:              Dict[str, str] = field(default_factory=dict)
    notes:             str            = ""
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        *,
        assessment_id:     str                    = "",
        source:            str                    = "",
        tags:              Optional[Dict[str, str]] = None,
        notes:             str                    = "",
    ) -> "RiskMetadata":
        return cls(
            assessment_id = assessment_id,
            source        = source,
            tags          = dict(tags or {}),
            notes         = notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id":     self.assessment_id,
            "source":            self.source,
            "tags":              dict(self.tags),
            "notes":             self.notes,
            "framework_version": self.framework_version,
        }
