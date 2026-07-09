"""iios/investment/company/profile/company_snapshot.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import (
    CompanyStage,
    DEFAULT_SNAPSHOT_TTL_SEC,
    FinancialHealth,
    GrowthProfile,
    ValuationStatus,
)


@dataclass
class CompanySnapshot:
    """Point-in-time observation of a company's key metrics."""

    snapshot_id:          str            = field(default_factory=lambda: str(uuid.uuid4()))
    company_id:           str            = ""
    timestamp:            float          = field(default_factory=time.time)

    # Price / market data
    price:                float          = 0.0
    price_change_pct:     float          = 0.0
    volume:               float          = 0.0
    market_cap:           float          = 0.0

    # Valuation ratios
    pe_ratio:             float | None   = None
    pb_ratio:             float | None   = None
    ev_ebitda:            float | None   = None
    price_to_sales:       float | None   = None

    # Financial ratios
    roe:                  float | None   = None
    roce:                 float | None   = None
    debt_to_equity:       float | None   = None
    current_ratio:        float | None   = None
    interest_coverage:    float | None   = None

    # Growth
    revenue_growth:       float | None   = None
    profit_growth:        float | None   = None
    ebitda_margin:        float | None   = None
    pat_margin:           float | None   = None

    # Ownership
    promoter_holding:     float | None   = None
    institutional_holding: float | None  = None
    promoter_pledge_pct:  float | None   = None

    # Derived classifications
    health:            FinancialHealth = FinancialHealth.UNKNOWN
    valuation_status:  ValuationStatus = ValuationStatus.UNKNOWN
    growth_profile:    GrowthProfile   = GrowthProfile.UNKNOWN
    stage:             CompanyStage    = CompanyStage.UNKNOWN

    metadata:             dict[str, Any] = field(default_factory=dict)
    created_at:           float          = field(default_factory=time.time)

    @property
    def age_sec(self) -> float:
        return time.time() - self.created_at

    def is_stale(self, ttl_sec: float = DEFAULT_SNAPSHOT_TTL_SEC) -> bool:
        return self.age_sec > ttl_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":          self.snapshot_id,
            "company_id":           self.company_id,
            "timestamp":            self.timestamp,
            "price":                self.price,
            "price_change_pct":     self.price_change_pct,
            "volume":               self.volume,
            "market_cap":           self.market_cap,
            "pe_ratio":             self.pe_ratio,
            "pb_ratio":             self.pb_ratio,
            "ev_ebitda":            self.ev_ebitda,
            "price_to_sales":       self.price_to_sales,
            "roe":                  self.roe,
            "roce":                 self.roce,
            "debt_to_equity":       self.debt_to_equity,
            "current_ratio":        self.current_ratio,
            "revenue_growth":       self.revenue_growth,
            "profit_growth":        self.profit_growth,
            "ebitda_margin":        self.ebitda_margin,
            "pat_margin":           self.pat_margin,
            "promoter_holding":     self.promoter_holding,
            "institutional_holding": self.institutional_holding,
            "promoter_pledge_pct":  self.promoter_pledge_pct,
            "health":               self.health.value,
            "valuation_status":     self.valuation_status.value,
            "growth_profile":       self.growth_profile.value,
            "stage":                self.stage.value,
            "metadata":             self.metadata,
            "created_at":           self.created_at,
        }
