"""iios/execution/risk/integration/execution_risk_response.py
==================================================
ExecutionRiskResponse — the ONLY output type returned by the integration
layer's evaluate() method.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.execution.risk.snapshot import ExecutionRiskSnapshot


@dataclass(frozen=True)
class ExecutionRiskResponse:
    """
    Immutable result returned by ExecutionRiskIntegrationEngine.evaluate().

    Contains the final approval decision, the M5 ExecutionRiskSnapshot,
    and all identifiers needed to correlate this result with the originating
    request.

    Downstream systems (Execution Gateway, Broker Adapters) MUST check
    ``approved`` before proceeding with order execution.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    response_id:    str
    request_id:     str
    execution_id:   str
    order_id:       str
    portfolio_id:   str
    strategy_id:    str
    correlation_id: str

    # ── Decision ──────────────────────────────────────────────────────────────
    approved:   bool    # True  → execution may proceed
    action:     str     # ControlAction value (e.g. "ALLOW", "BLOCK")
    risk_state: str     # Risk lifecycle state (e.g. "PASSED", "BLOCKED")

    # ── M5 Snapshot ───────────────────────────────────────────────────────────
    snapshot: ExecutionRiskSnapshot

    # ── Validation ────────────────────────────────────────────────────────────
    validation_passed: bool
    error_message:     str = ""

    # ── Timing ───────────────────────────────────────────────────────────────
    elapsed_ms:  float = 0.0
    responded_at: float = field(default_factory=time.time)

    # ── Extended ─────────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_blocked(self) -> bool:
        return not self.approved

    @property
    def is_error(self) -> bool:
        return bool(self.error_message)

    @property
    def is_emergency(self) -> bool:
        return self.action == "EMERGENCY_STOP" or self.snapshot.is_emergency

    @property
    def was_overridden(self) -> bool:
        return self.snapshot.was_overridden

    @property
    def has_warnings(self) -> bool:
        return self.snapshot.warning_count > 0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":      self.response_id,
            "request_id":       self.request_id,
            "execution_id":     self.execution_id,
            "order_id":         self.order_id,
            "portfolio_id":     self.portfolio_id,
            "strategy_id":      self.strategy_id,
            "correlation_id":   self.correlation_id,
            "approved":         self.approved,
            "action":           self.action,
            "risk_state":       self.risk_state,
            "is_blocked":       self.is_blocked,
            "is_emergency":     self.is_emergency,
            "was_overridden":   self.was_overridden,
            "has_warnings":     self.has_warnings,
            "validation_passed": self.validation_passed,
            "error_message":    self.error_message,
            "elapsed_ms":       self.elapsed_ms,
            "responded_at":     self.responded_at,
            "snapshot_id":      self.snapshot.snapshot_id,
            "snapshot":         self.snapshot.to_dict(),
            "metadata":         dict(self.metadata),
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)
