"""
risk_snapshot.py — iios.risk.snapshot
=======================================
Core immutable RiskSnapshot value object.

The RiskSnapshot is the ONLY published representation of the
Risk Intelligence subsystem.  It aggregates validated outputs from:
  - Risk Assessment Framework (M4)
  - Risk Policy Framework (M3)
  - Risk Engine (M2)
  - Risk Lifecycle (M1)

It performs NO calculations, NO policy evaluation,
NO optimization, and NO execution.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    IntegrityStatus,
    RiskLevel,
    RiskPriority,
    RiskRating,
    RiskScope,
    RiskTrend,
    RiskType,
    SCORE_TO_LEVEL,
    SCORE_TO_RATING,
    LEVEL_TO_PRIORITY,
    SnapshotStatus,
    VERSION,
)
from .risk_snapshot_metadata import (
    AssessmentSummarySection,
    OptimizationSummary,
    PolicySummary,
    QuantitativeMetrics,
    SnapshotAudit,
    SnapshotMetadata,
    SnapshotStatisticsSection,
    StressTestSummary,
    SystemHealthSummary,
)


# ---------------------------------------------------------------------------
# RiskSnapshotSummary — immutable risk summary section
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskSnapshotSummary:
    """High-level risk summary for the snapshot."""
    overall_risk_score: float
    risk_rating:        RiskRating
    risk_level:         RiskLevel
    risk_trend:         RiskTrend
    risk_confidence:    float        # 0.0–1.0
    assessment_status:  str

    @classmethod
    def from_score(
        cls,
        score:             float,
        assessment_status: str,
        *,
        trend:      RiskTrend = RiskTrend.UNKNOWN,
        confidence: float     = 1.0,
    ) -> "RiskSnapshotSummary":
        rating = RiskRating.CRITICAL
        for threshold, r in SCORE_TO_RATING:
            if score <= threshold:
                rating = r
                break
        level = RiskLevel.CRITICAL
        for threshold, lv in SCORE_TO_LEVEL:
            if score <= threshold:
                level = lv
                break
        return cls(
            overall_risk_score = score,
            risk_rating        = rating,
            risk_level         = level,
            risk_trend         = trend,
            risk_confidence    = max(0.0, min(1.0, confidence)),
            assessment_status  = assessment_status,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_risk_score": self.overall_risk_score,
            "risk_rating":        self.risk_rating.value,
            "risk_level":         self.risk_level.value,
            "risk_trend":         self.risk_trend.value,
            "risk_confidence":    self.risk_confidence,
            "assessment_status":  self.assessment_status,
        }


# ---------------------------------------------------------------------------
# RiskSnapshot — master immutable snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskSnapshot:
    """
    Complete, immutable published representation of the Risk Intelligence
    subsystem for a single risk assessment cycle.

    Every downstream subsystem MUST consume RiskSnapshot instead of
    directly accessing the Risk Engine, Risk Policy Framework, or
    Risk Assessment Framework.
    """

    # ── Identity fields ────────────────────────────────────────────────────
    snapshot_id:        str
    risk_session_id:    str
    risk_assessment_id: str
    workflow_id:        str
    portfolio_id:       str
    strategy_id:        str
    account_id:         str

    # ── Classification fields ──────────────────────────────────────────────
    risk_scope:     RiskScope
    risk_type:      RiskType
    risk_priority:  RiskPriority
    risk_status:    SnapshotStatus
    lifecycle_state: str

    # ── Versioning ─────────────────────────────────────────────────────────
    risk_version:      str
    framework_version: str
    snapshot_version:  int   # monotonic snapshot version for this assessment

    # ── Timestamps ─────────────────────────────────────────────────────────
    assessment_timestamp: float
    created_time:         float
    updated_time:         float

    # ── Risk Summary ───────────────────────────────────────────────────────
    summary: RiskSnapshotSummary

    # ── Assessment Summary ─────────────────────────────────────────────────
    assessment_summary: AssessmentSummarySection

    # ── Quantitative Metrics ───────────────────────────────────────────────
    quantitative_metrics: QuantitativeMetrics

    # ── Stress Test Summary ────────────────────────────────────────────────
    stress_test_summary: StressTestSummary

    # ── Optimization Summary ───────────────────────────────────────────────
    optimization_summary: OptimizationSummary

    # ── Policy Summary ─────────────────────────────────────────────────────
    policy_summary: PolicySummary

    # ── System Health ──────────────────────────────────────────────────────
    system_health: SystemHealthSummary

    # ── Audit ──────────────────────────────────────────────────────────────
    audit: SnapshotAudit

    # ── Statistics ────────────────────────────────────────────────────────
    statistics: SnapshotStatisticsSection

    # ── Metadata ──────────────────────────────────────────────────────────
    metadata: SnapshotMetadata

    # ── Optional previous snapshot reference ──────────────────────────────
    previous_snapshot_id: Optional[str] = None

    # ──────────────────────────────────────────────────────────────────────
    # Derived properties (frozen dataclass — all read-only)
    # ──────────────────────────────────────────────────────────────────────

    @property
    def risk_score(self) -> float:
        return self.summary.overall_risk_score

    @property
    def risk_level(self) -> RiskLevel:
        return self.summary.risk_level

    @property
    def risk_rating(self) -> RiskRating:
        return self.summary.risk_rating

    @property
    def is_published(self) -> bool:
        return self.risk_status == SnapshotStatus.PUBLISHED

    @property
    def is_valid(self) -> bool:
        return (
            self.risk_status not in (SnapshotStatus.FAILED, SnapshotStatus.INVALIDATED)
            and self.system_health.snapshot_integrity == IntegrityStatus.VALID.value
        )

    @property
    def has_policy_violations(self) -> bool:
        return self.policy_summary.has_violations

    @property
    def has_escalations(self) -> bool:
        return self.policy_summary.has_escalations

    @property
    def is_high_risk(self) -> bool:
        return self.summary.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    # ──────────────────────────────────────────────────────────────────────
    # Factory
    # ──────────────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        risk_session_id:    str,
        risk_assessment_id: str,
        portfolio_id:       str,
        risk_score:         float,
        assessment_status:  str,
        *,
        snapshot_id:          Optional[str]                       = None,
        workflow_id:          str                                  = "",
        strategy_id:          str                                  = "",
        account_id:           str                                  = "",
        risk_scope:           RiskScope                            = RiskScope.PORTFOLIO,
        risk_type:            RiskType                             = RiskType.COMPOSITE,
        risk_priority:        Optional[RiskPriority]               = None,
        lifecycle_state:      str                                  = "running",
        risk_version:         str                                  = VERSION,
        framework_version:    str                                  = VERSION,
        snapshot_version:     int                                  = 1,
        assessment_timestamp: Optional[float]                      = None,
        summary:              Optional[RiskSnapshotSummary]        = None,
        assessment_summary:   Optional[AssessmentSummarySection]   = None,
        quantitative_metrics: Optional[QuantitativeMetrics]        = None,
        stress_test_summary:  Optional[StressTestSummary]          = None,
        optimization_summary: Optional[OptimizationSummary]        = None,
        policy_summary:       Optional[PolicySummary]              = None,
        system_health:        Optional[SystemHealthSummary]        = None,
        audit:                Optional[SnapshotAudit]              = None,
        statistics:           Optional[SnapshotStatisticsSection]  = None,
        metadata:             Optional[SnapshotMetadata]           = None,
        previous_snapshot_id: Optional[str]                        = None,
    ) -> "RiskSnapshot":
        now = time.time()
        _summary = summary or RiskSnapshotSummary.from_score(risk_score, assessment_status)
        _priority = risk_priority or LEVEL_TO_PRIORITY.get(_summary.risk_level, RiskPriority.MEDIUM)
        return cls(
            snapshot_id          = snapshot_id or str(uuid.uuid4()),
            risk_session_id      = risk_session_id,
            risk_assessment_id   = risk_assessment_id,
            workflow_id          = workflow_id,
            portfolio_id         = portfolio_id,
            strategy_id          = strategy_id,
            account_id           = account_id,
            risk_scope           = risk_scope,
            risk_type            = risk_type,
            risk_priority        = _priority,
            risk_status          = SnapshotStatus.PUBLISHED,
            lifecycle_state      = lifecycle_state,
            risk_version         = risk_version,
            framework_version    = framework_version,
            snapshot_version     = snapshot_version,
            assessment_timestamp = assessment_timestamp or now,
            created_time         = now,
            updated_time         = now,
            summary              = _summary,
            assessment_summary   = assessment_summary
                                   or AssessmentSummarySection.build_uniform(risk_score),
            quantitative_metrics = quantitative_metrics or QuantitativeMetrics(),
            stress_test_summary  = stress_test_summary  or StressTestSummary(),
            optimization_summary = optimization_summary or OptimizationSummary(),
            policy_summary       = policy_summary       or PolicySummary(),
            system_health        = system_health        or SystemHealthSummary(),
            audit                = audit                or SnapshotAudit(),
            statistics           = statistics           or SnapshotStatisticsSection(),
            metadata             = metadata             or SnapshotMetadata(),
            previous_snapshot_id = previous_snapshot_id,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Serialisation
    # ──────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            # Identity
            "snapshot_id":          self.snapshot_id,
            "risk_session_id":      self.risk_session_id,
            "risk_assessment_id":   self.risk_assessment_id,
            "workflow_id":          self.workflow_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "account_id":           self.account_id,
            # Classification
            "risk_scope":           self.risk_scope.value,
            "risk_type":            self.risk_type.value,
            "risk_priority":        self.risk_priority.value,
            "risk_status":          self.risk_status.value,
            "lifecycle_state":      self.lifecycle_state,
            # Versioning
            "risk_version":         self.risk_version,
            "framework_version":    self.framework_version,
            "snapshot_version":     self.snapshot_version,
            # Timestamps
            "assessment_timestamp": self.assessment_timestamp,
            "created_time":         self.created_time,
            "updated_time":         self.updated_time,
            # Sections
            "summary":              self.summary.to_dict(),
            "assessment_summary":   self.assessment_summary.to_dict(),
            "quantitative_metrics": self.quantitative_metrics.to_dict(),
            "stress_test_summary":  self.stress_test_summary.to_dict(),
            "optimization_summary": self.optimization_summary.to_dict(),
            "policy_summary":       self.policy_summary.to_dict(),
            "system_health":        self.system_health.to_dict(),
            "audit":                self.audit.to_dict(),
            "statistics":           self.statistics.to_dict(),
            "metadata":             self.metadata.to_dict(),
            # References
            "previous_snapshot_id": self.previous_snapshot_id,
        }
