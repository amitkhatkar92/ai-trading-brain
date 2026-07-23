"""
risk_snapshot_builder.py — iios.risk.snapshot
===============================================
Builder for constructing RiskSnapshot from component outputs.

The builder provides a fluent API to set each section independently,
then produces a validated, immutable RiskSnapshot.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    ACTOR_SNAPSHOT_BUILDER,
    IntegrityStatus,
    RiskPriority,
    RiskScope,
    RiskTrend,
    RiskType,
    SnapshotStatus,
    VERSION,
)
from .exceptions import RiskSnapshotBuilderError
from .risk_snapshot import RiskSnapshot, RiskSnapshotSummary
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
from .risk_snapshot_validation import RiskSnapshotValidator


class RiskSnapshotBuilder:
    """
    Fluent builder for :class:`~.risk_snapshot.RiskSnapshot`.

    Required fields (must be set before calling :meth:`build`):
      - ``risk_session_id``
      - ``risk_assessment_id``
      - ``portfolio_id``
      - ``risk_score``
      - ``assessment_status``

    All other fields default to safe empty values.

    Usage::

        snapshot = (
            RiskSnapshotBuilder()
            .set_identity("sess-1", "assess-1", "port-1")
            .set_risk_score(42.0, "completed")
            .set_quantitative_metrics(var_95=10_000.0)
            .build()
        )
    """

    def __init__(self) -> None:
        self._reset()

    # ------------------------------------------------------------------
    # State reset
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._snapshot_id:          Optional[str]               = None
        self._risk_session_id:      str                         = ""
        self._risk_assessment_id:   str                         = ""
        self._workflow_id:          str                         = ""
        self._portfolio_id:         str                         = ""
        self._strategy_id:          str                         = ""
        self._account_id:           str                         = ""
        self._risk_scope:           RiskScope                   = RiskScope.PORTFOLIO
        self._risk_type:            RiskType                    = RiskType.COMPOSITE
        self._risk_priority:        Optional[RiskPriority]      = None
        self._lifecycle_state:      str                         = "running"
        self._risk_version:         str                         = VERSION
        self._framework_version:    str                         = VERSION
        self._snapshot_version:     int                         = 1
        self._assessment_timestamp: Optional[float]             = None
        self._risk_score:           float                       = 0.0
        self._assessment_status:    str                         = "completed"
        self._risk_trend:           RiskTrend                   = RiskTrend.UNKNOWN
        self._risk_confidence:      float                       = 1.0
        self._summary:              Optional[RiskSnapshotSummary]       = None
        self._assessment_summary:   Optional[AssessmentSummarySection]  = None
        self._quantitative_metrics: Optional[QuantitativeMetrics]       = None
        self._stress_test_summary:  Optional[StressTestSummary]         = None
        self._optimization_summary: Optional[OptimizationSummary]       = None
        self._policy_summary:       Optional[PolicySummary]             = None
        self._system_health:        Optional[SystemHealthSummary]       = None
        self._audit:                Optional[SnapshotAudit]             = None
        self._statistics:           Optional[SnapshotStatisticsSection] = None
        self._metadata:             Optional[SnapshotMetadata]          = None
        self._previous_snapshot_id: Optional[str]               = None

    # ------------------------------------------------------------------
    # Fluent setters — identity
    # ------------------------------------------------------------------

    def set_identity(
        self,
        risk_session_id:    str,
        risk_assessment_id: str,
        portfolio_id:       str,
        *,
        workflow_id:  str = "",
        strategy_id:  str = "",
        account_id:   str = "",
        snapshot_id:  Optional[str] = None,
    ) -> "RiskSnapshotBuilder":
        self._risk_session_id    = risk_session_id
        self._risk_assessment_id = risk_assessment_id
        self._portfolio_id       = portfolio_id
        self._workflow_id        = workflow_id
        self._strategy_id        = strategy_id
        self._account_id         = account_id
        self._snapshot_id        = snapshot_id
        return self

    def set_classification(
        self,
        *,
        risk_scope:      RiskScope           = RiskScope.PORTFOLIO,
        risk_type:       RiskType            = RiskType.COMPOSITE,
        risk_priority:   Optional[RiskPriority] = None,
        lifecycle_state: str                 = "running",
    ) -> "RiskSnapshotBuilder":
        self._risk_scope      = risk_scope
        self._risk_type       = risk_type
        self._risk_priority   = risk_priority
        self._lifecycle_state = lifecycle_state
        return self

    def set_versioning(
        self,
        *,
        risk_version:      str = VERSION,
        framework_version: str = VERSION,
        snapshot_version:  int = 1,
    ) -> "RiskSnapshotBuilder":
        self._risk_version      = risk_version
        self._framework_version = framework_version
        self._snapshot_version  = snapshot_version
        return self

    def set_assessment_timestamp(self, ts: float) -> "RiskSnapshotBuilder":
        self._assessment_timestamp = ts
        return self

    def set_previous_snapshot_id(self, snapshot_id: str) -> "RiskSnapshotBuilder":
        self._previous_snapshot_id = snapshot_id
        return self

    # ------------------------------------------------------------------
    # Fluent setters — risk summary
    # ------------------------------------------------------------------

    def set_risk_score(
        self,
        risk_score:        float,
        assessment_status: str,
        *,
        trend:      RiskTrend = RiskTrend.UNKNOWN,
        confidence: float     = 1.0,
    ) -> "RiskSnapshotBuilder":
        self._risk_score        = risk_score
        self._assessment_status = assessment_status
        self._risk_trend        = trend
        self._risk_confidence   = confidence
        return self

    def set_summary(self, summary: RiskSnapshotSummary) -> "RiskSnapshotBuilder":
        self._summary = summary
        return self

    # ------------------------------------------------------------------
    # Fluent setters — sections
    # ------------------------------------------------------------------

    def set_assessment_summary(
        self, summary: AssessmentSummarySection
    ) -> "RiskSnapshotBuilder":
        self._assessment_summary = summary
        return self

    def set_quantitative_metrics(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._quantitative_metrics = QuantitativeMetrics(**kwargs)
        return self

    def set_quantitative_metrics_obj(
        self, metrics: QuantitativeMetrics
    ) -> "RiskSnapshotBuilder":
        self._quantitative_metrics = metrics
        return self

    def set_stress_test_summary(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._stress_test_summary = StressTestSummary(**kwargs)
        return self

    def set_stress_test_summary_obj(
        self, summary: StressTestSummary
    ) -> "RiskSnapshotBuilder":
        self._stress_test_summary = summary
        return self

    def set_optimization_summary(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._optimization_summary = OptimizationSummary(**kwargs)
        return self

    def set_optimization_summary_obj(
        self, summary: OptimizationSummary
    ) -> "RiskSnapshotBuilder":
        self._optimization_summary = summary
        return self

    def set_policy_summary(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._policy_summary = PolicySummary(**kwargs)
        return self

    def set_policy_summary_obj(self, summary: PolicySummary) -> "RiskSnapshotBuilder":
        self._policy_summary = summary
        return self

    def set_system_health(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._system_health = SystemHealthSummary(**kwargs)
        return self

    def set_system_health_obj(
        self, health: SystemHealthSummary
    ) -> "RiskSnapshotBuilder":
        self._system_health = health
        return self

    def set_audit(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._audit = SnapshotAudit(**kwargs)
        return self

    def set_audit_obj(self, audit: SnapshotAudit) -> "RiskSnapshotBuilder":
        self._audit = audit
        return self

    def set_statistics(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._statistics = SnapshotStatisticsSection(**kwargs)
        return self

    def set_statistics_obj(
        self, stats: SnapshotStatisticsSection
    ) -> "RiskSnapshotBuilder":
        self._statistics = stats
        return self

    def set_metadata(self, **kwargs: Any) -> "RiskSnapshotBuilder":
        self._metadata = SnapshotMetadata(**kwargs)
        return self

    def set_metadata_obj(self, metadata: SnapshotMetadata) -> "RiskSnapshotBuilder":
        self._metadata = metadata
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, *, validate: bool = True) -> RiskSnapshot:
        """
        Construct and optionally validate the snapshot.

        Parameters
        ----------
        validate :
            When ``True`` (default), run :class:`RiskSnapshotValidator`
            and raise :exc:`~.exceptions.RiskSnapshotBuilderError` on failure.

        Returns
        -------
        RiskSnapshot
        """
        if not self._risk_session_id:
            raise RiskSnapshotBuilderError("risk_session_id is required")
        if not self._risk_assessment_id:
            raise RiskSnapshotBuilderError("risk_assessment_id is required")
        if not self._portfolio_id:
            raise RiskSnapshotBuilderError("portfolio_id is required")

        summary = self._summary or RiskSnapshotSummary.from_score(
            self._risk_score,
            self._assessment_status,
            trend      = self._risk_trend,
            confidence = self._risk_confidence,
        )

        snapshot = RiskSnapshot.create(
            risk_session_id      = self._risk_session_id,
            risk_assessment_id   = self._risk_assessment_id,
            portfolio_id         = self._portfolio_id,
            risk_score           = self._risk_score,
            assessment_status    = self._assessment_status,
            snapshot_id          = self._snapshot_id,
            workflow_id          = self._workflow_id,
            strategy_id          = self._strategy_id,
            account_id           = self._account_id,
            risk_scope           = self._risk_scope,
            risk_type            = self._risk_type,
            risk_priority        = self._risk_priority,
            lifecycle_state      = self._lifecycle_state,
            risk_version         = self._risk_version,
            framework_version    = self._framework_version,
            snapshot_version     = self._snapshot_version,
            assessment_timestamp = self._assessment_timestamp,
            summary              = summary,
            assessment_summary   = self._assessment_summary,
            quantitative_metrics = self._quantitative_metrics,
            stress_test_summary  = self._stress_test_summary,
            optimization_summary = self._optimization_summary,
            policy_summary       = self._policy_summary,
            system_health        = self._system_health,
            audit                = self._audit,
            statistics           = self._statistics,
            metadata             = self._metadata,
            previous_snapshot_id = self._previous_snapshot_id,
        )

        if validate:
            validator = RiskSnapshotValidator()
            result    = validator.validate(snapshot)
            if not result.passed:
                raise RiskSnapshotBuilderError(
                    f"Snapshot validation failed: {result.to_summary()}"
                )

        return snapshot
