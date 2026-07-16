"""iios/execution/engine/execution_factory.py
==================================================
ExecutionFactory — creates ExecutionRequest and ExecutionContext instances.

Responsibilities
----------------
• Build and validate ExecutionRequest objects.
• Resolve Order from an optional OrderRegistry.
• Assemble ExecutionContext with all optional intelligence snapshots.
• Generate execution IDs.

IIOS v1.0 framework: logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_FACTORY, FACTORY_SYSTEM_ID, ExecutionMode, ExecutionPriority,
    VERSION,
)
from .exceptions import ExecutionRequestError, ExecutionValidationError
from .execution_context import ExecutionContext
from .execution_request import ExecutionRequest
from .execution_validation import ExecutionValidator

if TYPE_CHECKING:
    from iios.decisions.models.decision import Decision
    from iios.execution.lifecycle.order import Order
    from iios.execution.lifecycle.order_registry import OrderRegistry
    from iios.investment.portfolio.integration.portfolio_snapshot import (
        PortfolioIntelligenceSnapshot,
    )
    from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot

_log   = get_logger(__name__, engine_id=FACTORY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=FACTORY_SYSTEM_ID,
                          component="ExecutionFactory")


class ExecutionFactory:
    """
    Factory for ExecutionRequest and ExecutionContext objects.

    Thread-safe — stateless, all inputs passed explicitly.

    Usage
    -----
        factory = ExecutionFactory()

        request = factory.create_request(
            order_id     = "ORD-001",
            decision_id  = "DEC-001",
            portfolio_id = "PORT-001",
            strategy_id  = "STRAT-001",
        )

        ctx = factory.create_context(
            request          = request,
            execution_id     = "EXEC-001",
            order_registry   = registry,
            portfolio_snapshot = portfolio_snap,
        )
    """

    SYSTEM_ID = FACTORY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self) -> None:
        self._validator = ExecutionValidator()

    # ── Request factory ───────────────────────────────────────────────────────

    def create_request(
        self,
        *,
        order_id:       str,
        decision_id:    str,
        portfolio_id:   str,
        strategy_id:    str,
        execution_mode: ExecutionMode     = ExecutionMode.PAPER,
        priority:       ExecutionPriority = ExecutionPriority.NORMAL,
        request_id:     str               = "",
        execution_id:   str               = "",
        requested_by:   str               = ACTOR_FACTORY,
        expires_at:     Optional[float]   = None,
        tags:           Optional[frozenset[str]] = None,
        notes:          str               = "",
        metadata:       Optional[dict[str, Any]] = None,
    ) -> ExecutionRequest:
        """
        Create and validate an ExecutionRequest.

        Raises
        ------
        ExecutionValidationError
            If any required identifier is empty or validation fails.
        """
        ctx = ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "create_request",
            stage     = "factory",
        )
        try:
            request = ExecutionRequest(
                request_id     = request_id or self._gen_request_id(),
                execution_id   = execution_id,
                order_id       = order_id,
                decision_id    = decision_id,
                portfolio_id   = portfolio_id,
                strategy_id    = strategy_id,
                execution_mode = execution_mode,
                priority       = priority,
                requested_by   = requested_by,
                expires_at     = expires_at,
                tags           = tags if tags is not None else frozenset(),
                notes          = notes,
                metadata       = dict(metadata) if metadata else {},
            )
            result = self._validator.validate_request(request)
            if not result.passed:
                raise ExecutionValidationError(
                    "ExecutionRequest validation failed: " + "; ".join(result.errors),
                    code   = "EX-002",
                    errors = result.errors,
                )
            _log.info(
                "ExecutionRequest created.",
                request_id   = request.request_id,
                order_id     = order_id,
                execution_mode = execution_mode.value,
            )
            _audit.log_workflow_event(
                workflow_id = self.SYSTEM_ID,
                stage       = "create_request",
                event       = "request_created",
                request_id  = request.request_id,
            )
            return request
        except ExecutionValidationError:
            raise
        except Exception as exc:
            _get_err_mgr().report_failure(self.SYSTEM_ID, exc, ctx)
            _log.exception("Unexpected error in ExecutionFactory.create_request.", exc=exc)
            raise

    # ── Context factory ───────────────────────────────────────────────────────

    def create_context(
        self,
        *,
        request:            ExecutionRequest,
        execution_id:       str,
        order_registry:     "Optional[OrderRegistry]"              = None,
        portfolio_snapshot: "Optional[PortfolioIntelligenceSnapshot]" = None,
        decision:           "Optional[Decision]"                   = None,
        strategy_snapshot:  "Optional[StrategySnapshot]"           = None,
        metadata:           Optional[dict[str, Any]]               = None,
    ) -> ExecutionContext:
        """
        Assemble an ExecutionContext.

        Resolves the Order from *order_registry* if provided, then
        packages all intelligence snapshots into an immutable context.

        Raises
        ------
        ExecutionRequestError
            If *request* is None.
        """
        if request is None:
            raise ExecutionRequestError(
                "ExecutionFactory.create_context requires a non-None request",
                code = "EX-001",
            )
        ctx_err = ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "create_context",
            stage     = "preparation",
        )
        try:
            # Resolve the Order
            order: "Optional[Order]" = None
            if order_registry is not None and request.order_id:
                try:
                    order = order_registry.get(request.order_id)
                except Exception:
                    # Order not found — context records absence; validator will flag it
                    _log.warning(
                        "Order not found during context preparation.",
                        order_id = request.order_id,
                    )

            context = ExecutionContext(
                context_id         = str(uuid.uuid4()),
                execution_id       = execution_id,
                request            = request,
                order              = order,
                portfolio_snapshot = portfolio_snapshot,
                decision           = decision,
                strategy_snapshot  = strategy_snapshot,
                execution_mode     = request.execution_mode,
                metadata           = dict(metadata) if metadata else {},
            )
            _log.info(
                "ExecutionContext assembled.",
                execution_id      = execution_id,
                has_order         = context.has_order,
                has_portfolio     = context.has_portfolio,
                has_decision      = context.has_decision,
                has_strategy      = context.has_strategy,
                completeness      = round(context.completeness, 2),
            )
            return context
        except ExecutionRequestError:
            raise
        except Exception as exc:
            _get_err_mgr().report_failure(self.SYSTEM_ID, exc, ctx_err)
            _log.exception("Unexpected error in ExecutionFactory.create_context.", exc=exc)
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _gen_request_id() -> str:
        return f"REQ-{uuid.uuid4().hex[:16].upper()}"

    @staticmethod
    def gen_execution_id() -> str:
        """Generate a unique execution session ID."""
        return f"EXEC-{uuid.uuid4().hex[:16].upper()}"
