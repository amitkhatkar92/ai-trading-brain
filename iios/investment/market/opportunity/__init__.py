"""iios/investment/market/opportunity/__init__.py
Public API for the Institutional Market Opportunity Engine.
"""
from iios.investment.market.opportunity.market_opportunity_engine import (
    InstitutionalMarketOpportunityEngine,
)
from iios.investment.market.opportunity.models import (
    AlertType,
    AssetObservation,
    Evidence,
    IntelligenceContext,
    Opportunity,
    OpportunityAlert,
    OpportunityCategory,
    OpportunityEvent,
    OpportunityEventType,
    OpportunityExplanation,
    OpportunityLifecycleStage,
    OpportunityPriority,
    OpportunitySnapshotData,
    RankingScore,
    ScanScope,
)
from iios.investment.market.opportunity.opportunity_category import (
    CategoryRule,
    BUILT_IN_RULES,
)
from iios.investment.market.opportunity.universe_scanner import Universe

__all__ = [
    # Primary engine
    "InstitutionalMarketOpportunityEngine",
    # Input types
    "AssetObservation",
    "IntelligenceContext",
    # Output types
    "OpportunitySnapshotData",
    "Opportunity",
    "OpportunityAlert",
    "OpportunityEvent",
    "OpportunityExplanation",
    "RankingScore",
    "Evidence",
    # Enums
    "OpportunityCategory",
    "OpportunityLifecycleStage",
    "OpportunityPriority",
    "AlertType",
    "OpportunityEventType",
    "ScanScope",
    # Configuration
    "CategoryRule",
    "BUILT_IN_RULES",
    "Universe",
]
