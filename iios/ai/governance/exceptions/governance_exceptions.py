"""
governance_exceptions.py -- iios.ai.governance.exceptions
===========================================================
A8 exception hierarchy.  All exceptions extend :class:`AIException` from A1.

Error code range: AI-1300 – AI-1399

Hierarchy
---------
AIException (A1)
└── AIGovernanceException                    AI-1300  base
    ├── AIPolicyException                    AI-1310  base policy
    │   ├── AIPolicyNotFoundError            AI-1311
    │   ├── AIPolicyAlreadyExistsError       AI-1312
    │   ├── AIPolicyViolationError           AI-1313
    │   ├── AIPolicyEvaluationError          AI-1314
    │   └── AIPolicyConflictError            AI-1315
    ├── AIPermissionException                AI-1320  base permission
    │   ├── AIPermissionDeniedError          AI-1321
    │   ├── AIRoleNotFoundError              AI-1322
    │   ├── AIRoleAlreadyExistsError         AI-1323
    │   └── AICapabilityRestrictionError     AI-1324
    ├── AIAuditException                     AI-1330  base audit
    │   ├── AIAuditRecordNotFoundError       AI-1331
    │   └── AIAuditReportError               AI-1332
    ├── AIExplainabilityException            AI-1340  base explainability
    │   ├── AIExplanationNotFoundError       AI-1341
    │   └── AIDecisionTraceError             AI-1342
    ├── AIComplianceException                AI-1350  base compliance
    │   ├── AIComplianceRuleNotFoundError    AI-1351
    │   ├── AIComplianceViolationError       AI-1352
    │   └── AIComplianceReportError          AI-1353
    ├── AIRiskGovernanceException            AI-1360  base risk governance
    │   ├── AIRiskThresholdExceededError     AI-1361
    │   ├── AIRiskPolicyNotFoundError        AI-1362
    │   └── AIEscalationRequiredError        AI-1363
    └── AIGovernancePolicyException          AI-1370  base governance policy
        └── AIGovernancePolicyViolationError AI-1371

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ── Base ──────────────────────────────────────────────────────────────────────

class AIGovernanceException(AIException):
    """Base exception for A8 AI Governance Platform (AI-1300)."""

    def __init__(self, message: str = "Governance error", code: str = "AI-1300") -> None:
        super().__init__(message, code=code)


# ── Policy ────────────────────────────────────────────────────────────────────

class AIPolicyException(AIGovernanceException):
    """Base policy exception (AI-1310)."""

    def __init__(self, message: str = "Policy error", code: str = "AI-1310") -> None:
        super().__init__(message, code=code)


class AIPolicyNotFoundError(AIPolicyException):
    """Raised when a policy is not found (AI-1311)."""

    def __init__(self, message: str = "Policy not found") -> None:
        super().__init__(message, code="AI-1311")


class AIPolicyAlreadyExistsError(AIPolicyException):
    """Raised when a policy already exists (AI-1312)."""

    def __init__(self, message: str = "Policy already exists") -> None:
        super().__init__(message, code="AI-1312")


class AIGovernanceRuleViolationError(AIPolicyException):
    """Raised when a governance policy rule is violated (AI-1313)."""

    def __init__(self, message: str = "Policy violated") -> None:
        super().__init__(message, code="AI-1313")


# Backward-compatible alias (deprecated — use AIGovernanceRuleViolationError)
AIPolicyViolationError = AIGovernanceRuleViolationError


class AIPolicyEvaluationError(AIPolicyException):
    """Raised when policy evaluation fails (AI-1314)."""

    def __init__(self, message: str = "Policy evaluation failed") -> None:
        super().__init__(message, code="AI-1314")


class AIPolicyConflictError(AIPolicyException):
    """Raised when conflicting policies are detected (AI-1315)."""

    def __init__(self, message: str = "Policy conflict detected") -> None:
        super().__init__(message, code="AI-1315")


# ── Permissions ───────────────────────────────────────────────────────────────

class AIPermissionException(AIGovernanceException):
    """Base permission exception (AI-1320)."""

    def __init__(self, message: str = "Permission error", code: str = "AI-1320") -> None:
        super().__init__(message, code=code)


class AIPermissionDeniedError(AIPermissionException):
    """Raised when a permission is denied (AI-1321)."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, code="AI-1321")


class AIRoleNotFoundError(AIPermissionException):
    """Raised when a role is not found (AI-1322)."""

    def __init__(self, message: str = "Role not found") -> None:
        super().__init__(message, code="AI-1322")


