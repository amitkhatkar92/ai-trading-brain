"""
iios/execution/recovery/failover/failover_factory.py
====================================================
FailoverFactory — lifecycle-aware factory for all Failover Framework DTOs.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_SYSTEM,
    FACTORY_ID,
    VERSION,
    FailoverAction,
    FailoverPhase,
    FailoverStatus,
    FailoverType,
)
from .failover_context import FailoverContext, make_failover_context
from .failover_request import FailoverRequest, make_failover_request
from .failover_response import (
    FailoverResponse,
    FailoverResult,
    VerificationReport,
    make_failover_response,
    make_failover_result,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class FailoverFactory(LifecycleAwareMixin):
    """Lifecycle-aware factory for Failover Framework DTOs."""

    def __init__(self) -> None:
        super().__init__()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(FACTORY_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverFactory started")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(FACTORY_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverFactory stopped")

    # ── Context ───────────────────────────────────────────────────────────────

    def create_context(
        self,
        failover_session_id: str,
        execution_session_id: str,
        subsystem_id: str,
        failover_type: FailoverType,
        primary_action: FailoverAction,
        source_decision_id: str,
        **kwargs: Any,
    ) -> FailoverContext:
        return make_failover_context(
            failover_session_id  = failover_session_id,
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            failover_type        = failover_type,
            primary_action       = primary_action,
            source_decision_id   = source_decision_id,
            **kwargs,
        )

    # ── Request ───────────────────────────────────────────────────────────────

    def create_request(
        self,
        failover_session_id: str,
        execution_session_id: str,
        subsystem_id: str,
        failover_type: FailoverType,
        primary_action: FailoverAction,
        source_decision_id: str,
        context: FailoverContext,
        **kwargs: Any,
    ) -> FailoverRequest:
        return make_failover_request(
            failover_session_id  = failover_session_id,
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            failover_type        = failover_type,
            primary_action       = primary_action,
            source_decision_id   = source_decision_id,
            context              = context,
            **kwargs,
        )

    # ── Response ──────────────────────────────────────────────────────────────

    def create_response(
        self,
        request_id: str,
        failover_session_id: str,
        source_decision_id: str,
        result: FailoverResult,
        verification_report: Optional[VerificationReport],
        response_time_ms: float,
        **kwargs: Any,
    ) -> FailoverResponse:
        return make_failover_response(
            request_id          = request_id,
            failover_session_id = failover_session_id,
            source_decision_id  = source_decision_id,
            result              = result,
            verification_report = verification_report,
            response_time_ms    = response_time_ms,
            **kwargs,
        )
