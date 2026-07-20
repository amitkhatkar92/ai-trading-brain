"""
decision_metadata.py — iios.decision.lifecycle
================================================
Metadata value object for decision lifecycle sessions.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import SCHEMA_VERSION, VERSION


@dataclass(frozen=True)
class DecisionMetadata:
    """
    Immutable structured metadata for a decision session.

    Carries supplementary classification data (tags, labels, annotations)
    that travels alongside a :class:`DecisionSession` without mutating it.

    Fields
    ------
    metadata_id :     Unique identifier for this metadata object.
    session_id :      Associated decision session identifier.
    decision_id :     Associated decision identifier.
    tags :            Immutable tuple of classification tags.
    labels :          Key-value label map (string → string).
    annotations :     Free-form annotation dict.
    schema_version :  Schema version string for forward compatibility.
    created_at :      Wall-clock creation time.
    updated_at :      Wall-clock time of last metadata update.
    framework_version : Framework version string.
    """
    metadata_id:      str
    session_id:       str
    decision_id:      str

    tags:             Tuple[str, ...]     = field(default_factory=tuple)
    labels:           Dict[str, str]      = field(default_factory=dict)
    annotations:      Dict[str, Any]      = field(default_factory=dict)

    schema_version:   str                 = SCHEMA_VERSION
    created_at:       float               = field(default_factory=time.time)
    updated_at:       float               = field(default_factory=time.time)
    framework_version: str                = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        *,
        session_id:  str,
        decision_id: str,
        tags:        Tuple[str, ...] = (),
        labels:      Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, Any]] = None,
    ) -> "DecisionMetadata":
        """
        Create a new :class:`DecisionMetadata` with a generated ID.

        Parameters
        ----------
        session_id :  Decision session identifier.
        decision_id : Decision identifier.
        tags :        Immutable tuple of classification tags.
        labels :      Optional key-value labels.
        annotations : Optional free-form annotations.
        """
        return cls(
            metadata_id  = str(uuid.uuid4()),
            session_id   = session_id,
            decision_id  = decision_id,
            tags         = tags,
            labels       = dict(labels or {}),
            annotations  = dict(annotations or {}),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def has_tag(self, tag: str) -> bool:
        """Return ``True`` when *tag* is in the tags tuple."""
        return tag in self.tags

    def get_label(self, key: str, default: str = "") -> str:
        """Return the value of label *key*, or *default* if absent."""
        return self.labels.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "metadata_id":      self.metadata_id,
            "session_id":       self.session_id,
            "decision_id":      self.decision_id,
            "tags":             list(self.tags),
            "labels":           dict(self.labels),
            "annotations":      dict(self.annotations),
            "schema_version":   self.schema_version,
            "created_at":       self.created_at,
            "updated_at":       self.updated_at,
            "framework_version": self.framework_version,
        }

    def __repr__(self) -> str:
        return (
            f"DecisionMetadata("
            f"metadata_id={self.metadata_id!r}, "
            f"session_id={self.session_id!r}, "
            f"tags={list(self.tags)!r})"
        )
