"""iios/investment/models/investment_request.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.investment.investment_constants import (
    AssetClass,
    IntelligenceType,
    InvestmentObjective,
    RiskProfile,
    TimeHorizon,
)


@dataclass
class InvestmentRequest:
    """
    Input to the Investment Intelligence Engine.

    Describes what asset(s) to analyse, for what purpose, and how.
    All domain-specific parameters belong in ``metadata``.
    """

    request_id:         str                    = field(default_factory=lambda: str(uuid.uuid4()))
    asset_class:        AssetClass             = AssetClass.EQUITY
    symbols:            list[str]              = field(default_factory=list)
    objective:          InvestmentObjective    = InvestmentObjective.GROWTH
    time_horizon:       TimeHorizon            = TimeHorizon.MEDIUM_TERM
    risk_profile:       RiskProfile            = RiskProfile.MODERATE
    market:             str                    = ""    # e.g. "NSE", "NYSE"
    country:            str                    = ""    # ISO 3166-1 alpha-2
    currency:           str                    = ""    # ISO 4217
    intelligence_types: list[IntelligenceType] = field(default_factory=list)
    metadata:           dict                   = field(default_factory=dict)
    created_at:         float                  = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "request_id":         self.request_id,
            "asset_class":        self.asset_class.value,
            "symbols":            self.symbols,
            "objective":          self.objective.value,
            "time_horizon":       self.time_horizon.value,
            "risk_profile":       self.risk_profile.value,
            "market":             self.market,
            "country":            self.country,
            "currency":           self.currency,
            "intelligence_types": [t.value for t in self.intelligence_types],
            "metadata":           self.metadata,
            "created_at":         self.created_at,
        }
