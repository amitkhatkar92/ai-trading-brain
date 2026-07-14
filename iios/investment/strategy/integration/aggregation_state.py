"""iios/investment/strategy/integration/aggregation_state.py
Data structures representing the current aggregation state per strategy.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    UpdateType,
)


@dataclass
class IntelligenceUpdate:
    """A single intelligence update from one source engine."""
    update_id:      str
    source:         IntelligenceSource
    strategy_id:    str
    update_type:    UpdateType
    payload:        Dict[str, Any]   # source-specific data; engine does not interpret
    confidence:     float             # 0–100: source's own confidence
    schema_version: str
    timestamp:      datetime
    tags:           List[str]         = field(default_factory=list)
    correlation_id: str               = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "update_id":      self.update_id,
            "source":         self.source.value,
            "strategy_id":    self.strategy_id,
            "update_type":    self.update_type.value,
            "confidence":     round(self.confidence, 2),
            "schema_version": self.schema_version,
            "timestamp":      self.timestamp.isoformat(),
            "tags":           self.tags,
            "correlation_id": self.correlation_id,
        }


def make_update(
    source:         IntelligenceSource,
    strategy_id:    str,
    payload:        Dict[str, Any],
    confidence:     float = 75.0,
    update_type:    UpdateType = UpdateType.FULL_SNAPSHOT,
    schema_version: str = "1.0",
    tags:           Optional[List[str]] = None,
    correlation_id: str = "",
) -> IntelligenceUpdate:
    return IntelligenceUpdate(
        update_id=str(uuid.uuid4()),
        source=source,
        strategy_id=strategy_id,
        update_type=update_type,
        payload=payload,
        confidence=min(max(confidence, 0.0), 100.0),
        schema_version=schema_version,
        timestamp=datetime.now(timezone.utc),
        tags=tags or [],
        correlation_id=correlation_id,
    )


class StrategyAggregationState:
    """
    Thread-safe per-strategy aggregation state.
    Holds the latest IntelligenceUpdate from each source and a history of all updates.
    """

    def __init__(self, strategy_id: str) -> None:
        self._lock            = threading.RLock()
        self._strategy_id     = strategy_id
        self._latest:         Dict[IntelligenceSource, IntelligenceUpdate] = {}
        self._history:        List[IntelligenceUpdate] = []
        self._version:        int = 0
        self._created_at      = datetime.now(timezone.utc)
        self._last_modified:  Optional[datetime] = None

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    @property
    def last_modified(self) -> Optional[datetime]:
        with self._lock:
            return self._last_modified

    def apply(self, update: IntelligenceUpdate) -> None:
        with self._lock:
            if update.update_type == UpdateType.INVALIDATION:
                self._latest.pop(update.source, None)
            else:
                self._latest[update.source] = update
            self._history.append(update)
            self._version        += 1
            self._last_modified   = update.timestamp

    def get_latest(self, source: IntelligenceSource) -> Optional[IntelligenceUpdate]:
        with self._lock:
            return self._latest.get(source)

    def all_latest(self) -> Dict[IntelligenceSource, IntelligenceUpdate]:
        with self._lock:
            return dict(self._latest)

    def present_sources(self) -> List[IntelligenceSource]:
        with self._lock:
            return list(self._latest.keys())

    def history(self, source: Optional[IntelligenceSource] = None) -> List[IntelligenceUpdate]:
        with self._lock:
            if source:
                return [u for u in self._history if u.source == source]
            return list(self._history)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "strategy_id":      self._strategy_id,
                "version":          self._version,
                "sources_present":  [s.value for s in self._latest],
                "last_modified":    self._last_modified.isoformat() if self._last_modified else None,
                "created_at":       self._created_at.isoformat(),
                "update_count":     len(self._history),
            }
