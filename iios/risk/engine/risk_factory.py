"""
risk_factory.py — iios.risk.engine
=====================================
Central factory for all Risk Engine value objects.

Eliminates scattered ``uuid.uuid4()`` and ``time.time()`` calls, and
provides a single location for construction logic.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    ENGINE_SYSTEM_ID,
    EngineState,
    RiskWorkflowType,
    SchedulerPriority,
)
from .risk_context import RiskEngineContext
from .risk_request import RiskRequest
from .risk_response import RiskEngineSnapshot, RiskResponse
from .risk_pipeline import RiskPipeline


class RiskEngineFactory:
    """
    Constructs Risk Engine value objects with consistent identifiers.

    All public methods are stateless and thread-safe.
    """

    system_id: str = ENGINE_SYSTEM_ID

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    @staticmethod
    def create_context(
        risk_id:       str,
        portfolio_id:  str,
        workflow_type: RiskWorkflowType,
        *,
        priority:    SchedulerPriority             = SchedulerPriority.NORMAL,
        strategy_id: str                           = "",
        metadata:    Optional[Dict[str, Any]]      = None,
    ) -> RiskEngineContext:
        return RiskEngineContext.create(
            risk_id,
            portfolio_id,
            workflow_type,
            priority    = priority,
            strategy_id = strategy_id,
            metadata    = metadata,
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    @staticmethod
    def create_request(
        risk_id:       str,
        portfolio_id:  str,
        workflow_type: RiskWorkflowType = RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
        *,
        priority:    SchedulerPriority             = SchedulerPriority.NORMAL,
        context:     Optional[RiskEngineContext]   = None,
        strategy_id: str                           = "",
        inputs:      Optional[Dict[str, Any]]      = None,
        metadata:    Optional[Dict[str, Any]]      = None,
    ) -> RiskRequest:
        return RiskRequest.create(
            risk_id,
            portfolio_id,
            workflow_type,
            priority    = priority,
            context     = context,
            strategy_id = strategy_id,
            inputs      = inputs,
            metadata    = metadata,
        )

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def create_pipeline(
        request:      RiskRequest,
        *,
        session_id:  str = "",
    ) -> RiskPipeline:
        return RiskPipeline(
            request_id    = request.request_id,
            risk_id       = request.risk_id,
            portfolio_id  = request.portfolio_id,
            workflow_type = request.workflow_type,
            session_id    = session_id,
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    @staticmethod
    def create_snapshot(
        risk_id:       str,
        portfolio_id:  str,
        session_id:    str,
        workflow_type: RiskWorkflowType,
        engine_state:  EngineState,
        *,
        inputs_summary: Optional[Dict[str, Any]] = None,
        outputs:        Optional[Dict[str, Any]] = None,
    ) -> RiskEngineSnapshot:
        return RiskEngineSnapshot.create(
            risk_id,
            portfolio_id,
            session_id,
            workflow_type,
            engine_state,
            inputs_summary = inputs_summary,
            outputs        = outputs,
        )

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------

    @staticmethod
    def create_success_response(
        request:   RiskRequest,
        *,
        snapshot:  Optional[RiskEngineSnapshot] = None,
        elapsed_s: float                        = 0.0,
        metadata:  Optional[Dict[str, Any]]     = None,
    ) -> RiskResponse:
        return RiskResponse.create_success(
            request.request_id,
            request.risk_id,
            request.portfolio_id,
            request.workflow_type,
            snapshot  = snapshot,
            elapsed_s = elapsed_s,
            metadata  = metadata,
        )

    @staticmethod
    def create_failure_response(
        request:       RiskRequest,
        *,
        error_message: str                      = "",
        elapsed_s:     float                    = 0.0,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> RiskResponse:
        return RiskResponse.create_failure(
            request.request_id,
            request.risk_id,
            request.portfolio_id,
            request.workflow_type,
            error_message = error_message,
            elapsed_s     = elapsed_s,
            metadata      = metadata,
        )
