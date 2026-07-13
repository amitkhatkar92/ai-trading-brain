"""iios/investment/company/governance/__init__.py
Management & Governance Intelligence Engine package.
"""
from iios.investment.company.governance.management_governance_engine import ManagementGovernanceEngine
from iios.investment.company.governance.management_snapshot import ManagementSnapshot
from iios.investment.company.governance.management_profile import (
    ManagementQualityProfile, GovernanceProfile, CapitalAllocationProfile,
    TransparencyProfile, GovernanceRiskProfile, ManagementIntelligenceScore,
    GovernanceStandard, LeadershipStability, BoardIndependenceLevel,
    CapitalAllocationLabel, TransparencyLabel, RiskLabel,
)
from iios.investment.company.governance.executive_profile import ExecutiveTeamProfile, ExecutiveRecord
from iios.investment.company.governance.board_profile import BoardComposition, CommitteeStructure
from iios.investment.company.governance.governance_plugin import GovernancePlugin, GovernancePluginRegistry

__all__ = [
    "ManagementGovernanceEngine",
    "ManagementSnapshot",
    "ManagementQualityProfile",
    "GovernanceProfile",
    "CapitalAllocationProfile",
    "TransparencyProfile",
    "GovernanceRiskProfile",
    "ManagementIntelligenceScore",
    "GovernanceStandard",
    "LeadershipStability",
    "BoardIndependenceLevel",
    "CapitalAllocationLabel",
    "TransparencyLabel",
    "RiskLabel",
    "ExecutiveTeamProfile",
    "ExecutiveRecord",
    "BoardComposition",
    "CommitteeStructure",
    "GovernancePlugin",
    "GovernancePluginRegistry",
]
