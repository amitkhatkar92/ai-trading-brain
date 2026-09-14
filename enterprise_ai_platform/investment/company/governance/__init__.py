"""enterprise_ai_platform/investment/company/governance/__init__.py
Management & Governance Intelligence Engine package.
"""
from enterprise_ai_platform.investment.company.governance.management_governance_engine import ManagementGovernanceEngine
from enterprise_ai_platform.investment.company.governance.management_snapshot import ManagementSnapshot
from enterprise_ai_platform.investment.company.governance.management_profile import (
    ManagementQualityProfile, GovernanceProfile, CapitalAllocationProfile,
    TransparencyProfile, GovernanceRiskProfile, ManagementIntelligenceScore,
    GovernanceStandard, LeadershipStability, BoardIndependenceLevel,
    CapitalAllocationLabel, TransparencyLabel, RiskLabel,
)
from enterprise_ai_platform.investment.company.governance.executive_profile import ExecutiveTeamProfile, ExecutiveRecord
from enterprise_ai_platform.investment.company.governance.board_profile import BoardComposition, CommitteeStructure
from enterprise_ai_platform.investment.company.governance.governance_plugin import GovernancePlugin, GovernancePluginRegistry

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
