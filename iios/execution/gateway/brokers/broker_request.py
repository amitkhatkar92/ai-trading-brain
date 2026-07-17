"""iios/execution/gateway/brokers/broker_request.py
==================================================
Standardized broker request models.

All broker operations are submitted as typed request objects.
Request objects are frozen (immutable after creation) and
carry a unique request_id for correlation.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    AssetClass,
    OrderSide,
    OrderType,
    ProductType,
    RequestType,
)


# ── Base ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrokerRequest:
    """
    Base frozen dataclass for all broker requests.

    Every concrete request type includes these fields.
    """
    request_id:   str
    request_type: RequestType
    broker_id:    str
    submitted_at: float
    metadata:     Dict[str, Any]


# ── Order request ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OrderRequest:
    """Request to place a new order."""
    request_id:    str
    broker_id:     str
    symbol:        str
    exchange:      str
    side:          OrderSide
    order_type:    OrderType
    product:       ProductType
    quantity:      float
    price:         float
    trigger_price: float
    tag:           str
    asset_class:   AssetClass
    submitted_at:  float
    metadata:      Dict[str, Any]

    request_type: RequestType = field(default=RequestType.ORDER, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "request_type":  self.request_type.value,
            "broker_id":     self.broker_id,
            "symbol":        self.symbol,
            "exchange":      self.exchange,
            "side":          self.side.value,
            "order_type":    self.order_type.value,
            "product":       self.product.value,
            "quantity":      self.quantity,
            "price":         self.price,
            "trigger_price": self.trigger_price,
            "tag":           self.tag,
            "asset_class":   self.asset_class.value,
            "submitted_at":  self.submitted_at,
            "metadata":      dict(self.metadata),
        }


# ── Modify order request ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModifyOrderRequest:
    """Request to modify a pending order."""
    request_id:    str
    broker_id:     str
    order_id:      str
    symbol:        str
    exchange:      str
    quantity:      float
    price:         float
    order_type:    OrderType
    trigger_price: float
    submitted_at:  float
    metadata:      Dict[str, Any]

    request_type: RequestType = field(default=RequestType.MODIFY_ORDER, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "request_type":  self.request_type.value,
            "broker_id":     self.broker_id,
            "order_id":      self.order_id,
            "symbol":        self.symbol,
            "exchange":      self.exchange,
            "quantity":      self.quantity,
            "price":         self.price,
            "order_type":    self.order_type.value,
            "trigger_price": self.trigger_price,
            "submitted_at":  self.submitted_at,
            "metadata":      dict(self.metadata),
        }


# ── Cancel order request ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class CancelOrderRequest:
    """Request to cancel a pending order."""
    request_id:   str
    broker_id:    str
    order_id:     str
    symbol:       str
    exchange:     str
    reason:       str
    submitted_at: float
    metadata:     Dict[str, Any]

    request_type: RequestType = field(default=RequestType.CANCEL_ORDER, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "request_type": self.request_type.value,
            "broker_id":    self.broker_id,
            "order_id":     self.order_id,
            "symbol":       self.symbol,
            "exchange":     self.exchange,
            "reason":       self.reason,
            "submitted_at": self.submitted_at,
            "metadata":     dict(self.metadata),
        }


# ── Position request ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PositionRequest:
    """Request to retrieve open positions."""
    request_id:   str
    broker_id:    str
    submitted_at: float
    metadata:     Dict[str, Any]

    request_type: RequestType = field(default=RequestType.POSITIONS, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "request_type": self.request_type.value,
            "broker_id":    self.broker_id,
            "submitted_at": self.submitted_at,
            "metadata":     dict(self.metadata),
        }


# ── Funds request ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FundsRequest:
    """Request to retrieve available funds / cash balance."""
    request_id:   str
    broker_id:    str
    submitted_at: float
    metadata:     Dict[str, Any]

    request_type: RequestType = field(default=RequestType.FUNDS, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "request_type": self.request_type.value,
            "broker_id":    self.broker_id,
            "submitted_at": self.submitted_at,
            "metadata":     dict(self.metadata),
        }


# ── Margin request ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MarginRequest:
    """Request to calculate required margin for a hypothetical order."""
    request_id:   str
    broker_id:    str
    symbol:       str
    exchange:     str
    quantity:     float
    price:        float
    order_type:   OrderType
    product:      ProductType
    side:         OrderSide
    submitted_at: float
    metadata:     Dict[str, Any]

    request_type: RequestType = field(default=RequestType.MARGIN, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "request_type": self.request_type.value,
            "broker_id":    self.broker_id,
            "symbol":       self.symbol,
            "exchange":     self.exchange,
            "quantity":     self.quantity,
            "price":        self.price,
            "order_type":   self.order_type.value,
            "product":      self.product.value,
            "side":         self.side.value,
            "submitted_at": self.submitted_at,
            "metadata":     dict(self.metadata),
        }


# ── Status request ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StatusRequest:
    """Request to retrieve broker connection / system status."""
    request_id:   str
    broker_id:    str
    submitted_at: float
    metadata:     Dict[str, Any]

    request_type: RequestType = field(default=RequestType.STATUS, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "request_type": self.request_type.value,
            "broker_id":    self.broker_id,
            "submitted_at": self.submitted_at,
            "metadata":     dict(self.metadata),
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def make_order_request(
    broker_id:     str,
    symbol:        str,
    exchange:      str,
    side:          OrderSide,
    order_type:    OrderType,
    product:       ProductType,
    quantity:      float,
    price:         float,
    *,
    trigger_price: float = 0.0,
    tag:           str = "",
    asset_class:   AssetClass = AssetClass.EQUITY,
    metadata:      Optional[Dict[str, Any]] = None,
) -> OrderRequest:
    return OrderRequest(
        request_id=str(uuid.uuid4()),
        broker_id=broker_id,
        symbol=symbol,
        exchange=exchange,
        side=side,
        order_type=order_type,
        product=product,
        quantity=quantity,
        price=price,
        trigger_price=trigger_price,
        tag=tag,
        asset_class=asset_class,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_modify_order_request(
    broker_id:    str,
    order_id:     str,
    symbol:       str,
    exchange:     str,
    quantity:     float,
    price:        float,
    order_type:   OrderType,
    *,
    trigger_price: float = 0.0,
    metadata:      Optional[Dict[str, Any]] = None,
) -> ModifyOrderRequest:
    return ModifyOrderRequest(
        request_id=str(uuid.uuid4()),
        broker_id=broker_id,
        order_id=order_id,
        symbol=symbol,
        exchange=exchange,
        quantity=quantity,
        price=price,
        order_type=order_type,
        trigger_price=trigger_price,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_cancel_order_request(
    broker_id: str,
    order_id:  str,
    symbol:    str,
    exchange:  str,
    *,
    reason:   str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> CancelOrderRequest:
    return CancelOrderRequest(
        request_id=str(uuid.uuid4()),
        broker_id=broker_id,
        order_id=order_id,
        symbol=symbol,
        exchange=exchange,
        reason=reason,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_position_request(
    broker_id: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> PositionRequest:
    return PositionRequest(
        request_id=str(uuid.uuid4()),
        broker_id=broker_id,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_funds_request(
    broker_id: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> FundsRequest:
    return FundsRequest(
        request_id=str(uuid.uuid4()),
        broker_id=broker_id,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_margin_request(
    broker_id:  str,
    symbol:     str,
    exchange:   str,
    quantity:   float,
    price:      float,
    order_type: OrderType,
    product:    ProductType,
    side:       OrderSide,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> MarginRequest:
    return MarginRequest(
        request_id=str(uuid.uuid4()),
        broker_id=broker_id,
        symbol=symbol,
        exchange=exchange,
        quantity=quantity,
        price=price,
        order_type=order_type,
        product=product,
        side=side,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_status_request(
    broker_id: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> StatusRequest:
    return StatusRequest(
        request_id=str(uuid.uuid4()),
        broker_id=broker_id,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )
