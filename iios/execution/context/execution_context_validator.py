"""iios/execution/context/execution_context_validator.py
==================================================
ExecutionContextValidator — stateless validator for ExecutionContext
objects and their component parts.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from iios.execution.context.constants import (
    ContextValidationCode,
    ExecutionEnvironment,
    ExecutionMode,
    MarketSession,
)
from iios.execution.context.execution_context import ExecutionContext
from iios.execution.context.execution_environment import ExecutionEnvironmentDescriptor
from iios.execution.context.execution_request_context import ExecutionRequestContext
from iios.execution.context.execution_session import ExecutionSession
from iios.execution.context.execution_metadata import ExecutionMetadata
from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__, engine_id="iios:execution:context:validator")


@dataclass(frozen=True)
class ContextValidationResult:
    """Outcome of a context validation pass."""

    passed:   bool
    errors:   tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(cls, *, warnings: tuple[str, ...] = ()) -> "ContextValidationResult":
        return cls(passed=True, errors=(), warnings=warnings)

    @classmethod
    def fail(cls, *errors: str) -> "ContextValidationResult":
        return cls(passed=False, errors=errors)

    def __bool__(self) -> bool:
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":   self.passed,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class ExecutionContextValidator:
    """
    Stateless validator for ExecutionContext objects.

    Thread-safe (no mutable state).
    """

    # ── Full context validation ───────────────────────────────────────────────

    def validate(self, ctx: ExecutionContext) -> ContextValidationResult:
        """
        Validate a fully assembled ExecutionContext.

        Checks: required identifiers, execution mode, session,
        environment, broker context, and snapshot consistency.
        """
        errors:   list[str] = []
        warnings: list[str] = []

        self._check_identifiers(ctx, errors)
        self._check_mode(ctx, errors)
        self._check_session(ctx, errors, warnings)
        self._check_environment(ctx, errors, warnings)
        self._check_broker_context(ctx, errors, warnings)
        self._check_snapshot_consistency(ctx, errors, warnings)

        if errors:
            return ContextValidationResult.fail(*errors)
        return ContextValidationResult.ok(warnings=tuple(warnings))

    # ── Sub-validations ───────────────────────────────────────────────────────

    def validate_request_context(
        self,
        rctx: ExecutionRequestContext,
    ) -> ContextValidationResult:
        """Validate a request context in isolation."""
        errors: list[str] = []
        if not rctx.execution_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_EXECUTION_ID.value}] "
                "execution_id must not be empty"
            )
        if not rctx.order_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        if not rctx.correlation_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_CORRELATION_ID.value}] "
                "correlation_id must not be empty"
            )
        if errors:
            return ContextValidationResult.fail(*errors)
        return ContextValidationResult.ok()

    def validate_session(self, session: ExecutionSession) -> ContextValidationResult:
        """Validate a session descriptor in isolation."""
        errors: list[str] = []
        if not session.exchange:
            errors.append(
                f"[{ContextValidationCode.SESSION_INVALID.value}] "
                "exchange must not be empty"
            )
        if not session.timezone:
            errors.append(
                f"[{ContextValidationCode.SESSION_INVALID.value}] "
                "timezone must not be empty"
            )
        if errors:
            return ContextValidationResult.fail(*errors)
        return ContextValidationResult.ok()

    def validate_environment(
        self,
        env: ExecutionEnvironmentDescriptor,
    ) -> ContextValidationResult:
        """Validate an environment descriptor in isolation."""
        errors: list[str] = []
        if env.is_live and env.dry_run:
            errors.append(
                f"[{ContextValidationCode.INVALID_ENVIRONMENT.value}] "
                "LIVE mode cannot have dry_run=True"
            )
        if env.allows_live_orders and not env.is_production:
            errors.append(
                f"[{ContextValidationCode.INVALID_ENVIRONMENT.value}] "
                "live_orders_enabled requires PRODUCTION environment"
            )
        if errors:
            return ContextValidationResult.fail(*errors)
        return ContextValidationResult.ok()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _check_identifiers(
        self,
        ctx:    ExecutionContext,
        errors: list[str],
    ) -> None:
        if not ctx.execution_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_EXECUTION_ID.value}] "
                "execution_id must not be empty"
            )
        if not ctx.workflow_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_WORKFLOW_ID.value}] "
                "workflow_id must not be empty"
            )
        if not ctx.order_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        if not ctx.decision_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_DECISION_ID.value}] "
                "decision_id must not be empty"
            )
        if not ctx.portfolio_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_PORTFOLIO_ID.value}] "
                "portfolio_id must not be empty"
            )
        if not ctx.strategy_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_STRATEGY_ID.value}] "
                "strategy_id must not be empty"
            )
        if not ctx.correlation_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_CORRELATION_ID.value}] "
                "correlation_id must not be empty"
            )
        if not ctx.request_id:
            errors.append(
                f"[{ContextValidationCode.MISSING_REQUEST_ID.value}] "
                "request_id must not be empty"
            )
        # Cross-check: request_context IDs must match the top-level IDs
        if ctx.request_context is not None:
            rc = ctx.request_context
            if rc.execution_id and rc.execution_id != ctx.execution_id:
                errors.append(
                    f"[{ContextValidationCode.INCONSISTENT_IDS.value}] "
                    "request_context.execution_id differs from context.execution_id"
                )
            if rc.order_id and rc.order_id != ctx.order_id:
                errors.append(
                    f"[{ContextValidationCode.INCONSISTENT_IDS.value}] "
                    "request_context.order_id differs from context.order_id"
                )

    def _check_mode(self, ctx: ExecutionContext, errors: list[str]) -> None:
        if ctx.execution_mode == ExecutionMode.LIVE:
            if ctx.environment is None:
                errors.append(
                    f"[{ContextValidationCode.INVALID_MODE.value}] "
                    "LIVE mode requires an environment descriptor"
                )
            elif not ctx.environment.allows_live_orders:
                errors.append(
                    f"[{ContextValidationCode.INVALID_MODE.value}] "
                    "LIVE mode requires live_orders_enabled=True in environment"
                )

    def _check_session(
        self,
        ctx:      ExecutionContext,
        errors:   list[str],
        warnings: list[str],
    ) -> None:
        if ctx.session is None:
            warnings.append(
                f"[{ContextValidationCode.SESSION_INVALID.value}] "
                "No session descriptor — market session context unavailable"
            )
            return
        r = self.validate_session(ctx.session)
        errors.extend(r.errors)

    def _check_environment(
        self,
        ctx:      ExecutionContext,
        errors:   list[str],
        warnings: list[str],
    ) -> None:
        if ctx.environment is None:
            warnings.append(
                f"[{ContextValidationCode.INVALID_ENVIRONMENT.value}] "
                "No environment descriptor — deployment context unavailable"
            )
            return
        r = self.validate_environment(ctx.environment)
        errors.extend(r.errors)

    def _check_broker_context(
        self,
        ctx:      ExecutionContext,
        errors:   list[str],
        warnings: list[str],
    ) -> None:
        if ctx.request_context is None or not ctx.request_context.has_broker:
            warnings.append(
                f"[{ContextValidationCode.BROKER_CONTEXT_INVALID.value}] "
                "No broker context — broker routing unavailable"
            )

    def _check_snapshot_consistency(
        self,
        ctx:      ExecutionContext,
        errors:   list[str],
        warnings: list[str],
    ) -> None:
        if not ctx.has_strategy_snapshot:
            warnings.append(
                f"[{ContextValidationCode.SNAPSHOT_MISMATCH.value}] "
                "No strategy_snapshot — strategy constraints unavailable"
            )
        if not ctx.has_portfolio_snapshot:
            warnings.append(
                f"[{ContextValidationCode.SNAPSHOT_MISMATCH.value}] "
                "No portfolio_snapshot — portfolio constraints unavailable"
            )
        if not ctx.has_decision:
            warnings.append(
                f"[{ContextValidationCode.SNAPSHOT_MISMATCH.value}] "
                "No decision — decision context unavailable"
            )
