"""iios/investment/strategy/integration/strategy_state.py
StrategyState — lightweight per-strategy derived state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    SnapshotStatus,
    ValidationStatus,
)


@dataclass
class SourceSummary:
    """Compact summary extracted from one source's latest intelligence update."""
    source:      IntelligenceSource
    headline:    str               # one-line summary
    score:       Optional[float]   # 0–100 if applicable
    status:      str               # source-specific status string
    confidence:  float
    updated_at:  datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":     self.source.value,
            "headline":   self.headline,
            "score":      round(self.score, 2) if self.score is not None else None,
            "status":     self.status,
            "confidence": round(self.confidence, 2),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class StrategyState:
    """
    Derived strategy state assembled from all source summaries.
    Immutable once built.
    """
    strategy_id:        str
    source_summaries:   Dict[str, SourceSummary]  # source.value → summary
    snapshot_status:    SnapshotStatus
    validation_status:  ValidationStatus
    completeness:       float                       # 0–1
    active_conflicts:   int
    intelligence_score: float                       # 0–100 overall
    computed_at:        datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":        self.strategy_id,
            "source_summaries":   {k: v.to_dict() for k, v in self.source_summaries.items()},
            "snapshot_status":    self.snapshot_status.value,
            "validation_status":  self.validation_status.value,
            "completeness":       round(self.completeness, 4),
            "active_conflicts":   self.active_conflicts,
            "intelligence_score": round(self.intelligence_score, 2),
            "computed_at":        self.computed_at.isoformat(),
        }


def _extract_source_summary(
    source:  IntelligenceSource,
    payload: Dict[str, Any],
    confidence: float,
    timestamp:  datetime,
) -> SourceSummary:
    """
    Generic extractor — reads common keys (headline, score, status) from payload.
    Source-specific logic can be added here.
    """
    headline = str(payload.get("headline", payload.get("summary", f"{source.display_name} update")))
    score    = payload.get("score")
    status   = str(payload.get("status", "active"))
    if score is not None:
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = None
    return SourceSummary(
        source=source,
        headline=headline[:200],
        score=score,
        status=status,
        confidence=confidence,
        updated_at=timestamp,
    )
