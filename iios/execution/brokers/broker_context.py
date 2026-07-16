"""iios/execution/brokers/broker_context.py
==================================================
BrokerOperationContext — immutable context snapshot for a single
broker operation, propagated through validation and event dispatch.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.broker_request import BrokerRequest
from iios.execution.brokers.constants import (
    BrokerConnectionState,
    BrokerHealthStatus,
    BrokerMode,
    BrokerRequestType,
)


@dataclass(frozen=True)
class BrokerOperationContext:
    """
    Immutable snapshot describing the context for a single broker operation.

    Created by BrokerManager before delegating to a broker adapter.
    Passed into validators and event publishers.
    """

    context_id:       str              = field(default_factory=lambda: str(uuid.uuid4()))
    operation_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    broker_id:        str              = ""
    operation:        str              = ""
    request_type:     BrokerRequestType = BrokerRequestType.HEALTH
    broker_mode:      BrokerMode       = BrokerMode.PAPER
    connection_state: BrokerConnectionState = BrokerConnectionState.DISCONNECTED
    health_status:    BrokerHealthStatus    = BrokerHealthStatus.UNKNOWN
    request_id:       str              = ""
    correlation_id:   str              = ""
    created_at:       float            = field(default_factory=time.time)
    metadata:         dict[str, Any]   = field(default_factory=dict)

    @property
    def is_connected(self) -> bool:
        return self.connection_state == BrokerConnectionState.CONNECTED

    @property
    def is_healthy(self) -> bool:
        return self.health_status == BrokerHealthStatus.HEALTHY

    @property
    def age_ms(self) -> float:
        return (time.time() - self.created_at) * 1_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":       self.context_id,
            "operation_id":     self.operation_id,
            "broker_id":        self.broker_id,
            "operation":        self.operation,
            "request_type":     self.request_type.value,
            "broker_mode":      self.broker_mode.value,
            "connection_state": self.connection_state.value,
            "health_status":    self.health_status.value,
            "request_id":       self.request_id,
            "correlation_id":   self.correlation_id,
            "created_at":       self.created_at,
            "is_connected":     self.is_connected,
            "is_healthy":       self.is_healthy,
        }

    def __repr__(self) -> str:
        return (
            f"BrokerOperationContext("
            f"broker={self.broker_id!r}, op={self.operation!r}, "
            f"connected={self.is_connected})"
        )


def make_context(
    broker_id:        str,
    operation:        str,
    request:          BrokerRequest,
    *,
    connection_state: BrokerConnectionState = BrokerConnectionState.DISCONNECTED,
    health_status:    BrokerHealthStatus    = BrokerHealthStatus.UNKNOWN,
    metadata:         dict[str, Any] | None = None,
) -> BrokerOperationContext:
    """Factory function for BrokerOperationContext."""
    return BrokerOperationContext(
        broker_id        = broker_id,
        operation        = operation,
        request_type     = request.request_type,
        broker_mode      = request.broker_mode,
        connection_state = connection_state,
        health_status    = health_status,
        request_id       = request.request_id,
        correlation_id   = request.correlation_id,
        metadata         = metadata or {},
    )
