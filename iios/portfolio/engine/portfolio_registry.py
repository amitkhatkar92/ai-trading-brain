"""
portfolio_registry.py — iios.portfolio.engine
==============================================
Thread-safe registry of active and completed portfolio pipelines
and requests for the Portfolio Engine.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_ARCHIVED_PIPELINES, DEFAULT_MAX_PIPELINES, PipelineStatus
from .portfolio_pipeline import PortfolioPipeline
from .portfolio_request import PortfolioRequest
from .exceptions import PortfolioCapacityError, PortfolioPipelineError


class PortfolioEngineRegistry:
    """
    Thread-safe registry of portfolio pipelines and requests.

    Maintains:
    * **active** — pipelines currently being processed.
    * **completed** — successfully completed pipelines (bounded).
    * **failed** — failed pipelines (bounded).
    * **requests** — all known requests by request_id.

    Parameters
    ----------
    max_active_pipelines :   Maximum concurrent in-flight pipelines.
    max_archived_pipelines : Maximum completed/failed pipelines retained.
    """

    def __init__(
        self,
        max_active_pipelines:   int = DEFAULT_MAX_PIPELINES,
        max_archived_pipelines: int = DEFAULT_MAX_ARCHIVED_PIPELINES,
    ) -> None:
        self._lock               = threading.RLock()
        self._active:   Dict[str, PortfolioPipeline] = {}
        self._completed: deque = deque(maxlen=max_archived_pipelines)
        self._failed:    deque = deque(maxlen=max_archived_pipelines)
        self._requests:  Dict[str, PortfolioRequest] = {}
        self._max_active = max_active_pipelines

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def register_pipeline(self, pipeline: PortfolioPipeline) -> None:
        with self._lock:
            if len(self._active) >= self._max_active:
                raise PortfolioCapacityError(self._max_active)
            self._active[pipeline.pipeline_id] = pipeline

    def update_pipeline(self, pipeline: PortfolioPipeline) -> None:
        """Update a pipeline record; moves to completed/failed if terminal."""
        with self._lock:
            if pipeline.status == PipelineStatus.COMPLETED:
                self._active.pop(pipeline.pipeline_id, None)
                self._completed.append(pipeline)
            elif pipeline.status in (PipelineStatus.FAILED, PipelineStatus.CANCELLED):
                self._active.pop(pipeline.pipeline_id, None)
                self._failed.append(pipeline)
            else:
                self._active[pipeline.pipeline_id] = pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[PortfolioPipeline]:
        with self._lock:
            pipeline = self._active.get(pipeline_id)
            if pipeline:
                return pipeline
            for p in self._completed:
                if p.pipeline_id == pipeline_id:
                    return p
            for p in self._failed:
                if p.pipeline_id == pipeline_id:
                    return p
        return None

    def active_pipelines(self) -> List[PortfolioPipeline]:
        with self._lock:
            return list(self._active.values())

    def completed_pipelines(self) -> List[PortfolioPipeline]:
        with self._lock:
            return list(self._completed)

    def failed_pipelines(self) -> List[PortfolioPipeline]:
        with self._lock:
            return list(self._failed)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def completed_count(self) -> int:
        with self._lock:
            return len(self._completed)

    def failed_count(self) -> int:
        with self._lock:
            return len(self._failed)

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def register_request(self, request: PortfolioRequest) -> None:
        with self._lock:
            self._requests[request.request_id] = request

    def get_request(self, request_id: str) -> Optional[PortfolioRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._completed.clear()
            self._failed.clear()
            self._requests.clear()
