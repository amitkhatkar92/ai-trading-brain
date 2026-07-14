"""iios/investment/decision/integration/decision_state.py
DecisionState — the overall integration-level status of a decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, FrozenSet

from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    SnapshotStatus,
)


@dataclass(frozen=True)
class IntegrationDecisionState:
    """
    Derived integration state for a single decision.
    Computed from AggregationState + ValidationReport + ConflictReport.
    """
    decision_id:         str
    subject_id:          str
    subject_type:        str
    snapshot_status:     SnapshotStatus
    completeness:        float          # 0–1
    present_components:  FrozenSet[str]
    missing_required:    FrozenSet[str]
    has_conflicts:       bool
    blocks_publishing:   bool
    is_valid:            bool
    version:             int
    computed_at:         datetime

    @property
    def is_complete(self) -> bool:
        return self.snapshot_status == SnapshotStatus.COMPLETE

    @property
    def is_publishable(self) -> bool:
        return (
            self.snapshot_status in {SnapshotStatus.COMPLETE, SnapshotStatus.PARTIAL}
            and not self.blocks_publishing
            and self.is_valid
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":        self.decision_id,
            "subject_id":         self.subject_id,
            "subject_type":       self.subject_type,
            "snapshot_status":    self.snapshot_status.value,
            "completeness":       round(self.completeness, 3),
            "present_components": sorted(self.present_components),
            "missing_required":   sorted(self.missing_required),
            "has_conflicts":      self.has_conflicts,
            "blocks_publishing":  self.blocks_publishing,
            "is_valid":           self.is_valid,
            "is_publishable":     self.is_publishable,
            "version":            self.version,
            "computed_at":        self.computed_at.isoformat(),
        }


def build_decision_state(
    decision_id:      str,
    subject_id:       str,
    subject_type:     str,
    completeness:     float,
    present:          FrozenSet,
    blocks_publishing: bool,
    is_valid:         bool,
    version:          int,
) -> IntegrationDecisionState:
    required    = ComponentId.required()
    missing     = frozenset(c.value for c in required if c not in present)
    present_str = frozenset(c.value if hasattr(c, "value") else str(c) for c in present)

    if completeness >= 1.0:
        status = SnapshotStatus.COMPLETE
    elif completeness > 0.0:
        status = SnapshotStatus.PARTIAL
    else:
        status = SnapshotStatus.FAILED

    return IntegrationDecisionState(
        decision_id        = decision_id,
        subject_id         = subject_id,
        subject_type       = subject_type,
        snapshot_status    = status,
        completeness       = completeness,
        present_components = present_str,
        missing_required   = missing,
        has_conflicts      = False,      # set by caller if needed
        blocks_publishing  = blocks_publishing,
        is_valid           = is_valid,
        version            = version,
        computed_at        = datetime.now(timezone.utc),
    )
