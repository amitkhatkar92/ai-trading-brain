"""
iios/execution/recovery/policies/recovery_context.py
====================================================
PolicyEvaluationContext — the complete input to the policy evaluation engine.

Aggregates all information the policy engine needs to select a recovery
strategy: failure metadata, subsystem health, risk state, and execution state.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import FailureCategory, FailureSeverity, VERSION


@dataclass(frozen=True)
class PolicyEvaluationContext:
    """
    Immutable evaluation context carrying all information needed for
    policy selection.

    Passed to every RecoveryPolicy.evaluate() call.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    context_id:           str
    execution_session_id: str
    subsystem_id:         str
    request_id:           str

    # ── Failure description ───────────────────────────────────────────────────
    failure_category:     FailureCategory
    failure_severity:     FailureSeverity
    failure_reason:       str
    failure_type:         str
    failure_frequency:    int              = 0   # occurrences in current window
    failure_id:           str              = ""

    # ── Retry state ───────────────────────────────────────────────────────────
    retry_count:          int              = 0
    max_retries:          int              = 3
    is_retry_exhausted:   bool             = False

    # ── Rollback / restart state ──────────────────────────────────────────────
    rollback_available:   bool             = False
    restart_count:        int              = 0
    max_restarts:         int              = 3

    # ── Risk state ────────────────────────────────────────────────────────────
    is_within_risk_limits: bool            = True
    risk_level:           str              = "UNKNOWN"   # LOW/MEDIUM/HIGH/CRITICAL
    breach_count:         int              = 0
    risk_exposure:        float            = 0.0

    # ── Subsystem health ──────────────────────────────────────────────────────
    is_subsystem_healthy: bool             = True
    subsystem_availability: float          = 1.0    # 0.0-1.0
    degraded_components:  Tuple[str, ...]  = ()
    error_count:          int              = 0

    # ── Snapshot availability ────────────────────────────────────────────────
    has_monitoring_snapshot: bool          = False
    has_gateway_snapshot:    bool          = False
    has_risk_snapshot:       bool          = False

    # ── Recovery history ─────────────────────────────────────────────────────
    recovery_history_count: int            = 0
    recent_recovery_failed: bool           = False
    last_recovery_strategy: str            = ""

    # ── Execution state ───────────────────────────────────────────────────────
    execution_age_ms:     float            = 0.0
    is_execution_active:  bool             = True

    # ── Metadata ──────────────────────────────────────────────────────────────
    tags:                 Tuple[str, ...]  = ()
    metadata:             Dict[str, Any]   = field(default_factory=dict)
    created_at:           float            = field(default_factory=time.time)
    framework_version:    str              = VERSION

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_risk_critical(self) -> bool:
        return not self.is_within_risk_limits or self.risk_level == "CRITICAL"

    @property
    def is_high_severity(self) -> bool:
        return self.failure_severity in (FailureSeverity.HIGH, FailureSeverity.CRITICAL)

    @property
    def can_retry(self) -> bool:
        return not self.is_retry_exhausted and self.retry_count < self.max_retries

    @property
    def can_restart(self) -> bool:
        return self.restart_count < self.max_restarts

    def get_field(self, field_name: str) -> Any:
        """Return the value of a context field by name (for rule evaluation)."""
        return getattr(self, field_name, None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":             self.context_id,
            "execution_session_id":   self.execution_session_id,
            "subsystem_id":           self.subsystem_id,
            "request_id":             self.request_id,
            "failure_category":       self.failure_category.value,
            "failure_severity":       self.failure_severity.value,
            "failure_reason":         self.failure_reason,
            "failure_type":           self.failure_type,
            "failure_frequency":      self.failure_frequency,
            "retry_count":            self.retry_count,
            "max_retries":            self.max_retries,
            "is_retry_exhausted":     self.is_retry_exhausted,
            "rollback_available":     self.rollback_available,
            "restart_count":          self.restart_count,
            "is_within_risk_limits":  self.is_within_risk_limits,
            "risk_level":             self.risk_level,
            "breach_count":           self.breach_count,
            "is_subsystem_healthy":   self.is_subsystem_healthy,
            "subsystem_availability": self.subsystem_availability,
            "recovery_history_count": self.recovery_history_count,
            "recent_recovery_failed": self.recent_recovery_failed,
            "framework_version":      self.framework_version,
        }


def make_policy_evaluation_context(
    execution_session_id: str,
    subsystem_id: str,
    failure_category: FailureCategory,
    failure_severity: FailureSeverity,
    failure_reason: str,
    *,
    request_id: str = "",
    failure_type: str = "",
    failure_frequency: int = 0,
    failure_id: str = "",
    retry_count: int = 0,
    max_retries: int = 3,
    is_retry_exhausted: bool = False,
    rollback_available: bool = False,
    restart_count: int = 0,
    max_restarts: int = 3,
    is_within_risk_limits: bool = True,
    risk_level: str = "UNKNOWN",
    breach_count: int = 0,
    risk_exposure: float = 0.0,
    is_subsystem_healthy: bool = True,
    subsystem_availability: float = 1.0,
    degraded_components: Tuple[str, ...] = (),
    error_count: int = 0,
    has_monitoring_snapshot: bool = False,
    has_gateway_snapshot: bool = False,
    has_risk_snapshot: bool = False,
    recovery_history_count: int = 0,
    recent_recovery_failed: bool = False,
    last_recovery_strategy: str = "",
    execution_age_ms: float = 0.0,
    is_execution_active: bool = True,
    tags: Tuple[str, ...] = (),
    metadata: Optional[Dict[str, Any]] = None,
    context_id: Optional[str] = None,
) -> PolicyEvaluationContext:
    """Factory for PolicyEvaluationContext."""
    return PolicyEvaluationContext(
        context_id             = context_id or str(uuid.uuid4()),
        execution_session_id   = execution_session_id,
        subsystem_id           = subsystem_id,
        request_id             = request_id,
        failure_category       = failure_category,
        failure_severity       = failure_severity,
        failure_reason         = failure_reason,
        failure_type           = failure_type,
        failure_frequency      = failure_frequency,
        failure_id             = failure_id,
        retry_count            = retry_count,
        max_retries            = max_retries,
        is_retry_exhausted     = is_retry_exhausted,
        rollback_available     = rollback_available,
        restart_count          = restart_count,
        max_restarts           = max_restarts,
        is_within_risk_limits  = is_within_risk_limits,
        risk_level             = risk_level,
        breach_count           = breach_count,
        risk_exposure          = risk_exposure,
        is_subsystem_healthy   = is_subsystem_healthy,
        subsystem_availability = subsystem_availability,
        degraded_components    = degraded_components,
        error_count            = error_count,
        has_monitoring_snapshot = has_monitoring_snapshot,
        has_gateway_snapshot   = has_gateway_snapshot,
        has_risk_snapshot      = has_risk_snapshot,
        recovery_history_count = recovery_history_count,
        recent_recovery_failed = recent_recovery_failed,
        last_recovery_strategy = last_recovery_strategy,
        execution_age_ms       = execution_age_ms,
        is_execution_active    = is_execution_active,
        tags                   = tags,
        metadata               = dict(metadata) if metadata else {},
    )
