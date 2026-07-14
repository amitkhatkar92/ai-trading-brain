"""iios/investment/strategy/integration/engine_health.py
Health status per source engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    HealthStatus,
    IntelligenceSource,
    STALENESS_WARNING_SECONDS,
    STALENESS_CRITICAL_SECONDS,
)
from iios.investment.strategy.integration.aggregation_state import StrategyAggregationState


@dataclass(frozen=True)
class EngineHealthEntry:
    source:              IntelligenceSource
    status:              HealthStatus
    last_update_ts:      Optional[datetime]
    gap_seconds:         Optional[float]    # seconds since last update (None if never)
    latency_ms:          Optional[float]    # not tracked internally — may be injected externally
    error_message:       Optional[str]
    checked_at:          datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":         self.source.value,
            "status":         self.status.value,
            "last_update_ts": self.last_update_ts.isoformat() if self.last_update_ts else None,
            "gap_seconds":    round(self.gap_seconds, 1) if self.gap_seconds is not None else None,
            "latency_ms":     round(self.latency_ms, 1) if self.latency_ms is not None else None,
            "error_message":  self.error_message,
            "checked_at":     self.checked_at.isoformat(),
        }


@dataclass(frozen=True)
class EngineHealthReport:
    report_id:          str
    generated_at:       datetime
    overall_status:     HealthStatus
    entries:            Dict[str, EngineHealthEntry]   # source.value → entry
    degraded_engines:   List[str]
    unavailable_engines: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":           self.report_id,
            "generated_at":        self.generated_at.isoformat(),
            "overall_status":      self.overall_status.value,
            "entries":             {k: v.to_dict() for k, v in self.entries.items()},
            "degraded_engines":    self.degraded_engines,
            "unavailable_engines": self.unavailable_engines,
        }


class EngineHealthChecker:
    """
    Derives health status for each source engine from the aggregation state map.
    Health = whether a source has published recently.
    """

    def check_all(
        self,
        state_map: Dict[str, StrategyAggregationState],
    ) -> EngineHealthReport:
        now = datetime.now(timezone.utc)
        entries: Dict[str, EngineHealthEntry] = {}

        # Collect most recent update timestamp per source across all strategies
        latest_by_source: Dict[IntelligenceSource, datetime] = {}
        for state in state_map.values():
            for src, upd in state.all_latest().items():
                ts = upd.timestamp
                if src not in latest_by_source or ts > latest_by_source[src]:
                    latest_by_source[src] = ts

        for source in IntelligenceSource:
            ts     = latest_by_source.get(source)
            gap    = (now - ts).total_seconds() if ts else None

            if ts is None:
                status = HealthStatus.UNKNOWN
            elif gap is not None and gap > STALENESS_CRITICAL_SECONDS:
                status = HealthStatus.UNAVAILABLE
            elif gap is not None and gap > STALENESS_WARNING_SECONDS:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            entries[source.value] = EngineHealthEntry(
                source=source,
                status=status,
                last_update_ts=ts,
                gap_seconds=gap,
                latency_ms=None,
                error_message=None,
                checked_at=now,
            )

        degraded     = [k for k, e in entries.items() if e.status == HealthStatus.DEGRADED]
        unavailable  = [k for k, e in entries.items() if e.status == HealthStatus.UNAVAILABLE]

        if unavailable and any(
            IntelligenceSource(k).is_required for k in unavailable
        ):
            overall = HealthStatus.UNAVAILABLE
        elif degraded:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return EngineHealthReport(
            report_id=str(uuid.uuid4()),
            generated_at=now,
            overall_status=overall,
            entries=entries,
            degraded_engines=degraded,
            unavailable_engines=unavailable,
        )
