"""
market_context.py — iios.market.lifecycle
===========================================
Immutable operational context attached to a market session.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    MarketPriority,
    MarketScope,
    MarketTimeframe,
    MarketType,
)


@dataclass(frozen=True)
class MarketContext:
    """
    Immutable operational context that parameterises a market session.

    Captured at session creation; never mutated afterwards.

    Fields
    ------
    context_id :        Unique identifier.
    market_analysis_id: Market analysis correlation identifier.
    workflow_id :       Optional workflow routing context.
    exchange :          Exchange or venue identifier (e.g. "NSE", "BSE").
    market_type :       Type of market being analysed.
    market_scope :      Scope of the market analysis.
    market_priority :   Priority level of this session.
    timeframe :         Analysis timeframe.
    metadata :          Supplementary context metadata.
    framework_version : Framework version.
    """
    context_id:          str
    market_analysis_id:  str
    workflow_id:         str            = ""
    exchange:            str            = ""
    market_type:         MarketType     = MarketType.CUSTOM
    market_scope:        MarketScope    = MarketScope.DOMESTIC
    market_priority:     MarketPriority = MarketPriority.MEDIUM
    timeframe:           MarketTimeframe = MarketTimeframe.D1
    metadata:            Dict[str, Any] = field(default_factory=dict)
    framework_version:   str            = VERSION

    @classmethod
    def create(
        cls,
        market_analysis_id: str,
        *,
        context_id:       Optional[str]            = None,
        workflow_id:      str                       = "",
        exchange:         str                       = "",
        market_type:      MarketType                = MarketType.CUSTOM,
        market_scope:     MarketScope               = MarketScope.DOMESTIC,
        market_priority:  MarketPriority            = MarketPriority.MEDIUM,
        timeframe:        MarketTimeframe            = MarketTimeframe.D1,
        metadata:         Optional[Dict[str, Any]]  = None,
    ) -> "MarketContext":
        return cls(
            context_id         = context_id or str(uuid.uuid4()),
            market_analysis_id = market_analysis_id,
            workflow_id        = workflow_id,
            exchange           = exchange,
            market_type        = market_type,
            market_scope       = market_scope,
            market_priority    = market_priority,
            timeframe          = timeframe,
            metadata           = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":          self.context_id,
            "market_analysis_id":  self.market_analysis_id,
            "workflow_id":         self.workflow_id,
            "exchange":            self.exchange,
            "market_type":         self.market_type.value,
            "market_scope":        self.market_scope.value,
            "market_priority":     self.market_priority.value,
            "timeframe":           self.timeframe.value,
            "framework_version":   self.framework_version,
        }
