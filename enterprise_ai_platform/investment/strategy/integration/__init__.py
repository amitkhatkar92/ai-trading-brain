"""enterprise_ai_platform/investment/strategy/integration/__init__.py
Public surface of the Strategy Intelligence Integration & Validation Engine.
"""
from enterprise_ai_platform.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    HealthStatus,
    IntelligenceSource,
    IntegrationEventType,
    IntegrationStatus,
    QualityDimension,
    ResolutionStrategy,
    SnapshotStatus,
    UpdateType,
    ValidationStatus,
    STALENESS_WARNING_SECONDS,
    STALENESS_CRITICAL_SECONDS,
)
from enterprise_ai_platform.investment.strategy.integration.integration_events import (
    IntegrationEvent,
    IntegrationEventBus,
)
from enterprise_ai_platform.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
    make_update,
)
from enterprise_ai_platform.investment.strategy.integration.aggregation_engine import AggregationEngine
from enterprise_ai_platform.investment.strategy.integration.aggregation_history import AggregationHistory
from enterprise_ai_platform.investment.strategy.integration.strategy_intelligence_aggregator import (
    StrategyIntelligenceAggregator,
)
from enterprise_ai_platform.investment.strategy.integration.consistency_rules import (
    ConsistencyRule,
    RuleCheckResult,
    RuleRegistry,
    create_default_rule_registry,
)
from enterprise_ai_platform.investment.strategy.integration.conflict_detector import ConflictDetector
from enterprise_ai_platform.investment.strategy.integration.validation_report import (
    ValidationCheck,
    ValidationReport,
    build_validation_report,
)
from enterprise_ai_platform.investment.strategy.integration.consistency_validator import ConsistencyValidator
from enterprise_ai_platform.investment.strategy.integration.conflict_classifier import (
    Conflict,
    ConflictClassifier,
)
from enterprise_ai_platform.investment.strategy.integration.conflict_resolution import ConflictResolver
from enterprise_ai_platform.investment.strategy.integration.conflict_engine import ConflictEngine
from enterprise_ai_platform.investment.strategy.integration.conflict_history import ConflictHistory
from enterprise_ai_platform.investment.strategy.integration.strategy_state import (
    SourceSummary,
    StrategyState,
)
from enterprise_ai_platform.investment.strategy.integration.strategy_summary import (
    StrategySummary,
    build_strategy_summary,
)
from enterprise_ai_platform.investment.strategy.integration.strategy_snapshot import (
    StrategySnapshot,
    build_snapshot,
)
from enterprise_ai_platform.investment.strategy.integration.snapshot_cache import SnapshotCache
from enterprise_ai_platform.investment.strategy.integration.strategy_statistics import (
    StrategyStatistics,
    StrategyStatisticsTracker,
)
from enterprise_ai_platform.investment.strategy.integration.strategy_confidence import (
    ConfidenceComponents,
    ConfidenceCalculator,
)
from enterprise_ai_platform.investment.strategy.integration.strategy_quality import (
    QualityReport,
    QualityFramework,
)
from enterprise_ai_platform.investment.strategy.integration.quality_statistics import (
    QualityStatistics,
    QualityStatisticsTracker,
)
from enterprise_ai_platform.investment.strategy.integration.quality_history import QualityHistory
from enterprise_ai_platform.investment.strategy.integration.engine_health import (
    EngineHealthChecker,
    EngineHealthEntry,
    EngineHealthReport,
)
from enterprise_ai_platform.investment.strategy.integration.dependency_monitor import (
    DependencyMonitor,
    DependencyStatus,
)
from enterprise_ai_platform.investment.strategy.integration.coverage_monitor import (
    CoverageMonitor,
    CoverageReport,
)
from enterprise_ai_platform.investment.strategy.integration.health_monitor import (
    HealthMonitor,
    HealthMonitorConfig,
)
from enterprise_ai_platform.investment.strategy.integration.strategy_intelligence_integration_engine import (
    StrategyIntelligenceIntegrationEngine,
)

__all__ = [
    # Constants / Enums
    "ConflictSeverity", "ConflictType", "HealthStatus", "IntelligenceSource",
    "IntegrationEventType", "IntegrationStatus", "QualityDimension",
    "ResolutionStrategy", "SnapshotStatus", "UpdateType", "ValidationStatus",
    "STALENESS_WARNING_SECONDS", "STALENESS_CRITICAL_SECONDS",
    # Events
    "IntegrationEvent", "IntegrationEventBus",
    # Aggregation
    "IntelligenceUpdate", "StrategyAggregationState", "make_update",
    "AggregationEngine", "AggregationHistory", "StrategyIntelligenceAggregator",
    # Validation
    "ConsistencyRule", "RuleCheckResult", "RuleRegistry",
    "create_default_rule_registry", "ConflictDetector",
    "ValidationCheck", "ValidationReport", "build_validation_report",
    "ConsistencyValidator",
    # Conflicts
    "Conflict", "ConflictClassifier", "ConflictResolver",
    "ConflictEngine", "ConflictHistory",
    # Snapshots
    "SourceSummary", "StrategyState",
    "StrategySummary", "build_strategy_summary",
    "StrategySnapshot", "build_snapshot", "SnapshotCache",
    "StrategyStatistics", "StrategyStatisticsTracker",
    # Quality & Confidence
    "ConfidenceComponents", "ConfidenceCalculator",
    "QualityReport", "QualityFramework",
    "QualityStatistics", "QualityStatisticsTracker",
    "QualityHistory",
    # Health
    "EngineHealthChecker", "EngineHealthEntry", "EngineHealthReport",
    "DependencyMonitor", "DependencyStatus",
    "CoverageMonitor", "CoverageReport",
    "HealthMonitor", "HealthMonitorConfig",
    # Main Facade
    "StrategyIntelligenceIntegrationEngine",
]
