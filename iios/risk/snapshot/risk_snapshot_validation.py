"""
risk_snapshot_validation.py — iios.risk.snapshot
==================================================
Validation logic for Risk Snapshot integrity.

Validates:
  - Identifier consistency (non-empty required IDs)
  - Version consistency
  - Assessment consistency (score range, status)
  - Policy consistency
  - Metric consistency (non-negative quantitative values)
  - Snapshot completeness
  - Metadata integrity
  - Audit completeness
  - System health consistency

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .constants import SnapshotValidationCode
from .exceptions import RiskSnapshotValidationError
from .risk_snapshot import RiskSnapshot


@dataclass
class SnapshotValidationCheck:
    """Result of a single validation check."""
    code:    SnapshotValidationCode
    passed:  bool
    message: str = ""


@dataclass
class SnapshotValidationResult:
    """Aggregated result of all snapshot validation checks."""
    snapshot_id: str
    checks:      List[SnapshotValidationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> List[SnapshotValidationCheck]:
        return [c for c in self.checks if not c.passed]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return len(self.failed_checks)

    def to_summary(self) -> str:
        if self.passed:
            return f"PASS ({self.passed_count}/{len(self.checks)} checks)"
        fails = "; ".join(f"{c.code.value}: {c.message}" for c in self.failed_checks)
        return f"FAIL ({self.failed_count} failures): {fails}"


class RiskSnapshotValidator:
    """
    Stateless validator for :class:`~.risk_snapshot.RiskSnapshot`.

    Usage::

        validator = RiskSnapshotValidator()
        result    = validator.validate(snapshot)
        if not result.passed:
            raise RiskSnapshotValidationError(result.to_summary())
    """

    def validate(self, snapshot: RiskSnapshot) -> SnapshotValidationResult:
        """Run all validation checks and return the aggregated result."""
        result = SnapshotValidationResult(snapshot_id=snapshot.snapshot_id)
        result.checks.extend([
            self._check_identifiers(snapshot),
            self._check_versions(snapshot),
            self._check_assessment(snapshot),
            self._check_policy(snapshot),
            self._check_metrics(snapshot),
            self._check_completeness(snapshot),
            self._check_metadata(snapshot),
            self._check_audit(snapshot),
            self._check_health(snapshot),
        ])
        return result

    def validate_or_raise(self, snapshot: RiskSnapshot) -> SnapshotValidationResult:
        """Run all checks; raise :exc:`RiskSnapshotValidationError` on failure."""
        result = self.validate(snapshot)
        if not result.passed:
            raise RiskSnapshotValidationError(result.to_summary())
        return result

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_identifiers(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.IDENTIFIER_CONSISTENT
        required = {
            "snapshot_id":        s.snapshot_id,
            "risk_session_id":    s.risk_session_id,
            "risk_assessment_id": s.risk_assessment_id,
            "portfolio_id":       s.portfolio_id,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            return SnapshotValidationCheck(
                code=code, passed=False,
                message=f"missing identifiers: {missing}",
            )
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_versions(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.VERSION_CONSISTENT
        if not s.risk_version:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="risk_version is empty")
        if not s.framework_version:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="framework_version is empty")
        if s.snapshot_version < 1:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="snapshot_version must be >= 1")
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_assessment(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.ASSESSMENT_CONSISTENT
        score = s.summary.overall_risk_score
        if not (0.0 <= score <= 100.0):
            return SnapshotValidationCheck(
                code=code, passed=False,
                message=f"risk_score {score} out of [0, 100] range",
            )
        if not s.summary.assessment_status:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="assessment_status is empty")
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_policy(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.POLICY_CONSISTENT
        ps = s.policy_summary
        if ps.violations < 0:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="violations count is negative")
        if ps.escalations < 0:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="escalations count is negative")
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_metrics(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.METRIC_CONSISTENT
        m = s.quantitative_metrics
        if m.var_95 < 0:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="var_95 is negative")
        if m.es_95 < 0:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="es_95 is negative")
        if m.portfolio_volatility < 0:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="portfolio_volatility is negative")
        if not (0.0 <= m.var_utilization <= 100.0):
            return SnapshotValidationCheck(
                code=code, passed=False,
                message=f"var_utilization {m.var_utilization} out of [0, 100]",
            )
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_completeness(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.SNAPSHOT_COMPLETE
        # All required sections must be present (guaranteed by frozen dataclass,
        # but validate non-None explicitly)
        sections = {
            "summary":              s.summary,
            "assessment_summary":   s.assessment_summary,
            "quantitative_metrics": s.quantitative_metrics,
            "stress_test_summary":  s.stress_test_summary,
            "optimization_summary": s.optimization_summary,
            "policy_summary":       s.policy_summary,
            "system_health":        s.system_health,
            "audit":                s.audit,
            "statistics":           s.statistics,
            "metadata":             s.metadata,
        }
        missing = [k for k, v in sections.items() if v is None]
        if missing:
            return SnapshotValidationCheck(
                code=code, passed=False,
                message=f"missing sections: {missing}",
            )
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_metadata(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.METADATA_INTEGRITY
        if not s.metadata.environment:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="metadata.environment is empty")
        if not s.metadata.framework_version:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="metadata.framework_version is empty")
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_audit(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.AUDIT_COMPLETE
        if not s.audit.assessment_version:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="audit.assessment_version is empty")
        return SnapshotValidationCheck(code=code, passed=True)

    def _check_health(self, s: RiskSnapshot) -> SnapshotValidationCheck:
        code = SnapshotValidationCode.HEALTH_CONSISTENT
        if not s.system_health.pipeline_health:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="system_health.pipeline_health is empty")
        if not s.system_health.framework_health:
            return SnapshotValidationCheck(code=code, passed=False,
                                           message="system_health.framework_health is empty")
        return SnapshotValidationCheck(code=code, passed=True)
