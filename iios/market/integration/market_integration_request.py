"""
market_integration_request.py — iios.market.integration
=========================================================
Immutable market integration request value object.

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
from .market_integration_context import MarketIntegrationContext


@dataclass(frozen=True)
class MarketIntegrationRequest:
    """
    Immutable market integration request.

    Submitted to :class:`~.market_integration_engine.MarketIntegrationEngine`
    via :meth:`~.market_integration_engine.MarketIntegrationEngine.submit`.

    Fields
    ------
    request_id :           Unique request identifier.
    integration_id :       Integration correlation identifier.
    exchange :             Target exchange.
    request_type :         Type of market analysis requested.
    priority :             Processing priority.
    context :              Operational context.
    inputs :               Raw market data inputs.
                           Common keys: ``index_prices``, ``sector_data``,
                           ``breadth_data``, ``volume_data``,
                           ``volatility_data``, ``economic_data``,
                           ``global_data``, ``corporate_actions``,
                           ``historical_data``, ``trading_calendar``.
    market_analysis_id :   Optional — caller-supplied correlation ID.
    requested_at :         Wall-clock creation time.
    metadata :             Supplementary metadata.
    framework_version :    Framework version string.
    """
    request_id:          str
    integration_id:      str
    exchange:            str
    request_type:        IntegrationRequestType
    priority:            IntegrationPriority
    context:             MarketIntegrationContext
    inputs:              Dict[str, Any]
    market_analysis_id:  str
    requested_at:        float
    metadata:            Dict[str, Any]
    framework_version:   str

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        exchange:     str,
        request_type: IntegrationRequestType = IntegrationRequestType.MARKET_OVERVIEW,
        *,
        request_id:         Optional[str]                  = None,
        integration_id:     str                            = "",
        market_analysis_id: str                            = "",
        priority:           IntegrationPriority            = IntegrationPriority.NORMAL,
        context:            Optional[MarketIntegrationContext] = None,
        inputs:             Optional[Dict[str, Any]]       = None,
        metadata:           Optional[Dict[str, Any]]       = None,
    ) -> "MarketIntegrationRequest":
        iid = integration_id or str(uuid.uuid4())
        ctx = context or MarketIntegrationContext.create(
            exchange      = exchange,
            request_type  = request_type,
            integration_id = iid,
            priority      = priority,
        )
        return cls(
            request_id         = request_id or str(uuid.uuid4()),
            integration_id     = iid,
            exchange           = exchange,
            request_type       = request_type,
            priority           = priority,
            context            = ctx,
            inputs             = dict(inputs or {}),
            market_analysis_id = market_analysis_id or str(uuid.uuid4()),
            requested_at       = time.time(),
            metadata           = dict(metadata or {}),
            framework_version  = VERSION,
        )

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def market_overview(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.MARKET_OVERVIEW, **kwargs)

    @classmethod
    def regime_analysis(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.MARKET_REGIME_ANALYSIS, **kwargs)

    @classmethod
    def sector_analysis(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.SECTOR_ANALYSIS, **kwargs)

    @classmethod
    def breadth_analysis(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.BREADTH_ANALYSIS, **kwargs)

    @classmethod
    def volatility_analysis(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.VOLATILITY_ANALYSIS, **kwargs)

    @classmethod
    def liquidity_analysis(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.LIQUIDITY_ANALYSIS, **kwargs)

    @classmethod
    def correlation_analysis(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.CORRELATION_ANALYSIS, **kwargs)

    @classmethod
    def forecast_request(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.FORECAST_REQUEST, **kwargs)

    @classmethod
    def snapshot_request(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.MARKET_SNAPSHOT_REQUEST, **kwargs)

    @classmethod
    def history_request(cls, exchange: str, **kwargs: Any) -> "MarketIntegrationRequest":
        return cls.create(exchange, IntegrationRequestType.MARKET_HISTORY_REQUEST, **kwargs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def with_inputs(self, inputs: Dict[str, Any]) -> "MarketIntegrationRequest":
        """Return a new request with the given inputs merged in."""
        merged = {**self.inputs, **inputs}
        import dataclasses
        return dataclasses.replace(self, inputs=merged)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":         self.request_id,
            "integration_id":     self.integration_id,
            "exchange":           self.exchange,
            "request_type":       self.request_type.value,
            "priority":           self.priority.value,
            "market_analysis_id": self.market_analysis_id,
            "requested_at":       self.requested_at,
            "framework_version":  self.framework_version,
        }
