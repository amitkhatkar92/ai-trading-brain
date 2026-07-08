"""iios/decision_governance/__init__.py — Decision Governance & Audit Engine"""
from __future__ import annotations

# ── constants ─────────────────────────────────────────────────────────────────
from iios.decision_governance.governance_constants import (
    AlertSeverity,
    ApprovalLevel,
    ApprovalMode,
    ApprovalStatus,
    AuditEventType,
    GovernanceMode,
    GovernanceStatus,
    PolicyType,
    PolicyViolationSeverity,
    GOVERNANCE_ENGINE_VERSION,
    GOVERNANCE_ENGINE_SYSTEM_ID,
)

# ── exceptions ────────────────────────────────────────────────────────────────
from iios.decision_governance.governance_exceptions import (
    GovernanceEngineError,
    GovernanceError,
    GovernanceNotFoundError,
    GovernanceAlreadyExistsError,
    GovernanceFailedError,
    ApprovalError,
    ApprovalNotFoundError,
    ApprovalAlreadyExistsError,
    ApprovalDeniedError,
    ApprovalExpiredError,
    ApprovalEscalatedError,
    ApprovalWorkflowError,
    AuditError,
    AuditNotFoundError,
    AuditAlreadyExistsError,
    AuditReplayError,
    PolicyError,
    PolicyNotFoundError,
    PolicyAlreadyExistsError,
    PolicyViolationError,
    PolicyInvalidError,
    PolicyExecutionError,
    EngineLifecycleError,
    EngineNotInitializedError,
    EngineAlreadyRunningError,
    RegistryError,
    RegistryOverflowError,
    CertificationError,
    CertificationNotFoundError,
    CertificationExpiredError,
    CertificationRevokedError,
    ComplianceError,
    ComplianceViolationError,
)

# ── context ───────────────────────────────────────────────────────────────────
from iios.decision_governance.governance_context import (
    GovernanceSubject,
    GovernanceContextState,
    get_governance_context,
    reset_governance_context,
    governance_session,
    gov_stage_scope,
)

# ── policies ──────────────────────────────────────────────────────────────────
from iios.decision_governance.policies.governance_policy import (
    GovernancePolicy,
    PolicyViolation,
    ScoreThresholdPolicy,
    PredicatePolicy,
    CompositePolicy,
)
from iios.decision_governance.policies.policy_executor import (
    PolicyExecutionResult,
    PolicyExecutor,
)
from iios.decision_governance.policies.policy_validator import PolicyValidator
from iios.decision_governance.policies.policy_loader import PolicyLoader

# ── approval ──────────────────────────────────────────────────────────────────
from iios.decision_governance.approval.approval_result import (
    ApprovalRecord,
    ApprovalResult,
)
from iios.decision_governance.approval.approval_policy import (
    ApprovalPolicy,
    AutoApprovalPolicy,
    ScoreThresholdApprovalPolicy,
    ConditionalApprovalPolicy,
    EscalationApprovalPolicy,
)
from iios.decision_governance.approval.approval_workflow import (
    ApprovalWorkflow,
    WorkflowStep,
)
from iios.decision_governance.approval.approval_engine import ApprovalEngine
from iios.decision_governance.approval.approval_manager import (
    ApprovalManager,
    get_approval_manager,
    reset_approval_manager,
)

# ── audit ─────────────────────────────────────────────────────────────────────
from iios.decision_governance.audit.audit_event import AuditEvent
from iios.decision_governance.audit.audit_history import AuditHistory
from iios.decision_governance.audit.audit_registry import (
    AuditRegistry,
    get_audit_registry,
    reset_audit_registry,
)
from iios.decision_governance.audit.audit_report import AuditReport, build_audit_report
from iios.decision_governance.audit.audit_engine import AuditEngine
from iios.decision_governance.audit.audit_manager import (
    AuditManager,
    get_audit_manager,
    reset_audit_manager,
)

# ── certification ─────────────────────────────────────────────────────────────
from iios.decision_governance.certification.certification_record import CertificationRecord
from iios.decision_governance.certification.certification_engine import CertificationEngine

# ── compliance ────────────────────────────────────────────────────────────────
from iios.decision_governance.compliance.compliance_result import (
    ComplianceResult,
    ComplianceViolation,
)
from iios.decision_governance.compliance.compliance_checker import (
    ComplianceChecker,
    ComplianceRule,
)

