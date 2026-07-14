"""iios/investment/strategy/integration/integration_constants.py
All enumerations and constants for the Strategy Intelligence Integration Engine.
"""
from __future__ import annotations

from enum import Enum


class IntelligenceSource(str, Enum):
    """Source engines that submit intelligence updates."""
    STRATEGY_FRAMEWORK = "strategy_framework"
    LIFECYCLE          = "lifecycle"
    EVALUATION         = "evaluation"
    OPPORTUNITY        = "opportunity"
    PORTFOLIO          = "portfolio"
    RISK               = "risk"
    LEARNING           = "learning"
    MIGRATION          = "migration"
    DEBATE             = "debate"
    MARKET             = "market"
    COMPANY            = "company"

    @property
    def is_required(self) -> bool:
        return self in (
            IntelligenceSource.STRATEGY_FRAMEWORK,
            IntelligenceSource.LIFECYCLE,
            IntelligenceSource.EVALUATION,
            IntelligenceSource.RISK,
        )

    @property
    def importance_weight(self) -> float:
        """Higher = more important for completeness scoring."""
        weights = {
            IntelligenceSource.STRATEGY_FRAMEWORK: 1.5,
            IntelligenceSource.LIFECYCLE:          1.5,
            IntelligenceSource.EVALUATION:         1.5,
            IntelligenceSource.RISK:               1.5,
            IntelligenceSource.OPPORTUNITY:        1.0,
            IntelligenceSource.PORTFOLIO:          1.0,
            IntelligenceSource.LEARNING:           1.0,
            IntelligenceSource.MIGRATION:          0.5,
            IntelligenceSource.DEBATE:             0.5,
            IntelligenceSource.MARKET:             0.5,
            IntelligenceSource.COMPANY:            0.5,
        }
        return weights.get(self, 1.0)

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()


class UpdateType(str, Enum):
    FULL_SNAPSHOT  = "full_snapshot"
    INCREMENTAL    = "incremental"
    CORRECTION     = "correction"
    INVALIDATION   = "invalidation"   # marks prior data invalid


class IntegrationStatus(str, Enum):
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    VALIDATING   = "validating"
    PUBLISHING   = "publishing"
    HEALTHY      = "healthy"
    DEGRADED     = "degraded"
    FAILED       = "failed"

    @property
    def is_operational(self) -> bool:
        return self in (
            IntegrationStatus.COLLECTING,
            IntegrationStatus.VALIDATING,
            IntegrationStatus.PUBLISHING,
            IntegrationStatus.HEALTHY,
            IntegrationStatus.DEGRADED,
        )


class ValidationStatus(str, Enum):
    PASSED     = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED     = "failed"
    INCOMPLETE = "incomplete"   # not enough data to validate
    PENDING    = "pending"


class ConflictType(str, Enum):
    EVALUATION_VS_RISK        = "evaluation_vs_risk"
    OPPORTUNITY_VS_PORTFOLIO  = "opportunity_vs_portfolio"
    LEARNING_VS_EVALUATION    = "learning_vs_evaluation"
    DEBATE_VS_RISK            = "debate_vs_risk"
    MIGRATION_VS_EVALUATION   = "migration_vs_evaluation"
    PORTFOLIO_VS_OPPORTUNITY  = "portfolio_vs_opportunity"
    LIFECYCLE_VS_EVALUATION   = "lifecycle_vs_evaluation"
    CROSS_ENGINE              = "cross_engine"

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()


class ConflictSeverity(str, Enum):
    CRITICAL = "critical"   # blocks publishing
    HIGH     = "high"       # flagged in report, reduces confidence
    MEDIUM   = "medium"     # noted, mild confidence reduction
    LOW      = "low"        # informational only

    @property
    def score_penalty(self) -> float:
        """Penalty applied to consistency score per unresolved conflict."""
        return {"critical": 20.0, "high": 10.0, "medium": 5.0, "low": 2.0}[self.value]

    @property
    def blocks_publishing(self) -> bool:
        return self == ConflictSeverity.CRITICAL


class ResolutionStrategy(str, Enum):
    HIGHER_CONFIDENCE = "higher_confidence"   # prefer the update with higher confidence
    MOST_RECENT       = "most_recent"         # prefer the newer update
    RISK_FIRST        = "risk_first"          # always side with risk intelligence
    CONSERVATIVE      = "conservative"        # prefer the more conservative of the two
    ESCALATE          = "escalate"            # no automatic resolution; flag for human review


class QualityDimension(str, Enum):
    COMPLETENESS  = "completeness"
    FRESHNESS     = "freshness"
    CONSISTENCY   = "consistency"
    RELIABILITY   = "reliability"
    COVERAGE      = "coverage"

    @property
    def default_weight(self) -> float:
        return {
            QualityDimension.COMPLETENESS: 0.30,
            QualityDimension.FRESHNESS:    0.25,
            QualityDimension.CONSISTENCY:  0.25,
            QualityDimension.RELIABILITY:  0.15,
            QualityDimension.COVERAGE:     0.05,
        }[self]


class HealthStatus(str, Enum):
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN     = "unknown"

    @property
    def is_operational(self) -> bool:
        return self in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


class SnapshotStatus(str, Enum):
    COMPLETE   = "complete"     # all required sources present
    PARTIAL    = "partial"      # some required sources missing
    STALE      = "stale"        # data older than staleness threshold
    INVALID    = "invalid"      # failed validation
    PENDING    = "pending"      # not yet generated

    @property
    def is_publishable(self) -> bool:
        return self in (SnapshotStatus.COMPLETE, SnapshotStatus.PARTIAL)


# Staleness thresholds (seconds)
STALENESS_WARNING_SECONDS  = 4 * 3600    # 4 hours
STALENESS_CRITICAL_SECONDS = 24 * 3600   # 24 hours

# Scoring weights
COMPLETENESS_WEIGHT = 0.30
FRESHNESS_WEIGHT    = 0.25
CONSISTENCY_WEIGHT  = 0.25
RELIABILITY_WEIGHT  = 0.15
COVERAGE_WEIGHT     = 0.05

# Integration events
class IntegrationEventType(str, Enum):
    UPDATE_RECEIVED     = "update_received"
    SNAPSHOT_PUBLISHED  = "snapshot_published"
    CONFLICT_DETECTED   = "conflict_detected"
    CONFLICT_RESOLVED   = "conflict_resolved"
    VALIDATION_FAILED   = "validation_failed"
    HEALTH_CHANGED      = "health_changed"
    ENGINE_STARTED      = "engine_started"
    ENGINE_STOPPED      = "engine_stopped"
    STALE_INTELLIGENCE  = "stale_intelligence"
