"""
market_request.py — iios.market.engine
=========================================
Immutable market workflow request value object.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    MarketWorkflowType,
    SchedulerPriority,
)
from .market_context import MarketEngineContext


@dataclass(frozen=True)
class MarketRequest:
    """
    Immutable market workflow request.

    Wraps all inputs required to execute a single market workflow pipeline.

    Fields
    ------
    request_id :          Unique request identifier.
    market_analysis_id :  Market analysis identifier.
    exchange :            Target exchange (e.g. "NSE", "BSE").
    workflow_type :       Market workflow classification.
    priority :            Scheduling priority.
    context :             Engine-level operational context.
    inputs :              Collected institutional market data snapshots.
                          Keys include: "market_feed", "index_data",
                          "sector_data", "breadth_data", "volume_data",
                          "volatility_data", "economic_calendar",
                          "corporate_actions", "news_metadata",
                          "trading_calendar", etc.
    requested_at :        Wall-clock request creation time.
    metadata :            Supplementary request metadata.
    framework_version :   Framework version string.
    """
    request_id:          str
    market_analysis_id:  str
    exchange:            str
    workflow_type:       MarketWorkflowType
    priority:            SchedulerPriority
    context:             MarketEngineContext
    inputs:              Dict[str, Any]   = field(default_factory=dict)
    requested_at:        float            = field(default_factory=time.time)
    metadata:            Dict[str, Any]   = field(default_factory=dict)
    framework_version:   str              = VERSION

    @classmethod
    def create(
        cls,
        market_analysis_id: str,
        exchange:           str,
        workflow_type:      MarketWorkflowType = MarketWorkflowType.MARKET_OVERVIEW,
        *,
        request_id:    Optional[str]                  = None,
        priority:      SchedulerPriority               = SchedulerPriority.NORMAL,
        context:       Optional[MarketEngineContext]   = None,
        instrument_id: str                            = "",
        inputs:        Optional[Dict[str, Any]]        = None,
        metadata:      Optional[Dict[str, Any]]        = None,
    ) -> "MarketRequest":
        rid = request_id or str(uuid.uuid4())
        ctx = context or MarketEngineContext.create(
            market_analysis_id,
            exchange,
            workflow_type,
            priority      = priority,
            instrument_id = instrument_id,
        )
        return cls(
            request_id         = rid,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            workflow_type      = workflow_type,
            priority           = priority,
            context            = ctx,
            inputs             = dict(inputs or {}),
            metadata           = dict(metadata or {}),
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "MarketRequest":
        """Return a new request with the given inputs merged in."""
        merged = {**self.inputs, **inputs}
        return MarketRequest(
            request_id         = self.request_id,
            market_analysis_id = self.market_analysis_id,
            exchange           = self.exchange,
            workflow_type      = self.workflow_type,
            priority           = self.priority,
            context            = self.context,
            inputs             = merged,
            requested_at       = self.requested_at,
            metadata           = dict(self.metadata),
            framework_version  = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":          self.request_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "workflow_type":       self.workflow_type.value,
            "priority":            self.priority.value,
            "input_keys":          list(self.inputs.keys()),
            "requested_at":        self.requested_at,
            "framework_version":   self.framework_version,
        }
