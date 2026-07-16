"""iios/execution/engine/execution_context.py
==================================================
ExecutionContext — the resolved, immutable context assembled during
the PREPARING phase of the Execution Engine.

The context bundles:
  • The original ExecutionRequest
  • The resolved Order (from M1 OrderRegistry)
  • Optional portfolio, decision, and strategy intelligence snapshots
  • Execution metadata

It is passed to all downstream phases (READY → EXECUTING) and
is published inside the ExecutionSnapshot.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from .constants import ExecutionMode

if TYPE_CHECKING:
    from iios.decisions.models.decision import Decision
    from iios.execution.lifecycle.order import Order
    from iios.investment.portfolio.integration.portfolio_snapshot import (
        PortfolioIntelligenceSnapshot,
    )
    from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot

    from .execution_request import ExecutionRequest


@dataclass(frozen=True)
class ExecutionContext:
    """
    Immutable resolved context for one execution run.

    Assembled by ExecutionFactory.create_context() during PREPARING.
    All references are set once and never mutated.

    Attributes
    ----------
    context_id         : Unique identifier for this context instance.
    execution_id       : Parent execution session ID.
    request            : The original ExecutionRequest.
    order              : Resolved Order (None if order_id not found).
    portfolio_snapshot : PortfolioIntelligenceSnapshot (None if not provided).
    decision           : Decision object (None if not provided).
    strategy_snapshot  : StrategySnapshot (None if not provided).
    execution_mode     : Resolved execution mode.
    prepared_at        : Unix timestamp of context creation.
    metadata           : Arbitrary extra data.
    """

    context_id:         str            = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id:       str            = ""
    request:            "Optional[ExecutionRequest]" = None

    # ── Resolved references ────────────────────────────────────────────────────
    order:              "Optional[Order]"                        = None
    portfolio_snapshot: "Optional[PortfolioIntelligenceSnapshot]" = None
    decision:           "Optional[Decision]"                     = None
    strategy_snapshot:  "Optional[StrategySnapshot]"             = None

    # ── Resolved parameters ────────────────────────────────────────────────────
    execution_mode: ExecutionMode = ExecutionMode.PAPER

    # ── Timestamps ────────────────────────────────────────────────────────────
    prepared_at: float          = field(default_factory=time.time)

    # ── Observability ─────────────────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def order_id(self) -> str:
        """Short-circuit to order.order_id (or empty string)."""
        if self.order is not None:
            return self.order.order_id
        if self.request is not None:
            return self.request.order_id
        return ""

    @property
    def portfolio_id(self) -> str:
        """Short-circuit to request.portfolio_id."""
        if self.request is not None:
            return self.request.portfolio_id
        return ""

    @property
    def strategy_id(self) -> str:
        """Short-circuit to request.strategy_id."""
        if self.request is not None:
            return self.request.strategy_id
        return ""

    @property
    def has_order(self) -> bool:
        return self.order is not None

    @property
    def has_portfolio(self) -> bool:
        return self.portfolio_snapshot is not None

    @property
    def has_decision(self) -> bool:
        return self.decision is not None

    @property
    def has_strategy(self) -> bool:
        return self.strategy_snapshot is not None

    @property
    def completeness(self) -> float:
        """Fraction of optional references that are present [0.0 – 1.0]."""
        present = sum([self.has_order, self.has_portfolio,
                       self.has_decision, self.has_strategy])
        return present / 4.0

    def to_dict(self) -> dict[str, Any]:
        order_dict = None
        if self.order is not None:
            try:
                order_dict = self.order.to_dict()
            except Exception:
                order_dict = {"order_id": self.order.order_id}

        return {
            "context_id":          self.context_id,
            "execution_id":        self.execution_id,
            "request_id":          self.request.request_id if self.request else "",
            "order_id":            self.order_id,
            "portfolio_id":        self.portfolio_id,
            "strategy_id":         self.strategy_id,
            "execution_mode":      self.execution_mode.value,
            "has_order":           self.has_order,
            "has_portfolio":       self.has_portfolio,
            "has_decision":        self.has_decision,
            "has_strategy":        self.has_strategy,
            "completeness":        round(self.completeness, 4),
            "prepared_at":         self.prepared_at,
            "order":               order_dict,
            "metadata":            dict(self.metadata),
        }
