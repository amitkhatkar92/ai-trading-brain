"""
risk_snapshot_metadata.py — iios.risk.snapshot
================================================
Metadata value objects for the Risk Snapshot Framework.

Contains:
  DomainRiskSummary    — per-domain risk summary
  QuantitativeMetrics  — consolidated quantitative measures
  StressTestSummary    — stress test consolidated summary
  OptimizationSummary  — optimization consolidated summary
  PolicySummary        — policy evaluation summary
  SystemHealthSummary  — subsystem and pipeline health
  SnapshotAudit        — audit trail and version info
  SnapshotStatistics   — timing and sizing statistics
  SnapshotMetadata     — environment and infrastructure metadata

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    IntegrityStatus,
    RiskLevel,
    VERSION,
)


# ---------------------------------------------------------------------------
# DomainRiskSummary — per-domain assessment summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DomainRiskSummary:
    """Summary of risk assessment for a single domain."""
    domain:           str
    risk_score:       float
    risk_level:       RiskLevel
    risk_contribution: float   # contribution to composite score (0-1)
    is_breached:      bool = False
    details:          Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain":            self.domain,
            "risk_score":        self.risk_score,
            "risk_level":        self.risk_level.value,
            "risk_contribution": self.risk_contribution,
            "is_breached":       self.is_breached,
        }


# ---------------------------------------------------------------------------
# AssessmentSummarySection — 10-domain assessment aggregation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssessmentSummarySection:
    """Consolidated per-domain risk summaries from the assessment framework."""
    market_risk:         DomainRiskSummary
    portfolio_risk:      DomainRiskSummary
    position_risk:       DomainRiskSummary
    credit_risk:         DomainRiskSummary
    liquidity_risk:      DomainRiskSummary
    operational_risk:    DomainRiskSummary
    infrastructure_risk: DomainRiskSummary
    counterparty_risk:   DomainRiskSummary
    concentration:       DomainRiskSummary
    exposure:            DomainRiskSummary

    def all_domains(self) -> Tuple[DomainRiskSummary, ...]:
        return (
            self.market_risk, self.portfolio_risk, self.position_risk,
            self.credit_risk, self.liquidity_risk, self.operational_risk,
            self.infrastructure_risk, self.counterparty_risk,
            self.concentration, self.exposure,
        )

    def breached_domains(self) -> Tuple[DomainRiskSummary, ...]:
        return tuple(d for d in self.all_domains() if d.is_breached)

    def to_dict(self) -> Dict[str, Any]:
        return {d.domain: d.to_dict() for d in self.all_domains()}

    @classmethod
    def build_uniform(cls, risk_score: float) -> "AssessmentSummarySection":
        """Build a uniform section where every domain shares the same score."""
        from .constants import SCORE_TO_LEVEL
        level = RiskLevel.MEDIUM
        for threshold, lvl in SCORE_TO_LEVEL:
            if risk_score <= threshold:
                level = lvl
                break
        contribution = 1.0 / 10.0
        def _d(name: str) -> DomainRiskSummary:
            return DomainRiskSummary(
                domain=name, risk_score=risk_score,
                risk_level=level, risk_contribution=contribution,
            )
        return cls(
            market_risk         = _d("market_risk"),
            portfolio_risk      = _d("portfolio_risk"),
            position_risk       = _d("position_risk"),
            credit_risk         = _d("credit_risk"),
            liquidity_risk      = _d("liquidity_risk"),
            operational_risk    = _d("operational_risk"),
            infrastructure_risk = _d("infrastructure_risk"),
            counterparty_risk   = _d("counterparty_risk"),
            concentration       = _d("concentration"),
            exposure            = _d("exposure"),
        )


# ---------------------------------------------------------------------------
# QuantitativeMetrics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuantitativeMetrics:
    """Consolidated quantitative risk measures from the assessment framework."""
    # Value at Risk
    var_95:             float = 0.0    # Absolute currency amount at 95%
    var_95_pct:         float = 0.0    # % of portfolio value
    var_99:             float = 0.0
    var_99_pct:         float = 0.0

    # Expected Shortfall
    es_95:              float = 0.0
    es_95_pct:          float = 0.0
    es_99:              float = 0.0
    es_99_pct:          float = 0.0

    # Portfolio metrics
    max_drawdown:       float = 0.0
    portfolio_volatility: float = 0.0   # Annualised
    portfolio_beta:     float = 1.0

    # Exposure
    gross_exposure:     float = 0.0
    net_exposure:       float = 0.0
    gross_exposure_pct: float = 0.0

    # Concentration
    hhi:                float = 0.0    # Herfindahl-Hirschman Index
    top_position_pct:   float = 0.0    # Largest single position %

    # Liquidity
    liquidity_ratio:    float = 1.0

    # Capital
    capital_at_risk:    float = 0.0

    # Utilisation
    var_utilization:      float = 0.0   # % of limit consumed
    exposure_utilization: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "var_95":               self.var_95,
            "var_95_pct":           self.var_95_pct,
            "var_99":               self.var_99,
            "var_99_pct":           self.var_99_pct,
            "es_95":                self.es_95,
            "es_95_pct":            self.es_95_pct,
            "es_99":                self.es_99,
            "es_99_pct":            self.es_99_pct,
            "max_drawdown":         self.max_drawdown,
            "portfolio_volatility": self.portfolio_volatility,
            "portfolio_beta":       self.portfolio_beta,
            "gross_exposure":       self.gross_exposure,
            "net_exposure":         self.net_exposure,
            "gross_exposure_pct":   self.gross_exposure_pct,
            "hhi":                  self.hhi,
            "top_position_pct":     self.top_position_pct,
            "liquidity_ratio":      self.liquidity_ratio,
            "capital_at_risk":      self.capital_at_risk,
            "var_utilization":      self.var_utilization,
            "exposure_utilization": self.exposure_utilization,
        }


# ---------------------------------------------------------------------------
# StressTestSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StressTestSummary:
    """Consolidated stress test results from the assessment framework."""
    tests_executed:    int   = 0
    worst_case_loss:   float = 0.0
    worst_case_loss_pct: float = 0.0
    worst_scenario:    str   = ""
    recovery_estimate: float = 0.0   # Days to recover from worst-case loss
    scenario_count:    int   = 0
    results:           Tuple[Dict[str, Any], ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tests_executed":     self.tests_executed,
            "worst_case_loss":    self.worst_case_loss,
            "worst_case_loss_pct": self.worst_case_loss_pct,
            "worst_scenario":     self.worst_scenario,
            "recovery_estimate":  self.recovery_estimate,
            "scenario_count":     self.scenario_count,
        }


# ---------------------------------------------------------------------------
# OptimizationSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationSummary:
    """Consolidated optimization output from the assessment framework."""
    status:                   str   = "not_run"
    objective:                str   = ""
    risk_score_before:        float = 0.0
    risk_score_after:         float = 0.0
    optimization_gain:        float = 0.0
    recommendations_count:    int   = 0
    high_priority_count:      int   = 0
    mitigation_count:         int   = 0
    priority_actions:         Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":                self.status,
            "objective":             self.objective,
            "risk_score_before":     self.risk_score_before,
            "risk_score_after":      self.risk_score_after,
            "optimization_gain":     self.optimization_gain,
            "recommendations_count": self.recommendations_count,
            "high_priority_count":   self.high_priority_count,
            "mitigation_count":      self.mitigation_count,
            "priority_actions":      list(self.priority_actions),
        }


# ---------------------------------------------------------------------------
# PolicySummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PolicySummary:
    """Policy evaluation summary captured in the snapshot."""
    policy_decision:    str   = ""
    policy_outcome:     str   = ""
    violations:         int   = 0
    warnings:           int   = 0
    exceptions_count:   int   = 0
    escalations:        int   = 0
    conditions:         Tuple[str, ...] = ()
    dominant_policy_id: str   = ""
    rationale:          str   = ""

    @property
    def has_violations(self) -> bool:
        return self.violations > 0

    @property
    def has_escalations(self) -> bool:
        return self.escalations > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_decision":    self.policy_decision,
            "policy_outcome":     self.policy_outcome,
            "violations":         self.violations,
            "warnings":           self.warnings,
            "exceptions_count":   self.exceptions_count,
            "escalations":        self.escalations,
            "conditions":         list(self.conditions),
            "dominant_policy_id": self.dominant_policy_id,
            "rationale":          self.rationale,
        }


# ---------------------------------------------------------------------------
# SystemHealthSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SystemHealthSummary:
    """Subsystem and pipeline health state at snapshot time."""
    subsystem_status: Dict[str, str] = field(default_factory=dict)
    validation_status: str           = IntegrityStatus.VALID.value
    snapshot_integrity: str          = IntegrityStatus.VALID.value
    pipeline_health:    str          = "healthy"
    framework_health:   str          = "healthy"

    @property
    def is_healthy(self) -> bool:
        return (
            self.snapshot_integrity == IntegrityStatus.VALID.value
            and self.pipeline_health == "healthy"
            and self.framework_health == "healthy"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem_status":  self.subsystem_status,
            "validation_status": self.validation_status,
            "snapshot_integrity": self.snapshot_integrity,
            "pipeline_health":   self.pipeline_health,
            "framework_health":  self.framework_health,
        }


# ---------------------------------------------------------------------------
# SnapshotAudit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SnapshotAudit:
    """Audit trail and version information for the snapshot."""
    assessment_version: str                   = VERSION
    model_versions:     Dict[str, str]        = field(default_factory=dict)
    policy_versions:    Dict[str, str]        = field(default_factory=dict)
    validation_summary: str                   = ""
    audit_trail:        Tuple[str, ...]       = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_version": self.assessment_version,
            "model_versions":     self.model_versions,
            "policy_versions":    self.policy_versions,
            "validation_summary": self.validation_summary,
            "audit_trail":        list(self.audit_trail),
        }


# ---------------------------------------------------------------------------
# SnapshotStatistics (timing / sizing)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SnapshotStatisticsSection:
    """Timing and sizing metrics for the snapshot."""
    assessment_duration_s:   float = 0.0
    calculation_duration_s:  float = 0.0
    optimization_duration_s: float = 0.0
    snapshot_size_bytes:     int   = 0
    component_count:         int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_duration_s":   self.assessment_duration_s,
            "calculation_duration_s":  self.calculation_duration_s,
            "optimization_duration_s": self.optimization_duration_s,
            "snapshot_size_bytes":     self.snapshot_size_bytes,
            "component_count":         self.component_count,
        }


# ---------------------------------------------------------------------------
# SnapshotMetadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SnapshotMetadata:
    """Environment and infrastructure metadata for the snapshot."""
    environment:       str             = "production"
    framework_version: str             = VERSION
    build_version:     str             = VERSION
    source_components: Tuple[str, ...] = ()
    correlation_ids:   Tuple[str, ...] = ()
    trace_ids:         Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment":       self.environment,
            "framework_version": self.framework_version,
            "build_version":     self.build_version,
            "source_components": list(self.source_components),
            "correlation_ids":   list(self.correlation_ids),
            "trace_ids":         list(self.trace_ids),
        }
