"""iios/execution/context/execution_context_factory.py
==================================================
ExecutionContextFactory — creates, validates, and registers
ExecutionContext objects.

Uses ExecutionContextBuilder internally.
IIOS v1.0: logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_FACTORY,
    FACTORY_SYSTEM_ID,
    ContextStatus,
    ExecutionEnvironment,
    ExecutionMode,
    VERSION,
)
from .exceptions import ContextBuildError, ContextValidationError
from .execution_context import ExecutionContext
from .execution_context_builder import ExecutionContextBuilder
from .execution_context_validator import ExecutionContextValidator, ContextValidationResult
from .execution_context_statistics import ContextBuildStatistics
from .execution_environment import ExecutionEnvironmentDescriptor
from .execution_metadata import ExecutionMetadata
from .execution_session import ExecutionSession
from .execution_request_context import ExecutionRequestContext

_log   = get_logger(__name__, engine_id=FACTORY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=FACTORY_SYSTEM_ID,
                          component="ExecutionContextFactory")


class ExecutionContextFactory:
    """
    Factory that produces validated ExecutionContext objects.

    Steps for each creation:
    1. ExecutionContextBuilder assembles the context.
    2. ExecutionContextValidator runs all validation rules.
    3. On pass: context status is set to VALIDATED.
    4. On fail: ContextValidationError is raised.
    5. ContextBuildStatistics is populated.

    The factory does NOT register contexts — that is the responsibility
    of ExecutionContextRegistry.
    """

    def __init__(self) -> None:
        self._validator = ExecutionContextValidator()

    # ── Main creation interface ───────────────────────────────────────────────

    def create(
        self,
        *,
        execution_id:      str,
        workflow_id:       str,
        order_id:          str,
        decision_id:       str,
        portfolio_id:      str,
        strategy_id:       str,
        correlation_id:    str,
        request_id:        str,
        execution_mode:    ExecutionMode                         = ExecutionMode.PAPER,
        session:           Optional[ExecutionSession]            = None,
        environment:       Optional[ExecutionEnvironmentDescriptor] = None,
        metadata:          Optional[ExecutionMetadata]           = None,
        request_context:   Optional[ExecutionRequestContext]     = None,
        market_snapshot:   Optional[Any]                         = None,
        company_snapshot:  Optional[Any]                         = None,
        strategy_snapshot: Optional[Any]                         = None,
        portfolio_snapshot: Optional[Any]                        = None,
        decision:          Optional[Any]                         = None,
        trace_id:          str                                   = "",
        tags:              frozenset[str]                        = frozenset(),
        extra:             dict[str, Any] | None                 = None,
        strict:            bool                                  = False,
    ) -> tuple[ExecutionContext, ContextBuildStatistics]:
        """
        Create and validate an ExecutionContext.

        Parameters
        ----------
        strict : bool
            If True, treat validation warnings as errors.

        Returns
        -------
        (ExecutionContext, ContextBuildStatistics)
            The validated context and its build statistics.

        Raises
        ------
        ContextBuildError
            If the builder fails to assemble the context.
        ContextValidationError
            If validation fails (always) or warns in strict mode.
        """
        t0 = time.time()

        # Build
        builder = (
            ExecutionContextBuilder()
            .with_ids(
                execution_id = execution_id,
                workflow_id  = workflow_id,
                order_id     = order_id,
                decision_id  = decision_id,
                portfolio_id = portfolio_id,
                strategy_id  = strategy_id,
            )
            .with_correlation(
                correlation_id = correlation_id,
                trace_id       = trace_id,
                request_id     = request_id,
            )
            .with_mode(execution_mode)
        )
        if session:
            builder = builder.with_session(session)
        if environment:
            builder = builder.with_environment(environment)
        if metadata:
            builder = builder.with_metadata(metadata)
        if request_context:
            builder = builder.with_request_context(request_context)
        if market_snapshot:
            builder = builder.with_market_snapshot(market_snapshot)
        if company_snapshot:
            builder = builder.with_company_snapshot(company_snapshot)
        if strategy_snapshot:
            builder = builder.with_strategy_snapshot(strategy_snapshot)
        if portfolio_snapshot:
            builder = builder.with_portfolio_snapshot(portfolio_snapshot)
        if decision:
            builder = builder.with_decision(decision)
        if tags:
            builder = builder.with_tags(*tags)
        if extra:
            builder = builder.with_extra(**extra)

        build_time_ms = (time.time() - t0) * 1_000
        ctx = builder.build()

        # Validate
        tv0 = time.time()
        result = self._validator.validate(ctx)
        val_time_ms = (time.time() - tv0) * 1_000

        if not result.passed:
            stats = ContextBuildStatistics(
                context_id         = ctx.context_id,
                execution_id       = ctx.execution_id,
                builder_time_ms    = build_time_ms,
                validation_passed  = False,
                validation_time_ms = val_time_ms,
                errors             = result.errors,
            )
            _log.warning(
                "ExecutionContext validation failed.",
                execution_id = execution_id,
                errors       = result.errors,
            )
            raise ContextValidationError(
                "ExecutionContext validation failed.",
                errors=result.errors,
            )

        if strict and result.warnings:
            stats = ContextBuildStatistics(
                context_id         = ctx.context_id,
                execution_id       = ctx.execution_id,
                builder_time_ms    = build_time_ms,
                validation_passed  = False,
                validation_time_ms = val_time_ms,
                errors             = result.warnings,
            )
            raise ContextValidationError(
                "ExecutionContext has validation warnings (strict mode).",
                errors=result.warnings,
            )

        # Mark as VALIDATED
        import dataclasses
        ctx = dataclasses.replace(ctx, status=ContextStatus.VALIDATED)

        stats = ContextBuildStatistics(
            context_id         = ctx.context_id,
            execution_id       = ctx.execution_id,
            builder_time_ms    = build_time_ms,
            validation_passed  = True,
            validation_time_ms = val_time_ms,
            snapshot_count     = ctx.snapshot_count,
            completeness       = ctx.completeness,
        )

        _log.info(
            "ExecutionContext created.",
            context_id   = ctx.context_id,
            execution_id = ctx.execution_id,
            mode         = execution_mode.value,
            completeness = ctx.completeness,
        )
        _audit.log_workflow_event(
            FACTORY_SYSTEM_ID, "create", "CONTEXT_CREATED",
            actor        = ACTOR_FACTORY,
            context_id   = ctx.context_id,
            execution_id = ctx.execution_id,
        )
        return ctx, stats

    # ── Identity generation ───────────────────────────────────────────────────

    @staticmethod
    def gen_execution_id() -> str:
        return f"exec-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def gen_workflow_id() -> str:
        return f"wf-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def gen_correlation_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def gen_request_id() -> str:
        return f"req-{uuid.uuid4().hex[:12]}"
