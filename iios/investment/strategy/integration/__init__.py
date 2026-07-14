"""iios/investment/strategy/integration/__init__.py
Public surface of the Strategy Intelligence Integration & Validation Engine.
"""
from iios.investment.strategy.integration.integration_constants import (
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
from iios.investment.strategy.integration.integration_events import (
    IntegrationEvent,
    IntegrationEventBus,
)
from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
    make_update,
)
from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.aggregation_history import AggregationHistory
from iios.investment.strategy.integration.strategy_intelligence_aggregator import (
    StrategyIntelligenceAggregator,
)
from iios.investment.strategy.integration.consistency_rules import (
    ConsistencyRule,
    RuleCheckResult,
    RuleRegistry,
    create_default_rule_registry,
)
from iios.investment.strategy.integration.conflict_detector import ConflictDetector
from iios.investment.strategy.integration.validation_report import (
    ValidationCheck,
    ValidationReport,
    build_validation_report,
)
from iios.investment.strategy.integration.consistency_validator import ConsistencyValidator
from iios.investment.strategy.integration.conflict_classifier import (
    Conflict,
    ConflictClassifier,
)
from iios.investment.strategy.integration.conflict_resolution import ConflictResolver
from iios.investment.strategy.integration.conflict_engine import ConflictEngine
from iios.investment.strategy.integration.conflict_history import ConflictHistory
from iios.investment.strategy.integration.strategy_state import (
    SourceSummary,
    StrategyState,
)
from iios.investment.strategy.integration.strategy_summary import (
    StrategySummary,
    build_strategy_summary,
)
from iios.investment.strategy.integration.strategy_snapshot import (
    StrategySnapshot,
    build_snapshot,
)
from iios.investment.strategy.integration.snapshot_cache import SnapshotCache
from iios.investment.strategy.integration.strategy_statistics import (
    StrategyStatistics,
    StrategyStatisticsTracker,
)
from iios.investment.strategy.integration.strategy_confidence import (
    ConfidenceComponents,
    ConfidenceCalculator,
)
from iios.investment.strategy.integration.strategy_quality import (
    QualityReport,
    QualityFramework,
)
from iios.investment.strategy.integration.quality_statistics import (
    QualityStatistics,
    QualityStatisticsTracker,
)
from iios.investment.strategy.integration.quality_history import QualityHistory
from iios.investment.strategy.integration.engine_health import (
    EngineHealthChecker,
    EngineHealthEntry,
    EngineHealthReport,
)
from iios.investment.strategy.integration.dependency_monitor import (
    DependencyMonitor,
    DependencyStatus,
)
from iios.investment.strategy.integration.coverage_monitor import (
    CoverageMonitor,
    CoverageReport,
)
from iios.investment.strategy.integration.health_monitor import (
    HealthMonitor,
    HealthMonitorConfig,
)
from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
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
