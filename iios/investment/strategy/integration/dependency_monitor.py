"""iios/investment/strategy/integration/dependency_monitor.py
Tracks which intelligence sources have been seen recently.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    STALENESS_WARNING_SECONDS,
)


@dataclass
class DependencyStatus:
    source:       IntelligenceSource
    is_available: bool
    last_seen:    Optional[datetime]
    gap_seconds:  Optional[float]
    error_count:  int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":       self.source.value,
            "is_available": self.is_available,
            "last_seen":    self.last_seen.isoformat() if self.last_seen else None,
            "gap_seconds":  round(self.gap_seconds, 1) if self.gap_seconds is not None else None,
            "error_count":  self.error_count,
        }


class DependencyMonitor:
    """
    Records when each IntelligenceSource was last observed and flags missing sources.
    Does NOT check external network connections — derived purely from submitted updates.
    """

    def __init__(self) -> None:
        self._lock:      threading.RLock                   = threading.RLock()
        self._last_seen: Dict[IntelligenceSource, datetime] = {}
        self._errors:    Dict[IntelligenceSource, int]      = {}

    def record_seen(self, source: IntelligenceSource) -> None:
        with self._lock:
            self._last_seen[source] = datetime.now(timezone.utc)

    def record_error(self, source: IntelligenceSource) -> None:
        with self._lock:
            self._errors[source] = self._errors.get(source, 0) + 1

    def check_all(self) -> Dict[IntelligenceSource, DependencyStatus]:
        now = datetime.now(timezone.utc)
        with self._lock:
            result: Dict[IntelligenceSource, DependencyStatus] = {}
            for source in IntelligenceSource:
                ts  = self._last_seen.get(source)
                gap = (now - ts).total_seconds() if ts else None
                ok  = ts is not None and (gap is None or gap <= STALENESS_WARNING_SECONDS)
                result[source] = DependencyStatus(
                    source=source,
                    is_available=ok,
                    last_seen=ts,
                    gap_seconds=gap,
                    error_count=self._errors.get(source, 0),
                )
            return result

    def missing_sources(
        self,
        threshold_seconds: float = STALENESS_WARNING_SECONDS,
    ) -> List[IntelligenceSource]:
        now = datetime.now(timezone.utc)
        with self._lock:
            missing = []
            for source in IntelligenceSource:
                ts = self._last_seen.get(source)
                if ts is None:
                    missing.append(source)
                elif (now - ts).total_seconds() > threshold_seconds:
                    missing.append(source)
            return missing