class AIRoleAlreadyExistsError(AIPermissionException):
    """Raised when a role already exists (AI-1323)."""

    def __init__(self, message: str = "Role already exists") -> None:
        super().__init__(message, code="AI-1323")


class AICapabilityRestrictionError(AIPermissionException):
    """Raised when a capability restriction is violated (AI-1324)."""

    def __init__(self, message: str = "Capability restricted") -> None:
        super().__init__(message, code="AI-1324")


# ── Audit ─────────────────────────────────────────────────────────────────────

class AIAuditException(AIGovernanceException):
    """Base audit exception (AI-1330)."""

    def __init__(self, message: str = "Audit error", code: str = "AI-1330") -> None:
        super().__init__(message, code=code)


class AIAuditRecordNotFoundError(AIAuditException):
    """Raised when an audit record is not found (AI-1331)."""

    def __init__(self, message: str = "Audit record not found") -> None:
        super().__init__(message, code="AI-1331")


class AIAuditReportError(AIAuditException):
    """Raised when audit report generation fails (AI-1332)."""

    def __init__(self, message: str = "Audit report error") -> None:
        super().__init__(message, code="AI-1332")


# ── Explainability ────────────────────────────────────────────────────────────

class AIExplainabilityException(AIGovernanceException):
    """Base explainability exception (AI-1340)."""

    def __init__(self, message: str = "Explainability error", code: str = "AI-1340") -> None:
        super().__init__(message, code=code)


class AIExplanationNotFoundError(AIExplainabilityException):
    """Raised when an explanation is not found (AI-1341)."""

    def __init__(self, message: str = "Explanation not found") -> None:
        super().__init__(message, code="AI-1341")


class AIDecisionTraceError(AIExplainabilityException):
    """Raised when a decision trace fails (AI-1342)."""

    def __init__(self, message: str = "Decision trace error") -> None:
        super().__init__(message, code="AI-1342")


# ── Compliance ────────────────────────────────────────────────────────────────

class AIComplianceException(AIGovernanceException):
    """Base compliance exception (AI-1350)."""

    def __init__(self, message: str = "Compliance error", code: str = "AI-1350") -> None:
        super().__init__(message, code=code)


class AIComplianceRuleNotFoundError(AIComplianceException):
    """Raised when a compliance rule is not found (AI-1351)."""

    def __init__(self, message: str = "Compliance rule not found") -> None:
        super().__init__(message, code="AI-1351")


class AIComplianceViolationError(AIComplianceException):
    """Raised when a compliance violation is detected (AI-1352)."""

    def __init__(self, message: str = "Compliance violation") -> None:
        super().__init__(message, code="AI-1352")


class AIComplianceReportError(AIComplianceException):
    """Raised when compliance report generation fails (AI-1353)."""

    def __init__(self, message: str = "Compliance report error") -> None:
        super().__init__(message, code="AI-1353")


# ── Risk Governance ───────────────────────────────────────────────────────────

class AIRiskGovernanceException(AIGovernanceException):
    """Base risk governance exception (AI-1360)."""

    def __init__(self, message: str = "Risk governance error", code: str = "AI-1360") -> None:
        super().__init__(message, code=code)


class AIRiskThresholdExceededError(AIRiskGovernanceException):
    """Raised when a risk threshold is exceeded (AI-1361)."""

    def __init__(self, message: str = "Risk threshold exceeded") -> None:
        super().__init__(message, code="AI-1361")


class AIRiskPolicyNotFoundError(AIRiskGovernanceException):
    """Raised when a risk policy is not found (AI-1362)."""

    def __init__(self, message: str = "Risk policy not found") -> None:
        super().__init__(message, code="AI-1362")


class AIEscalationRequiredError(AIRiskGovernanceException):
    """Raised when manual escalation is required (AI-1363)."""

    def __init__(self, message: str = "Manual escalation required") -> None:
        super().__init__(message, code="AI-1363")


# ── Governance Policy ─────────────────────────────────────────────────────────

class AIGovernancePolicyException(AIGovernanceException):
    """Base governance policy exception (AI-1370)."""

    def __init__(self, message: str = "Governance policy error", code: str = "AI-1370") -> None:
        super().__init__(message, code=code)


class AIGovernancePolicyViolationError(AIGovernancePolicyException):
    """Raised when a governance policy is violated (AI-1371)."""

    def __init__(self, message: str = "Governance policy violated") -> None:
        super().__init__(message, code="AI-1371")
