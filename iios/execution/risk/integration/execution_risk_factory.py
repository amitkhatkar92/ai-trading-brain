"""iios/execution/risk/integration/execution_risk_factory.py
==================================================
IntegrationRequestFactory — convenience factories for creating
ExecutionRiskRequest and ExecutionContext objects.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from .constants import DEFAULT_TIMEOUT_MS, EvaluationMode
from .execution_risk_context import ExecutionContext, make_execution_context
from .execution_risk_request import ExecutionRiskRequest, make_execution_risk_request


class IntegrationRequestFactory:
    """
    Convenience factories for creating integration input objects.

    All methods are static — no instantiation required.
    """

    # ── Context factories ─────────────────────────────────────────────────────

    @staticmethod
    def create_context(
        execution_id: str,
        order_id:     str,
        **kw,
    ) -> ExecutionContext:
        """Create an ExecutionContext with the given identifiers."""
        return make_execution_context(execution_id, order_id, **kw)

    @staticmethod
    def create_equity_context(
        execution_id: str,
        order_id:     str,
        symbol:       str,
        side:         str,
        quantity:     float,
        price:        float,
        **kw,
    ) -> ExecutionContext:
        """Create an equity order ExecutionContext."""
        return make_execution_context(
            execution_id=execution_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            asset_class="EQUITY",
            order_type=kw.pop("order_type", "LIMIT"),
            **kw,
        )

    @staticmethod
    def create_option_context(
        execution_id: str,
        order_id:     str,
        symbol:       str,
        side:         str,
        quantity:     float,
        price:        float,
        **kw,
    ) -> ExecutionContext:
        """Create an options order ExecutionContext."""
        return make_execution_context(
            execution_id=execution_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            asset_class="OPTION",
            order_type=kw.pop("order_type", "LIMIT"),
            **kw,
        )

    # ── Request factories ─────────────────────────────────────────────────────

    @staticmethod
    def create_request(
        execution_context: ExecutionContext,
        *,
        evaluation_mode: EvaluationMode = EvaluationMode.STANDARD,
        timeout_ms:      float          = DEFAULT_TIMEOUT_MS,
        requested_by:    str            = "",
        correlation_id:  str            = "",
        risk_category:   str            = "EXECUTION",
        metadata:        Dict[str, Any] | None = None,
    ) -> ExecutionRiskRequest:
        """Build a request from an existing ExecutionContext."""
        return make_execution_risk_request(
            execution_context=execution_context,
            evaluation_mode=evaluation_mode,
            timeout_ms=timeout_ms,
            requested_by=requested_by,
            correlation_id=correlation_id,
            risk_category=risk_category,
            metadata=metadata,
        )

    @staticmethod
    def create_minimal_request(
        execution_id: str,
        order_id:     str,
        *,
        portfolio_id: str = "",
        strategy_id:  str = "",
        **kw,
    ) -> ExecutionRiskRequest:
        """
        Create a minimal request from raw identifiers.

        Convenience for cases where a full ExecutionContext is not pre-built.
        """
        ctx = make_execution_context(
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
        )
        return make_execution_risk_request(execution_context=ctx, **kw)

    @staticmethod
    def create_strict_request(
        execution_context: ExecutionContext,
        **kw,
    ) -> ExecutionRiskRequest:
        """Create a STRICT mode request."""
        return IntegrationRequestFactory.create_request(
            execution_context,
            evaluation_mode=EvaluationMode.STRICT,
            **kw,
        )

    @staticmethod
    def create_emergency_request(
        execution_context: ExecutionContext,
        **kw,
    ) -> ExecutionRiskRequest:
        """Create an EMERGENCY mode request."""
        return IntegrationRequestFactory.create_request(
            execution_context,
            evaluation_mode=EvaluationMode.EMERGENCY,
            **kw,
        )
