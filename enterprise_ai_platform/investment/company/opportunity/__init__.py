"""enterprise_ai_platform/investment/company/opportunity/__init__.py
Institutional Company Opportunity Intelligence Engine — public API.
"""
from enterprise_ai_platform.investment.company.opportunity.company_opportunity_engine import CompanyOpportunityEngine
from enterprise_ai_platform.investment.company.opportunity.opportunity_snapshot import OpportunitySnapshot
from enterprise_ai_platform.investment.company.opportunity.company_opportunity import CompanyOpportunity
from enterprise_ai_platform.investment.company.opportunity.opportunity_profile import (
    OpportunityCategory, OpportunityLifecycle, OpportunityPriority,
    OpportunityStrength, ConfidenceLevel, ChangeSignal, AlertSeverity,
    ComponentScore, OpportunityScoreBreakdown, OpportunityAlert, WatchlistEntry,
)
from enterprise_ai_platform.investment.company.opportunity.opportunity_category import (
    ClassificationResult, get_category_description,
)
from enterprise_ai_platform.investment.company.opportunity.investment_thesis import (
    InvestmentThesis, ThesisEvidence,
)
from enterprise_ai_platform.investment.company.opportunity.opportunity_lifecycle import (
    LifecycleChange, determine_lifecycle, is_valid_transition,
)
from enterprise_ai_platform.investment.company.opportunity.ranking_score import (
    RankingScore, RankingResult, RankingChange,
)
from enterprise_ai_platform.investment.company.opportunity.opportunity_plugin import (
    OpportunityPlugin, OpportunityPluginRegistry,
)

__all__ = [
    # Primary engine
    "CompanyOpportunityEngine",
    # Snapshot
    "OpportunitySnapshot",
    # State
    "CompanyOpportunity",
    # Enums
    "OpportunityCategory",
    "OpportunityLifecycle",
    "OpportunityPriority",
    "OpportunityStrength",
    "ConfidenceLevel",
    "ChangeSignal",
    "AlertSeverity",
    # Score structures
    "ComponentScore",
    "OpportunityScoreBreakdown",
    # Alert
    "OpportunityAlert",
    # Watchlist
    "WatchlistEntry",
    # Classification
    "ClassificationResult",
    "get_category_description",
    # Thesis
    "InvestmentThesis",
    "ThesisEvidence",
    # Lifecycle
    "LifecycleChange",
    "determine_lifecycle",
    "is_valid_transition",
    # Ranking
    "RankingScore",
    "RankingResult",
    "RankingChange",
    # Plugin
    "OpportunityPlugin",
    "OpportunityPluginRegistry",
]
