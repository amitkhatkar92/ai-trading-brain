"""
iios/knowledge/versioning/models/version_diff.py
=================================================
FieldChange and RecordDiff — structured diff between two knowledge versions.

FieldChange captures a single field-level change (added / modified / removed).
RecordDiff aggregates all field changes between two version payloads and
provides a human-readable summary.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..version_constants import ChangeType

__all__ = ["FieldChange", "RecordDiff"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class FieldChange:
    """One field-level change between two payloads."""

    field_name:   str
    change_type:  ChangeType
    before_value: Any = None
    after_value:  Any = None

    @property
    def is_modification(self) -> bool:
        return self.change_type == ChangeType.MODIFIED

    @property
    def is_addition(self) -> bool:
        return self.change_type == ChangeType.ADDED

    @property
    def is_removal(self) -> bool:
        return self.change_type == ChangeType.REMOVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name":   self.field_name,
            "change_type":  self.change_type.value,
            "before_value": self.before_value,
            "after_value":  self.after_value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FieldChange":
        return cls(
            field_name   = d["field_name"],
            change_type  = ChangeType(d["change_type"]),
            before_value = d.get("before_value"),
            after_value  = d.get("after_value"),
        )


@dataclass
class RecordDiff:
    """Aggregated field-level diff between two knowledge version payloads.

    ``field_changes`` lists only fields that actually changed (ADDED,
    MODIFIED, or REMOVED) — UNCHANGED fields are omitted for brevity.
    """

    diff_id:           str                 = field(default_factory=_new_id)
    knowledge_id:      str                 = ""
    version_id_before: Optional[str]       = None
    version_id_after:  Optional[str]       = None

    field_changes:     list[FieldChange]   = field(default_factory=list)
    summary:           str                 = ""
    created_at:        float               = field(default_factory=time.time)

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def changed_fields(self) -> list[str]:
        return [fc.field_name for fc in self.field_changes]

    @property
    def change_count(self) -> int:
        return len(self.field_changes)

    @property
    def is_empty(self) -> bool:
        return not self.field_changes

    def get_change(self, field_name: str) -> Optional[FieldChange]:
        for fc in self.field_changes:
            if fc.field_name == field_name:
                return fc
        return None

    def added_fields(self) -> list[str]:
        return [fc.field_name for fc in self.field_changes
                if fc.change_type == ChangeType.ADDED]

    def modified_fields(self) -> list[str]:
        return [fc.field_name for fc in self.field_changes
                if fc.change_type == ChangeType.MODIFIED]

    def removed_fields(self) -> list[str]:
        return [fc.field_name for fc in self.field_changes
                if fc.change_type == ChangeType.REMOVED]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "diff_id":           self.diff_id,
            "knowledge_id":      self.knowledge_id,
            "version_id_before": self.version_id_before,
            "version_id_after":  self.version_id_after,
            "field_changes":     [fc.to_dict() for fc in self.field_changes],
            "summary":           self.summary,
            "created_at":        self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RecordDiff":
        return cls(
            diff_id           = d.get("diff_id",           _new_id()),
            knowledge_id      = d.get("knowledge_id",      ""),
            version_id_before = d.get("version_id_before"),
            version_id_after  = d.get("version_id_after"),
            field_changes     = [FieldChange.from_dict(fc)
                                 for fc in d.get("field_changes", [])],
            summary           = d.get("summary",           ""),
            created_at        = d.get("created_at",        time.time()),
        )
