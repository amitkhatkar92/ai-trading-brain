"""iios/investment/decision/evidence/change_tracker.py
ChangeTracker — detects changes between successive evidence snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


@dataclass(frozen=True)
class ValueChange:
    key:          str
    old_value:    Any
    new_value:    Any
    delta:        Optional[float]   # numeric delta when both values are numeric
    pct_change:   Optional[float]   # percentage change when meaningful

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":        self.key,
            "old_value":  self.old_value,
            "new_value":  self.new_value,
            "delta":      self.delta,
            "pct_change": self.pct_change,
        }


@dataclass(frozen=True)
class ChangeReport:
    decision_id:     str
    from_snapshot:   str
    to_snapshot:     str
    item_added:      int
    item_removed:    int
    value_changes:   Tuple[ValueChange, ...]
    quality_delta:   float   # new_quality - old_quality
    has_changes:     bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":   self.decision_id,
            "from_snapshot": self.from_snapshot,
            "to_snapshot":   self.to_snapshot,
            "item_added":    self.item_added,
            "item_removed":  self.item_removed,
            "value_changes": [v.to_dict() for v in self.value_changes],
            "quality_delta": self.quality_delta,
            "has_changes":   self.has_changes,
        }


class ChangeTracker:
    """Computes the diff between two EvidenceSnapshots."""

    def compare(
        self,
        old: EvidenceSnapshot,
        new: EvidenceSnapshot,
    ) -> ChangeReport:
        old_by_key = {i.key: i for i in old.items}
        new_by_key = {i.key: i for i in new.items}

        added   = sum(1 for k in new_by_key if k not in old_by_key)
        removed = sum(1 for k in old_by_key if k not in new_by_key)

        changes: List[ValueChange] = []
        for key in set(old_by_key) & set(new_by_key):
            ov = old_by_key[key].value
            nv = new_by_key[key].value
            if ov != nv:
                delta = pct = None
                try:
                    o_f, n_f = float(ov), float(nv)
                    delta = round(n_f - o_f, 6)
                    if o_f != 0:
                        pct = round((n_f - o_f) / abs(o_f) * 100.0, 2)
                except (TypeError, ValueError):
                    pass
                changes.append(ValueChange(
                    key=key, old_value=ov, new_value=nv,
                    delta=delta, pct_change=pct,
                ))

        quality_delta = round(new.quality_score - old.quality_score, 2)
        has_changes   = bool(added or removed or changes)

        return ChangeReport(
            decision_id=new.decision_id,
            from_snapshot=old.snapshot_id,
            to_snapshot=new.snapshot_id,
            item_added=added,
            item_removed=removed,
            value_changes=tuple(changes),
            quality_delta=quality_delta,
            has_changes=has_changes,
        )
