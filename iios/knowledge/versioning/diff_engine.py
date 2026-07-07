"""
iios/knowledge/versioning/diff_engine.py
=========================================
DiffEngine — computes field-level diffs between two knowledge version
payloads and produces a structured RecordDiff.

Key behaviours:
- Recursively compares flat and nested dict payloads.
- Fields in DIFF_SKIP_FIELDS (timestamps, monotonic counters) are excluded
  to suppress spurious changes that carry no semantic meaning.
- Both string and non-string values are compared by equality; no fuzzy matching.
- A human-readable summary is auto-generated.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .version_constants import ChangeType, DIFF_SKIP_FIELDS
from .version_exceptions import DiffError
from .models.version_diff import FieldChange, RecordDiff

__all__ = ["DiffEngine", "get_diff_engine", "reset_diff_engine"]

_LOG = logging.getLogger("iios.knowledge.versioning.diff")
_lock = threading.Lock()
_engine: Optional["DiffEngine"] = None


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict to dot-separated keys (single level deep for
    standard KnowledgeRecord payloads).  Scalars and lists are left as-is."""
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out.update(_flatten(v, full_key))
            else:
                out[full_key] = v
    else:
        out[prefix] = obj
    return out


class DiffEngine:
    """Stateless engine that computes field-level diffs between payloads."""

    # ── Core diff ─────────────────────────────────────────────────────────────

    def compute_delta(
        self,
        payload_before: dict[str, Any],
        payload_after:  dict[str, Any],
        skip_fields:    Optional[frozenset[str]] = None,
    ) -> list[FieldChange]:
        """Return a list of FieldChange for every differing field.

        Only ADDED, MODIFIED, and REMOVED changes are returned;
        UNCHANGED fields are omitted.
        """
        skip = skip_fields if skip_fields is not None else DIFF_SKIP_FIELDS

        before_flat = _flatten(payload_before)
        after_flat  = _flatten(payload_after)

        all_keys = set(before_flat) | set(after_flat)
        changes: list[FieldChange] = []

        for key in sorted(all_keys):
            # Strip the base part for skip check (e.g. "metadata.updated_at")
            base = key.split(".")[-1]
            if base in skip:
                continue

            in_before = key in before_flat
            in_after  = key in after_flat

            if in_before and in_after:
                bv, av = before_flat[key], after_flat[key]
                if bv != av:
                    changes.append(FieldChange(key, ChangeType.MODIFIED, bv, av))
            elif in_before:
                changes.append(FieldChange(key, ChangeType.REMOVED,
                                           before_flat[key], None))
            else:
                changes.append(FieldChange(key, ChangeType.ADDED,
                                           None, after_flat[key]))

        return changes

    def compute_diff(
        self,
        knowledge_id:      str,
        version_before:    Any,   # KnowledgeVersion
        version_after:     Any,   # KnowledgeVersion
        skip_fields:       Optional[frozenset[str]] = None,
    ) -> RecordDiff:
        """Build a full RecordDiff from two KnowledgeVersion objects."""
        try:
            changes = self.compute_delta(
                version_before.payload,
                version_after.payload,
                skip_fields=skip_fields,
            )
        except Exception as exc:
            raise DiffError(
                f"Diff computation failed for '{knowledge_id}': {exc}",
                code="DE-001",
            ) from exc

        summary = self._summarize(changes)
        return RecordDiff(
            knowledge_id      = knowledge_id,
            version_id_before = version_before.version_id,
            version_id_after  = version_after.version_id,
            field_changes     = changes,
            summary           = summary,
        )

    def compute_diff_payloads(
        self,
        knowledge_id: str,
        payload_before: dict[str, Any],
        payload_after:  dict[str, Any],
        version_id_before: Optional[str] = None,
        version_id_after:  Optional[str] = None,
        skip_fields: Optional[frozenset[str]] = None,
    ) -> RecordDiff:
        """Build a RecordDiff directly from raw payloads."""
        changes = self.compute_delta(payload_before, payload_after,
                                     skip_fields=skip_fields)
        return RecordDiff(
            knowledge_id      = knowledge_id,
            version_id_before = version_id_before,
            version_id_after  = version_id_after,
            field_changes     = changes,
            summary           = self._summarize(changes),
        )

    # ── Summary generation ────────────────────────────────────────────────────

    @staticmethod
    def _summarize(changes: list[FieldChange]) -> str:
        if not changes:
            return "No changes."
        added    = [c.field_name for c in changes if c.change_type == ChangeType.ADDED]
        modified = [c.field_name for c in changes if c.change_type == ChangeType.MODIFIED]
        removed  = [c.field_name for c in changes if c.change_type == ChangeType.REMOVED]
        parts: list[str] = []
        if modified:
            parts.append(f"modified: {', '.join(modified[:5])}"
                         + (f" (+{len(modified)-5} more)" if len(modified) > 5 else ""))
        if added:
            parts.append(f"added: {', '.join(added[:5])}")
        if removed:
            parts.append(f"removed: {', '.join(removed[:5])}")
        return "; ".join(parts)

    # ── Conflict detection ────────────────────────────────────────────────────

    def detect_conflict_fields(
        self,
        source_changes: RecordDiff,
        target_changes: RecordDiff,
    ) -> list[str]:
        """Return field names modified in BOTH source and target diffs."""
        src_modified = set(source_changes.changed_fields)
        tgt_modified = set(target_changes.changed_fields)
        return sorted(src_modified & tgt_modified)


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_diff_engine() -> DiffEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = DiffEngine()
    return _engine


def reset_diff_engine() -> None:
    global _engine
    with _lock:
        _engine = None
