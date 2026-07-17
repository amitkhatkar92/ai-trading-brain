"""iios/execution/risk/controls/risk_control_context.py
==================================================
ControlContext — immutable context passed through the Controls Framework.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ControlContext:
    """
    Immutable context object passed to the control engine and policies.

    Contains all identifiers, snapshots, and limits needed to enforce
    control actions without coupling to risk evaluation internals.

    The context is read-only.  Policies MUST NOT mutate it.
    """

    context_id:    str
    evaluation_id: str
    execution_id:  str
    order_id:      str
    position_id:   str
    portfolio_id:  str
    strategy_id:   str
    decision_id:   str
    workflow_id:   str
    correlation_id: str
    created_at:    float

    # ── External data snapshots ───────────────────────────────────────────────
    execution_snapshot: Dict[str, Any] = field(default_factory=dict, compare=False)
    position_snapshot:  Dict[str, Any] = field(default_factory=dict, compare=False)
    risk_limits:        Dict[str, Any] = field(default_factory=dict, compare=False)
    session_info:       Dict[str, Any] = field(default_factory=dict, compare=False)
    system_info:        Dict[str, Any] = field(default_factory=dict, compare=False)
    metadata:           Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def age_ms(self) -> float:
        return (time.time() - self.created_at) * 1_000.0

    @property
    def has_execution_snapshot(self) -> bool:
        return bool(self.execution_snapshot)

    @property
    def has_position_snapshot(self) -> bool:
        return bool(self.position_snapshot)

    @property
    def emergency_stop_active(self) -> bool:
        """True if any upstream source signals an emergency stop."""
        return bool(
            self.system_info.get("emergency_stop", False)
            or self.execution_snapshot.get("emergency_stop", False)
        )

    @property
    def session_valid(self) -> bool:
        return bool(self.session_info.get("session_valid", True))

    @property
    def system_healthy(self) -> bool:
        return bool(self.system_info.get("system_healthy", True))

    def get_limit(self, key: str, default: Any = None) -> Any:
        return self.risk_limits.get(key, default)

    def get_exec(self, key: str, default: Any = None) -> Any:
        return self.execution_snapshot.get(key, default)

    def get_pos(self, key: str, default: Any = None) -> Any:
        return self.position_snapshot.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":    self.context_id,
            "evaluation_id": self.evaluation_id,
            "execution_id":  self.execution_id,
            "order_id":      self.order_id,
            "portfolio_id":  self.portfolio_id,
            "strategy_id":   self.strategy_id,
            "correlation_id": self.correlation_id,
            "created_at":    self.created_at,
            "age_ms":        self.age_ms,
            "emergency_stop_active": self.emergency_stop_active,
            "session_valid":  self.session_valid,
            "system_healthy": self.system_healthy,
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_control_context(
    *,
    evaluation_id:      str = "",
    execution_id:       str = "",
    order_id:           str = "",
    position_id:        str = "",
    portfolio_id:       str = "",
    strategy_id:        str = "",
    decision_id:        str = "",
    workflow_id:        str = "",
    correlation_id:     str = "",
    execution_snapshot: Dict[str, Any] | None = None,
    position_snapshot:  Dict[str, Any] | None = None,
    risk_limits:        Dict[str, Any] | None = None,
    session_info:       Dict[str, Any] | None = None,
    system_info:        Dict[str, Any] | None = None,
    metadata:           Dict[str, Any] | None = None,
) -> ControlContext:
    return ControlContext(
        context_id=str(uuid.uuid4()),
        evaluation_id=evaluation_id,
        execution_id=execution_id,
        order_id=order_id,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id=decision_id,
        workflow_id=workflow_id,
        correlation_id=correlation_id,
        created_at=time.time(),
        execution_snapshot=execution_snapshot or {},
        position_snapshot=position_snapshot or {},
        risk_limits=risk_limits or {},
        session_info=session_info or {},
        system_info=system_info or {},
        metadata=metadata or {},
    )


def make_control_context_from_rule_context(rule_ctx: Any) -> ControlContext:
    """
    Bridge factory — build a ControlContext from an M3 RuleContext.

    Avoids importing RuleContext at module level to prevent circular imports.
    """
    return ControlContext(
        context_id=str(uuid.uuid4()),
        evaluation_id=getattr(rule_ctx, "evaluation_id", ""),
        execution_id=getattr(rule_ctx, "execution_id", ""),
        order_id=getattr(rule_ctx, "order_id", ""),
        position_id=getattr(rule_ctx, "position_id", ""),
        portfolio_id=getattr(rule_ctx, "portfolio_id", ""),
        strategy_id=getattr(rule_ctx, "strategy_id", ""),
        decision_id=getattr(rule_ctx, "decision_id", ""),
        workflow_id=getattr(rule_ctx, "workflow_id", ""),
        correlation_id=getattr(rule_ctx, "correlation_id", ""),
        created_at=time.time(),
        execution_snapshot=dict(getattr(rule_ctx, "execution_snapshot", {})),
        position_snapshot=dict(getattr(rule_ctx, "position_snapshot", {})),
        risk_limits=dict(getattr(rule_ctx, "risk_limits", {})),
        session_info=dict(getattr(rule_ctx, "session_info", {})),
        system_info=dict(getattr(rule_ctx, "system_info", {})),
        metadata=dict(getattr(rule_ctx, "metadata", {})),
    )