# ── monitoring ────────────────────────────────────────────────────────────────
from iios.decision_governance.monitoring.governance_metrics import GovernanceMetrics
from iios.decision_governance.monitoring.governance_alerts import (
    GovernanceAlert,
    GovernanceAlerts,
    AlertHandler,
)
from iios.decision_governance.monitoring.decision_monitor import DecisionMonitor
from iios.decision_governance.monitoring.decision_dashboard import (
    DashboardSnapshot,
    DecisionDashboard,
)

# ── history ───────────────────────────────────────────────────────────────────
from iios.decision_governance.history.governance_history import GovernanceHistory

# ── registry ──────────────────────────────────────────────────────────────────
from iios.decision_governance.governance_registry import (
    GovernanceRegistry,
    get_governance_registry,
    reset_governance_registry,
)

# ── manager ───────────────────────────────────────────────────────────────────
from iios.decision_governance.governance_manager import (
    GovernanceRequest,
    GovernanceResult,
    GovernanceManager,
    get_governance_manager,
    reset_governance_manager,
)

# ── factory ───────────────────────────────────────────────────────────────────
from iios.decision_governance.governance_factory import GovernanceFactory

# ── engine ────────────────────────────────────────────────────────────────────
from iios.decision_governance.decision_governance_engine import (
    DecisionGovernanceEngine,
    get_decision_governance_engine,
    reset_decision_governance_engine,
)

__version__ = GOVERNANCE_ENGINE_VERSION

__all__ = [
    # constants
    "AlertSeverity", "ApprovalLevel", "ApprovalMode", "ApprovalStatus",
    "AuditEventType", "GovernanceMode", "GovernanceStatus",
    "PolicyType", "PolicyViolationSeverity",
    "GOVERNANCE_ENGINE_VERSION", "GOVERNANCE_ENGINE_SYSTEM_ID",
    # exceptions
    "GovernanceEngineError", "GovernanceError", "GovernanceNotFoundError",
    "GovernanceAlreadyExistsError", "GovernanceFailedError",
    "ApprovalError", "ApprovalNotFoundError", "ApprovalAlreadyExistsError",
    "ApprovalDeniedError", "ApprovalExpiredError", "ApprovalEscalatedError",
    "ApprovalWorkflowError",
    "AuditError", "AuditNotFoundError", "AuditAlreadyExistsError", "AuditReplayError",
    "PolicyError", "PolicyNotFoundError", "PolicyAlreadyExistsError",
    "PolicyViolationError", "PolicyInvalidError", "PolicyExecutionError",
    "EngineLifecycleError", "EngineNotInitializedError", "EngineAlreadyRunningError",
    "RegistryError", "RegistryOverflowError",
    "CertificationError", "CertificationNotFoundError",
    "CertificationExpiredError", "CertificationRevokedError",
    "ComplianceError", "ComplianceViolationError",
    # context
    "GovernanceSubject", "GovernanceContextState",
    "get_governance_context", "reset_governance_context",
    "governance_session", "gov_stage_scope",
    # policies
    "GovernancePolicy", "PolicyViolation",
    "ScoreThresholdPolicy", "PredicatePolicy", "CompositePolicy",
    "PolicyExecutionResult", "PolicyExecutor", "PolicyValidator", "PolicyLoader",
    # approval
    "ApprovalRecord", "ApprovalResult",
    "ApprovalPolicy", "AutoApprovalPolicy", "ScoreThresholdApprovalPolicy",
    "ConditionalApprovalPolicy", "EscalationApprovalPolicy",
    "ApprovalWorkflow", "WorkflowStep", "ApprovalEngine",
    "ApprovalManager", "get_approval_manager", "reset_approval_manager",
    # audit
    "AuditEvent", "AuditHistory", "AuditRegistry",
    "get_audit_registry", "reset_audit_registry",
    "AuditReport", "build_audit_report", "AuditEngine",
    "AuditManager", "get_audit_manager", "reset_audit_manager",
    # certification
    "CertificationRecord", "CertificationEngine",
    # compliance
    "ComplianceResult", "ComplianceViolation", "ComplianceChecker", "ComplianceRule",
    # monitoring
    "GovernanceMetrics", "GovernanceAlert", "GovernanceAlerts", "AlertHandler",
    "DecisionMonitor", "DashboardSnapshot", "DecisionDashboard",
    # history
    "GovernanceHistory",
    # registry
    "GovernanceRegistry", "get_governance_registry", "reset_governance_registry",
    # manager
    "GovernanceRequest", "GovernanceResult",
    "GovernanceManager", "get_governance_manager", "reset_governance_manager",
    # factory
    "GovernanceFactory",
    # engine
    "DecisionGovernanceEngine",
    "get_decision_governance_engine", "reset_decision_governance_engine",
]
