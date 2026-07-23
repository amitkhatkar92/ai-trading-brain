"""
market_analytics_request.py — iios.market.analytics
=====================================================
Immutable market analytics request value object.

Carries all input data required by the analytics pipeline.
Only policy-approved requests are processed.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION
from .market_analytics_context import MarketAnalyticsContext


@dataclass(frozen=True)
class MarketAnalyticsRequest:
    """
    Immutable request submitted to the Market Analytics Framework.

    Only requests with ``policy_approved=True`` are processed.

    Fields
    ------
    request_id :          Unique identifier.
    analytics_id :        Analytics run correlation identifier.
    market_analysis_id :  Target market analysis identifier.
    exchange :            Exchange identifier.
    context :             Analytics configuration context.
    policy_approved :     Must be True — engine rejects unapproved requests.
    policy_response :     Serialised MarketPolicyResponse metadata.
    index_prices :        Dict of index_name → price series (list of floats).
    sector_data :         Dict of sector_name → {prices, volume, ...}.
    breadth_data :        Advance/decline and breadth indicator data.
    volume_data :         Aggregate volume and volume profile data.
    volatility_data :     Volatility surface and historical vol data.
    economic_data :       Economic calendar and event impact data.
    global_data :         Global market data (FX, bonds, global indices).
    corporate_actions :   Corporate action metadata.
    historical_data :     Historical OHLCV and other time-series data.
    requested_at :        Wall-clock submission time.
    metadata :            Supplementary metadata.
    framework_version :   Framework version string.
    """
    request_id:          str
    analytics_id:        str
    market_analysis_id:  str
    exchange:            str
    context:             MarketAnalyticsContext
    policy_approved:     bool
    policy_response:     Dict[str, Any]
    index_prices:        Dict[str, List[float]]
    sector_data:         Dict[str, Any]
    breadth_data:        Dict[str, Any]
    volume_data:         Dict[str, Any]
    volatility_data:     Dict[str, Any]
    economic_data:       Dict[str, Any]
    global_data:         Dict[str, Any]
    corporate_actions:   Dict[str, Any]
    historical_data:     Dict[str, Any]
    requested_at:        float           = field(default_factory=time.time)
    metadata:            Dict[str, Any]  = field(default_factory=dict)
    framework_version:   str             = VERSION

    @classmethod
    def create(
        cls,
        analytics_id:       str,
        market_analysis_id: str,
        exchange:           str,
        *,
        request_id:       Optional[str]                    = None,
        context:          Optional[MarketAnalyticsContext] = None,
        policy_approved:  bool                             = False,
        policy_response:  Optional[Dict[str, Any]]         = None,
        index_prices:     Optional[Dict[str, List[float]]] = None,
        sector_data:      Optional[Dict[str, Any]]         = None,
        breadth_data:     Optional[Dict[str, Any]]         = None,
        volume_data:      Optional[Dict[str, Any]]         = None,
        volatility_data:  Optional[Dict[str, Any]]         = None,
        economic_data:    Optional[Dict[str, Any]]         = None,
        global_data:      Optional[Dict[str, Any]]         = None,
        corporate_actions: Optional[Dict[str, Any]]        = None,
        historical_data:  Optional[Dict[str, Any]]         = None,
        metadata:         Optional[Dict[str, Any]]         = None,
    ) -> "MarketAnalyticsRequest":
        ctx = context or MarketAnalyticsContext.create(
            analytics_id       = analytics_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
        )
        return cls(
            request_id         = request_id or str(uuid.uuid4()),
            analytics_id       = analytics_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            context            = ctx,
            policy_approved    = policy_approved,
            policy_response    = dict(policy_response or {}),
            index_prices       = dict(index_prices or {}),
            sector_data        = dict(sector_data or {}),
            breadth_data       = dict(breadth_data or {}),
            volume_data        = dict(volume_data or {}),
            volatility_data    = dict(volatility_data or {}),
            economic_data      = dict(economic_data or {}),
            global_data        = dict(global_data or {}),
            corporate_actions  = dict(corporate_actions or {}),
            historical_data    = dict(historical_data or {}),
            metadata           = dict(metadata or {}),
        )

    @property
    def has_index_data(self) -> bool:
        return bool(self.index_prices)

    @property
    def has_sector_data(self) -> bool:
        return bool(self.sector_data)

    @property
    def has_breadth_data(self) -> bool:
        return bool(self.breadth_data)

    @property
    def index_count(self) -> int:
        return len(self.index_prices)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":          self.request_id,
            "analytics_id":        self.analytics_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "policy_approved":     self.policy_approved,
            "index_count":         self.index_count,
            "has_sector_data":     self.has_sector_data,
            "has_breadth_data":    self.has_breadth_data,
            "requested_at":        self.requested_at,
            "framework_version":   self.framework_version,
        }
