"""iios/investment/market/correlation — Institutional Correlation & Intermarket Intelligence Engine."""
from iios.investment.market.correlation.models import (
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
from iios.investment.market.correlation.correlation_estimator import CorrelationEstimator
from iios.investment.market.correlation.estimator_registry import EstimatorRegistry
from iios.investment.market.correlation.pearson_estimator import PearsonEstimator
from iios.investment.market.correlation.spearman_estimator import SpearmanEstimator
from iios.investment.market.correlation.kendall_estimator import KendallEstimator
from iios.investment.market.correlation.correlation_intelligence_engine import (
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

