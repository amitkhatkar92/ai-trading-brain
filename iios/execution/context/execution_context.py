"""iios/execution/context/execution_context.py
==================================================
ExecutionContext — the canonical immutable object exchanged
between all C6 Execution Intelligence modules.

It represents the complete execution environment for a single
execution request: identifiers, snapshots, session, environment,
broker context, metadata, and tracing ids.

It CONTAINS context only. It performs NO execution.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from iios.execution.context.constants import (
    ContextStatus,
    ExecutionEnvironment,
    ExecutionMode,
    VERSION,
)
from iios.execution.context.execution_environment import ExecutionEnvironmentDescriptor
from iios.execution.context.execution_metadata import ExecutionMetadata
from iios.execution.context.execution_request_context import ExecutionRequestContext
from iios.execution.context.execution_session import ExecutionSession

# Type-check-only imports: avoid circular dependencies at runtime.
if TYPE_CHECKING:
    from iios.integration.market_data.core.market_snapshot import MarketSnapshot
    from iios.investment.company.profile.company_snapshot import CompanySnapshot
    from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot
    from iios.investment.portfolio.integration.portfolio_snapshot import (
        PortfolioIntelligenceSnapshot,
    )
    from iios.decisions.models.decision import Decision


@dataclass(frozen=True)
class ExecutionContext:
    """
    Canonical immutable execution context.

    This is the single object passed between all C6 modules.
    It is assembled once by ExecutionContextBuilder, validated once by
    ExecutionContextValidator, and never mutated thereafter.

    All fields are either:
    - Primitive identifiers (str, float, bool)
    - Immutable sub-contexts (ExecutionSession, ExecutionEnvironmentDescriptor …)
    - Optional intelligence snapshots (MarketSnapshot, StrategySnapshot …)

    Thread-safe: dataclass(frozen=True) + all containers immutable.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    context_id:       str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version:   str = VERSION

    # ── Primary identifiers ───────────────────────────────────────────────────
    execution_id:     str = ""
    workflow_id:      str = ""
    order_id:         str = ""
    decision_id:      str = ""
    portfolio_id:     str = ""
    strategy_id:      str = ""

    # ── Tracing ───────────────────────────────────────────────────────────────
    correlation_id:   str = ""
    trace_id:         str = ""
    request_id:       str = ""

    # ── Mode / status ─────────────────────────────────────────────────────────
    execution_mode:   ExecutionMode   = ExecutionMode.PAPER
    status:           ContextStatus   = ContextStatus.BUILDING

    # ── Sub-contexts ──────────────────────────────────────────────────────────
    request_context:  Optional[ExecutionRequestContext]       = None
    session:          Optional[ExecutionSession]              = None
    environment:      Optional[ExecutionEnvironmentDescriptor] = None
    metadata:         Optional[ExecutionMetadata]             = None

    # ── Intelligence snapshots (TYPE_CHECKING only) ───────────────────────────
    market_snapshot:    Optional[Any] = None   # MarketSnapshot
    company_snapshot:   Optional[Any] = None   # CompanySnapshot
    strategy_snapshot:  Optional[Any] = None   # StrategySnapshot
    portfolio_snapshot: Optional[Any] = None   # PortfolioIntelligenceSnapshot
    decision:           Optional[Any] = None   # Decision

    # ── Timing ────────────────────────────────────────────────────────────────
    created_at:   float = field(default_factory=time.time)
    published_at: Optional[float] = None

    # ── Extra ─────────────────────────────────────────────────────────────────
    tags:       frozenset[str]    = field(default_factory=frozenset)
    extra:      dict[str, Any]    = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────────────
    # Computed properties
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def has_market_snapshot(self) -> bool:
        return self.market_snapshot is not None

    @property
    def has_company_snapshot(self) -> bool:
        return self.company_snapshot is not None

    @property
    def has_strategy_snapshot(self) -> bool:
        return self.strategy_snapshot is not None

    @property
    def has_portfolio_snapshot(self) -> bool:
        return self.portfolio_snapshot is not None

    @property
    def has_decision(self) -> bool:
        return self.decision is not None

    @property
    def has_session(self) -> bool:
        return self.session is not None

    @property
    def has_environment(self) -> bool:
        return self.environment is not None

    @property
    def has_broker_context(self) -> bool:
        return (
            self.request_context is not None
            and self.request_context.has_broker
        )

    @property
    def snapshot_count(self) -> int:
        """Number of non-None intelligence snapshots."""
        return sum([
            self.has_market_snapshot,
            self.has_company_snapshot,
            self.has_strategy_snapshot,
            self.has_portfolio_snapshot,
            self.has_decision,
        ])

    @property
    def completeness(self) -> float:
        """
        Fraction of optional intelligence slots that are populated.
        Returns a value in [0.0, 1.0].
        """
        return self.snapshot_count / 5.0

    @property
    def has_all_required_ids(self) -> bool:
        return all([
            self.execution_id,
            self.workflow_id,
            self.order_id,
            self.decision_id,
            self.portfolio_id,
            self.strategy_id,
            self.correlation_id,
            self.request_id,
        ])

    @property
    def age_sec(self) -> float:
        return time.time() - self.created_at

    # ─────────────────────────────────────────────────────────────────────────
    # Serialisation
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":       self.context_id,
            "schema_version":   self.schema_version,
            "execution_id":     self.execution_id,
            "workflow_id":      self.workflow_id,
            "order_id":         self.order_id,
            "decision_id":      self.decision_id,
            "portfolio_id":     self.portfolio_id,
            "strategy_id":      self.strategy_id,
            "correlation_id":   self.correlation_id,
            "trace_id":         self.trace_id,
            "request_id":       self.request_id,
            "execution_mode":   self.execution_mode.value,
            "status":           self.status.value,
            "has_market_snapshot":    self.has_market_snapshot,
            "has_company_snapshot":   self.has_company_snapshot,
            "has_strategy_snapshot":  self.has_strategy_snapshot,
            "has_portfolio_snapshot": self.has_portfolio_snapshot,
            "has_decision":           self.has_decision,
            "snapshot_count":         self.snapshot_count,
            "completeness":           round(self.completeness, 4),
            "has_all_required_ids":   self.has_all_required_ids,
            "created_at":       self.created_at,
            "published_at":     self.published_at,
            "age_sec":          round(self.age_sec, 3),
            "tags":             sorted(self.tags),
            "session":          self.session.to_dict()     if self.session     else None,
            "environment":      self.environment.to_dict() if self.environment else None,
            "metadata":         self.metadata.to_dict()    if self.metadata    else None,
            "request_context":  self.request_context.to_dict() if self.request_context else None,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionContext("
            f"id={self.context_id[:8]}, "
            f"execution={self.execution_id[:8] if self.execution_id else '?'}, "
            f"mode={self.execution_mode.value}, "
            f"completeness={self.completeness:.0%})"
        )
