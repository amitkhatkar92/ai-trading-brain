"""iios/investment/company/governance/management_snapshot.py
Primary output of the Management & Governance Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.governance.management_profile import (
    ManagementQualityProfile, GovernanceProfile, CapitalAllocationProfile,
    TransparencyProfile, GovernanceRiskProfile, ManagementIntelligenceScore,
)
from iios.investment.company.governance.executive_profile import ExecutiveTeamProfile
from iios.investment.company.governance.board_profile import (
    BoardComposition, CommitteeStructure,
)


@dataclass
class ManagementSnapshot:
    """
    Primary output of ManagementGovernanceEngine.
    Authoritative source of management and governance intelligence across IIOS.
    NOT a buy/sell/hold recommendation.
    """
    ticker:       str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Leadership structure
    executive_team:     ExecutiveTeamProfile  = field(default_factory=ExecutiveTeamProfile)
    board:              BoardComposition      = field(default_factory=BoardComposition)
    committees:         CommitteeStructure    = field(default_factory=CommitteeStructure)

    # Intelligence profiles
    management_quality:  ManagementQualityProfile  = field(default_factory=ManagementQualityProfile)
    governance:          GovernanceProfile          = field(default_factory=GovernanceProfile)
    capital_allocation:  CapitalAllocationProfile   = field(default_factory=CapitalAllocationProfile)
    transparency:        TransparencyProfile        = field(default_factory=TransparencyProfile)
    governance_risk:     GovernanceRiskProfile      = field(default_factory=GovernanceRiskProfile)

    # Composite score
    management_score:    ManagementIntelligenceScore = field(default_factory=ManagementIntelligenceScore)

    # Metadata
    confidence:          float = 0.0
    governance_standard: str   = "generic"
    data_sources:        List[str] = field(default_factory=list)

    # ── Convenience properties ─────────────────────────────────────────────────

    @property
    def overall_management_score(self) -> float:
        return self.management_score.overall_score

    @property
    def management_label(self) -> str:
        return self.management_score.label

    @property
    def has_high_governance_risk(self) -> bool:
        return self.governance_risk.overall_risk_score >= 65.0

    @property
    def is_founder_led(self) -> bool:
        return self.executive_team.is_founder_led

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":            self.ticker,
            "generated_at":      self.generated_at.isoformat(),
            "confidence":        round(self.confidence, 2),
            "governance_standard": self.governance_standard,
            "data_sources":      self.data_sources,
            "is_founder_led":    self.is_founder_led,
            "management_label":  self.management_label,
            "executive_team":    self.executive_team.to_dict(),
            "board":             self.board.to_dict(),
            "committees":        self.committees.to_dict(),
            "management_quality": self.management_quality.to_dict(),
            "governance":        self.governance.to_dict(),
            "capital_allocation": self.capital_allocation.to_dict(),
            "transparency":      self.transparency.to_dict(),
            "governance_risk":   self.governance_risk.to_dict(),
            "management_score":  self.management_score.to_dict(),
        }
