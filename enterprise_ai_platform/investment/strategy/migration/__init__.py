"""enterprise_ai_platform/investment/strategy/migration/__init__.py
Public API for the Strategy Migration Framework.
"""

# ── Status & enums ─────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.migration_status import (
    MigrationStatus,
    MigrationPhase,
    CompatibilityLevel,
    MigrationRisk,
    RollbackReason,
)

# ── Events ─────────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.migration_events import (
    MigrationEvent,
    MigrationEventBus,
    MigrationEventType,
)

# ── Legacy metadata ────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.legacy_metadata import (
    EntryCondition,
    LegacyHealthStatus,
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)

# ── Registry & catalog ─────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.legacy_registry import LegacyStrategyRegistry
from enterprise_ai_platform.investment.strategy.migration.legacy_catalog import LegacyCatalog

# ── Discovery ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.legacy_discovery import (
    DiscoveryConfig,
    DiscoveryResult,
    LegacyDiscoveryEngine,
)

# ── Adapters ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.strategy_adapter import (
    AdaptationMode,
    LegacyStrategyAdapter,
)
from enterprise_ai_platform.investment.strategy.migration.adapter_registry import AdapterRegistry
from enterprise_ai_platform.investment.strategy.migration.adapter_factory import AdapterFactory

# ── Compatibility ──────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.compatibility_layer import CompatibilityLayer

# ── Validation ─────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.validation_report import (
    CheckSeverity,
    ValidationCheck,
    ValidationCheckType,
    ValidationReport,
    build_validation_report,
)
from enterprise_ai_platform.investment.strategy.migration.compatibility_validator import CompatibilityValidator
from enterprise_ai_platform.investment.strategy.migration.migration_validator import (
    AdapterValidationResult,
    MigrationValidator,
)

# ── Pipeline ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.migration_steps import (
    MigrationStepExecutor,
    MigrationStepResult,
    StepResult,
)
from enterprise_ai_platform.investment.strategy.migration.migration_statistics import MigrationStatistics
from enterprise_ai_platform.investment.strategy.migration.migration_session import MigrationSession
from enterprise_ai_platform.investment.strategy.migration.migration_pipeline import (
    MigrationPipeline,
    PipelineConfig,
)

# ── Signal & behavior ─────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.signal_comparator import (
    FieldComparison,
    SignalComparator,
    SignalComparison,
    SignalField,
)
from enterprise_ai_platform.investment.strategy.migration.signal_equivalence import (
    EquivalenceResult,
    SignalEquivalenceChecker,
)
from enterprise_ai_platform.investment.strategy.migration.behavior_validator import (
    BehaviorCaseResult,
    BehaviorReport,
    BehaviorTestCase,
    BehaviorValidator,
)
from enterprise_ai_platform.investment.strategy.migration.result_comparator import (
    ComparisonResult,
    ResultComparator,
)

# ── Reporting ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.migration_report import (
    MigrationReport,
    build_migration_report,
    RECOMMEND_APPROVE,
    RECOMMEND_REJECT,
    RECOMMEND_REVIEW,
)
from enterprise_ai_platform.investment.strategy.migration.migration_summary import (
    MigrationSummary,
    MigrationSummaryBuilder,
)
from enterprise_ai_platform.investment.strategy.migration.migration_audit import (
    AuditEntry,
    MigrationAudit,
    make_entry,
)
from enterprise_ai_platform.investment.strategy.migration.migration_confidence import MigrationConfidence

# ── Engine ─────────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.migration.strategy_migration_engine import (
    StrategyMigrationEngine,
)

__all__ = [
    # Status
    "MigrationStatus", "MigrationPhase", "CompatibilityLevel",
    "MigrationRisk", "RollbackReason",
    # Events
    "MigrationEvent", "MigrationEventBus", "MigrationEventType",
    # Metadata
    "EntryCondition", "LegacyHealthStatus", "LegacyStrategyMetadata",
    "LegacyStrategySource", "LegacyStrategyType",
    # Registry / catalog
    "LegacyStrategyRegistry", "LegacyCatalog",
    # Discovery
    "DiscoveryConfig", "DiscoveryResult", "LegacyDiscoveryEngine",
    # Adapters
    "AdaptationMode", "LegacyStrategyAdapter",
    "AdapterRegistry", "AdapterFactory",
    # Compatibility
    "CompatibilityLayer",
    # Validation
    "CheckSeverity", "ValidationCheck", "ValidationCheckType",
    "ValidationReport", "build_validation_report",
    "CompatibilityValidator",
    "AdapterValidationResult", "MigrationValidator",
    # Pipeline
    "MigrationStepExecutor", "MigrationStepResult", "StepResult",
    "MigrationStatistics", "MigrationSession",
    "MigrationPipeline", "PipelineConfig",
    # Signal / behavior
    "FieldComparison", "SignalComparator", "SignalComparison", "SignalField",
    "EquivalenceResult", "SignalEquivalenceChecker",
    "BehaviorCaseResult", "BehaviorReport", "BehaviorTestCase", "BehaviorValidator",
    "ComparisonResult", "ResultComparator",
    # Reporting
    "MigrationReport", "build_migration_report",
    "RECOMMEND_APPROVE", "RECOMMEND_REJECT", "RECOMMEND_REVIEW",
    "MigrationSummary", "MigrationSummaryBuilder",
    "AuditEntry", "MigrationAudit", "make_entry",
    "MigrationConfidence",
    # Engine
    "StrategyMigrationEngine",
]
