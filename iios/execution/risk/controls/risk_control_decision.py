"""iios/execution/risk/controls/risk_control_decision.py
==================================================
RiskControlDecision — immutable decision produced by the Controls Framework.

Also defines OverrideInfo and EmergencyInfo supporting types.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    BLOCKING_ACTIONS,
    PASSTHROUGH_ACTIONS,
    TERMINAL_ACTIONS,
    ControlAction,
    PolicyType,
)


# ── Override support ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OverrideInfo:
    """
    Records an authorized override applied to a control decision.

    An override converts a blocking/deferral action into ALLOW or
    ALLOW_WITH_WARNING under explicit human authorization.
    """

    override_id:       str
    approver:          str
    reason:            str
    timestamp:         float
    affected_rule_ids: Tuple[str, ...]
    original_action:   ControlAction
    new_action:        ControlAction
    metadata:          Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "override_id":       self.override_id,
            "approver":          self.approver,
            "reason":            self.reason,
            "timestamp":         self.timestamp,
            "affected_rule_ids": list(self.affected_rule_ids),
            "original_action":   self.original_action.value,
            "new_action":        self.new_action.value,
        }


def make_override_info(
    *,
    approver:          str,
    reason:            str,
    original_action:   ControlAction,
    new_action:        ControlAction,
    affected_rule_ids: List[str] | None = None,
    metadata:          Dict[str, Any] | None = None,
) -> OverrideInfo:
    return OverrideInfo(
        override_id=str(uuid.uuid4()),
        approver=approver,
        reason=reason,
        timestamp=time.time(),
        affected_rule_ids=tuple(affected_rule_ids or []),
        original_action=original_action,
        new_action=new_action,
        metadata=metadata or {},
    )


# ── Emergency support ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EmergencyInfo:
    """
    Records an emergency action triggered during control evaluation.

    Captures the trigger type, halt level, and source rule for audit trail.
    """

    trigger:        str   # e.g. "EMERGENCY_STOP_RULE", "MANUAL_HALT"
    trigger_reason: str
    halt_level:     str   # "SUBSYSTEM" | "TRADING" | "FULL"
    source_rule_id: str
    triggered_at:   float
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger":        self.trigger,
            "trigger_reason": self.trigger_reason,
            "halt_level":     self.halt_level,
            "source_rule_id": self.source_rule_id,
            "triggered_at":   self.triggered_at,
        }


def make_emergency_info(
    *,
    trigger:        str,
    trigger_reason: str,
    halt_level:     str = "TRADING",
    source_rule_id: str = "",
    metadata:       Dict[str, Any] | None = None,
) -> EmergencyInfo:
    return EmergencyInfo(
        trigger=trigger,
        trigger_reason=trigger_reason,
        halt_level=halt_level,
        source_rule_id=source_rule_id,
        triggered_at=time.time(),
        metadata=metadata or {},
    )


# ── Control decision ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RiskControlDecision:
    """
    Immutable decision produced by the RiskControlEngine.

    The decision records which action was selected, which policy made the
    selection, the originating rule results, and optional override/emergency
    supplementary data.
    """

    decision_id:   str
    evaluation_id: str
    execution_id:  str
    order_id:      str
    portfolio_id:  str
    strategy_id:   str
    correlation_id: str

    action:      ControlAction
    policy_used: PolicyType
    reason:      str
    message:     str
    elapsed_ms:  float
    decided_at:  float

    # ── Rule results that drove the decision ──────────────────────────────────
    # Typed as Any to avoid hard import of M3 at module level
    rule_results: Tuple[Any, ...]

    # ── Optional supplementary data ───────────────────────────────────────────
    override_info:  Optional[OverrideInfo] = field(default=None)
    emergency_info: Optional[EmergencyInfo] = field(default=None)
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def allowed(self) -> bool:
        return self.action in PASSTHROUGH_ACTIONS

    @property
    def blocked(self) -> bool:
        return self.action in BLOCKING_ACTIONS

    @property
    def is_terminal(self) -> bool:
        return self.action in TERMINAL_ACTIONS

    @property
    def is_emergency(self) -> bool:
        return self.action == ControlAction.EMERGENCY_STOP

    @property
    def requires_override(self) -> bool:
        return self.action == ControlAction.REQUIRE_OVERRIDE

    @property
    def is_paused(self) -> bool:
        return self.action == ControlAction.PAUSE

    @property
    def was_overridden(self) -> bool:
        return self.override_info is not None

    @property
    def rule_count(self) -> int:
        return len(self.rule_results)

    @property
    def blocked_rules(self) -> List[Any]:
        return [r for r in self.rule_results if getattr(r, "blocked", False)]

    @property
    def warning_rules(self) -> List[Any]:
        return [r for r in self.rule_results if getattr(r, "warned", False)]

    @property
    def passed_rules(self) -> List[Any]:
        return [r for r in self.rule_results if getattr(r, "passed", False)]

    @property
    def failed_rules(self) -> List[Any]:
        return [r for r in self.rule_results if getattr(r, "failed", False)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":    self.decision_id,
            "evaluation_id":  self.evaluation_id,
            "execution_id":   self.execution_id,
            "order_id":       self.order_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "correlation_id": self.correlation_id,
            "action":         self.action.value,
            "policy_used":    self.policy_used.value,
            "reason":         self.reason,
            "message":        self.message,
            "elapsed_ms":     self.elapsed_ms,
            "decided_at":     self.decided_at,
            "rule_count":     self.rule_count,
            "allowed":        self.allowed,
            "blocked":        self.blocked,
            "is_terminal":    self.is_terminal,
            "is_emergency":   self.is_emergency,
            "was_overridden": self.was_overridden,
            "override_info":  self.override_info.to_dict() if self.override_info else None,
            "emergency_info": self.emergency_info.to_dict() if self.emergency_info else None,
            "metadata":       dict(self.metadata),
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def _base_decision(
    *,
    evaluation_id:  str,
    execution_id:   str,
    order_id:       str,
    portfolio_id:   str,
    strategy_id:    str,
    correlation_id: str,
    action:         ControlAction,
    policy_used:    PolicyType,
    reason:         str,
    message:        str,
    elapsed_ms:     float,
    rule_results,
    override_info:  Optional[OverrideInfo] = None,
    emergency_info: Optional[EmergencyInfo] = None,
    metadata:       Dict[str, Any] | None = None,
) -> RiskControlDecision:
    return RiskControlDecision(
        decision_id=str(uuid.uuid4()),
        evaluation_id=evaluation_id,
        execution_id=execution_id,
        order_id=order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        correlation_id=correlation_id,
        action=action,
        policy_used=policy_used,
        reason=reason,
        message=message,
        elapsed_ms=elapsed_ms,
        decided_at=time.time(),
        rule_results=tuple(rule_results),
        override_info=override_info,
        emergency_info=emergency_info,
        metadata=metadata or {},
    )


def make_allow_decision(
    *,
    evaluation_id:  str = "",
    execution_id:   str = "",
    order_id:       str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    correlation_id: str = "",
    policy_used:    PolicyType = PolicyType.HIGHEST_SEVERITY,
    elapsed_ms:     float = 0.0,
    rule_results=(),
    message:        str = "Execution allowed — all risk checks passed.",
    metadata:       Dict[str, Any] | None = None,
) -> RiskControlDecision:
    return _base_decision(
        evaluation_id=evaluation_id, execution_id=execution_id,
        order_id=order_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, correlation_id=correlation_id,
        action=ControlAction.ALLOW, policy_used=policy_used,
        reason="all_rules_passed", message=message,
        elapsed_ms=elapsed_ms, rule_results=rule_results, metadata=metadata,
    )


def make_block_decision(
    *,
    evaluation_id:  str = "",
    execution_id:   str = "",
    order_id:       str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    correlation_id: str = "",
    policy_used:    PolicyType = PolicyType.HIGHEST_SEVERITY,
    elapsed_ms:     float = 0.0,
    rule_results=(),
    reason:         str = "rule_blocked",
    message:        str = "Execution blocked by risk rule.",
    metadata:       Dict[str, Any] | None = None,
) -> RiskControlDecision:
    return _base_decision(
        evaluation_id=evaluation_id, execution_id=execution_id,
        order_id=order_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, correlation_id=correlation_id,
        action=ControlAction.BLOCK, policy_used=policy_used,
        reason=reason, message=message,
        elapsed_ms=elapsed_ms, rule_results=rule_results, metadata=metadata,
    )


def make_emergency_decision(
    *,
    evaluation_id:  str = "",
    execution_id:   str = "",
    order_id:       str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    correlation_id: str = "",
    policy_used:    PolicyType = PolicyType.EMERGENCY,
    elapsed_ms:     float = 0.0,
    rule_results=(),
    reason:         str = "emergency_stop_triggered",
    message:        str = "Emergency stop — all execution halted.",
    emergency_info: Optional[EmergencyInfo] = None,
    metadata:       Dict[str, Any] | None = None,
) -> RiskControlDecision:
    return _base_decision(
        evaluation_id=evaluation_id, execution_id=execution_id,
        order_id=order_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, correlation_id=correlation_id,
        action=ControlAction.EMERGENCY_STOP, policy_used=policy_used,
        reason=reason, message=message, elapsed_ms=elapsed_ms,
        rule_results=rule_results, emergency_info=emergency_info, metadata=metadata,
    )


def make_warning_decision(
    *,
    evaluation_id:  str = "",
    execution_id:   str = "",
    order_id:       str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    correlation_id: str = "",
    policy_used:    PolicyType = PolicyType.HIGHEST_SEVERITY,
    elapsed_ms:     float = 0.0,
    rule_results=(),
    reason:         str = "risk_warning",
    message:        str = "Execution allowed with warnings.",
    metadata:       Dict[str, Any] | None = None,
) -> RiskControlDecision:
    return _base_decision(
        evaluation_id=evaluation_id, execution_id=execution_id,
        order_id=order_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, correlation_id=correlation_id,
        action=ControlAction.ALLOW_WITH_WARNING, policy_used=policy_used,
        reason=reason, message=message,
        elapsed_ms=elapsed_ms, rule_results=rule_results, metadata=metadata,
    )


def make_override_required_decision(
    *,
    evaluation_id:  str = "",
    execution_id:   str = "",
    order_id:       str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    correlation_id: str = "",
    policy_used:    PolicyType = PolicyType.HIGHEST_SEVERITY,
    elapsed_ms:     float = 0.0,
    rule_results=(),
    reason:         str = "override_required",
    message:        str = "Execution requires authorized override.",
    metadata:       Dict[str, Any] | None = None,
) -> RiskControlDecision:
    return _base_decision(
        evaluation_id=evaluation_id, execution_id=execution_id,
        order_id=order_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, correlation_id=correlation_id,
        action=ControlAction.REQUIRE_OVERRIDE, policy_used=policy_used,
        reason=reason, message=message,
        elapsed_ms=elapsed_ms, rule_results=rule_results, metadata=metadata,
    )
