"""
ai_model.py -- iios.ai.model_management.core
=============================================
:class:`AIModel` — mutable, thread-safe aggregate root for a registered AI
model.  Wraps immutable :class:`ModelMetadata` and an ordered collection of
:class:`AIModelVersion` instances.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional

from .model_metadata import ModelMetadata
from .model_version   import AIModelVersion
from ..exceptions     import AIModelVersionError


class AIModel:
    """
    Mutable, thread-safe aggregate root for a registered AI model.

    All external writes go through this class's methods, never by direct
    field mutation.
    """

    def __init__(self, metadata: ModelMetadata) -> None:
        self._metadata: ModelMetadata                = metadata
        self._versions: Dict[str, AIModelVersion]    = {}
        self._version_order: List[str]               = []   # insertion order
        self._active_version_id: Optional[str]       = None
        self._enabled: bool                          = True
        self._lock: RLock                            = RLock()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def model_id(self) -> str:
        return self._metadata.model_id

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def active_version(self) -> Optional[AIModelVersion]:
        with self._lock:
            if self._active_version_id is None:
                return None
            return self._versions.get(self._active_version_id)

    # ── Versioning ────────────────────────────────────────────────────────────

    def add_version(self, version: AIModelVersion, *, activate: bool = True) -> AIModelVersion:
        """Add a new version; optionally activate it immediately."""
        with self._lock:
            # Deactivate previous active
            if activate and self._active_version_id is not None:
                old = self._versions[self._active_version_id]
                self._versions[self._active_version_id] = old.with_active(False)

            new = version.with_active(activate)
            self._versions[version.version_id] = new
            self._version_order.append(version.version_id)
            if activate:
                self._active_version_id = version.version_id
            return new

    def activate_version(self, version_id: str) -> AIModelVersion:
        """Explicitly activate a previously registered version."""
        with self._lock:
            if version_id not in self._versions:
                raise AIModelVersionError(
                    f"Version {version_id!r} not found on model {self.model_id!r}."
                )
            if self._active_version_id is not None:
                old = self._versions[self._active_version_id]
                self._versions[self._active_version_id] = old.with_active(False)

            activated = self._versions[version_id].with_active(True)
            self._versions[version_id] = activated
            self._active_version_id = version_id
            return activated

    def get_version(self, version_id: str) -> Optional[AIModelVersion]:
        with self._lock:
            return self._versions.get(version_id)

    def history(self) -> List[AIModelVersion]:
        """Return all versions in insertion order."""
        with self._lock:
            return [self._versions[vid] for vid in self._version_order]

    # ── Enable / Disable ──────────────────────────────────────────────────────

    def enable(self) -> None:
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        with self._lock:
            self._enabled = False

    # ── Repr ──────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"<AIModel name={self._metadata.name!r} "
            f"id={self.model_id!r} enabled={self._enabled} "
            f"versions={len(self._versions)}>"
        )
