"""
portfolio_metadata.py — iios.portfolio.lifecycle
==================================================
Immutable metadata attached to a portfolio session.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class PortfolioMetadata:
    """
    Immutable supplementary metadata for a portfolio session.

    Fields
    ------
    metadata_id :      Unique identifier.
    session_id :       Owning portfolio session.
    portfolio_id :     Portfolio identifier.
    tags :             Tuple of classification tags.
    labels :           Key-value label dict.
    annotations :      Free-form annotation dict.
    schema_version :   Schema version string.
    created_at :       Wall-clock creation time.
    framework_version: Framework version.
    """
    metadata_id:       str
    session_id:        str
    portfolio_id:      str
    tags:              Tuple[str, ...]  = field(default_factory=tuple)
    labels:            Dict[str, str]   = field(default_factory=dict)
    annotations:       Dict[str, Any]   = field(default_factory=dict)
    schema_version:    str              = "1.0"
    created_at:        float            = field(default_factory=time.time)
    framework_version: str              = VERSION

    @classmethod
    def create(
        cls,
        session_id:    str,
        portfolio_id:  str,
        *,
        metadata_id:   Optional[str]          = None,
        tags:          Tuple[str, ...]         = (),
        labels:        Optional[Dict[str, str]] = None,
        annotations:   Optional[Dict[str, Any]] = None,
        schema_version: str                   = "1.0",
    ) -> "PortfolioMetadata":
        return cls(
            metadata_id    = metadata_id or str(uuid.uuid4()),
            session_id     = session_id,
            portfolio_id   = portfolio_id,
            tags           = tuple(tags),
            labels         = dict(labels or {}),
            annotations    = dict(annotations or {}),
            schema_version = schema_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_id":      self.metadata_id,
            "session_id":       self.session_id,
            "portfolio_id":     self.portfolio_id,
            "tags":             list(self.tags),
            "labels":           dict(self.labels),
            "annotations":      dict(self.annotations),
            "schema_version":   self.schema_version,
            "created_at":       self.created_at,
            "framework_version": self.framework_version,
        }
