"""
supervisor_registry.py — iios.supervisor.engine
-------------------------------------------------
Thread-safe registry for active supervisor pipelines, archived pipelines,
and supervisor requests.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_ARCHIVED_PIPELINES,
)
from .supervisor_pipeline import SupervisorPipeline
from .supervisor_request import SupervisorRequest
from .supervisor_response import SupervisorResponse
from .exceptions import SupervisorEngineCapacityError


class SupervisorEngineRegistry:
    """
    Thread-safe registry for supervisor engine operational data.

    Tracks:
    - Active (PENDING / RUNNING) pipelines — bounded by *max_pipelines*
    - Archived (COMPLETED / FAILED / CANCELLED) pipelines — bounded by
      *max_archived* (oldest discarded when full)
    - Submitted requests — keyed by request_id
    - Responses — keyed by request_id

    Parameters
    ----------
    max_pipelines : Maximum active pipelines.
    max_archived :  Maximum archived pipelines.
    """

    def __init__(
        self,
        max_pipelines: int = DEFAULT_MAX_PIPELINES,
        max_archived:  int = DEFAULT_MAX_ARCHIVED_PIPELINES,
    ) -> None:
        self._lock     = threading.Lock()
        self._max      = max_pipelines
        self._max_arch = max_archived

        self._active:              Dict[str, SupervisorPipeline]  = {}
        self._archived:            OrderedDict                    = OrderedDict()
        self._requests:            Dict[str, SupervisorRequest]   = {}
        self._responses:           Dict[str, SupervisorResponse]  = {}
        self._request_to_pipeline: Dict[str, str]                 = {}

    # ------------------------------------------------------------------
    # Pipeline management
    # ------------------------------------------------------------------

    def register_pipeline(self, pipeline: SupervisorPipeline) -> None:
        with self._lock:
            if len(self._active) >= self._max:
                raise SupervisorEngineCapacityError(self._max)
            self._active[pipeline.pipeline_id] = pipeline
            self._request_to_pipeline[pipeline.request_id] = pipeline.pipeline_id

    def archive_pipeline(self, pipeline: SupervisorPipeline) -> None:
        with self._lock:
            self._active.pop(pipeline.pipeline_id, None)
            if len(self._archived) >= self._max_arch:
                self._archived.popitem(last=False)
            self._archived[pipeline.pipeline_id] = pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[SupervisorPipeline]:
        with self._lock:
            return self._active.get(pipeline_id) or self._archived.get(pipeline_id)

    def get_pipeline_for_request(self, request_id: str) -> Optional[SupervisorPipeline]:
        with self._lock:
            pid = self._request_to_pipeline.get(request_id)
            if pid is None:
                return None
            return self._active.get(pid) or self._archived.get(pid)

    def active_pipelines(self) -> List[SupervisorPipeline]:
        with self._lock:
            return list(self._active.values())

    def active_pipeline_count(self) -> int:
        with self._lock:
            return len(self._active)

    def archived_pipeline_count(self) -> int:
        with self._lock:
            return len(self._archived)

    def is_ready(self) -> bool:
        with self._lock:
            return len(self._active) < self._max

    # ------------------------------------------------------------------
    # Request management
    # ------------------------------------------------------------------

    def register_request(self, request: SupervisorRequest) -> None:
        with self._lock:
            self._requests[request.request_id] = request

    def get_request(self, request_id: str) -> Optional[SupervisorRequest]:
        with self._lock:
            return self._requests.get(request_id)

    # ------------------------------------------------------------------
    # Response management
    # ------------------------------------------------------------------

    def register_response(self, response: SupervisorResponse) -> None:
        with self._lock:
            self._responses[response.request_id] = response

    def get_response(self, request_id: str) -> Optional[SupervisorResponse]:
        with self._lock:
            return self._responses.get(request_id)

    def recent_responses(self, n: int = 20) -> List[SupervisorResponse]:
        with self._lock:
            items = list(self._responses.values())
        return items[-n:] if n < len(items) else items

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._archived.clear()
            self._requests.clear()
            self._responses.clear()
            self._request_to_pipeline.clear()
