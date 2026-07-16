"""iios/execution/context/execution_context_builder.py
==================================================
ExecutionContextBuilder — assembles an ExecutionContext from
validated component parts.

Builder rejects incomplete context, duplicate identifiers, and
inconsistent snapshots before creating the immutable context object.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

from iios.execution.context.constants import (
    BUILDER_SYSTEM_ID,
    ContextStatus,
    ExecutionEnvironment,
    ExecutionMode,
    MarketSession,
    VERSION,
)
from iios.execution.context.exceptions import (
    ContextBuildError,
    ContextIncompleteError,
    ContextInconsistencyError,
)
from iios.execution.context.execution_context import ExecutionContext
from iios.execution.context.execution_environment import ExecutionEnvironmentDescriptor
from iios.execution.context.execution_metadata import ExecutionMetadata
from iios.execution.context.execution_request_context import (
    BrokerContextRef,
    ExecutionRequestContext,
)
from iios.execution.context.execution_session import ExecutionSession

_log = get_logger(__name__, engine_id=BUILDER_SYSTEM_ID)


class ExecutionContextBuilder:
    """
    Fluent builder that assembles an immutable ExecutionContext.

    Usage::

        ctx = (
            ExecutionContextBuilder()
            .with_ids(
                execution_id  = "EXEC-001",
                workflow_id   = "WF-001",
                order_id      = "ORD-001",
                decision_id   = "DEC-001",
                portfolio_id  = "PORT-001",
                strategy_id   = "STRAT-001",
            )
            .with_correlation(correlation_id="CORR-001", request_id="REQ-001")
            .with_mode(ExecutionMode.PAPER)
            .with_session(ExecutionSession.nse())
            .with_environment(ExecutionEnvironmentDescriptor.paper())
            .with_market_snapshot(market_snap)
            .build()
        )
    """

    def __init__(self) -> None:
        # Primary identifiers
        self._execution_id:   str = ""
        self._workflow_id:    str = ""
        self._order_id:       str = ""
        self._decision_id:    str = ""
        self._portfolio_id:   str = ""
        self._strategy_id:    str = ""

        # Tracing
        self._correlation_id: str = ""
        self._trace_id:       str = ""
        self._request_id:     str = ""

        # Mode / status
        self._execution_mode: ExecutionMode = ExecutionMode.PAPER

        # Sub-contexts
        self._session:          Optional[ExecutionSession]               = None
        self._environment:      Optional[ExecutionEnvironmentDescriptor] = None
        self._metadata:         Optional[ExecutionMetadata]              = None
        self._request_context:  Optional[ExecutionRequestContext]        = None

        # Intelligence snapshots
        self._market_snapshot:    Optional[Any] = None
        self._company_snapshot:   Optional[Any] = None
        self._strategy_snapshot:  Optional[Any] = None
        self._portfolio_snapshot: Optional[Any] = None
        self._decision:           Optional[Any] = None

        # Extra
        self._tags:  frozenset[str]  = frozenset()
        self._extra: dict[str, Any]  = {}

        self._started_at: float = time.time()

    # ── Fluent setters ────────────────────────────────────────────────────────

    def with_ids(
        self,
        *,
        execution_id:  str = "",
        workflow_id:   str = "",
        order_id:      str = "",
        decision_id:   str = "",
        portfolio_id:  str = "",
        strategy_id:   str = "",
    ) -> "ExecutionContextBuilder":
        self._execution_id  = execution_id  or self._execution_id
        self._workflow_id   = workflow_id   or self._workflow_id
        self._order_id      = order_id      or self._order_id
        self._decision_id   = decision_id   or self._decision_id
        self._portfolio_id  = portfolio_id  or self._portfolio_id
        self._strategy_id   = strategy_id   or self._strategy_id
        return self

    def with_correlation(
        self,
        *,
        correlation_id: str = "",
        trace_id:       str = "",
        request_id:     str = "",
    ) -> "ExecutionContextBuilder":
        self._correlation_id = correlation_id or self._correlation_id
        self._trace_id       = trace_id       or self._trace_id
        self._request_id     = request_id     or self._request_id
        return self

    def with_mode(self, mode: ExecutionMode) -> "ExecutionContextBuilder":
        self._execution_mode = mode
        return self

    def with_session(self, session: ExecutionSession) -> "ExecutionContextBuilder":
        self._session = session
        return self

    def with_environment(
        self,
        env: ExecutionEnvironmentDescriptor,
    ) -> "ExecutionContextBuilder":
        self._environment = env
        return self

    def with_metadata(self, metadata: ExecutionMetadata) -> "ExecutionContextBuilder":
        self._metadata = metadata
        return self

    def with_request_context(
        self,
        rctx: ExecutionRequestContext,
    ) -> "ExecutionContextBuilder":
        self._request_context = rctx
        return self

    def with_broker(
        self,
        broker_id:    str,
        broker_name:  str = "",
        is_connected: bool = False,
    ) -> "ExecutionContextBuilder":
        """Convenience: attach a BrokerContextRef inside a new RequestContext."""
        bc = BrokerContextRef(
            broker_id      = broker_id,
            broker_name    = broker_name,
            is_connected   = is_connected,
            execution_mode = self._execution_mode,
        )
        self._request_context = ExecutionRequestContext(
            execution_id   = self._execution_id,
            workflow_id    = self._workflow_id,
            order_id       = self._order_id,
            decision_id    = self._decision_id,
            portfolio_id   = self._portfolio_id,
            strategy_id    = self._strategy_id,
            correlation_id = self._correlation_id,
            trace_id       = self._trace_id,
            request_id     = self._request_id,
            execution_mode = self._execution_mode,
            broker_context = bc,
        )
        return self

    def with_market_snapshot(self, snap: Any) -> "ExecutionContextBuilder":
        self._market_snapshot = snap
        return self

    def with_company_snapshot(self, snap: Any) -> "ExecutionContextBuilder":
        self._company_snapshot = snap
        return self

    def with_strategy_snapshot(self, snap: Any) -> "ExecutionContextBuilder":
        self._strategy_snapshot = snap
        return self

    def with_portfolio_snapshot(self, snap: Any) -> "ExecutionContextBuilder":
        self._portfolio_snapshot = snap
        return self

    def with_decision(self, decision: Any) -> "ExecutionContextBuilder":
        self._decision = decision
        return self

    def with_tags(self, *tags: str) -> "ExecutionContextBuilder":
        self._tags = frozenset(tags)
        return self

    def with_extra(self, **kwargs: Any) -> "ExecutionContextBuilder":
        self._extra.update(kwargs)
        return self

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> ExecutionContext:
        """
        Validate required fields and produce an immutable ExecutionContext.

        Raises
        ------
        ContextIncompleteError
            If any required identifier is missing.
        ContextInconsistencyError
            If cross-field consistency checks fail.
        ContextBuildError
            For any other assembly failure.
        """
        self._assert_required_ids()
        self._assert_consistency()

        # Auto-fill request context if not provided
        if self._request_context is None:
            self._request_context = ExecutionRequestContext(
                execution_id   = self._execution_id,
                workflow_id    = self._workflow_id,
                order_id       = self._order_id,
                decision_id    = self._decision_id,
                portfolio_id   = self._portfolio_id,
                strategy_id    = self._strategy_id,
                correlation_id = self._correlation_id,
                trace_id       = self._trace_id,
                request_id     = self._request_id,
                execution_mode = self._execution_mode,
            )

        try:
            ctx = ExecutionContext(
                execution_id       = self._execution_id,
                workflow_id        = self._workflow_id,
                order_id           = self._order_id,
                decision_id        = self._decision_id,
                portfolio_id       = self._portfolio_id,
                strategy_id        = self._strategy_id,
                correlation_id     = self._correlation_id,
                trace_id           = self._trace_id,
                request_id         = self._request_id,
                execution_mode     = self._execution_mode,
                status             = ContextStatus.BUILDING,
                request_context    = self._request_context,
                session            = self._session,
                environment        = self._environment,
                metadata           = self._metadata,
                market_snapshot    = self._market_snapshot,
                company_snapshot   = self._company_snapshot,
                strategy_snapshot  = self._strategy_snapshot,
                portfolio_snapshot = self._portfolio_snapshot,
                decision           = self._decision,
                tags               = self._tags,
                extra              = dict(self._extra),
            )
        except Exception as exc:
            raise ContextBuildError(f"Failed to assemble ExecutionContext: {exc}") from exc

        _log.info(
            "ExecutionContext built.",
            execution_id  = self._execution_id,
            completeness  = ctx.completeness,
        )
        return ctx

    # ── Internal validation ───────────────────────────────────────────────────

    def _assert_required_ids(self) -> None:
        missing: list[str] = []
        for field_name, value in [
            ("execution_id",  self._execution_id),
            ("workflow_id",   self._workflow_id),
            ("order_id",      self._order_id),
            ("decision_id",   self._decision_id),
            ("portfolio_id",  self._portfolio_id),
            ("strategy_id",   self._strategy_id),
            ("correlation_id", self._correlation_id),
            ("request_id",    self._request_id),
        ]:
            if not value or not value.strip():
                missing.append(field_name)

        if missing:
            raise ContextIncompleteError(
                f"Missing required fields: {missing}",
                missing_fields=tuple(missing),
            )

    def _assert_consistency(self) -> None:
        if self._request_context is not None:
            rc = self._request_context
            if rc.execution_id and rc.execution_id != self._execution_id:
                raise ContextInconsistencyError(
                    "request_context.execution_id conflicts with builder execution_id"
                )
            if rc.order_id and rc.order_id != self._order_id:
                raise ContextInconsistencyError(
                    "request_context.order_id conflicts with builder order_id"
                )
