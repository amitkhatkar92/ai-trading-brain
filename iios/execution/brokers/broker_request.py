"""iios/execution/brokers/broker_request.py
==================================================
Request dataclasses for all broker operations.

Each request type carries only the fields needed to describe WHAT to do.
It does NOT carry credentials, API keys, or transport details.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from iios.execution.brokers.constants import (
    BrokerCapabilityCode,
    BrokerMode,
    BrokerRequestType,
    Exchange,
    ProductType,
    TimeInForce,
)


# ── Base request ──────────────────────────────────────────────────────────────

@dataclass
class BrokerRequest:
    """Common fields for every broker request."""

    request_id:   str              = field(default_factory=lambda: str(uuid.uuid4()))
    broker_id:    str              = ""
    request_type: BrokerRequestType = BrokerRequestType.HEALTH
    broker_mode:  BrokerMode      = BrokerMode.PAPER
    requested_at: float           = field(default_factory=time.time)
    correlation_id: str           = ""
    metadata:     dict[str, Any]  = field(default_factory=dict)

    @property
    def age_sec(self) -> float:
        return time.time() - self.requested_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "broker_id":     self.broker_id,
            "request_type":  self.request_type.value,
            "broker_mode":   self.broker_mode.value,
            "requested_at":  self.requested_at,
            "correlation_id": self.correlation_id,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self.request_id[:8]}, broker={self.broker_id!r}, "
            f"type={self.request_type.value})"
        )


# ── Specialised request types ─────────────────────────────────────────────────

@dataclass
class ConnectionRequest(BrokerRequest):
    """Request to connect or reconnect to a broker."""

    request_type: BrokerRequestType = BrokerRequestType.CONNECTION
    reconnect:    bool = False
    timeout_sec:  float = 30.0

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"reconnect": self.reconnect, "timeout_sec": self.timeout_sec})
        return d


@dataclass
class OrderRequest(BrokerRequest):
    """Request to submit a new order via the broker."""

    request_type:  BrokerRequestType = BrokerRequestType.ORDER
    order_id:      str               = ""
    instrument:    str               = ""
    exchange:      Exchange          = Exchange.UNKNOWN
    product:       ProductType       = ProductType.UNKNOWN
    side:          str               = ""        # "BUY" | "SELL"
    quantity:      Decimal           = Decimal("0")
    order_type:    str               = ""        # "MARKET" | "LIMIT" | "STOP" …
    price:         Optional[Decimal] = None
    trigger_price: Optional[Decimal] = None
    tif:           TimeInForce       = TimeInForce.DAY
    capability:    BrokerCapabilityCode = BrokerCapabilityCode.MARKET_ORDER

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "order_id":      self.order_id,
            "instrument":    self.instrument,
            "exchange":      self.exchange.value,
            "product":       self.product.value,
            "side":          self.side,
            "quantity":      str(self.quantity),
            "order_type":    self.order_type,
            "price":         str(self.price) if self.price is not None else None,
            "trigger_price": str(self.trigger_price) if self.trigger_price else None,
            "tif":           self.tif.value,
        })
        return d


@dataclass
class ModifyRequest(BrokerRequest):
    """Request to modify an existing order."""

    request_type:  BrokerRequestType = BrokerRequestType.MODIFY
    order_id:      str               = ""
    new_quantity:  Optional[Decimal] = None
    new_price:     Optional[Decimal] = None
    new_trigger:   Optional[Decimal] = None

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "order_id":     self.order_id,
            "new_quantity": str(self.new_quantity) if self.new_quantity is not None else None,
            "new_price":    str(self.new_price)    if self.new_price    is not None else None,
            "new_trigger":  str(self.new_trigger)  if self.new_trigger  is not None else None,
        })
        return d


@dataclass
class CancelRequest(BrokerRequest):
    """Request to cancel an existing order."""

    request_type: BrokerRequestType = BrokerRequestType.CANCEL
    order_id:     str               = ""
    reason:       str               = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"order_id": self.order_id, "reason": self.reason})
        return d


@dataclass
class PositionRequest(BrokerRequest):
    """Request to fetch current open positions."""

    request_type: BrokerRequestType = BrokerRequestType.POSITION
    portfolio_id: str               = ""
    instrument:   str               = ""   # empty = all positions

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"portfolio_id": self.portfolio_id, "instrument": self.instrument})
        return d


@dataclass
class BalanceRequest(BrokerRequest):
    """Request to fetch account balance / margin."""

    request_type: BrokerRequestType = BrokerRequestType.BALANCE
    portfolio_id: str               = ""
    include_margin: bool            = True

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"portfolio_id": self.portfolio_id, "include_margin": self.include_margin})
        return d


@dataclass
class HeartbeatRequest(BrokerRequest):
    """Lightweight liveness probe."""

    request_type: BrokerRequestType = BrokerRequestType.HEARTBEAT

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict()
