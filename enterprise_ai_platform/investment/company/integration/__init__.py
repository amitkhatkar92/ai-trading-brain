"""enterprise_ai_platform/investment/company/integration/__init__.py
Public exports for the Company Intelligence Integration Engine.
"""
from enterprise_ai_platform.investment.company.integration.company_state import (
    IntelligenceCompleteness,
    ValidationStatus,
    ConflictSeverity,
    ConflictStatus,
    ConflictType,
    ResolutionStrategy,
    EngineStatus,
    KNOWN_ENGINES,
    SCORED_ENGINES,
    ENGINE_WEIGHTS,
    score_to_grade,
    completeness_from_fraction,
)
from enterprise_ai_platform.investment.company.integration.company_statistics import (
    clamp, safe_float, weighted_average, safe_average, score_to_label,
    compute_completeness, compute_freshness, compute_consistency,
    composite_quality_score,
)
from enterprise_ai_platform.investment.company.integration.aggregation_state import (
    AggregationState, EngineUpdate,
)
from enterprise_ai_platform.investment.company.integration.aggregation_history import AggregationHistory
from enterprise_ai_platform.investment.company.integration.company_summary import (
    CompanySummary, DimensionSummary,
)
from enterprise_ai_platform.investment.company.integration.company_snapshot import (
    CompanyIntelligenceSnapshot,
)
from enterprise_ai_platform.investment.company.integration.validation_report import (
    ValidationCheck, ValidationReport,
)
from enterprise_ai_platform.investment.company.integration.quality_statistics import (
    quality_grade, freshness_from_ages, confidence_from_quality,
)
from enterprise_ai_platform.investment.company.integration.quality_history import (
    QualityHistory, QualityRecord,
)
from enterprise_ai_platform.investment.company.integration.company_quality import (
    CompanyQualityScore, compute_company_quality,
)
from enterprise_ai_platform.investment.company.integration.company_confidence import (
    compute_confidence, explain_confidence,
)
from enterprise_ai_platform.investment.company.integration.consistency_rules import ALL_RULES
from enterprise_ai_platform.investment.company.integration.consistency_validator import ConsistencyValidator
from enterprise_ai_platform.investment.company.integration.conflict_detector import (
    ConflictRecord, detect_conflicts,
)
from enterprise_ai_platform.investment.company.integration.conflict_classifier import (
    classify_severity, conflict_summary, sort_by_priority,
)
from enterprise_ai_platform.investment.company.integration.conflict_resolution import ConflictResolver
from enterprise_ai_platform.investment.company.integration.conflict_history import ConflictHistory
from enterprise_ai_platform.investment.company.integration.conflict_engine import ConflictEngine
from enterprise_ai_platform.investment.company.integration.engine_health import (
    EngineHealthRecord, compute_engine_status,
)
from enterprise_ai_platform.investment.company.integration.dependency_monitor import DependencyMonitor
from enterprise_ai_platform.investment.company.integration.coverage_monitor import CoverageMonitor
from enterprise_ai_platform.investment.company.integration.health_monitor import HealthMonitor
from enterprise_ai_platform.investment.company.integration.company_intelligence_aggregator import (
    AggregatedIntelligence, aggregate_intelligence,
)
from enterprise_ai_platform.investment.company.integration.aggregation_engine import (
    AggregationEngine, compute_overall_score, build_summary,
)
from enterprise_ai_platform.investment.company.integration.company_intelligence_integration_engine import (
    CompanyIntelligenceIntegrationEngine,
)

__all__ = [
    # State enums and constants
    "IntelligenceCompleteness",
    "ValidationStatus",
    "ConflictSeverity", "ConflictStatus", "ConflictType", "ResolutionStrategy",
    "EngineStatus",
    "KNOWN_ENGINES", "SCORED_ENGINES", "ENGINE_WEIGHTS",
    "score_to_grade", "completeness_from_fraction",
    # Statistics
    "clamp", "safe_float", "weighted_average", "safe_average", "score_to_label",
    "compute_completeness", "compute_freshness", "compute_consistency",
    "composite_quality_score",
    # Aggregation
    "AggregationState", "EngineUpdate",
    "AggregationHistory",
    "AggregatedIntelligence", "aggregate_intelligence",
    "AggregationEngine", "compute_overall_score", "build_summary",
    # Snapshot
    "CompanyIntelligenceSnapshot",
    "CompanySummary", "DimensionSummary",
    # Quality
    "CompanyQualityScore", "compute_company_quality",
    "QualityHistory", "QualityRecord",
    "quality_grade", "freshness_from_ages", "confidence_from_quality",
    "compute_confidence", "explain_confidence",
    # Validation
    "ValidationCheck", "ValidationReport",
    "ALL_RULES", "ConsistencyValidator",
    # Conflicts
    "ConflictRecord", "detect_conflicts",
    "classify_severity", "conflict_summary", "sort_by_priority",
    "ConflictResolver",
    "ConflictHistory",
    "ConflictEngine",
    # Health
    "EngineHealthRecord", "compute_engine_status",
    "DependencyMonitor", "CoverageMonitor", "HealthMonitor",
    # Primary engine
    "CompanyIntelligenceIntegrationEngine",
]
