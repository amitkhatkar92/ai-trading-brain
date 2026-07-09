"""iios/execution/brokers/core/broker_connection.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.broker_constants import ConnectionStatus


@dataclass
class BrokerConnection:
    """Represents the transport-layer connection to a single broker endpoint."""

    broker_id:      str              = ""
    host:           str              = ""
    port:           int              = 0
    is_ssl:         bool             = True
    status:         ConnectionStatus = ConnectionStatus.DISCONNECTED
    connection_id:  str              = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:     float            = field(default_factory=time.time)
    connected_at:   float | None     = None
    disconnected_at: float | None    = None
    last_heartbeat_at: float | None  = None
    retry_count:    int              = 0
    failure_count:  int              = 0
    error_message:  str              = ""
    metadata:       dict[str, Any]   = field(default_factory=dict)

    # ── State transitions ─────────────────────────────────────────────────────

    def mark_connected(self) -> None:
        self.status       = ConnectionStatus.CONNECTED
        self.connected_at = time.time()
        self.disconnected_at = None
        self.error_message   = ""

    def mark_disconnected(self, reason: str = "") -> None:
        self.status          = ConnectionStatus.DISCONNECTED
        self.disconnected_at = time.time()
        self.error_message   = reason

    def mark_failed(self, reason: str = "") -> None:
        self.status        = ConnectionStatus.FAILED
        self.failure_count += 1
        self.error_message = reason

    def mark_reconnecting(self) -> None:
        self.status      = ConnectionStatus.RECONNECTING
        self.retry_count += 1

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def update_heartbeat(self) -> None:
        self.last_heartbeat_at = time.time()

    def heartbeat_age_sec(self) -> float | None:
        if self.last_heartbeat_at is None:
            return None
        return time.time() - self.last_heartbeat_at

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED

    def uptime_sec(self) -> float | None:
        if self.connected_at is None:
            return None
        end = self.disconnected_at if self.disconnected_at else time.time()
        return max(0.0, end - self.connected_at)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection_id":     self.connection_id,
            "broker_id":         self.broker_id,
            "host":              self.host,
            "port":              self.port,
            "is_ssl":            self.is_ssl,
            "status":            self.status.value,
            "created_at":        self.created_at,
            "connected_at":      self.connected_at,
            "disconnected_at":   self.disconnected_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "retry_count":       self.retry_count,
            "failure_count":     self.failure_count,
            "error_message":     self.error_message,
            "metadata":          self.metadata,
        }
