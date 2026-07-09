"""iios/execution/brokers/models/broker_statistics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrokerStatistics:
    """Running operational statistics for a single broker adapter."""

    broker_id:        str   = ""
    requests_total:   int   = 0
    requests_ok:      int   = 0
    requests_failed:  int   = 0
    total_latency_ms: float = 0.0
    connect_count:    int   = 0
    disconnect_count: int   = 0
    auth_count:       int   = 0
    error_count:      int   = 0
    started_at:       float = field(default_factory=time.time)
    last_request_at:  float | None = None

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_request(self, success: bool, latency_ms: float = 0.0) -> None:
        self.requests_total  += 1
        self.total_latency_ms += latency_ms
        self.last_request_at = time.time()
        if success:
            self.requests_ok += 1
        else:
            self.requests_failed += 1
            self.error_count     += 1

    def record_connect(self) -> None:
        self.connect_count += 1

    def record_disconnect(self) -> None:
        self.disconnect_count += 1

    def record_auth(self) -> None:
        self.auth_count += 1

    # ── Computed ──────────────────────────────────────────────────────────────

    def avg_latency_ms(self) -> float:
        if self.requests_total == 0:
            return 0.0
        return self.total_latency_ms / self.requests_total

    def success_rate(self) -> float:
        if self.requests_total == 0:
            return 1.0
        return self.requests_ok / self.requests_total

    def uptime_sec(self) -> float:
        return time.time() - self.started_at

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":        self.broker_id,
            "requests_total":   self.requests_total,
            "requests_ok":      self.requests_ok,
            "requests_failed":  self.requests_failed,
            "avg_latency_ms":   round(self.avg_latency_ms(), 3),
            "success_rate":     round(self.success_rate(), 4),
            "connect_count":    self.connect_count,
            "disconnect_count": self.disconnect_count,
            "auth_count":       self.auth_count,
            "error_count":      self.error_count,
            "uptime_sec":       round(self.uptime_sec(), 1),
            "last_request_at":  self.last_request_at,
        }
