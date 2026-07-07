"""
iios/observation/collectors/categories/__init__.py
"""
from __future__ import annotations

from .base_category import (
    MarketDataCollector,
    NewsCollector,
    MacroCollector,
    CorporateActionCollector,
    FinancialStatementCollector,
    ExchangeCollector,
    BrokerCollector,
    AlternativeDataCollector,
    SocialMediaCollector,
    ResearchCollector,
    InternalSystemCollector,
    PluginCollector,
)

__all__ = [
    "MarketDataCollector",
    "NewsCollector",
    "MacroCollector",
    "CorporateActionCollector",
    "FinancialStatementCollector",
    "ExchangeCollector",
    "BrokerCollector",
    "AlternativeDataCollector",
    "SocialMediaCollector",
    "ResearchCollector",
    "InternalSystemCollector",
    "PluginCollector",
]
