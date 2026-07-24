"""
integration_dispatcher.py — iios.integration.engine
-----------------------------------------------------
IntegrationDispatcher — coordinates the dispatch of a single
IntegrationRequest through the pipeline.

Does NOT implement connector or protocol logic.
Delegates all execution to IntegrationPipeline.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .integration_context import IntegrationEngineContext
from .integration_pipeline import IntegrationPipeline, PipelineExecution
from .integration_request import IntegrationRequest

_log = get_logger(__name__)


class IntegrationDispatcher:
    """
    Coordinates dispatch of integration requests through the pipeline.

    Thread-safe.  Each dispatch creates a PipelineExecution that tracks
    stage completion independently from concurrent dispatches.
    """

    def __init__(
        self,
        pipeline: Optional[IntegrationPipeline] = None,
    ) -> None:
        self._pipeline = pipeline or IntegrationPipeline()
        self._lock     = threading.Lock()

    def dispatch(
        self,
        request: IntegrationRequest,
        context: IntegrationEngineContext,
    ) -> PipelineExecution:
        """
        Dispatch a single integration request through the pipeline.

        Returns:
            PipelineExecution with stage completion results.
        """
        _log.debug(
            f"Dispatcher: dispatch request={request.request_id!r} "
            f"session={context.session_id!r}"
        )
        return self._pipeline.execute(request, context)

    def dispatch_batch(
        self,
        requests: List[IntegrationRequest],
        contexts: List[IntegrationEngineContext],
    ) -> List[PipelineExecution]:
        """
        Dispatch multiple requests in sequence.

        Each request is dispatched independently.  Failures in one
        request do not affect others.
        """
        results = []
        for req, ctx in zip(requests, contexts):
            execution = self.dispatch(req, ctx)
            results.append(execution)
        return results

    def pipeline_stage_count(self) -> int:
        from .constants import PIPELINE_STAGE_ORDER
        return len(PIPELINE_STAGE_ORDER)
