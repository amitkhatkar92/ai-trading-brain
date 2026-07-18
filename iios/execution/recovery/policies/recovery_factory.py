"""
iios/execution/recovery/policies/recovery_factory.py
====================================================
RecoveryPolicyFactory — lifecycle-aware factory for all framework DTOs.

Produces PolicyEvaluationContext, PolicyEvaluationRequest, and
RecoveryPolicyDecision objects with consistent defaults and IDs.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_SYSTEM,
    FACTORY_ID,
    VERSION,
    FailureCategory,
    FailureSeverity,
    PolicyPriority,
    RecoveryRecommendation,
    RecoveryStrategyType,
)
from .recovery_context import PolicyEvaluationContext, make_policy_evaluation_context
from .recovery_request import PolicyEvaluationRequest, make_policy_evaluation_request
from .recovery_response import (
    PolicyEvaluationReport,
    RecoveryPolicyDecision,
    make_policy_decision,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class RecoveryPolicyFactory(LifecycleAwareMixin):
    """
    Lifecycle-aware factory for policy framework DTOs.

    Must be started before use.
    """

    def __init__(self) -> None:
        super().__init__()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(FACTORY_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("RecoveryPolicyFactory started", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(FACTORY_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("RecoveryPolicyFactory stopped")

    # ── Context factory ───────────────────────────────────────────────────────

    def create_evaluation_context(
        self,
        execution_session_id: str,
        subsystem_id: str,
        failure_category: FailureCategory,
        failure_severity: FailureSeverity,
        failure_reason: str,
        *,
        request_id: str = "",
        failure_type: str = "",
        retry_count: int = 0,
        max_retries: int = 3,
        is_retry_exhausted: bool = False,
        rollback_available: bool = False,
        restart_count: int = 0,
        is_within_risk_limits: bool = True,
        risk_level: str = "UNKNOWN",
        breach_count: int = 0,
        is_subsystem_healthy: bool = True,
        subsystem_availability: float = 1.0,
        has_monitoring_snapshot: bool = False,
        has_gateway_snapshot: bool = False,
        has_risk_snapshot: bool = False,
        recovery_history_count: int = 0,
        recent_recovery_failed: bool = False,
        failure_frequency: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        context_id: Optional[str] = None,
    ) -> PolicyEvaluationContext:
        return make_policy_evaluation_context(
            execution_session_id    = execution_session_id,
            subsystem_id            = subsystem_id,
            failure_category        = failure_category,
            failure_severity        = failure_severity,
            failure_reason          = failure_reason,
            request_id              = request_id,
            failure_type            = failure_type,
            retry_count             = retry_count,
            max_retries             = max_retries,
            is_retry_exhausted      = is_retry_exhausted,
            rollback_available      = rollback_available,
            restart_count           = restart_count,
            is_within_risk_limits   = is_within_risk_limits,
            risk_level              = risk_level,
            breach_count            = breach_count,
            is_subsystem_healthy    = is_subsystem_healthy,
            subsystem_availability  = subsystem_availability,
            has_monitoring_snapshot = has_monitoring_snapshot,
            has_gateway_snapshot    = has_gateway_snapshot,
            has_risk_snapshot       = has_risk_snapshot,
            recovery_history_count  = recovery_history_count,
            recent_recovery_failed  = recent_recovery_failed,
            failure_frequency       = failure_frequency,
            metadata                = metadata or {},
            context_id              = context_id,
        )

    # ── Request factory ───────────────────────────────────────────────────────

    def create_evaluation_request(
        self,
        execution_session_id: str,
        subsystem_id: str,
        context: PolicyEvaluationContext,
        failure_category: FailureCategory,
        failure_severity: FailureSeverity,
        *,
        requester: str = ACTOR_SYSTEM,
        evaluation_mode: str = "standard",
        tags: Tuple[str, ...] = (),
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> PolicyEvaluationRequest:
        return make_policy_evaluation_request(
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            context              = context,
            failure_category     = failure_category,
            failure_severity     = failure_severity,
            requester            = requester,
            evaluation_mode      = evaluation_mode,
            tags                 = tags,
            metadata             = metadata,
            request_id           = request_id,
        )

    # ── Decision factory ──────────────────────────────────────────────────────

    def create_decision(
        self,
        request_id: str,
        execution_session_id: str,
        subsystem_id: str,
        is_approved: bool,
        strategy_type: RecoveryStrategyType,
        priority: PolicyPriority,
        recommendation: RecoveryRecommendation,
        failure_category: FailureCategory,
        failure_severity: FailureSeverity,
        confidence_score: float,
        policy_name: str,
        evaluation_report: PolicyEvaluationReport,
        *,
        matched_rules: Tuple[str, ...] = (),
        evaluation_reasons: Tuple[str, ...] = (),
        requires_failover: bool = False,
        requires_manual_intervention: bool = False,
        evaluation_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        decision_id: Optional[str] = None,
    ) -> RecoveryPolicyDecision:
        return make_policy_decision(
            request_id                   = request_id,
            execution_session_id         = execution_session_id,
            subsystem_id                 = subsystem_id,
            is_approved                  = is_approved,
            strategy_type                = strategy_type,
            priority                     = priority,
            recommendation               = recommendation,
            failure_category             = failure_category,
            failure_severity             = failure_severity,
            confidence_score             = confidence_score,
            policy_name                  = policy_name,
            evaluation_report            = evaluation_report,
            matched_rules                = matched_rules,
            evaluation_reasons           = evaluation_reasons,
            requires_failover            = requires_failover,
            requires_manual_intervention = requires_manual_intervention,
            evaluation_time_ms           = evaluation_time_ms,
            metadata                     = metadata,
            decision_id                  = decision_id,
        )
