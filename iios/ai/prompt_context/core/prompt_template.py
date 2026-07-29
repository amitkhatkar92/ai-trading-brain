"""
prompt_template.py -- iios.ai.prompt_context.core
====================================================
:class:`PromptTemplate` -- the aggregate root for a registered prompt.

Owns its :class:`PromptMetadata`, the full ordered history of
:class:`PromptVersion` objects, the currently active version, and the
enabled/disabled flag.  Thread-safe -- may be read/written concurrently
by the registry, version manager, and composer.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..exceptions       import AIPromptVersionError
from .prompt_metadata   import PromptMetadata
from .prompt_version    import PromptVersion


class PromptTemplate:
    """
    Mutable aggregate: identity metadata + version history + activation state.

    Version mutation is normally performed through
    :class:`iios.ai.prompt_context.versioning.VersionManager`, which also
    records audit history.  ``add_version`` / ``activate_version`` remain
    public so :class:`PromptRegistry` and tests can operate directly.
    """

    def __init__(self, metadata: PromptMetadata) -> None:
        self._metadata:           PromptMetadata            = metadata
        self._versions:           Dict[str, PromptVersion]  = {}
        self._version_order:      List[str]                 = []
        self._active_version_id:  Optional[str]             = None
        self._enabled:            bool                      = True
        self._lock:               threading.RLock           = threading.RLock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def prompt_id(self) -> str:
        return self._metadata.prompt_id

    @property
    def metadata(self) -> PromptMetadata:
        return self._metadata

    # ── Enable / disable ──────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def enable(self) -> None:
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        with self._lock:
            self._enabled = False

    # ── Version management ───────────────────────────────────────────────────

    @property
    def active_version(self) -> Optional[PromptVersion]:
        with self._lock:
            if self._active_version_id is None:
                return None
            return self._versions.get(self._active_version_id)

    def add_version(self, version: PromptVersion, *, activate: bool = True) -> PromptVersion:
        """Append ``version`` to history; activates it if requested or first version."""
        with self._lock:
            self._versions[version.version_id] = version
            self._version_order.append(version.version_id)
            if activate or self._active_version_id is None:
                self._activate_locked(version.version_id)
            return self._versions[version.version_id]

    def activate_version(self, version_id: str) -> PromptVersion:
        """Activate a previously added version (used for rollback)."""
        with self._lock:
            if version_id not in self._versions:
                raise AIPromptVersionError(
                    f"Unknown version_id {version_id!r} for prompt {self.prompt_id!r}"
                )
            self._activate_locked(version_id)
            return self._versions[version_id]

    def history(self) -> List[PromptVersion]:
        """Return all versions in creation order."""
        with self._lock:
            return [self._versions[vid] for vid in self._version_order]

    def get_version(self, version_id: str) -> PromptVersion:
        with self._lock:
            v = self._versions.get(version_id)
        if v is None:
            raise AIPromptVersionError(
                f"Unknown version_id {version_id!r} for prompt {self.prompt_id!r}"
            )
        return v

    # ── Internals ─────────────────────────────────────────────────────────────

    def _activate_locked(self, version_id: str) -> None:
        if self._active_version_id and self._active_version_id in self._versions:
            prev = self._versions[self._active_version_id]
            self._versions[self._active_version_id] = prev.with_active(False)
        self._versions[version_id] = self._versions[version_id].with_active(True)
        self._active_version_id = version_id

    def __repr__(self) -> str:
        return (
            f"<PromptTemplate id={self.prompt_id!r} name={self._metadata.name!r} "
            f"versions={len(self._version_order)} enabled={self.enabled}>"
        )
