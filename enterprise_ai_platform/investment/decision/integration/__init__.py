"""enterprise_ai_platform/investment/decision/integration/__init__.py
Public surface of the Decision Intelligence Integration & Validation Engine.
"""
from enterprise_ai_platform.investment.decision.integration.integration_constants import (
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
from enterprise_ai_platform.investment.decision.integration.aggregation_state import (
    AggregationState,
    _AggregationStateSnapshot as AggregationStateSnapshot,
)
from enterprise_ai_platform.investment.decision.integration.aggregation_history import AggregationHistory
from enterprise_ai_platform.investment.decision.integration.aggregation_engine import AggregationEngine
from enterprise_ai_platform.investment.decision.integration.decision_intelligence_aggregator import (
    DecisionIntelligenceAggregator,
)
from enterprise_ai_platform.investment.decision.integration.validation_report import (
    ValidationCheck,
    ValidationReport,
    build_validation_report,
)
from enterprise_ai_platform.investment.decision.integration.consistency_rules import (
    ConsistencyRule,
    DEFAULT_RULES,
)
from enterprise_ai_platform.investment.decision.integration.consistency_validator import ConsistencyValidator
from enterprise_ai_platform.investment.decision.integration.conflict_detector import (
    ConflictDetector,
    DetectedConflict,
)
from enterprise_ai_platform.investment.decision.integration.conflict_classifier import ConflictClassifier
from enterprise_ai_platform.investment.decision.integration.conflict_resolution import (
    ConflictResolver,
    ResolutionResult,
)
from enterprise_ai_platform.investment.decision.integration.conflict_history import ConflictHistory
from enterprise_ai_platform.investment.decision.integration.conflict_engine import (
    ConflictEngine,
    ConflictReport,
)
from enterprise_ai_platform.investment.decision.integration.decision_state import (
    IntegrationDecisionState,
    build_decision_state,
)
from enterprise_ai_platform.investment.decision.integration.decision_summary import (
    CommitteeSummary,
    ConfidenceSummary,
    DecisionSummaryBuilder,
    EvidenceSummary,
    ExplanationSummary,
    ReasoningSummary,
    RecommendationSummary,
    RiskSummary,
)
from enterprise_ai_platform.investment.decision.integration.decision_statistics import (
    IntegrationStatistics,
    IntegrationStatisticsTracker,
)
from enterprise_ai_platform.investment.decision.integration.decision_snapshot import (
    DecisionIntelligenceSnapshot,
    build_decision_snapshot,
)
from enterprise_ai_platform.investment.decision.integration.decision_quality import DecisionQualityEvaluator
from enterprise_ai_platform.investment.decision.integration.decision_confidence import (
    IntegrationConfidenceCalculator,
)
from enterprise_ai_platform.investment.decision.integration.quality_statistics import (
    QualityStatistics,
    QualityStatisticsTracker,
)
from enterprise_ai_platform.investment.decision.integration.quality_history import (
    QualityHistory,
    QualityRecord,
)
from enterprise_ai_platform.investment.decision.integration.engine_health import (
    EngineHealthMonitor,
    EngineHealthRecord,
)
from enterprise_ai_platform.investment.decision.integration.dependency_monitor import (
    DependencyMonitor,
    DependencyStatus,
)
from enterprise_ai_platform.investment.decision.integration.coverage_monitor import (
    CoverageMonitor,
    CoverageReport,
)
from enterprise_ai_platform.investment.decision.integration.health_monitor import (
    IntegrationHealthMonitor,
    IntegrationHealthReport,
)
from enterprise_ai_platform.investment.decision.integration.decision_intelligence_integration_engine import (
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
