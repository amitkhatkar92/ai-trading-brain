"""iios/investment/strategy/migration/__init__.py
Public API for the Strategy Migration Framework.
"""

# ── Status & enums ─────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.migration_status import (
    MigrationStatus,
    MigrationPhase,
    CompatibilityLevel,
    MigrationRisk,
    RollbackReason,
)

# ── Events ─────────────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.migration_events import (
    MigrationEvent,
    MigrationEventBus,
    MigrationEventType,
)

# ── Legacy metadata ────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.legacy_metadata import (
    EntryCondition,
    LegacyHealthStatus,
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)

# ── Registry & catalog ─────────────────────────────────────────────────────────
from iios.investment.strategy.migration.legacy_registry import LegacyStrategyRegistry
from iios.investment.strategy.migration.legacy_catalog import LegacyCatalog

# ── Discovery ──────────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.legacy_discovery import (
    DiscoveryConfig,
    DiscoveryResult,
    LegacyDiscoveryEngine,
)

# ── Adapters ───────────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.strategy_adapter import (
    AdaptationMode,
    LegacyStrategyAdapter,
)
from iios.investment.strategy.migration.adapter_registry import AdapterRegistry
from iios.investment.strategy.migration.adapter_factory import AdapterFactory

# ── Compatibility ──────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.compatibility_layer import CompatibilityLayer

# ── Validation ─────────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.validation_report import (
    CheckSeverity,
    ValidationCheck,
    ValidationCheckType,
    ValidationReport,
    build_validation_report,
)
from iios.investment.strategy.migration.compatibility_validator import CompatibilityValidator
from iios.investment.strategy.migration.migration_validator import (
    AdapterValidationResult,
    MigrationValidator,
)

# ── Pipeline ───────────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.migration_steps import (
    MigrationStepExecutor,
    MigrationStepResult,
    StepResult,
)
from iios.investment.strategy.migration.migration_statistics import MigrationStatistics
from iios.investment.strategy.migration.migration_session import MigrationSession
from iios.investment.strategy.migration.migration_pipeline import (
    MigrationPipeline,
    PipelineConfig,
)

# ── Signal & behavior ─────────────────────────────────────────────────────────
from iios.investment.strategy.migration.signal_comparator import (
    FieldComparison,
    SignalComparator,
    SignalComparison,
    SignalField,
)
from iios.investment.strategy.migration.signal_equivalence import (
    EquivalenceResult,
    SignalEquivalenceChecker,
)
from iios.investment.strategy.migration.behavior_validator import (
    BehaviorCaseResult,
    BehaviorReport,
    BehaviorTestCase,
    BehaviorValidator,
)
from iios.investment.strategy.migration.result_comparator import (
    ComparisonResult,
    ResultComparator,
)

# ── Reporting ──────────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.migration_report import (
    MigrationReport,
    build_migration_report,
    RECOMMEND_APPROVE,
    RECOMMEND_REJECT,
    RECOMMEND_REVIEW,
)
from iios.investment.strategy.migration.migration_summary import (
    MigrationSummary,
    MigrationSummaryBuilder,
)
from iios.investment.strategy.migration.migration_audit import (
    AuditEntry,
    MigrationAudit,
    make_entry,
)
from iios.investment.strategy.migration.migration_confidence import MigrationConfidence

# ── Engine ─────────────────────────────────────────────────────────────────────
from iios.investment.strategy.migration.strategy_migration_engine import (
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
