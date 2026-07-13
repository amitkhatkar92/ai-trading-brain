"""iios/investment/company/ownership/ownership_snapshot.py
Primary output of the Ownership Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.ownership.ownership_profile import (
    OwnershipStructureProfile,
    InsiderActivityProfile,
    OwnershipCapitalAllocationProfile,
    ShareholderValueProfile,
    OwnershipRiskProfile,
    OwnershipIntelligenceScore,
    OwnershipQualityLabel,
)
from iios.investment.company.ownership.shareholder_registry import ShareholderRegistry


@dataclass
class OwnershipSnapshot:
    """
    Authoritative ownership intelligence output for a single ticker.
    Produced by OwnershipIntelligenceEngine.ingest().
    """
    ticker:           str
    generated_at:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Sub-profiles
    shareholder_registry:   ShareholderRegistry                 = field(default_factory=lambda: ShareholderRegistry(ticker=""))
    ownership_structure:    OwnershipStructureProfile           = field(default_factory=OwnershipStructureProfile)
    insider_activity:       InsiderActivityProfile              = field(default_factory=InsiderActivityProfile)
    capital_allocation:     OwnershipCapitalAllocationProfile   = field(default_factory=OwnershipCapitalAllocationProfile)
    shareholder_value:      ShareholderValueProfile             = field(default_factory=ShareholderValueProfile)
    ownership_risk:         OwnershipRiskProfile                = field(default_factory=OwnershipRiskProfile)
    ownership_score:        OwnershipIntelligenceScore          = field(default_factory=OwnershipIntelligenceScore)

    confidence:          float = 0.0     # 0-1; how complete the input data was
    ownership_standard:  str   = "generic"
    data_sources:        List[str] = field(default_factory=list)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def overall_ownership_score(self) -> float:
        return self.ownership_score.overall_score

    @property
    def ownership_label(self) -> str:
        return self.ownership_score.label.value

    @property
    def has_high_ownership_risk(self) -> bool:
        from iios.investment.company.ownership.ownership_profile import OwnershipRiskLabel
        return self.ownership_risk.risk_label in (
            OwnershipRiskLabel.HIGH,
            OwnershipRiskLabel.CRITICAL,
        )

    @property
    def is_promoter_backed(self) -> bool:
        """True if identifiable promoter holds >= 25%."""
        p = self.shareholder_registry.promoter_pct
        return (p is not None) and p >= 25.0

    @property
    def has_institutional_support(self) -> bool:
        """True if institutional holding >= 15%."""
        i = self.shareholder_registry.institutional_pct
        return (i is not None) and i >= 15.0

    @property
    def is_insider_accumulating(self) -> bool:
        from iios.investment.company.ownership.ownership_profile import InsiderActivityLabel
        return self.insider_activity.insider_activity_label in (
            InsiderActivityLabel.ACCUMULATING,
            InsiderActivityLabel.STEADY,
        )

    @property
    def promoter_pledge_pct(self) -> Optional[float]:
        return self.shareholder_registry.promoter_pledge_pct

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":             self.ticker,
            "generated_at":       self.generated_at.isoformat(),
            "ownership_standard": self.ownership_standard,
            "confidence":         round(self.confidence, 3),
            "data_sources":       self.data_sources,
            "ownership_structure":  self.ownership_structure.to_dict(),
            "insider_activity":     self.insider_activity.to_dict(),
            "capital_allocation":   self.capital_allocation.to_dict(),
            "shareholder_value":    self.shareholder_value.to_dict(),
            "ownership_risk":       self.ownership_risk.to_dict(),
            "ownership_score":      self.ownership_score.to_dict(),
        }
