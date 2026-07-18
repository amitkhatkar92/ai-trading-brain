"""
iios/execution/recovery/failover/failover_context.py
====================================================
FailoverContext — all information needed to execute a failover decision.

Bridges the M3 RecoveryPolicyDecision (what to do) and the current
resource/health state (whether it's possible and what resources are available).

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    DEFAULT_EXECUTION_TIMEOUT_MS,
    VERSION,
    FailoverAction,
    FailoverType,
)


@dataclass(frozen=True)
class FailoverContext:
    """
    Immutable execution context for a single failover session.

    Built by FailoverEngine from the M3 RecoveryPolicyDecision plus
    current resource/health state keywords.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    context_id:           str
    failover_session_id:  str
    execution_session_id: str
    subsystem_id:         str

    # ── Failover instruction ──────────────────────────────────────────────────
    failover_type:        FailoverType
    primary_action:       FailoverAction

    # ── Source M3 decision ────────────────────────────────────────────────────
    source_decision_id:       str
    source_policy_name:       str
    recovery_strategy_type:   str    # M3 RecoveryStrategyType.value

    # ── Retry / restart state ─────────────────────────────────────────────────
    is_retry_exhausted:   bool  = False
    retry_count:          int   = 0
    max_retries:          int   = 3
    restart_available:    bool  = True
    restart_count:        int   = 0

    # ── Resource availability ─────────────────────────────────────────────────
    backup_gateway_available: bool  = False
    backup_broker_available:  bool  = False
    rollback_available:       bool  = False

    # ── Health state ──────────────────────────────────────────────────────────
    primary_subsystem_healthy: bool  = True
    monitoring_active:          bool  = True
    execution_active:           bool  = True

    # ── Risk constraints ──────────────────────────────────────────────────────
    is_within_risk_limits:        bool  = True
    emergency_shutdown_requested: bool  = False

    # ── Snapshot availability ─────────────────────────────────────────────────
    has_monitoring_snapshot: bool = False
    has_gateway_snapshot:    bool = False
    has_risk_snapshot:       bool = False

    # ── Timing ────────────────────────────────────────────────────────────────
    max_execution_time_ms: float  = DEFAULT_EXECUTION_TIMEOUT_MS
    created_at:            float  = field(default_factory=time.time)

    # ── Metadata ──────────────────────────────────────────────────────────────
    tags:     Tuple[str, ...]  = ()
    metadata: Dict[str, Any]   = field(default_factory=dict)
    version:  str              = VERSION

    # ── Derived ──────────────────────────────────────────────────────────────

    @property
    def is_emergency(self) -> bool:
        return self.emergency_shutdown_requested or not self.is_within_risk_limits

    @property
    def has_backup_resource(self) -> bool:
        return self.backup_gateway_available or self.backup_broker_available

    @property
    def can_retry(self) -> bool:
        return not self.is_retry_exhausted and self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":            self.context_id,
            "failover_session_id":   self.failover_session_id,
            "execution_session_id":  self.execution_session_id,
            "subsystem_id":          self.subsystem_id,
            "failover_type":         self.failover_type.value,
            "primary_action":        self.primary_action.value,
            "source_decision_id":    self.source_decision_id,
            "recovery_strategy_type": self.recovery_strategy_type,
            "backup_gateway_available": self.backup_gateway_available,
            "backup_broker_available":  self.backup_broker_available,
            "rollback_available":       self.rollback_available,
            "restart_available":        self.restart_available,
            "is_within_risk_limits":    self.is_within_risk_limits,
        }


def make_failover_context(
    failover_session_id: str,
    execution_session_id: str,
    subsystem_id: str,
    failover_type: FailoverType,
    primary_action: FailoverAction,
    source_decision_id: str,
    *,
    source_policy_name: str = "",
    recovery_strategy_type: str = "",
    is_retry_exhausted: bool = False,
    retry_count: int = 0,
    max_retries: int = 3,
    restart_available: bool = True,
    restart_count: int = 0,
    backup_gateway_available: bool = False,
    backup_broker_available: bool = False,
    rollback_available: bool = False,
    primary_subsystem_healthy: bool = True,
    monitoring_active: bool = True,
    execution_active: bool = True,
    is_within_risk_limits: bool = True,
    emergency_shutdown_requested: bool = False,
    has_monitoring_snapshot: bool = False,
    has_gateway_snapshot: bool = False,
    has_risk_snapshot: bool = False,
    max_execution_time_ms: float = DEFAULT_EXECUTION_TIMEOUT_MS,
    tags: Tuple[str, ...] = (),
    metadata: Optional[Dict[str, Any]] = None,
    context_id: Optional[str] = None,
) -> FailoverContext:
    """Factory for FailoverContext."""
    return FailoverContext(
        context_id             = context_id or str(uuid.uuid4()),
        failover_session_id    = failover_session_id,
        execution_session_id   = execution_session_id,
        subsystem_id           = subsystem_id,
        failover_type          = failover_type,
        primary_action         = primary_action,
        source_decision_id     = source_decision_id,
        source_policy_name     = source_policy_name,
        recovery_strategy_type = recovery_strategy_type,
        is_retry_exhausted     = is_retry_exhausted,
        retry_count            = retry_count,
        max_retries            = max_retries,
        restart_available      = restart_available,
        restart_count          = restart_count,
        backup_gateway_available = backup_gateway_available,
        backup_broker_available  = backup_broker_available,
        rollback_available       = rollback_available,
        primary_subsystem_healthy = primary_subsystem_healthy,
        monitoring_active        = monitoring_active,
        execution_active         = execution_active,
        is_within_risk_limits    = is_within_risk_limits,
        emergency_shutdown_requested = emergency_shutdown_requested,
        has_monitoring_snapshot  = has_monitoring_snapshot,
        has_gateway_snapshot     = has_gateway_snapshot,
        has_risk_snapshot        = has_risk_snapshot,
        max_execution_time_ms    = max_execution_time_ms,
        tags                     = tags,
        metadata                 = dict(metadata) if metadata else {},
    )
