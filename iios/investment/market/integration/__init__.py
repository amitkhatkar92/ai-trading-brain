"""iios/investment/market/integration/__init__.py
Public API for the Market Intelligence Integration & Validation Engine.
"""
from iios.investment.market.integration.market_intelligence_integration_engine import (
    MarketIntelligenceIntegrationEngine,
)
from iios.investment.market.integration.models import (
    ConflictSeverity,
    ConflictSummary,
    ConflictType,
    EngineHealthRecord,
    EnginePayload,
    EngineSource,
    HealthStatus,
    IntelligenceBundle,
    MarketIntelligenceSnapshot,
    MarketStateLabel,
    QualityDimension,
    QualityScore,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
    Conflict,
)
from iios.investment.market.integration.consistency_rules import ConsistencyRule, BUILT_IN_RULES

__all__ = [
    # Primary engine
    "MarketIntelligenceIntegrationEngine",
    # Input
    "IntelligenceBundle",
    "EnginePayload",
    "EngineSource",
    # Output
    "MarketIntelligenceSnapshot",
    "ValidationReport",
    "ValidationIssue",
    "ValidationStatus",
    "ConflictSummary",
    "Conflict",
    "ConflictType",
    "ConflictSeverity",
    "QualityScore",
    "QualityDimension",
    "EngineHealthRecord",
    "HealthStatus",
    # State
    "MarketStateLabel",
    # Configuration
    "ConsistencyRule",
    "BUILT_IN_RULES",
]
