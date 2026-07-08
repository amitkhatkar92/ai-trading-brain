"""
iios/intelligence/governance/quality_exceptions.py
===================================================
Exception hierarchy for the Intelligence Quality & Explainability Engine.
Error-code prefix: IQE-
"""
from __future__ import annotations


class IntelligenceQualityError(Exception):
    """Base exception for all IQE errors.  Code: IQE-000"""
    code = "IQE-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Quality errors (IQE-01x) ──────────────────────────────────────────────────

class QualityError(IntelligenceQualityError):
    """Base quality evaluation error.  Code: IQE-010"""
    code = "IQE-010"


class QualityBelowThresholdError(QualityError):
    """Product quality score is below the acceptance threshold.  IQE-011"""
    code = "IQE-011"

    def __init__(self, product_id: str, score: float, threshold: float) -> None:
        super().__init__(
            f"Product {product_id!r} quality {score:.3f} < threshold {threshold:.3f}"
        )


class QualityRecordNotFoundError(QualityError):
    """Quality record not in registry.  IQE-012"""
    code = "IQE-012"

    def __init__(self, record_id: str) -> None:
        super().__init__(f"Quality record not found: {record_id!r}")


class QualityAlreadyExistsError(QualityError):
    """Duplicate quality record.  IQE-013"""
    code = "IQE-013"

    def __init__(self, record_id: str) -> None:
        super().__init__(f"Quality record already exists: {record_id!r}")


# ── Explainability errors (IQE-02x) ───────────────────────────────────────────

class ExplainabilityError(IntelligenceQualityError):
    """Base explainability error.  Code: IQE-020"""
    code = "IQE-020"


class TraceNotFoundError(ExplainabilityError):
    """Requested trace/explanation not found.  IQE-021"""
    code = "IQE-021"

    def __init__(self, trace_id: str) -> None:
        super().__init__(f"Trace not found: {trace_id!r}")


class ExplanationGenerationError(ExplainabilityError):
    """Failed to generate explanation.  IQE-022"""
    code = "IQE-022"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Explanation generation failed: {detail}")


# ── Audit errors (IQE-03x) ────────────────────────────────────────────────────

class AuditError(IntelligenceQualityError):
    """Base audit error.  Code: IQE-030"""
    code = "IQE-030"


class AuditRecordNotFoundError(AuditError):
    """Audit record not found.  IQE-031"""
    code = "IQE-031"

    def __init__(self, audit_id: str) -> None:
        super().__init__(f"Audit record not found: {audit_id!r}")


class AuditWriteError(AuditError):
    """Failed to write audit record.  IQE-032"""
    code = "IQE-032"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Audit write failed: {detail}")


# ── Certification errors (IQE-04x) ────────────────────────────────────────────

class CertificationError(IntelligenceQualityError):
    """Base certification error.  Code: IQE-040"""
    code = "IQE-040"


class CertificationNotFoundError(CertificationError):
    """Certification record not found.  IQE-041"""
    code = "IQE-041"

    def __init__(self, cert_id: str) -> None:
        super().__init__(f"Certification not found: {cert_id!r}")


class CertificationExpiredError(CertificationError):
    """Certification has exceeded its TTL.  IQE-042"""
    code = "IQE-042"

    def __init__(self, cert_id: str) -> None:
        super().__init__(f"Certification {cert_id!r} has expired")


class CertificationRevokedError(CertificationError):
    """Certification has been revoked.  IQE-043"""
    code = "IQE-043"

    def __init__(self, cert_id: str, reason: str) -> None:
        super().__init__(f"Certification {cert_id!r} revoked: {reason}")


class CertificationFailedError(CertificationError):
    """Product failed certification policy checks.  IQE-044"""
    code = "IQE-044"

    def __init__(self, product_id: str, reason: str) -> None:
        super().__init__(
            f"Certification failed for {product_id!r}: {reason}"
        )


class PolicyViolationError(CertificationError):
    """Intelligence product violates a certification policy.  IQE-045"""
    code = "IQE-045"

    def __init__(self, policy_name: str, detail: str) -> None:
        super().__init__(
            f"Policy {policy_name!r} violated: {detail}"
        )


# ── Monitoring errors (IQE-05x) ───────────────────────────────────────────────

class MonitoringError(IntelligenceQualityError):
    """Base monitoring error.  Code: IQE-050"""
    code = "IQE-050"


class DriftAlertError(MonitoringError):
    """Significant model/quality drift detected.  IQE-051"""
    code = "IQE-051"

    def __init__(self, source_id: str, drift_type: str, delta: float) -> None:
        super().__init__(
            f"Drift alert for {source_id!r}: {drift_type} Δ={delta:.3f}"
        )


# ── Evaluation errors (IQE-06x) ───────────────────────────────────────────────

class EvaluationError(IntelligenceQualityError):
    """Base evaluation error.  Code: IQE-060"""
    code = "IQE-060"


class EvaluationMetricError(EvaluationError):
    """A specific evaluation metric failed.  IQE-061"""
    code = "IQE-061"

    def __init__(self, metric: str, detail: str) -> None:
        super().__init__(f"Metric {metric!r} failed: {detail}")


# ── Engine errors (IQE-07x) ───────────────────────────────────────────────────

class GovernanceEngineError(IntelligenceQualityError):
    """Base governance engine error.  Code: IQE-070"""
    code = "IQE-070"


class GovernanceEngineNotInitializedError(GovernanceEngineError):
    """Engine used before initialize().  IQE-071"""
    code = "IQE-071"

    def __init__(self) -> None:
        super().__init__(
            "Governance engine not initialized; call initialize() first"
        )


class GovernanceEngineAlreadyRunningError(GovernanceEngineError):
    """Engine.initialize() called while already running.  IQE-072"""
    code = "IQE-072"

    def __init__(self) -> None:
        super().__init__("Governance engine is already running")
