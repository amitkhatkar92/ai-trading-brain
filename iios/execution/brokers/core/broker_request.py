"""iios/execution/brokers/core/broker_request.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrokerRequest:
    """Uniform request envelope sent from IIOS to a broker adapter."""

    operation:   str                = ""       # e.g. "place_order", "fetch_balance"
    payload:     dict[str, Any]     = field(default_factory=dict)
    request_id:  str                = field(default_factory=lambda: str(uuid.uuid4()))
    broker_id:   str                = ""
    account_id:  str                = ""
    timeout_sec: float              = 10.0
    metadata:    dict[str, Any]     = field(default_factory=dict)
    created_at:  float              = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":  self.request_id,
            "broker_id":   self.broker_id,
            "account_id":  self.account_id,
            "operation":   self.operation,
            "payload":     self.payload,
            "timeout_sec": self.timeout_sec,
            "metadata":    self.metadata,
            "created_at":  self.created_at,
        }
