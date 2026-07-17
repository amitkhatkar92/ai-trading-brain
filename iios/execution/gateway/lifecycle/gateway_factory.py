"""iios/execution/gateway/lifecycle/gateway_factory.py
==================================================
GatewayFactory — creates GatewayRequest instances with validated
identifiers and sensible defaults.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import uuid
from typing import Optional

from .constants import ACTOR_FACTORY, FACTORY_SYSTEM_ID, VERSION
from .exceptions import GatewayValidationError
from .gateway_context import GatewayContext
from .gateway_events import GatewayEvent, make_gateway_created
from .gateway_request import GatewayRequest


class GatewayFactory:
    """
    Stateless factory for ``GatewayRequest`` objects.

    Validates inputs before construction.  Never stores state itself.
    """

    # ── Primary constructor ───────────────────────────────────────────────────

    def create(
        self,
        *,
        gateway_id:     Optional[str]            = None,
        execution_id:   str                      = "",
        workflow_id:    str                      = "",
        order_id:       str                      = "",
        position_id:    str                      = "",
        portfolio_id:   str                      = "",
        strategy_id:    str                      = "",
        decision_id:    str                      = "",
        correlation_id: str                      = "",
        max_history:    int                      = 500,
        context:        Optional[GatewayContext] = None,
    ) -> GatewayRequest:
        """
        Create and return a new ``GatewayRequest`` in the ``CREATED`` state.

        Parameters
        ----------
        gateway_id:
            Optional override; a UUID4 is generated if omitted.
        context:
            Optional ``GatewayContext`` carrying execution input data.

        Raises
        ------
        GatewayValidationError
            If required parameters are missing.
        """
        gid = gateway_id or str(uuid.uuid4())

        return GatewayRequest(
            gateway_id=gid,
            execution_id=execution_id,
            workflow_id=workflow_id,
            order_id=order_id,
            position_id=position_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            decision_id=decision_id,
            correlation_id=correlation_id,
            max_history=max_history,
            context=context,
        )

    # ── Context-aware constructor ─────────────────────────────────────────────

    def create_from_context(
        self,
        ctx: GatewayContext,
        *,
        gateway_id:  Optional[str] = None,
        max_history: int           = 500,
    ) -> GatewayRequest:
        """
        Create a ``GatewayRequest`` from a ``GatewayContext``.

        All identifiers are extracted from *ctx*.
        """
        return self.create(
            gateway_id=gateway_id,
            execution_id=ctx.execution_id,
            workflow_id=ctx.workflow_id,
            order_id=ctx.order_id,
            position_id=ctx.position_id,
            portfolio_id=ctx.portfolio_id,
            strategy_id=ctx.strategy_id,
            decision_id=ctx.decision_id,
            correlation_id=ctx.correlation_id,
            max_history=max_history,
            context=ctx,
        )

    # ── Event emission ────────────────────────────────────────────────────────

    def create_with_event(
        self,
        *,
        gateway_id:     Optional[str]            = None,
        execution_id:   str                      = "",
        workflow_id:    str                      = "",
        order_id:       str                      = "",
        position_id:    str                      = "",
        portfolio_id:   str                      = "",
        strategy_id:    str                      = "",
        decision_id:    str                      = "",
        correlation_id: str                      = "",
        max_history:    int                      = 500,
        context:        Optional[GatewayContext] = None,
    ) -> tuple[GatewayRequest, GatewayEvent]:
        """
        Create a ``GatewayRequest`` and return it together with a
        ``GATEWAY_CREATED`` event.

        Returns
        -------
        (request, event)
        """
        request = self.create(
            gateway_id=gateway_id,
            execution_id=execution_id,
            workflow_id=workflow_id,
            order_id=order_id,
            position_id=position_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            decision_id=decision_id,
            correlation_id=correlation_id,
            max_history=max_history,
            context=context,
        )
        event = make_gateway_created(
            request.gateway_id,
            execution_id=execution_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            actor=ACTOR_FACTORY,
        )
        return request, event
