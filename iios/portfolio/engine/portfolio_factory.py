"""
portfolio_factory.py — iios.portfolio.engine
=============================================
Factory for creating Portfolio Engine domain objects.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    FACTORY_SYSTEM_ID,
    VERSION,
    EngineState,
    PipelineStatus,
    PortfolioWorkflowType,
    ResponseStatus,
    SchedulerPriority,
)
from .portfolio_context import PortfolioContext
from .portfolio_pipeline import PortfolioPipeline
from .portfolio_request import PortfolioRequest
from .portfolio_response import PortfolioResponse, PortfolioSnapshot


class PortfolioEngineFactory:
    """
    Creates Portfolio Engine domain objects with validated defaults.

    Usage
    -----
    ::

        factory = PortfolioEngineFactory()
        request  = factory.create_request("pf-001", PortfolioWorkflowType.PORTFOLIO_CREATION)
        pipeline = factory.create_pipeline(request)
        snapshot = factory.create_snapshot(request, session_id="s1")
        response = factory.create_success_response(request, snapshot=snapshot)
    """

    def create_request(
        self,
        portfolio_id:  str,
        workflow_type: PortfolioWorkflowType = PortfolioWorkflowType.PORTFOLIO_CREATION,
        *,
        priority:  SchedulerPriority          = SchedulerPriority.NORMAL,
        inputs:    Optional[Dict[str, Any]]   = None,
        metadata:  Optional[Dict[str, Any]]   = None,
        request_id: Optional[str]             = None,
    ) -> PortfolioRequest:
        return PortfolioRequest.create(
            portfolio_id,
            workflow_type,
            request_id = request_id,
            priority   = priority,
            inputs     = inputs,
            metadata   = metadata,
        )

    def create_pipeline(
        self,
        request: PortfolioRequest,
        *,
        session_id: str = "",
    ) -> PortfolioPipeline:
        return PortfolioPipeline(
            request_id    = request.request_id,
            portfolio_id  = request.portfolio_id,
            workflow_type = request.workflow_type,
            session_id    = session_id,
        )

    def create_snapshot(
        self,
        request:    PortfolioRequest,
        session_id: str,
        *,
        engine_state:   EngineState                  = EngineState.PUBLISHING,
        inputs_summary: Optional[Dict[str, Any]]     = None,
        outputs:        Optional[Dict[str, Any]]     = None,
    ) -> PortfolioSnapshot:
        return PortfolioSnapshot.create(
            portfolio_id   = request.portfolio_id,
            session_id     = session_id,
            workflow_type  = request.workflow_type,
            engine_state   = engine_state,
            inputs_summary = inputs_summary or {"input_keys": list(request.inputs.keys())},
            outputs        = outputs or {},
        )

    def create_success_response(
        self,
        request:    PortfolioRequest,
        *,
        snapshot:  Optional[PortfolioSnapshot] = None,
        elapsed_s: float                       = 0.0,
        metadata:  Optional[Dict[str, Any]]    = None,
    ) -> PortfolioResponse:
        return PortfolioResponse.create_success(
            request_id    = request.request_id,
            portfolio_id  = request.portfolio_id,
            workflow_type = request.workflow_type,
            snapshot      = snapshot,
            elapsed_s     = elapsed_s,
            metadata      = metadata,
        )

    def create_failure_response(
        self,
        request:       PortfolioRequest,
        *,
        error_message: str                       = "",
        elapsed_s:     float                     = 0.0,
        metadata:      Optional[Dict[str, Any]]  = None,
    ) -> PortfolioResponse:
        return PortfolioResponse.create_failure(
            request_id    = request.request_id,
            portfolio_id  = request.portfolio_id,
            workflow_type = request.workflow_type,
            error_message = error_message,
            elapsed_s     = elapsed_s,
            metadata      = metadata,
        )
