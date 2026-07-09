"""iios/execution/orders/core/order_metadata.py

Extended, mutable metadata attached to an order for analytics and decision context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderMetadata:
    """Rich metadata accompanying an order — does not affect execution logic."""

    order_id: str = ""

    # Decision context
    source:          str   = ""     # originating system / agent
    signal_strength: float = 0.0    # 0-1
    confidence:      float = 0.0    # 0-1
    decision_score:  float = 0.0

    # Risk context
    risk_score:           float = 0.0
    expected_slippage:    float = 0.0
    market_impact_est:    float = 0.0
    liquidity_score:      float = 0.0

    # Portfolio context
    portfolio_weight_before: float = 0.0
    portfolio_weight_after:  float = 0.0

    # Annotation
    notes:           str        = ""
    labels:          list[str]  = field(default_factory=list)
    custom:          dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id":               self.order_id,
            "source":                 self.source,
            "signal_strength":        self.signal_strength,
            "confidence":             self.confidence,
            "decision_score":         self.decision_score,
            "risk_score":             self.risk_score,
            "expected_slippage":      self.expected_slippage,
            "market_impact_est":      self.market_impact_est,
            "liquidity_score":        self.liquidity_score,
            "portfolio_weight_before": self.portfolio_weight_before,
            "portfolio_weight_after":  self.portfolio_weight_after,
            "notes":                  self.notes,
            "labels":                 list(self.labels),
            "custom":                 dict(self.custom),
        }
