"""
market_context.py — iios.market.engine
=========================================
Immutable engine-level operational context for a market workflow request.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    MarketWorkflowType,
    SchedulerPriority,
)


@dataclass(frozen=True)
class MarketEngineContext:
    """
    Immutable operational context attached to a market workflow request.

    Captured at request creation; never mutated afterwards.

    Fields
    ------
    context_id :          Unique identifier.
    market_analysis_id :  Market analysis identifier.
    exchange :            Target exchange (e.g. "NSE", "BSE").
    workflow_type :       Market workflow classification.
    priority :            Scheduling priority.
    instrument_id :       Optional specific instrument being analysed.
    workflow_id :         Workflow routing correlation.
    metadata :            Supplementary context metadata.
    framework_version :   Framework version.
    """
    context_id:          str
    market_analysis_id:  str
    exchange:            str
    workflow_type:       MarketWorkflowType
    priority:            SchedulerPriority  = SchedulerPriority.NORMAL
    instrument_id:       str               = ""
    workflow_id:         str               = ""
    metadata:            Dict[str, Any]    = field(default_factory=dict)
    framework_version:   str               = VERSION

    @classmethod
    def create(
        cls,
        market_analysis_id: str,
        exchange:           str,
        workflow_type:      MarketWorkflowType,
        *,
        context_id:    Optional[str]           = None,
        priority:      SchedulerPriority        = SchedulerPriority.NORMAL,
        instrument_id: str                     = "",
        workflow_id:   str                     = "",
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "MarketEngineContext":
        return cls(
            context_id         = context_id or str(uuid.uuid4()),
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            workflow_type      = workflow_type,
            priority           = priority,
            instrument_id      = instrument_id,
            workflow_id        = workflow_id,
            metadata           = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":          self.context_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "workflow_type":       self.workflow_type.value,
            "priority":            self.priority.value,
            "instrument_id":       self.instrument_id,
            "workflow_id":         self.workflow_id,
            "framework_version":   self.framework_version,
        }
