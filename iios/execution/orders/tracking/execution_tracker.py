"""iios/execution/orders/tracking/execution_tracker.py

Aggregate fill / execution statistics across all orders.
"""
from __future__ import annotations

import threading
from typing import Any

from ..core.order_execution import OrderExecution


class ExecutionTracker:
    """Thread-safe aggregate of all fill events processed by the OMS."""

    def __init__(self) -> None:
        self._total_fills:       int   = 0
        self._total_fill_qty:    float = 0.0
        self._total_fill_value:  float = 0.0
        self._total_commission:  float = 0.0
        self._total_slippage:    float = 0.0
        self._total_latency_ms:  float = 0.0
        self._lock               = threading.Lock()

    def record(self, execution: OrderExecution, latency_ms: float = 0.0) -> None:
        with self._lock:
            self._total_fills       += 1
            self._total_fill_qty    += execution.fill_quantity
            self._total_fill_value  += execution.fill_value
            self._total_commission  += execution.commission
            self._total_slippage    += execution.slippage
            self._total_latency_ms  += latency_ms

    @property
    def total_fills(self) -> int:
        return self._total_fills

    @property
    def avg_latency_ms(self) -> float:
        return self._total_latency_ms / self._total_fills if self._total_fills else 0.0

    @property
    def avg_commission(self) -> float:
        return self._total_commission / self._total_fills if self._total_fills else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_fills":       self._total_fills,
            "total_fill_qty":    round(self._total_fill_qty,   4),
            "total_fill_value":  round(self._total_fill_value, 4),
            "total_commission":  round(self._total_commission, 4),
            "total_slippage":    round(self._total_slippage,   4),
            "avg_latency_ms":    round(self.avg_latency_ms,    2),
            "avg_commission":    round(self.avg_commission,    4),
        }

    def reset(self) -> None:
        with self._lock:
            self._total_fills      = 0
            self._total_fill_qty   = 0.0
            self._total_fill_value = 0.0
            self._total_commission = 0.0
            self._total_slippage   = 0.0
            self._total_latency_ms = 0.0
