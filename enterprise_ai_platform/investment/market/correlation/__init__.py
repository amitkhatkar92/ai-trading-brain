"""enterprise_ai_platform/investment/market/correlation — Institutional Correlation & Intermarket Intelligence Engine."""
from enterprise_ai_platform.investment.market.correlation.models import (
    AssetClass,
    ContagionPath,
    CorrelationConfidenceScore,
    CorrelationEvent,
    CorrelationEventType,
    CorrelationIntelligenceSnapshot,
    CorrelationMatrix,
    CorrelationMethod,
    CorrelationPair,
    CorrelationRegimeSnapshot,
    CorrelationRegimeType,
    DependencyEdge,
    DependencyGraph,
    DependencyType,
    DiversificationLevel,
    DiversificationMetrics,
    IntermarketAnalysis,
    IntermarketRelationship,
    MultiAssetSnapshot,
    PriceObservation,
    RelationshipType,
    RiskLevel,
    SystemicRiskMetrics,
)
from enterprise_ai_platform.investment.market.correlation.correlation_estimator import CorrelationEstimator
from enterprise_ai_platform.investment.market.correlation.estimator_registry import EstimatorRegistry
from enterprise_ai_platform.investment.market.correlation.pearson_estimator import PearsonEstimator
from enterprise_ai_platform.investment.market.correlation.spearman_estimator import SpearmanEstimator
from enterprise_ai_platform.investment.market.correlation.kendall_estimator import KendallEstimator
from enterprise_ai_platform.investment.market.correlation.correlation_intelligence_engine import (
    InstitutionalCorrelationIntelligenceEngine,
)

__all__ = [
    # Models
    "PriceObservation",
    "MultiAssetSnapshot",
    "CorrelationPair",
    "CorrelationMatrix",
    "DependencyEdge",
    "DependencyGraph",
    "IntermarketRelationship",
    "IntermarketAnalysis",
    "ContagionPath",
    "SystemicRiskMetrics",
    "DiversificationMetrics",
    "CorrelationRegimeSnapshot",
    "CorrelationConfidenceScore",
    "CorrelationEvent",
    "CorrelationIntelligenceSnapshot",
    # Enums
    "CorrelationRegimeType",
    "CorrelationEventType",
    "AssetClass",
    "CorrelationMethod",
    "DependencyType",
    "RiskLevel",
    "DiversificationLevel",
    "RelationshipType",
    # Protocols / Registries
    "CorrelationEstimator",
    "EstimatorRegistry",
    # Built-in estimators
    "PearsonEstimator",
    "SpearmanEstimator",
    "KendallEstimator",
    # Primary engine
    "InstitutionalCorrelationIntelligenceEngine",
]

