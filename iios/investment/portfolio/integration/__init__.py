"""iios/investment/portfolio/integration/__init__.py

Public API for the Portfolio Intelligence Integration & Validation Engine.
"""
from __future__ import annotations

# ── Types and constants ────────────────────────────────────────────────────────
from iios.investment.portfolio.integration.integration_types import (
    ALL_ENGINE_IDS,
    DEFAULT_FRESHNESS_HOURS,
    DEFAULT_MIN_COMPLETENESS,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_CONSISTENCY,
    DEFAULT_MIN_QUALITY_PUBLISH,
    DEFAULT_QUALITY_HISTORY,
    DEFAULT_SNAPSHOT_HISTORY,
    QUALITY_SCORE_AVERAGE,
    QUALITY_SCORE_EXCELLENT,
    QUALITY_SCORE_GOOD,
    QUALITY_SCORE_POOR,
    REQUIRED_ENGINES,
    AggregationStatus,
    ConflictResolutionStatus,
    ConflictSeverity,
    EngineId,
    HealthStatus,
    IntegrationParameters,
    QualityGrade,
    SnapshotStatus,
    ValidationStatus,
    hours_since,
    now_utc,
    score_to_grade,
)

# ── Aggregation ────────────────────────────────────────────────────────────────
from iios.investment.portfolio.integration.aggregation_state import (
    AggregationState,
    EngineContribution,
)
from iios.investment.portfolio.integration.aggregation_history import (
    AggregationHistory,
    AggregationRecord,
)
from iios.investment.portfolio.integration.aggregation_engine import AggregationEngine
from iios.investment.portfolio.integration.portfolio_intelligence_aggregator import (
    PortfolioIntelligenceAggregator,
)

# ── Consistency validation ─────────────────────────────────────────────────────
from iios.investment.portfolio.integration.consistency_rules import (
    check_allocation_weights_sum,
    check_construction_allocation_position_count,
    check_diversification_hhi,
    check_optimization_vs_construction_quality,
    check_rebalancing_vs_allocation_drift,
    check_recommendation_vs_risk_budget,
    check_risk_performance_drawdown,
)
from iios.investment.portfolio.integration.validation_report import (
    ConsistencyValidationReport,
    ValidationCheck,
)
from iios.investment.portfolio.integration.consistency_validator import (
    ConsistencyValidator,
)

# ── Conflict detection and resolution ─────────────────────────────────────────
from iios.investment.portfolio.integration.conflict_detector import (
    ConflictDetector,
    DetectedConflict,
)
from iios.investment.portfolio.integration.conflict_classifier import (
    ClassifiedConflict,
    ConflictClassifier,
)
from iios.investment.portfolio.integration.conflict_resolution import (
    ConflictResolutionResult,
    ConflictResolver,
)
from iios.investment.portfolio.integration.conflict_history import ConflictHistory
from iios.investment.portfolio.integration.conflict_engine import (
    ConflictEngine,
    ConflictReport,
)

# ── Snapshot and summary ───────────────────────────────────────────────────────
from iios.investment.portfolio.integration.portfolio_snapshot import (
    PortfolioIntelligenceSnapshot,
)
from iios.investment.portfolio.integration.portfolio_summary import (
    PortfolioState,
    PortfolioSummary,
    build_state,
    build_summary,
)
from iios.investment.portfolio.integration.portfolio_statistics import (
    IntegrationRunMetric,
    PortfolioIntegrationStatistics,
    PortfolioIntegrationStatisticsSnapshot,
)

# ── Quality ────────────────────────────────────────────────────────────────────
from iios.investment.portfolio.integration.portfolio_quality import (
    PortfolioQualityAssessor,
    PortfolioQualityReport,
)
from iios.investment.portfolio.integration.portfolio_confidence import (
    PortfolioConfidenceCalculator,
    PortfolioConfidenceScore,
)
from iios.investment.portfolio.integration.quality_statistics import (
    QualityRunMetric,
    QualityStatistics,
)
from iios.investment.portfolio.integration.quality_history import QualityHistory

# ── Health and monitoring ──────────────────────────────────────────────────────
from iios.investment.portfolio.integration.engine_health import (
    EngineHealthMonitor,
    EngineHealthRecord,
    EngineHealthStatus,
)
from iios.investment.portfolio.integration.health_monitor import (
    IntegrationHealthMonitor,
    IntegrationHealthReport,
)
from iios.investment.portfolio.integration.coverage_monitor import (
    CoverageMonitor,
    CoverageReport,
)
from iios.investment.portfolio.integration.dependency_monitor import (
    DependencyMonitor,
    DependencyStatus,
)

# ── Main engine ────────────────────────────────────────────────────────────────
from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
    PortfolioIntelligenceIntegrationEngine,
)

__all__ = [
    # Types
    "EngineId", "AggregationStatus", "ValidationStatus", "ConflictSeverity",
    "ConflictResolutionStatus", "QualityGrade", "HealthStatus", "SnapshotStatus",
    "IntegrationParameters",
    "ALL_ENGINE_IDS", "REQUIRED_ENGINES",
    "QUALITY_SCORE_EXCELLENT", "QUALITY_SCORE_GOOD",
    "QUALITY_SCORE_AVERAGE", "QUALITY_SCORE_POOR",
    "DEFAULT_MIN_COMPLETENESS", "DEFAULT_MIN_CONSISTENCY",
    "DEFAULT_FRESHNESS_HOURS", "DEFAULT_MIN_CONFIDENCE",
    "DEFAULT_MIN_QUALITY_PUBLISH",
    "now_utc", "hours_since", "score_to_grade",
    # Aggregation
    "EngineContribution", "AggregationState",
    "AggregationRecord", "AggregationHistory",
    "AggregationEngine", "PortfolioIntelligenceAggregator",
    # Consistency
    "check_allocation_weights_sum",
    "check_construction_allocation_position_count",
    "check_optimization_vs_construction_quality",
    "check_risk_performance_drawdown",
    "check_rebalancing_vs_allocation_drift",
    "check_recommendation_vs_risk_budget",
    "check_diversification_hhi",
    "ValidationCheck", "ConsistencyValidationReport",
    "ConsistencyValidator",
    # Conflict
    "DetectedConflict", "ConflictDetector",
    "ClassifiedConflict", "ConflictClassifier",
    "ConflictResolutionResult", "ConflictResolver",
    "ConflictHistory",
    "ConflictReport", "ConflictEngine",
    # Snapshot / summary
    "PortfolioIntelligenceSnapshot",
    "PortfolioState", "PortfolioSummary", "build_state", "build_summary",
    "IntegrationRunMetric",
    "PortfolioIntegrationStatisticsSnapshot", "PortfolioIntegrationStatistics",
    # Quality
    "PortfolioQualityReport", "PortfolioQualityAssessor",
    "PortfolioConfidenceScore", "PortfolioConfidenceCalculator",
    "QualityRunMetric", "QualityStatistics", "QualityHistory",
    # Health / monitoring
    "EngineHealthRecord", "EngineHealthStatus", "EngineHealthMonitor",
    "IntegrationHealthReport", "IntegrationHealthMonitor",
    "CoverageReport", "CoverageMonitor",
    "DependencyStatus", "DependencyMonitor",
    # Engine
    "PortfolioIntelligenceIntegrationEngine",
]
