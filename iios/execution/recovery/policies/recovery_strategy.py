"""
iios/execution/recovery/policies/recovery_strategy.py
=====================================================
RecoveryStrategy — describes how a recovery should be executed.

Strategies are selected by policies and returned in RecoveryPolicyDecision.
The Recovery Engine (M2) uses the strategy to orchestrate recovery;
the Failover Framework (M4) uses it when failover is required.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    FailureCategory,
    RecoveryStrategyType,
    RecoveryRecommendation,
)


@dataclass(frozen=True)
class RecoveryStrategy:
    """Immutable description of a recovery strategy."""

    strategy_id:                  str
    strategy_type:                RecoveryStrategyType
    name:                         str
    description:                  str
    recommendation:               RecoveryRecommendation
    max_retries:                  int                    = 3
    timeout_ms:                   int                    = 30_000
    requires_failover:            bool                   = False
    requires_manual_intervention: bool                   = False
    is_disruptive:                bool                   = False
    applicable_categories:        Tuple[FailureCategory, ...] = ()
    priority:                     int                    = 50
    version:                      str                    = VERSION
    metadata:                     Dict[str, Any]         = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":                  self.strategy_id,
            "strategy_type":                self.strategy_type.value,
            "name":                         self.name,
            "description":                  self.description,
            "recommendation":               self.recommendation.value,
            "max_retries":                  self.max_retries,
            "timeout_ms":                   self.timeout_ms,
            "requires_failover":            self.requires_failover,
            "requires_manual_intervention": self.requires_manual_intervention,
            "is_disruptive":                self.is_disruptive,
            "applicable_categories":        [c.value for c in self.applicable_categories],
            "priority":                     self.priority,
            "version":                      self.version,
        }


# ── Strategy factories ────────────────────────────────────────────────────────

def make_retry_strategy(
    max_retries: int = 3,
    timeout_ms: int = 30_000,
) -> RecoveryStrategy:
    return RecoveryStrategy(
        strategy_id  = str(uuid.uuid4()),
        strategy_type = RecoveryStrategyType.RETRY,
        name          = "RetryStrategy",
        description   = "Retry the failed operation up to max_retries times",
        recommendation = RecoveryRecommendation.RETRY,
        max_retries   = max_retries,
        timeout_ms    = timeout_ms,
        applicable_categories = (
            FailureCategory.TIMEOUT,
            FailureCategory.GATEWAY_FAILURE,
            FailureCategory.NETWORK_FAILURE,
        ),
        priority = 60,
    )


def make_resume_strategy() -> RecoveryStrategy:
    return RecoveryStrategy(
        strategy_id  = str(uuid.uuid4()),
        strategy_type = RecoveryStrategyType.RESUME,
        name          = "ResumeStrategy",
        description   = "Resume execution from the last checkpoint",
        recommendation = RecoveryRecommendation.RESUME,
        max_retries   = 1,
        timeout_ms    = 60_000,
        applicable_categories = (FailureCategory.EXECUTION_FAILURE,),
        priority = 55,
    )


def make_rollback_strategy() -> RecoveryStrategy:
    return RecoveryStrategy(
        strategy_id  = str(uuid.uuid4()),
        strategy_type = RecoveryStrategyType.ROLLBACK,
        name          = "RollbackStrategy",
        description   = "Roll back to previous consistent state",
        recommendation = RecoveryRecommendation.ROLLBACK,
        max_retries   = 1,
        timeout_ms    = 120_000,
        is_disruptive = True,
        applicable_categories = (
            FailureCategory.DATA_INTEGRITY_FAILURE,
            FailureCategory.EXECUTION_FAILURE,
        ),
        priority = 70,
    )


def make_restart_strategy(max_retries: int = 2) -> RecoveryStrategy:
    return RecoveryStrategy(
        strategy_id  = str(uuid.uuid4()),
        strategy_type = RecoveryStrategyType.RESTART,
        name          = "RestartStrategy",
        description   = "Restart the failed subsystem component",
        recommendation = RecoveryRecommendation.RESTART,
        max_retries   = max_retries,
        timeout_ms    = 60_000,
        is_disruptive = True,
        applicable_categories = (
            FailureCategory.EXECUTION_FAILURE,
            FailureCategory.INFRASTRUCTURE_FAILURE,
        ),
        priority = 65,
    )


def make_failover_strategy() -> RecoveryStrategy:
    return RecoveryStrategy(
        strategy_id  = str(uuid.uuid4()),
        strategy_type = RecoveryStrategyType.FAILOVER,
        name          = "FailoverStrategy",
        description   = "Fail over to a redundant subsystem or broker",
        recommendation = RecoveryRecommendation.FAILOVER,
        max_retries   = 1,
        timeout_ms    = 30_000,
        requires_failover = True,
        is_disruptive = True,
        applicable_categories = (
            FailureCategory.BROKER_FAILURE,
            FailureCategory.GATEWAY_FAILURE,
            FailureCategory.INFRASTRUCTURE_FAILURE,
        ),
        priority = 80,
    )


def make_manual_intervention_strategy() -> RecoveryStrategy:
    return RecoveryStrategy(
        strategy_id  = str(uuid.uuid4()),
        strategy_type = RecoveryStrategyType.MANUAL_INTERVENTION,
        name          = "ManualInterventionStrategy",
        description   = "Require human operator review and intervention",
        recommendation = RecoveryRecommendation.MANUAL_INTERVENTION,
        max_retries   = 0,
        timeout_ms    = 0,
        requires_manual_intervention = True,
        applicable_categories = tuple(FailureCategory),  # all categories
        priority = 10,   # lowest priority — used as fallback
    )


def make_emergency_shutdown_strategy() -> RecoveryStrategy:
    return RecoveryStrategy(
        strategy_id  = str(uuid.uuid4()),
        strategy_type = RecoveryStrategyType.EMERGENCY_SHUTDOWN,
        name          = "EmergencyShutdownStrategy",
        description   = "Immediately halt execution due to critical risk violation",
        recommendation = RecoveryRecommendation.EMERGENCY_SHUTDOWN,
        max_retries   = 0,
        timeout_ms    = 5_000,
        requires_manual_intervention = True,
        is_disruptive = True,
        applicable_categories = (FailureCategory.RISK_VIOLATION,),
        priority = 100,  # absolute highest
    )


# ── Strategy type → factory map ──────────────────────────────────────────────

STRATEGY_FACTORY_MAP = {
    RecoveryStrategyType.RETRY:               make_retry_strategy,
    RecoveryStrategyType.RESUME:              make_resume_strategy,
    RecoveryStrategyType.ROLLBACK:            make_rollback_strategy,
    RecoveryStrategyType.RESTART:             make_restart_strategy,
    RecoveryStrategyType.FAILOVER:            make_failover_strategy,
    RecoveryStrategyType.MANUAL_INTERVENTION: make_manual_intervention_strategy,
    RecoveryStrategyType.EMERGENCY_SHUTDOWN:  make_emergency_shutdown_strategy,
}


def make_strategy(strategy_type: RecoveryStrategyType) -> RecoveryStrategy:
    """Create the default strategy for the given strategy type."""
    factory = STRATEGY_FACTORY_MAP.get(strategy_type)
    if factory is None:
        return make_manual_intervention_strategy()
    return factory()
