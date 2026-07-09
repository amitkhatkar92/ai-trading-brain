"""iios/execution/brokers/connection/connection_health.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.broker_constants import BrokerStatus, ConnectionStatus


@dataclass
class ConnectionHealth:
    """Point-in-time health snapshot for a single broker connection."""

    broker_id:         str              = ""
    is_healthy:        bool             = True
    broker_status:     BrokerStatus     = BrokerStatus.UNKNOWN
    connection_status: ConnectionStatus = ConnectionStatus.UNKNOWN
    response_time_ms:  float            = 0.0
    error_message:     str              = ""
    last_check_at:     float            = field(default_factory=time.time)
    heartbeat_age_sec: float | None     = None
    circuit_open:      bool             = False
    retry_count:       int              = 0
    uptime_sec:        float | None     = None
    check_id:          str              = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:          dict[str, Any]   = field(default_factory=dict)

    @classmethod
    def healthy(
        cls,
        broker_id: str,
        response_time_ms: float = 0.0,
        **kwargs: Any,
    ) -> ConnectionHealth:
        return cls(
            broker_id=broker_id,
            is_healthy=True,
            broker_status=BrokerStatus.CONNECTED,
            connection_status=ConnectionStatus.CONNECTED,
            response_time_ms=response_time_ms,
            **kwargs,
        )

    @classmethod
    def unhealthy(
        cls,
        broker_id: str,
        error_message: str = "",
        **kwargs: Any,
    ) -> ConnectionHealth:
        return cls(
            broker_id=broker_id,
            is_healthy=False,
            broker_status=BrokerStatus.ERROR,
            connection_status=ConnectionStatus.FAILED,
            error_message=error_message,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id":          self.check_id,
            "broker_id":         self.broker_id,
            "is_healthy":        self.is_healthy,
            "broker_status":     self.broker_status.value,
            "connection_status": self.connection_status.value,
            "response_time_ms":  self.response_time_ms,
            "error_message":     self.error_message,
            "last_check_at":     self.last_check_at,
            "heartbeat_age_sec": self.heartbeat_age_sec,
            "circuit_open":      self.circuit_open,
            "retry_count":       self.retry_count,
            "uptime_sec":        self.uptime_sec,
            "metadata":          self.metadata,
        }
