"""
decision_registry.py — iios.decision.engine
=============================================
Thread-safe registry tracking active and completed engine requests and
pipelines.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_ACTIVE, DEFAULT_MAX_COMPLETED
from .decision_pipeline import DecisionPipeline
from .decision_request  import DecisionRequest
from .exceptions import DecisionRequestNotFoundError


class DecisionEngineRegistry:
    """
    Thread-safe registry for :class:`DecisionRequest` and
    :class:`DecisionPipeline` objects managed by the engine.

    Active pipelines are stored in a ``Dict[pipeline_id → DecisionPipeline]``.
    Completed pipelines are moved to a bounded ``deque`` for history.

    Parameters
    ----------
    max_active :    Maximum simultaneous active pipelines.
    max_completed : Maximum completed pipelines retained in memory.
    """

    def __init__(
        self,
        max_active:    int = DEFAULT_MAX_ACTIVE,
        max_completed: int = DEFAULT_MAX_COMPLETED,
    ) -> None:
        self._lock = threading.RLock()
        self._max_active    = max_active
        self._max_completed = max_completed

        self._requests:  Dict[str, DecisionRequest]  = {}   # request_id → request
        self._pipelines: Dict[str, DecisionPipeline] = {}   # pipeline_id → pipeline
        self._completed: deque[DecisionPipeline]     = deque(maxlen=max_completed)

        # Secondary index: decision_id → list of pipeline_ids
        self._by_decision: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Request management
    # ------------------------------------------------------------------
    def register_request(self, request: DecisionRequest) -> None:
        with self._lock:
            self._requests[request.request_id] = request

    def get_request(self, request_id: str) -> DecisionRequest:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None:
                raise DecisionRequestNotFoundError(request_id)
            return req

    def find_request(self, request_id: str) -> Optional[DecisionRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def deregister_request(self, request_id: str) -> None:
        with self._lock:
            self._requests.pop(request_id, None)

    # ------------------------------------------------------------------
    # Pipeline management
    # ------------------------------------------------------------------
    def register_pipeline(self, pipeline: DecisionPipeline) -> None:
        with self._lock:
            if len(self._pipelines) >= self._max_active:
                raise RuntimeError(
                    f"DecisionEngineRegistry: max_active ({self._max_active}) "
                    "reached — cannot register new pipeline"
                )
            self._pipelines[pipeline.pipeline_id] = pipeline
            did = pipeline.decision_id
            if did not in self._by_decision:
                self._by_decision[did] = []
            self._by_decision[did].append(pipeline.pipeline_id)

    def move_to_completed(self, pipeline_id: str) -> None:
        """Remove pipeline from active store and archive it."""
        with self._lock:
            pipeline = self._pipelines.pop(pipeline_id, None)
            if pipeline is not None:
                self._completed.append(pipeline)

    def get_pipeline(self, pipeline_id: str) -> Optional[DecisionPipeline]:
        with self._lock:
            return self._pipelines.get(pipeline_id)

    def find_completed(self, pipeline_id: str) -> Optional[DecisionPipeline]:
        with self._lock:
            for p in self._completed:
                if p.pipeline_id == pipeline_id:
                    return p
            return None

    def find_any(self, pipeline_id: str) -> Optional[DecisionPipeline]:
        with self._lock:
            return (
                self._pipelines.get(pipeline_id)
                or next((p for p in self._completed if p.pipeline_id == pipeline_id), None)
            )

    def active_pipelines(self) -> List[DecisionPipeline]:
        with self._lock:
            return list(self._pipelines.values())

    def pipelines_for_decision(self, decision_id: str) -> List[DecisionPipeline]:
        with self._lock:
            ids = self._by_decision.get(decision_id, [])
            result = []
            for pid in ids:
                p = self._pipelines.get(pid)
                if p is not None:
                    result.append(p)
            return result

    def active_count(self) -> int:
        with self._lock:
            return len(self._pipelines)

    def completed_count(self) -> int:
        with self._lock:
            return len(self._completed)

    def total_count(self) -> int:
        with self._lock:
            return len(self._pipelines) + len(self._completed)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._pipelines.clear()
            self._completed.clear()
            self._by_decision.clear()
