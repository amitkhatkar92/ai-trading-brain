"""iios/investment/company/models/company_intelligence.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import (
    CompanyStage,
    FinancialHealth,
    GovernanceQuality,
    GrowthProfile,
    OwnershipConcentration,
    SectorClassification,
    ValuationStatus,
)
from iios.investment.company.models.company_health import CompanyHealth
from iios.investment.company.models.company_signal import CompanySignal


@dataclass
class CompanyIntelligence:
    """
    Top-level intelligence product for a single company.
    Produced by CompanyManager.analyze() and stored in CompanyHistory.
    """

    intelligence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    company_id:      str = ""
    ticker:          str = ""
    request_id:      str = ""

    # Classification
    sector:   SectorClassification  = SectorClassification.UNKNOWN
    stage:    CompanyStage          = CompanyStage.UNKNOWN

    # Health dimensions
    financial_health:      FinancialHealth       = FinancialHealth.UNKNOWN
    growth_profile:        GrowthProfile         = GrowthProfile.UNKNOWN
    valuation_status:      ValuationStatus        = ValuationStatus.UNKNOWN
    ownership_concentration: OwnershipConcentration = OwnershipConcentration.UNKNOWN
    governance_quality:    GovernanceQuality      = GovernanceQuality.UNKNOWN

    # Composite scores (0–100)
    health_score:                 float = 50.0
    financial_strength_score:     float = 50.0
    competitive_position_score:   float = 50.0
    growth_potential_score:       float = 50.0
    business_quality_score:       float = 50.0
    management_quality_score:     float = 50.0
    governance_score:             float = 50.0
    investment_attractiveness_score: float = 50.0
    risk_profile_score:           float = 50.0

    # Health model
    health: CompanyHealth = field(default_factory=CompanyHealth)

    # Intelligence products
    opportunities:    list[str]          = field(default_factory=list)
    risks:            list[str]          = field(default_factory=list)
    key_observations: list[str]          = field(default_factory=list)
    signals:          list[CompanySignal] = field(default_factory=list)

    # Meta
    confidence:  float          = 0.0
    metadata:    dict[str, Any] = field(default_factory=dict)
    created_at:  float          = field(default_factory=time.time)
    duration_ms: float          = 0.0

    # ── mutation helpers ──────────────────────────────────────────────────────

    def add_signal(self, signal: CompanySignal) -> None:
        self.signals.append(signal)

    def add_opportunity(self, desc: str) -> None:
        if desc and desc not in self.opportunities:
            self.opportunities.append(desc)

    def add_risk(self, desc: str) -> None:
        if desc and desc not in self.risks:
            self.risks.append(desc)

    def add_observation(self, obs: str) -> None:
        if obs and obs not in self.key_observations:
            self.key_observations.append(obs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intelligence_id":               self.intelligence_id,
            "company_id":                    self.company_id,
            "ticker":                        self.ticker,
            "request_id":                    self.request_id,
            "sector":                        self.sector.value,
            "stage":                         self.stage.value,
            "financial_health":              self.financial_health.value,
            "growth_profile":                self.growth_profile.value,
            "valuation_status":              self.valuation_status.value,
            "ownership_concentration":       self.ownership_concentration.value,
            "governance_quality":            self.governance_quality.value,
            "health_score":                  self.health_score,
            "financial_strength_score":      self.financial_strength_score,
            "competitive_position_score":    self.competitive_position_score,
            "growth_potential_score":        self.growth_potential_score,
            "business_quality_score":        self.business_quality_score,
            "management_quality_score":      self.management_quality_score,
            "governance_score":              self.governance_score,
            "investment_attractiveness_score": self.investment_attractiveness_score,
            "risk_profile_score":            self.risk_profile_score,
            "health":                        self.health.to_dict(),
            "opportunities":                 self.opportunities,
            "risks":                         self.risks,
            "key_observations":              self.key_observations,
            "signals":                       [s.to_dict() for s in self.signals],
            "confidence":                    self.confidence,
            "metadata":                      self.metadata,
            "created_at":                    self.created_at,
            "duration_ms":                   self.duration_ms,
        }
