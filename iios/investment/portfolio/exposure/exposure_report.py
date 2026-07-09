"""iios/investment/portfolio/exposure/exposure_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import AllocationStatus


@dataclass
class ExposureReport:
    """
    Point-in-time exposure summary for a portfolio.

    All exposure fractions are relative to total_nav.
    """

    report_id:         str             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str             = ""
    timestamp:         float           = field(default_factory=time.time)

    # Overall exposure (fraction of NAV)
    gross_exposure:    float           = 0.0    # sum(abs(market_value)) / nav
    net_exposure:      float           = 0.0    # (long_mv - short_mv) / nav
    long_exposure:     float           = 0.0
    short_exposure:    float           = 0.0
    cash_pct:          float           = 0.0

    # Breakdowns: dimension_value → weight fraction
    by_sector:         dict[str, float] = field(default_factory=dict)
    by_country:        dict[str, float] = field(default_factory=dict)
    by_asset_class:    dict[str, float] = field(default_factory=dict)
    by_currency:       dict[str, float] = field(default_factory=dict)
    by_strategy:       dict[str, float] = field(default_factory=dict)

    # Limit breach details
    limit_breaches:    list[str]       = field(default_factory=list)
    status:            AllocationStatus = AllocationStatus.UNKNOWN

    metadata:          dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":       self.report_id,
            "portfolio_id":    self.portfolio_id,
            "timestamp":       self.timestamp,
            "gross_exposure":  self.gross_exposure,
            "net_exposure":    self.net_exposure,
            "long_exposure":   self.long_exposure,
            "short_exposure":  self.short_exposure,
            "cash_pct":        self.cash_pct,
            "by_sector":       self.by_sector,
            "by_country":      self.by_country,
            "by_asset_class":  self.by_asset_class,
            "by_currency":     self.by_currency,
            "by_strategy":     self.by_strategy,
            "limit_breaches":  self.limit_breaches,
            "status":          self.status.value,
            "metadata":        self.metadata,
        }
