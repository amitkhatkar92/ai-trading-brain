"""
iios/knowledge/versioning/models/version_history.py
=====================================================
VersionHistory — ordered, queryable collection of KnowledgeVersion objects
for a single knowledge item (and optionally a single branch).

VersionHistory is a value object; it is always produced fresh by
VersionManager.get_history() and is not meant to be mutated.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .knowledge_version import KnowledgeVersion, VersionStatus
from ..version_constants import DEFAULT_BRANCH

__all__ = ["VersionHistory"]


@dataclass
class VersionHistory:
    """Ordered sequence of versions for one knowledge item.

    Versions are stored oldest-first (ascending ``version_seq``).
    """

    knowledge_id: str
    branch:       str                  = DEFAULT_BRANCH
    versions:     list[KnowledgeVersion] = field(default_factory=list)
    fetched_at:   float                = field(default_factory=time.time)

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self.versions)

    @property
    def is_empty(self) -> bool:
        return not self.versions

    def latest(self) -> Optional[KnowledgeVersion]:
        """Most recent version (highest ``version_seq``)."""
        return self.versions[-1] if self.versions else None

    def earliest(self) -> Optional[KnowledgeVersion]:
        """Oldest recorded version."""
        return self.versions[0] if self.versions else None

    def get(self, version_id: str) -> Optional[KnowledgeVersion]:
        """Look up a version by its ``version_id``."""
        for v in self.versions:
            if v.version_id == version_id:
                return v
        return None

    def get_by_string(self, version_string: str,
                      branch: Optional[str] = None) -> Optional[KnowledgeVersion]:
        """Look up by semantic version string, optionally scoped to a branch."""
        for v in reversed(self.versions):
            if v.version_string == version_string:
                if branch is None or v.branch_name == branch:
                    return v
        return None

    def since(self, version_id: str) -> list[KnowledgeVersion]:
        """Return all versions after (not including) ``version_id``."""
        result: list[KnowledgeVersion] = []
        found = False
        for v in self.versions:
            if found:
                result.append(v)
            elif v.version_id == version_id:
                found = True
        return result

    def filter(
        self,
        *,
        branch: Optional[str] = None,
        status: Optional[VersionStatus] = None,
        author: Optional[str] = None,
        after_ts: Optional[float] = None,
        before_ts: Optional[float] = None,
    ) -> list[KnowledgeVersion]:
        """Return versions matching all supplied criteria."""
        out: list[KnowledgeVersion] = []
        for v in self.versions:
            if branch is not None and v.branch_name != branch:
                continue
            if status is not None and v.status != status:
                continue
            if author is not None and v.author != author:
                continue
            if after_ts is not None and v.created_at <= after_ts:
                continue
            if before_ts is not None and v.created_at >= before_ts:
                continue
            out.append(v)
        return out

    def released(self) -> list[KnowledgeVersion]:
        return self.filter(status=VersionStatus.RELEASED)

    def drafts(self) -> list[KnowledgeVersion]:
        return self.filter(status=VersionStatus.DRAFT)

    def major_versions(self) -> list[KnowledgeVersion]:
        """Return one entry per major version (latest patch for each major)."""
        by_major: dict[int, KnowledgeVersion] = {}
        for v in self.versions:
            m = v.major
            if m not in by_major or v.version_seq > by_major[m].version_seq:
                by_major[m] = v
        return [by_major[m] for m in sorted(by_major)]

    def version_strings(self) -> list[str]:
        return [v.version_string for v in self.versions]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "branch":       self.branch,
            "count":        self.count,
            "fetched_at":   self.fetched_at,
            "versions":     [v.to_dict() for v in self.versions],
        }
