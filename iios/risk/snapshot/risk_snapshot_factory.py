"""
risk_snapshot_factory.py — iios.risk.snapshot
===============================================
Factory for creating RiskSnapshot from Risk Assessment Framework outputs.

Consumes a RiskAssessmentReport (M4) and optional policy summary,
and produces a fully populated RiskSnapshot.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from .constants import (
    ACTOR_SNAPSHOT_FACTORY,
    FACTORY_SYSTEM_ID,
    IntegrityStatus,
    RiskLevel,
    RiskScope,
    RiskTrend,
    RiskType,
    SCORE_TO_LEVEL,
    VERSION,
)
from .exceptions import RiskSnapshotBuilderError
from .risk_snapshot import RiskSnapshot
from .risk_snapshot_builder import RiskSnapshotBuilder
from .risk_snapshot_metadata import (
    AssessmentSummarySection,
    DomainRiskSummary,
    OptimizationSummary,
    PolicySummary,
    QuantitativeMetrics,
    SnapshotAudit,
    SnapshotMetadata,
    SnapshotStatisticsSection,
    StressTestSummary,
    SystemHealthSummary,
)


def _score_to_level(score: float) -> RiskLevel:
    for threshold, level in SCORE_TO_LEVEL:
        if score <= threshold:
            return level
    return RiskLevel.CRITICAL


class RiskSnapshotFactory:
    """
    Factory that assembles a :class:`~.risk_snapshot.RiskSnapshot` from
    Risk Assessment Framework (M4) output objects.

    The factory performs NO calculation.  It reads values that have already
    been computed and packages them into the snapshot structure.
    """

    def __init__(self, *, environment: str = "production") -> None:
        self._environment = environment

    # ------------------------------------------------------------------
    # Primary creation method
    # ------------------------------------------------------------------

    def from_assessment_report(
        self,
        assessment_report:   Any,    # RiskAssessmentReport from M4
        risk_session_id:     str,
        *,
        workflow_id:         str                     = "",
        strategy_id:         str                     = "",
        account_id:          str                     = "",
        risk_scope:          RiskScope                = RiskScope.PORTFOLIO,
        risk_type:           RiskType                 = RiskType.COMPOSITE,
        lifecycle_state:     str                     = "running",
        policy_decision:     str                     = "",
        policy_outcome:      str                     = "",
        violations:          int                     = 0,
        warnings:            int                     = 0,
        exceptions_count:    int                     = 0,
        escalations:         int                     = 0,
        dominant_policy_id:  str                     = "",
        policy_rationale:    str                     = "",
        risk_trend:          RiskTrend               = RiskTrend.UNKNOWN,
        previous_snapshot_id: Optional[str]          = None,
        snapshot_version:    int                     = 1,
    ) -> RiskSnapshot:
        """
        Build a snapshot from a :class:`~iios.risk.assessment.RiskAssessmentReport`.

        Parameters
        ----------
        assessment_report :
            Completed M4 ``RiskAssessmentReport``.
        risk_session_id :
            Risk lifecycle session ID.
        """
        r = assessment_report

        # ── Quantitative Metrics ──────────────────────────────────────
        var_report = getattr(r, "var_report", None)
        es_report  = getattr(r, "es_report", None)
        stress_rep = getattr(r, "stress_test_report", None)
        exp_report = getattr(r, "exposure_report", None)
        summary    = getattr(r, "summary", None)

        var_95     = getattr(var_report, "historical_var",     0.0)
        var_95_pct = getattr(var_report, "historical_var_pct", 0.0)
        var_99     = getattr(var_report, "parametric_var",     0.0)
        var_99_pct = getattr(var_report, "parametric_var_pct", 0.0)
        es_95      = getattr(es_report,  "es_historical",      0.0)
        es_95_pct  = getattr(es_report,  "es_historical_pct",  0.0)
        es_99      = getattr(es_report,  "es_parametric",      0.0)
        es_99_pct  = getattr(es_report,  "es_parametric_pct",  0.0)

        gross_exp     = getattr(exp_report, "gross_exposure",     0.0)
        net_exp       = getattr(exp_report, "net_exposure",       0.0)
        gross_exp_pct = getattr(exp_report, "gross_exposure_pct", 0.0)

        hhi           = getattr(summary, "hhi",     0.0)
        max_drawdown  = getattr(summary, "var_95",  0.0)   # proxy from summary
        risk_score    = float(getattr(r, "risk_score", 0.0))

        qm = QuantitativeMetrics(
            var_95             = var_95,
            var_95_pct         = var_95_pct,
            var_99             = var_99,
            var_99_pct         = var_99_pct,
            es_95              = es_95,
            es_95_pct          = es_95_pct,
            es_99              = es_99,
            es_99_pct          = es_99_pct,
            max_drawdown       = max_drawdown,
            portfolio_volatility = 0.0,
            portfolio_beta     = 1.0,
            gross_exposure     = gross_exp,
            net_exposure       = net_exp,
            gross_exposure_pct = gross_exp_pct,
            hhi                = hhi,
            capital_at_risk    = var_95,
        )

        # ── Stress Test Summary ───────────────────────────────────────
        if stress_rep is not None:
            scenarios_list = [
                s.to_dict() for s in getattr(stress_rep, "scenarios", [])
            ]
            sts = StressTestSummary(
                tests_executed     = len(getattr(stress_rep, "scenarios", ())),
                worst_case_loss    = getattr(stress_rep, "worst_loss",      0.0),
                worst_case_loss_pct= getattr(stress_rep, "worst_loss_pct",  0.0),
                worst_scenario     = getattr(
                    getattr(stress_rep, "worst_scenario", None), "value", ""
                ),
                scenario_count     = len(getattr(stress_rep, "scenarios", ())),
                results            = tuple(scenarios_list),
            )
        else:
            sts = StressTestSummary()

        # ── Optimization Summary ──────────────────────────────────────
        opt_rep = getattr(r, "optimization_report", None)
        mit_rep = getattr(r, "mitigation_plan", None)
        if opt_rep is not None:
            recs = list(getattr(opt_rep, "recommendations", []))
            objs = [o.value for o in getattr(opt_rep, "objectives", [])]
            opts = OptimizationSummary(
                status                = "completed",
                objective             = objs[0] if objs else "",
                risk_score_before     = getattr(opt_rep, "risk_score_before", risk_score),
                risk_score_after      = getattr(opt_rep, "risk_score_after",  risk_score),
                optimization_gain     = getattr(opt_rep, "optimization_gain", 0.0),
                recommendations_count = len(recs),
                high_priority_count   = getattr(mit_rep, "high_priority", 0) if mit_rep else 0,
                mitigation_count      = getattr(mit_rep, "total_actions", 0) if mit_rep else 0,
                priority_actions      = tuple(
                    a.description for a in getattr(mit_rep, "actions", [])
                    if getattr(a, "priority", "") == "high"
                )[:5] if mit_rep else (),
            )
        else:
            opts = OptimizationSummary(
                status            = "not_run",
                mitigation_count  = getattr(mit_rep, "total_actions", 0) if mit_rep else 0,
                high_priority_count = getattr(mit_rep, "high_priority", 0) if mit_rep else 0,
            )

        # ── Policy Summary ────────────────────────────────────────────
        ps = PolicySummary(
            policy_decision    = policy_decision,
            policy_outcome     = policy_outcome,
            violations         = violations,
            warnings           = warnings,
            exceptions_count   = exceptions_count,
            escalations        = escalations,
            dominant_policy_id = dominant_policy_id,
            rationale          = policy_rationale,
        )

        # ── Assessment Summary ────────────────────────────────────────
        assessment_summary = AssessmentSummarySection.build_uniform(risk_score)

        # ── System Health ─────────────────────────────────────────────
        health = SystemHealthSummary(
            validation_status  = IntegrityStatus.VALID.value,
            snapshot_integrity = IntegrityStatus.VALID.value,
            pipeline_health    = "healthy",
            framework_health   = "healthy",
        )

        # ── Audit ─────────────────────────────────────────────────────
        model_ver = getattr(r, "model_version", VERSION)
        audit = SnapshotAudit(
            assessment_version = model_ver,
            validation_summary = f"assessment_id={getattr(r, 'assessment_id', '')}",
        )

        # ── Statistics ────────────────────────────────────────────────
        duration_s = float(getattr(r, "duration_s", 0.0))
        stats = SnapshotStatisticsSection(
            assessment_duration_s  = duration_s,
            calculation_duration_s = duration_s * 0.8,
            component_count        = 10,
        )

        # ── Metadata ─────────────────────────────────────────────────
        meta = SnapshotMetadata(
            environment        = self._environment,
            framework_version  = VERSION,
            source_components  = (FACTORY_SYSTEM_ID,),
            correlation_ids    = (getattr(r, "assessment_id", ""),),
        )

        builder = (
            RiskSnapshotBuilder()
            .set_identity(
                risk_session_id    = risk_session_id,
                risk_assessment_id = getattr(r, "assessment_id", ""),
                portfolio_id       = getattr(r, "portfolio_id", ""),
                workflow_id        = workflow_id,
                strategy_id        = strategy_id,
                account_id         = account_id,
            )
            .set_classification(
                risk_scope      = risk_scope,
                risk_type       = risk_type,
                lifecycle_state = lifecycle_state,
            )
            .set_versioning(snapshot_version=snapshot_version)
            .set_risk_score(
                risk_score,
                getattr(getattr(r, "status", None), "value", "completed"),
                trend = risk_trend,
            )
            .set_assessment_summary(assessment_summary)
            .set_quantitative_metrics_obj(qm)
            .set_stress_test_summary_obj(sts)
            .set_optimization_summary_obj(opts)
            .set_policy_summary_obj(ps)
            .set_system_health_obj(health)
            .set_audit_obj(audit)
            .set_statistics_obj(stats)
            .set_metadata_obj(meta)
        )
        if previous_snapshot_id:
            builder.set_previous_snapshot_id(previous_snapshot_id)
        if r is not None:
            ts = getattr(r, "published_at", None)
            if ts:
                builder.set_assessment_timestamp(float(ts))

        return builder.build(validate=True)

    # ------------------------------------------------------------------
    # Minimal snapshot (for testing / error states)
    # ------------------------------------------------------------------

    def create_minimal(
        self,
        risk_session_id:    str,
        risk_assessment_id: str,
        portfolio_id:       str,
        risk_score:         float,
        assessment_status:  str,
        *,
        snapshot_version: int = 1,
    ) -> RiskSnapshot:
        """Create a minimal valid snapshot with default empty sections."""
        meta = SnapshotMetadata(environment=self._environment)
        return (
            RiskSnapshotBuilder()
            .set_identity(risk_session_id, risk_assessment_id, portfolio_id)
            .set_versioning(snapshot_version=snapshot_version)
            .set_risk_score(risk_score, assessment_status)
            .set_metadata_obj(meta)
            .build(validate=True)
        )
