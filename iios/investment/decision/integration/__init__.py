"""iios/investment/decision/integration/__init__.py
Public surface of the Decision Intelligence Integration & Validation Engine.
"""
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    ConflictResolutionStrategy,
    ConflictSeverity,
    ConflictType,
    HealthStatus,
    IntegrationStatus,
    QualityGrade,
    SnapshotStatus,
    ValidationStatus,
)
from iios.investment.decision.integration.aggregation_state import (
    AggregationState,
    _AggregationStateSnapshot as AggregationStateSnapshot,
)
from iios.investment.decision.integration.aggregation_history import AggregationHistory
from iios.investment.decision.integration.aggregation_engine import AggregationEngine
from iios.investment.decision.integration.decision_intelligence_aggregator import (
    DecisionIntelligenceAggregator,
)
from iios.investment.decision.integration.validation_report import (
    ValidationCheck,
    ValidationReport,
    build_validation_report,
)
from iios.investment.decision.integration.consistency_rules import (
    ConsistencyRule,
    DEFAULT_RULES,
)
from iios.investment.decision.integration.consistency_validator import ConsistencyValidator
from iios.investment.decision.integration.conflict_detector import (
    ConflictDetector,
    DetectedConflict,
)
from iios.investment.decision.integration.conflict_classifier import ConflictClassifier
from iios.investment.decision.integration.conflict_resolution import (
    ConflictResolver,
    ResolutionResult,
)
from iios.investment.decision.integration.conflict_history import ConflictHistory
from iios.investment.decision.integration.conflict_engine import (
    ConflictEngine,
    ConflictReport,
)
from iios.investment.decision.integration.decision_state import (
    IntegrationDecisionState,
    build_decision_state,
)
from iios.investment.decision.integration.decision_summary import (
    CommitteeSummary,
    ConfidenceSummary,
    DecisionSummaryBuilder,
    EvidenceSummary,
    ExplanationSummary,
    ReasoningSummary,
    RecommendationSummary,
    RiskSummary,
)
from iios.investment.decision.integration.decision_statistics import (
    IntegrationStatistics,
    IntegrationStatisticsTracker,
)
from iios.investment.decision.integration.decision_snapshot import (
    DecisionIntelligenceSnapshot,
    build_decision_snapshot,
)
from iios.investment.decision.integration.decision_quality import DecisionQualityEvaluator
from iios.investment.decision.integration.decision_confidence import (
    IntegrationConfidenceCalculator,
)
from iios.investment.decision.integration.quality_statistics import (
    QualityStatistics,
    QualityStatisticsTracker,
)
from iios.investment.decision.integration.quality_history import (
    QualityHistory,
    QualityRecord,
)
from iios.investment.decision.integration.engine_health import (
    EngineHealthMonitor,
    EngineHealthRecord,
)
from iios.investment.decision.integration.dependency_monitor import (
    DependencyMonitor,
    DependencyStatus,
)
from iios.investment.decision.integration.coverage_monitor import (
    CoverageMonitor,
    CoverageReport,
)
from iios.investment.decision.integration.health_monitor import (
    IntegrationHealthMonitor,
    IntegrationHealthReport,
)
from iios.investment.decision.integration.decision_intelligence_integration_engine import (
    DecisionIntelligenceIntegrationEngine,
)

__all__ = [
    # Constants
    "ComponentId",
    "ConflictResolutionStrategy",
    "ConflictSeverity",
    "ConflictType",
    "HealthStatus",
    "IntegrationStatus",
    "QualityGrade",
    "SnapshotStatus",
    "ValidationStatus",
    # Aggregation
    "AggregationEngine",
    "AggregationHistory",
    "AggregationState",
    "AggregationStateSnapshot",
    "DecisionIntelligenceAggregator",
    # Validation
    "ConsistencyRule",
    "ConsistencyValidator",
    "DEFAULT_RULES",
    "ValidationCheck",
    "ValidationReport",
    "build_validation_report",
    # Conflict
    "ConflictClassifier",
    "ConflictDetector",
    "ConflictEngine",
    "ConflictHistory",
    "ConflictReport",
    "ConflictResolver",
    "DetectedConflict",
    "ResolutionResult",
    # Snapshot
    "DecisionIntelligenceSnapshot",
    "build_decision_snapshot",
    "DecisionSummaryBuilder",
    "EvidenceSummary",
    "ReasoningSummary",
    "ConfidenceSummary",
    "RiskSummary",
    "ExplanationSummary",
    "CommitteeSummary",
    "RecommendationSummary",
    # State & stats
    "IntegrationDecisionState",
    "build_decision_state",
    "IntegrationStatistics",
    "IntegrationStatisticsTracker",
    # Quality
    "DecisionQualityEvaluator",
    "IntegrationConfidenceCalculator",
    "QualityHistory",
    "QualityRecord",
    "QualityStatistics",
    "QualityStatisticsTracker",
    # Health
    "CoverageMonitor",
    "CoverageReport",
    "DependencyMonitor",
    "DependencyStatus",
    "EngineHealthMonitor",
    "EngineHealthRecord",
    "IntegrationHealthMonitor",
    "IntegrationHealthReport",
    # Main engine
    "DecisionIntelligenceIntegrationEngine",
]
