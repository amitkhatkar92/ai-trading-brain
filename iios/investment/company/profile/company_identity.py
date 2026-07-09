"""iios/investment/company/profile/company_identity.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import (
    ListingStatus,
    MarketCapCategory,
    SectorClassification,
)


@dataclass
class CompanyIdentity:
    """Immutable identification record for a listed company."""

    company_id:          str                 = field(default_factory=lambda: str(uuid.uuid4()))
    ticker:              str                 = ""
    isin:                str                 = ""
    name:                str                 = ""
    short_name:          str                 = ""
    exchange:            str                 = ""
    sector:              SectorClassification = SectorClassification.UNKNOWN
    industry:            str                 = ""
    sub_industry:        str                 = ""
    country:             str                 = ""
    currency:            str                 = "INR"
    listing_status:      ListingStatus       = ListingStatus.UNKNOWN
    listed_date:         str                 = ""
    market_cap_category: MarketCapCategory   = MarketCapCategory.UNKNOWN
    created_at:          float               = field(default_factory=time.time)

    def display_name(self) -> str:
        return self.short_name or self.name or self.ticker or self.company_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id":          self.company_id,
            "ticker":              self.ticker,
            "isin":                self.isin,
            "name":                self.name,
            "short_name":          self.short_name,
            "exchange":            self.exchange,
            "sector":              self.sector.value,
            "industry":            self.industry,
            "sub_industry":        self.sub_industry,
            "country":             self.country,
            "currency":            self.currency,
            "listing_status":      self.listing_status.value,
            "listed_date":         self.listed_date,
            "market_cap_category": self.market_cap_category.value,
            "created_at":          self.created_at,
        }
