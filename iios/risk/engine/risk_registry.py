"""
risk_registry.py — iios.risk.engine
======================================
Thread-safe registry for active risk pipelines, archived pipelines,
and risk requests.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_ARCHIVED_PIPELINES,
    PipelineStatus,
)
from .risk_pipeline import RiskPipeline
from .risk_request import RiskRequest
from .risk_response import RiskResponse
from .exceptions import RiskCapacityError


class RiskEngineRegistry:
    """
    Thread-safe registry for risk engine operational data.

    Tracks:
    - Active (PENDING / RUNNING) pipelines — bounded by *max_pipelines*
    - Archived (COMPLETED / FAILED / CANCELLED) pipelines — bounded by
      *max_archived*
    - Submitted requests — keyed by request_id
    - Responses — keyed by request_id

    Parameters
    ----------
    max_pipelines : Maximum active pipelines (raises RiskCapacityError when exceeded).
    max_archived :  Maximum archived pipelines (oldest discarded when full).
    """

    def __init__(
        self,
        max_pipelines: int = DEFAULT_MAX_PIPELINES,
        max_archived:  int = DEFAULT_MAX_ARCHIVED_PIPELINES,
    ) -> None:
        self._lock     = threading.Lock()
        self._max      = max_pipelines
        self._max_arch = max_archived

        self._active:   Dict[str, RiskPipeline] = {}              # pipeline_id → pipeline
        self._archived: OrderedDict             = OrderedDict()   # pipeline_id → pipeline
        self._requests: Dict[str, RiskRequest]  = {}              # request_id  → request
        self._responses: Dict[str, RiskResponse] = {}             # request_id  → response
        self._request_to_pipeline: Dict[str, str] = {}            # request_id → pipeline_id

    # ------------------------------------------------------------------
    # Pipeline management
    # ------------------------------------------------------------------

    def register_pipeline(self, pipeline: RiskPipeline) -> None:
        with self._lock:
            if len(self._active) >= self._max:
                raise RiskCapacityError(self._max)
            self._active[pipeline.pipeline_id] = pipeline
            self._request_to_pipeline[pipeline.request_id] = pipeline.pipeline_id

    def archive_pipeline(self, pipeline: RiskPipeline) -> None:
        with self._lock:
            self._active.pop(pipeline.pipeline_id, None)
            if len(self._archived) >= self._max_arch:
                self._archived.popitem(last=False)  # evict oldest
            self._archived[pipeline.pipeline_id] = pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[RiskPipeline]:
        with self._lock:
            return self._active.get(pipeline_id) or self._archived.get(pipeline_id)

    def get_pipeline_for_request(self, request_id: str) -> Optional[RiskPipeline]:
        with self._lock:
            pid = self._request_to_pipeline.get(request_id)
            if pid is None:
                return None
            return self._active.get(pid) or self._archived.get(pid)

    def active_pipelines(self) -> List[RiskPipeline]:
        with self._lock:
            return list(self._active.values())

    def archived_pipeline_count(self) -> int:
        with self._lock:
            return len(self._archived)

    def active_pipeline_count(self) -> int:
        with self._lock:
            return len(self._active)

    def is_ready(self) -> bool:
        """True when the registry is below capacity limits."""
        with self._lock:
            return len(self._active) < self._max

    # ------------------------------------------------------------------
    # Request management
    # ------------------------------------------------------------------

    def register_request(self, request: RiskRequest) -> None:
        with self._lock:
            self._requests[request.request_id] = request

    def get_request(self, request_id: str) -> Optional[RiskRequest]:
        with self._lock:
            return self._requests.get(request_id)

    # ------------------------------------------------------------------
    # Response management
    # ------------------------------------------------------------------

    def register_response(self, response: RiskResponse) -> None:
        with self._lock:
            self._responses[response.request_id] = response

    def get_response(self, request_id: str) -> Optional[RiskResponse]:
        with self._lock:
            return self._responses.get(request_id)

    # ------------------------------------------------------------------
    # Query / filter
    # ------------------------------------------------------------------

    def query(self, **filters: Any) -> List[RiskPipeline]:
        """
        Return pipelines matching all supplied keyword filters.

        Supported filters:
        - status (PipelineStatus)
        - portfolio_id (str)
        - risk_id (str)
        - workflow_type (RiskWorkflowType)
        """
        with self._lock:
            candidates: List[RiskPipeline] = (
                list(self._active.values()) + list(self._archived.values())
            )

        result = []
        for p in candidates:
            match = True
            for k, v in filters.items():
                if getattr(p, k, None) != v:
                    match = False
                    break
            if match:
                result.append(p)
        return result

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, int]:
        with self._lock:
            return {
                "active_pipelines":   len(self._active),
                "archived_pipelines": len(self._archived),
                "requests":           len(self._requests),
                "responses":          len(self._responses),
            }
