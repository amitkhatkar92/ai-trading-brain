"""
market_factory.py — iios.market.engine
=========================================
Central factory for all Market Engine value objects.

Eliminates scattered ``uuid.uuid4()`` and ``time.time()`` calls, and
provides a single location for construction logic.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    ENGINE_SYSTEM_ID,
    EngineState,
    MarketWorkflowType,
    SchedulerPriority,
)
from .market_context import MarketEngineContext
from .market_request import MarketRequest
from .market_response import MarketEngineSnapshot, MarketResponse
from .market_pipeline import MarketPipeline


class MarketEngineFactory:
    """
    Constructs Market Engine value objects with consistent identifiers.

    All public methods are stateless and thread-safe.
    """

    system_id: str = ENGINE_SYSTEM_ID

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    @staticmethod
    def create_context(
        market_analysis_id: str,
        exchange:           str,
        workflow_type:      MarketWorkflowType,
        *,
        priority:      SchedulerPriority           = SchedulerPriority.NORMAL,
        instrument_id: str                        = "",
        metadata:      Optional[Dict[str, Any]]   = None,
    ) -> MarketEngineContext:
        return MarketEngineContext.create(
            market_analysis_id,
            exchange,
            workflow_type,
            priority      = priority,
            instrument_id = instrument_id,
            metadata      = metadata,
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    @staticmethod
    def create_request(
        market_analysis_id: str,
        exchange:           str,
        workflow_type:      MarketWorkflowType = MarketWorkflowType.MARKET_OVERVIEW,
        *,
        priority:      SchedulerPriority               = SchedulerPriority.NORMAL,
        context:       Optional[MarketEngineContext]   = None,
        instrument_id: str                            = "",
        inputs:        Optional[Dict[str, Any]]        = None,
        metadata:      Optional[Dict[str, Any]]        = None,
    ) -> MarketRequest:
        return MarketRequest.create(
            market_analysis_id,
            exchange,
            workflow_type,
            priority      = priority,
            context       = context,
            instrument_id = instrument_id,
            inputs        = inputs,
            metadata      = metadata,
        )

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def create_pipeline(
        request:     MarketRequest,
        *,
        session_id:  str = "",
    ) -> MarketPipeline:
        return MarketPipeline(
            request_id         = request.request_id,
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            workflow_type      = request.workflow_type,
            session_id         = session_id,
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    @staticmethod
    def create_snapshot(
        market_analysis_id: str,
        exchange:           str,
        session_id:         str,
        workflow_type:      MarketWorkflowType,
        engine_state:       EngineState,
        *,
        inputs_summary: Optional[Dict[str, Any]] = None,
        outputs:        Optional[Dict[str, Any]] = None,
    ) -> MarketEngineSnapshot:
        return MarketEngineSnapshot.create(
            market_analysis_id,
            exchange,
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
        request:   MarketRequest,
        *,
        snapshot:  Optional[MarketEngineSnapshot] = None,
        elapsed_s: float                          = 0.0,
        metadata:  Optional[Dict[str, Any]]       = None,
    ) -> MarketResponse:
        return MarketResponse.create_success(
            request.request_id,
            request.market_analysis_id,
            request.exchange,
            request.workflow_type,
            snapshot  = snapshot,
            elapsed_s = elapsed_s,
            metadata  = metadata,
        )

    @staticmethod
    def create_failure_response(
        request:       MarketRequest,
        *,
        error_message: str                      = "",
        elapsed_s:     float                    = 0.0,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> MarketResponse:
        return MarketResponse.create_failure(
            request.request_id,
            request.market_analysis_id,
            request.exchange,
            request.workflow_type,
            error_message = error_message,
            elapsed_s     = elapsed_s,
            metadata      = metadata,
        )
