"""
iios/execution/recovery/failover/failover_plan.py
=================================================
FailoverPlan — describes how to execute a specific failover action.

Plans are immutable blueprints stored in FailoverStrategyRegistry.
Each plan specifies: which phases to run, what the primary + fallback
actions are, and whether verification is required.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    FailoverAction,
    FailoverPhase,
    FailoverType,
)

# Default phase sequences
_FULL_PHASES = (
    FailoverPhase.VALIDATION,
    FailoverPhase.RESOURCE_CHECK,
    FailoverPhase.PREPARATION,
    FailoverPhase.EXECUTION,
    FailoverPhase.VERIFICATION,
    FailoverPhase.RESTORATION,
    FailoverPhase.COMPLETION,
)

_SIMPLE_PHASES = (
    FailoverPhase.VALIDATION,
    FailoverPhase.RESOURCE_CHECK,
    FailoverPhase.EXECUTION,
    FailoverPhase.COMPLETION,
)

_SHUTDOWN_PHASES = (
    FailoverPhase.VALIDATION,
    FailoverPhase.PREPARATION,
    FailoverPhase.EXECUTION,
    FailoverPhase.COMPLETION,
)


@dataclass(frozen=True)
class FailoverPlan:
    """
    Immutable blueprint for executing a failover action.

    Stored in FailoverStrategyRegistry keyed by primary_action.
    """

    plan_id:                str
    name:                   str
    failover_type:          FailoverType
    primary_action:         FailoverAction
    fallback_actions:       Tuple[FailoverAction, ...]
    phases:                 Tuple[FailoverPhase, ...]
    max_execution_time_ms:  int
    requires_verification:  bool
    verification_checks:    Tuple[str, ...]   # check names to run
    applicable_strategy_types: Tuple[str, ...] # M3 strategy values
    priority:               int
    is_disruptive:          bool
    version:                str               = VERSION
    metadata:               Dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":               self.plan_id,
            "name":                  self.name,
            "failover_type":         self.failover_type.value,
            "primary_action":        self.primary_action.value,
            "fallback_actions":      [a.value for a in self.fallback_actions],
            "phases":                [p.value for p in self.phases],
            "max_execution_time_ms": self.max_execution_time_ms,
            "requires_verification": self.requires_verification,
            "priority":              self.priority,
            "is_disruptive":         self.is_disruptive,
        }


# ── Plan factories ────────────────────────────────────────────────────────────

def _plan(
    name: str,
    failover_type: FailoverType,
    primary_action: FailoverAction,
    fallback_actions: Tuple[FailoverAction, ...] = (),
    phases: Tuple[FailoverPhase, ...] = _SIMPLE_PHASES,
    max_ms: int = 30_000,
    requires_verification: bool = True,
    verification_checks: Tuple[str, ...] = ("service_health", "execution_readiness", "monitoring_status"),
    applicable_strategy_types: Tuple[str, ...] = (),
    priority: int = 50,
    is_disruptive: bool = False,
) -> FailoverPlan:
    return FailoverPlan(
        plan_id                  = str(uuid.uuid4()),
        name                     = name,
        failover_type            = failover_type,
        primary_action           = primary_action,
        fallback_actions         = fallback_actions,
        phases                   = phases,
        max_execution_time_ms    = max_ms,
        requires_verification    = requires_verification,
        verification_checks      = verification_checks,
        applicable_strategy_types = applicable_strategy_types,
        priority                 = priority,
        is_disruptive            = is_disruptive,
    )


def make_retry_plan() -> FailoverPlan:
    return _plan(
        "RetryPlan",
        FailoverType.COMPONENT,
        FailoverAction.RETRY,
        fallback_actions  = (FailoverAction.RESTART_COMPONENT,),
        phases            = _SIMPLE_PHASES,
        max_ms            = 5_000,
        requires_verification = False,
        verification_checks   = ("execution_readiness",),
        applicable_strategy_types = ("retry",),
        priority          = 60,
    )


def make_resume_plan() -> FailoverPlan:
    return _plan(
        "ResumePlan",
        FailoverType.WORKFLOW,
        FailoverAction.RESUME,
        fallback_actions  = (FailoverAction.RESTART_WORKFLOW,),
        phases            = _SIMPLE_PHASES,
        max_ms            = 15_000,
        requires_verification = True,
        verification_checks   = ("service_health", "workflow_health", "execution_readiness"),
        applicable_strategy_types = ("resume",),
        priority          = 55,
    )


def make_rollback_plan() -> FailoverPlan:
    return _plan(
        "RollbackPlan",
        FailoverType.WORKFLOW,
        FailoverAction.ROLLBACK,
        fallback_actions  = (FailoverAction.MANUAL_ESCALATION,),
        phases            = _FULL_PHASES,
        max_ms            = 60_000,
        requires_verification = True,
        verification_checks   = ("service_health", "workflow_health", "execution_readiness", "monitoring_status"),
        applicable_strategy_types = ("rollback",),
        priority          = 70,
        is_disruptive     = True,
    )


def make_component_restart_plan() -> FailoverPlan:
    return _plan(
        "ComponentRestartPlan",
        FailoverType.COMPONENT,
        FailoverAction.RESTART_COMPONENT,
        fallback_actions  = (FailoverAction.RESTART_WORKFLOW, FailoverAction.MANUAL_ESCALATION),
        phases            = _FULL_PHASES,
        max_ms            = 30_000,
        requires_verification = True,
        verification_checks   = ("service_health", "execution_readiness", "monitoring_status"),
        applicable_strategy_types = ("restart",),
        priority          = 65,
        is_disruptive     = True,
    )


def make_workflow_restart_plan() -> FailoverPlan:
    return _plan(
        "WorkflowRestartPlan",
        FailoverType.WORKFLOW,
        FailoverAction.RESTART_WORKFLOW,
        fallback_actions  = (FailoverAction.MANUAL_ESCALATION,),
        phases            = _FULL_PHASES,
        max_ms            = 60_000,
        requires_verification = True,
        verification_checks   = ("service_health", "workflow_health", "execution_readiness", "monitoring_status"),
        applicable_strategy_types = ("restart",),
        priority          = 60,
        is_disruptive     = True,
    )


def make_gateway_failover_plan() -> FailoverPlan:
    return _plan(
        "GatewayFailoverPlan",
        FailoverType.GATEWAY,
        FailoverAction.SWITCH_GATEWAY,
        fallback_actions  = (FailoverAction.MANUAL_ESCALATION,),
        phases            = _FULL_PHASES,
        max_ms            = 30_000,
        requires_verification = True,
        verification_checks   = ("gateway_availability", "service_health", "execution_readiness"),
        applicable_strategy_types = ("failover",),
        priority          = 75,
        is_disruptive     = True,
    )


def make_broker_failover_plan() -> FailoverPlan:
    return _plan(
        "BrokerFailoverPlan",
        FailoverType.HOT,
        FailoverAction.SWITCH_BROKER,
        fallback_actions  = (FailoverAction.SWITCH_GATEWAY, FailoverAction.MANUAL_ESCALATION),
        phases            = _FULL_PHASES,
        max_ms            = 30_000,
        requires_verification = True,
        verification_checks   = ("broker_availability", "gateway_availability", "service_health"),
        applicable_strategy_types = ("failover",),
        priority          = 80,
        is_disruptive     = True,
    )


def make_backup_activation_plan() -> FailoverPlan:
    return _plan(
        "BackupActivationPlan",
        FailoverType.WARM,
        FailoverAction.ACTIVATE_BACKUP,
        fallback_actions  = (FailoverAction.MANUAL_ESCALATION,),
        phases            = _FULL_PHASES,
        max_ms            = 45_000,
        requires_verification = True,
        verification_checks   = ("service_health", "execution_readiness", "monitoring_status"),
        applicable_strategy_types = ("failover",),
        priority          = 70,
        is_disruptive     = True,
    )


def make_graceful_shutdown_plan() -> FailoverPlan:
    return _plan(
        "GracefulShutdownPlan",
        FailoverType.SERVICE,
        FailoverAction.GRACEFUL_SHUTDOWN,
        fallback_actions  = (),
        phases            = _SHUTDOWN_PHASES,
        max_ms            = 15_000,
        requires_verification = False,
        verification_checks   = ("monitoring_status",),
        applicable_strategy_types = ("emergency_shutdown",),
        priority          = 100,
        is_disruptive     = True,
    )


def make_manual_escalation_plan() -> FailoverPlan:
    return _plan(
        "ManualEscalationPlan",
        FailoverType.MANUAL,
        FailoverAction.MANUAL_ESCALATION,
        fallback_actions  = (),
        phases            = (FailoverPhase.VALIDATION, FailoverPhase.EXECUTION, FailoverPhase.COMPLETION),
        max_ms            = 5_000,
        requires_verification = False,
        verification_checks   = (),
        applicable_strategy_types = ("manual_intervention",),
        priority          = 10,
    )


def make_deactivate_primary_plan() -> FailoverPlan:
    return _plan(
        "DeactivatePrimaryPlan",
        FailoverType.COMPONENT,
        FailoverAction.DEACTIVATE_PRIMARY,
        fallback_actions  = (),
        phases            = _SIMPLE_PHASES,
        max_ms            = 10_000,
        requires_verification = True,
        verification_checks   = ("service_health",),
        applicable_strategy_types = ("failover",),
        priority          = 75,
        is_disruptive     = True,
    )


# ── Default plan registry (action → factory) ─────────────────────────────────

DEFAULT_PLAN_FACTORIES = {
    FailoverAction.RETRY:              make_retry_plan,
    FailoverAction.RESUME:             make_resume_plan,
    FailoverAction.ROLLBACK:           make_rollback_plan,
    FailoverAction.RESTART_COMPONENT:  make_component_restart_plan,
    FailoverAction.RESTART_WORKFLOW:   make_workflow_restart_plan,
    FailoverAction.SWITCH_GATEWAY:     make_gateway_failover_plan,
    FailoverAction.SWITCH_BROKER:      make_broker_failover_plan,
    FailoverAction.ACTIVATE_BACKUP:    make_backup_activation_plan,
    FailoverAction.GRACEFUL_SHUTDOWN:  make_graceful_shutdown_plan,
    FailoverAction.MANUAL_ESCALATION:  make_manual_escalation_plan,
    FailoverAction.DEACTIVATE_PRIMARY: make_deactivate_primary_plan,
}
