"""iios/execution/execution_factory.py"""
from __future__ import annotations

from typing import Any

from iios.execution.core.execution_metadata  import ExecutionMetadata
from iios.execution.core.execution_plan      import ExecutionPlan
from iios.execution.core.execution_request   import ExecutionRequest
from iios.execution.core.execution_result    import ExecutionResult
from iios.execution.core.execution_session   import ExecutionSession
from iios.execution.core.execution_state     import ExecutionState
from iios.execution.core.execution_statistics import ExecutionStatistics
from iios.execution.execution_constants      import (
    ExecutionMode,
    ExecutionPriority,
    ExecutionType,
    TimeInForce,
)


class ExecutionFactory:
    """
    Factory for creating well-formed execution domain objects.

    Centralises defaults so callers don't need to know internal structure.
    """

    # ── Requests ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_request(
        ticker: str,
        quantity: float,
        execution_type: ExecutionType = ExecutionType.BUY,
        *,
        execution_mode: ExecutionMode     = ExecutionMode.PAPER,
        priority:       ExecutionPriority = ExecutionPriority.NORMAL,
        target_price:   float | None      = None,
        price_limit:    float | None      = None,
        stop_loss:      float | None      = None,
        take_profit:    float | None      = None,
        time_in_force:  TimeInForce       = TimeInForce.DAY,
        decision_id:    str               = "",
        strategy_id:    str               = "",
        portfolio_id:   str               = "",
        company_id:     str               = "",
        notes:          str               = "",
        constraints:    dict[str, Any]    | None = None,
        metadata:       dict[str, Any]    | None = None,
    ) -> ExecutionRequest:
        return ExecutionRequest(
            ticker=ticker,
            quantity=quantity,
            execution_type=execution_type,
            execution_mode=execution_mode,
            priority=priority,
            target_price=target_price,
            price_limit=price_limit,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            decision_id=decision_id,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
            company_id=company_id,
            notes=notes,
            constraints=constraints or {},
            metadata=metadata or {},
        )

    @staticmethod
    def create_buy_request(
        ticker: str,
        quantity: float,
        target_price: float | None = None,
        **kwargs: Any,
    ) -> ExecutionRequest:
        return ExecutionFactory.create_request(
            ticker=ticker,
            quantity=quantity,
            execution_type=ExecutionType.BUY,
            target_price=target_price,
            **kwargs,
        )

    @staticmethod
    def create_sell_request(
        ticker: str,
        quantity: float,
        target_price: float | None = None,
        **kwargs: Any,
    ) -> ExecutionRequest:
        return ExecutionFactory.create_request(
            ticker=ticker,
            quantity=quantity,
            execution_type=ExecutionType.SELL,
            target_price=target_price,
            **kwargs,
        )

    # ── Sessions ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_session(request: ExecutionRequest) -> ExecutionSession:
        state = ExecutionState()
        session = ExecutionSession(request=request, state=state)
        session.state.execution_id = session.execution_id
        return session

    # ── Plans ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create_plan(
        execution_id: str,
        request: ExecutionRequest,
    ) -> ExecutionPlan:
        price = request.target_price or request.price_limit or 0.0
        return ExecutionPlan(
            execution_id=execution_id,
            request_id=request.request_id,
            estimated_quantity=request.quantity,
            estimated_price=price,
            estimated_value=request.quantity * price,
        )

    # ── Metadata ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_metadata(
        execution_id: str,
        *,
        source: str = "ExecutionEngine",
        mode: ExecutionMode = ExecutionMode.PAPER,
    ) -> ExecutionMetadata:
        return ExecutionMetadata.for_execution(
            execution_id, source=source, mode=mode
        )

    # ── Statistics ────────────────────────────────────────────────────────────

    @staticmethod
    def create_statistics() -> ExecutionStatistics:
        return ExecutionStatistics()
