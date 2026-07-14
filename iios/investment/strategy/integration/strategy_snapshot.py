"""iios/investment/strategy/integration/strategy_snapshot.py
StrategySnapshot — the canonical, immutable, publishable intelligence view.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    SnapshotStatus,
    ValidationStatus,
)
from iios.investment.strategy.integration.aggregation_state import StrategyAggregationState
from iios.investment.strategy.integration.strategy_summary import StrategySummary
from iios.investment.strategy.integration.validation_report import ValidationReport
from iios.investment.strategy.integration.conflict_classifier import Conflict


@dataclass(frozen=True)
class StrategySnapshot:
    """
    The canonical Strategy Intelligence Snapshot.

    This is the ONLY Strategy Intelligence interface consumed by downstream components:
    - Decision Layer
    - Portfolio AI
    - Execution Layer
    - Investment Intelligence Layer

    This snapshot is read-only. It contains integrated, validated intelligence.
    It does NOT contain trading decisions or orders.
    """
    snapshot_id:        str
    strategy_id:        str
    generated_at:       datetime
    version:            int

    # Aggregated source summaries (None = source not yet available)
    source_payloads:    Dict[str, Dict[str, Any]]  # source.value → payload dict
    sources_present:    Tuple[str, ...]
    last_updated_by:    Dict[str, str]              # source.value → ISO timestamp

    # Composed views
    summary:            StrategySummary
    validation_report:  ValidationReport

    # Active conflicts (unresolved)
    active_conflicts:   Tuple[Dict[str, Any], ...]  # serialised for immutability

    # Scoring
    intelligence_score: float    # 0–100 overall
    quality_score:      float    # 0–100
    confidence_score:   float    # 0–100

    # Status
    status:             SnapshotStatus
    validation_status:  ValidationStatus
    completeness:       float    # 0–1
    freshness_score:    float    # 0–1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "strategy_id":        self.strategy_id,
            "generated_at":       self.generated_at.isoformat(),
            "version":            self.version,
            "sources_present":    list(self.sources_present),
            "last_updated_by":    self.last_updated_by,
            "summary":            self.summary.to_dict(),
            "validation_report":  self.validation_report.to_dict(),
            "active_conflicts":   list(self.active_conflicts),
            "intelligence_score": round(self.intelligence_score, 2),
            "quality_score":      round(self.quality_score, 2),
            "confidence_score":   round(self.confidence_score, 2),
            "status":             self.status.value,
            "validation_status":  self.validation_status.value,
            "completeness":       round(self.completeness, 4),
            "freshness_score":    round(self.freshness_score, 4),
        }


def build_snapshot(
    state:              StrategyAggregationState,
    summary:            StrategySummary,
    validation_report:  ValidationReport,
    active_conflicts:   List[Conflict],
    intelligence_score: float,
    quality_score:      float,
    confidence_score:   float,
    freshness_score:    float,
) -> StrategySnapshot:
    latest = state.all_latest()

    # Serialise source payloads for immutability
    source_payloads = {
        src.value: dict(upd.payload)
        for src, upd in latest.items()
    }

    last_updated_by = {
        src.value: upd.timestamp.isoformat()
        for src, upd in latest.items()
    }

    sources_present = tuple(sorted(src.value for src in latest.keys()))

    active_conflict_dicts = tuple(
        c.to_dict() for c in active_conflicts
    )

    # Determine status
    if intelligence_score == 0 and not latest:
        snap_status = SnapshotStatus.PENDING
    elif validation_report.status == ValidationStatus.FAILED:
        snap_status = SnapshotStatus.INVALID
    elif summary.completeness < 0.5:
        snap_status = SnapshotStatus.PARTIAL
    elif freshness_score < 0.5:
        snap_status = SnapshotStatus.STALE
    else:
        snap_status = SnapshotStatus.COMPLETE

    return StrategySnapshot(
        snapshot_id=str(uuid.uuid4()),
        strategy_id=state.strategy_id,
        generated_at=datetime.now(timezone.utc),
        version=state.version,
        source_payloads=source_payloads,
        sources_present=sources_present,
        last_updated_by=last_updated_by,
        summary=summary,
        validation_report=validation_report,
        active_conflicts=active_conflict_dicts,
        intelligence_score=round(intelligence_score, 2),
        quality_score=round(quality_score, 2),
        confidence_score=round(confidence_score, 2),
        status=snap_status,
        validation_status=validation_report.status,
        completeness=round(summary.completeness, 4),
        freshness_score=round(freshness_score, 4),
    )
