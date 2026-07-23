"""
market_integration_snapshot.py — iios.market.integration
==========================================================
Integration-level point-in-time snapshot.

Captures the live operational state of the Market Integration engine,
including the latest published MarketSnapshot.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION


@dataclass(frozen=True)
class MarketIntegrationSnapshot:
    """
    Immutable point-in-time snapshot of the Market Integration engine state.

    Published by
    :meth:`~.market_integration_engine.MarketIntegrationEngine.snapshot`.

    Fields
    ------
    snapshot_id :        Unique snapshot identifier.
    integration_id :     Integration engine identifier.
    lifecycle_state :    Integration engine lifecycle state.
    exchange :           Primary exchange.
    request_count :      Total requests processed since start.
    success_count :      Total successful requests.
    failure_count :      Total failed requests.
    rejection_count :    Total rejected requests.
    market_snapshot_id : ID of the latest published MarketSnapshot (may be empty).
    health :             Aggregate health report dict.
    statistics :         Statistics snapshot dict.
    component_statuses : Component availability map.
    captured_at :        Wall-clock time this snapshot was taken.
    framework_version :  Framework version string.
    """
    snapshot_id:        str
    integration_id:     str
    lifecycle_state:    str
    exchange:           str
    request_count:      int
    success_count:      int
    failure_count:      int
    rejection_count:    int
    market_snapshot_id: str
    health:             Dict[str, Any]
    statistics:         Dict[str, Any]
    component_statuses: Dict[str, str]
    captured_at:        float
    framework_version:  str

    @property
    def availability_rate(self) -> float:
        total = self.request_count
        if total == 0:
            return 1.0
        return round(self.success_count / total, 4)

    @property
    def has_market_snapshot(self) -> bool:
        return bool(self.market_snapshot_id)

    @property
    def overall_health(self) -> str:
        return self.health.get("overall", "unknown")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "integration_id":     self.integration_id,
            "lifecycle_state":    self.lifecycle_state,
            "exchange":           self.exchange,
            "request_count":      self.request_count,
            "success_count":      self.success_count,
            "failure_count":      self.failure_count,
            "rejection_count":    self.rejection_count,
            "market_snapshot_id": self.market_snapshot_id,
            "availability_rate":  self.availability_rate,
            "overall_health":     self.overall_health,
            "component_statuses": dict(self.component_statuses),
            "captured_at":        self.captured_at,
            "framework_version":  self.framework_version,
        }

    @classmethod
    def create(
        cls,
        *,
        integration_id:     str                      = "",
        lifecycle_state:    str                      = "stopped",
        exchange:           str                      = "",
        request_count:      int                      = 0,
        success_count:      int                      = 0,
        failure_count:      int                      = 0,
        rejection_count:    int                      = 0,
        market_snapshot_id: str                      = "",
        health:             Optional[Dict[str, Any]] = None,
        statistics:         Optional[Dict[str, Any]] = None,
        component_statuses: Optional[Dict[str, str]] = None,
    ) -> "MarketIntegrationSnapshot":
        return cls(
            snapshot_id        = str(uuid.uuid4()),
            integration_id     = integration_id,
            lifecycle_state    = lifecycle_state,
            exchange           = exchange,
            request_count      = request_count,
            success_count      = success_count,
            failure_count      = failure_count,
            rejection_count    = rejection_count,
            market_snapshot_id = market_snapshot_id,
            health             = dict(health or {"overall": "unknown"}),
            statistics         = dict(statistics or {}),
            component_statuses = dict(component_statuses or {}),
            captured_at        = time.time(),
            framework_version  = VERSION,
        )
