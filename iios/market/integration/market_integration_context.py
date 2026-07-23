"""
market_integration_context.py — iios.market.integration
=========================================================
Immutable integration context value object.

Carries the operational configuration for a single integration request.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    VERSION,
    IntegrationPriority,
    IntegrationRequestType,
)


@dataclass(frozen=True)
class MarketIntegrationContext:
    """
    Immutable operational context for a single market integration request.

    Fields
    ------
    context_id :        Unique context identifier.
    integration_id :    Owning integration identifier.
    exchange :          Target exchange (e.g. "NSE", "BSE").
    market :            Market name / description.
    market_type :       Market type string.
    timeframe :         Analysis timeframe.
    trading_session :   Trading session identifier.
    request_type :      Type of integration request.
    priority :          Processing priority.
    enable_analytics :  Whether to invoke the analytics framework.
    enable_policy :     Whether to invoke the policy framework.
    timeout_s :         Maximum processing time before timeout.
    tags :              Arbitrary key-value tags for routing.
    created_at :        Creation timestamp.
    framework_version : Framework version string.
    """
    context_id:        str
    integration_id:    str
    exchange:          str
    market:            str
    market_type:       str
    timeframe:         str
    trading_session:   str
    request_type:      IntegrationRequestType
    priority:          IntegrationPriority
    enable_analytics:  bool
    enable_policy:     bool
    timeout_s:         float
    tags:              Dict[str, str]
    created_at:        float
    framework_version: str

    @classmethod
    def create(
        cls,
        exchange:       str,
        request_type:   IntegrationRequestType = IntegrationRequestType.MARKET_OVERVIEW,
        *,
        context_id:      Optional[str]             = None,
        integration_id:  str                       = "",
        market:          str                       = "",
        market_type:     str                       = "equity",
        timeframe:       str                       = "1d",
        trading_session: str                       = "regular",
        priority:        IntegrationPriority       = IntegrationPriority.NORMAL,
        enable_analytics: bool                     = True,
        enable_policy:    bool                     = True,
        timeout_s:        float                    = 60.0,
        tags:             Optional[Dict[str, str]] = None,
    ) -> "MarketIntegrationContext":
        return cls(
            context_id        = context_id or str(uuid.uuid4()),
            integration_id    = integration_id or str(uuid.uuid4()),
            exchange          = exchange,
            market            = market,
            market_type       = market_type,
            timeframe         = timeframe,
            trading_session   = trading_session,
            request_type      = request_type,
            priority          = priority,
            enable_analytics  = enable_analytics,
            enable_policy     = enable_policy,
            timeout_s         = timeout_s,
            tags              = dict(tags or {}),
            created_at        = time.time(),
            framework_version = VERSION,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "integration_id":    self.integration_id,
            "exchange":          self.exchange,
            "market":            self.market,
            "market_type":       self.market_type,
            "timeframe":         self.timeframe,
            "trading_session":   self.trading_session,
            "request_type":      self.request_type.value,
            "priority":          self.priority.value,
            "enable_analytics":  self.enable_analytics,
            "enable_policy":     self.enable_policy,
            "timeout_s":         self.timeout_s,
            "tags":              dict(self.tags),
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }
