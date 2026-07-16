"""iios/execution/brokers/broker_response.py
==================================================
Response dataclasses for all broker operations.

Responses carry only the outcome data.  They do NOT carry credentials,
transport headers, or HTTP status codes.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from iios.execution.brokers.constants import (
    BrokerConnectionState,
    BrokerHealthStatus,
    BrokerRequestType,
    BrokerResponseStatus,
)


# ── Base response ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrokerResponse:
    """Common fields for every broker response."""

    response_id:    str                  = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:     str                  = ""
    broker_id:      str                  = ""
    request_type:   BrokerRequestType   = BrokerRequestType.HEALTH
    status:         BrokerResponseStatus = BrokerResponseStatus.SUCCESS
    responded_at:   float                = field(default_factory=time.time)
    duration_ms:    float                = 0.0
    error_message:  str                  = ""
    error_code:     str                  = ""
    correlation_id: str                  = ""
    metadata:       dict[str, Any]       = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == BrokerResponseStatus.SUCCESS

    @property
    def failed(self) -> bool:
        return self.status in (
            BrokerResponseStatus.FAILURE,
            BrokerResponseStatus.REJECTED,
            BrokerResponseStatus.TIMEOUT,
        )

    @property
    def has_error(self) -> bool:
        return bool(self.error_message) or self.failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id":    self.response_id,
            "request_id":     self.request_id,
            "broker_id":      self.broker_id,
            "request_type":   self.request_type.value,
            "status":         self.status.value,
            "succeeded":      self.succeeded,
            "responded_at":   self.responded_at,
            "duration_ms":    self.duration_ms,
            "error_message":  self.error_message,
            "error_code":     self.error_code,
            "correlation_id": self.correlation_id,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self.response_id[:8]}, broker={self.broker_id!r}, "
            f"status={self.status.value})"
        )


# ── Specialised response types ────────────────────────────────────────────────

@dataclass(frozen=True)
class ConnectionResponse(BrokerResponse):
    """Response to a ConnectionRequest."""

    request_type:     BrokerRequestType    = BrokerRequestType.CONNECTION
    connection_state: BrokerConnectionState = BrokerConnectionState.DISCONNECTED

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["connection_state"] = self.connection_state.value
        return d


@dataclass(frozen=True)
class OrderResponse(BrokerResponse):
    """Response to an OrderRequest."""

    request_type:      BrokerRequestType = BrokerRequestType.ORDER
    order_id:          str               = ""
    broker_order_id:   str               = ""    # exchange / broker reference
    submitted_qty:     Decimal           = Decimal("0")
    acknowledged:      bool              = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "order_id":        self.order_id,
            "broker_order_id": self.broker_order_id,
            "submitted_qty":   str(self.submitted_qty),
            "acknowledged":    self.acknowledged,
        })
        return d


@dataclass(frozen=True)
class ModifyResponse(BrokerResponse):
    """Response to a ModifyRequest."""

    request_type:    BrokerRequestType = BrokerRequestType.MODIFY
    order_id:        str               = ""
    broker_order_id: str               = ""
    modified:        bool              = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "order_id":        self.order_id,
            "broker_order_id": self.broker_order_id,
            "modified":        self.modified,
        })
        return d


@dataclass(frozen=True)
class CancelResponse(BrokerResponse):
    """Response to a CancelRequest."""

    request_type:    BrokerRequestType = BrokerRequestType.CANCEL
    order_id:        str               = ""
    broker_order_id: str               = ""
    cancelled:       bool              = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "order_id":        self.order_id,
            "broker_order_id": self.broker_order_id,
            "cancelled":       self.cancelled,
        })
        return d


@dataclass(frozen=True)
class PositionItem:
    """A single open position."""
    instrument:    str
    exchange:      str
    quantity:      Decimal   = Decimal("0")
    average_price: Decimal   = Decimal("0")
    current_price: Decimal   = Decimal("0")
    pnl:           Decimal   = Decimal("0")
    product:       str       = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument":    self.instrument,
            "exchange":      self.exchange,
            "quantity":      str(self.quantity),
            "average_price": str(self.average_price),
            "current_price": str(self.current_price),
            "pnl":           str(self.pnl),
            "product":       self.product,
        }


@dataclass(frozen=True)
class PositionResponse(BrokerResponse):
    """Response to a PositionRequest."""

    request_type: BrokerRequestType = BrokerRequestType.POSITION
    positions:    tuple[PositionItem, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["positions"] = [p.to_dict() for p in self.positions]
        return d


@dataclass(frozen=True)
class BalanceResponse(BrokerResponse):
    """Response to a BalanceRequest."""

    request_type:     BrokerRequestType = BrokerRequestType.BALANCE
    available_cash:   Decimal           = Decimal("0")
    used_margin:      Decimal           = Decimal("0")
    available_margin: Decimal           = Decimal("0")
    total_value:      Decimal           = Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "available_cash":   str(self.available_cash),
            "used_margin":      str(self.used_margin),
            "available_margin": str(self.available_margin),
            "total_value":      str(self.total_value),
        })
        return d


@dataclass(frozen=True)
class HealthResponse(BrokerResponse):
    """Response to a health check."""

    request_type:  BrokerRequestType = BrokerRequestType.HEALTH
    health_status: BrokerHealthStatus = BrokerHealthStatus.UNKNOWN
    latency_ms:    float              = 0.0
    message:       str                = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "health_status": self.health_status.value,
            "latency_ms":    self.latency_ms,
            "message":       self.message,
        })
        return d
