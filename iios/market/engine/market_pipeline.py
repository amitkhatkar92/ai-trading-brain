"""
market_pipeline.py — iios.market.engine
==========================================
Market workflow pipeline and stage value objects.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    VERSION,
    EngineState,
    PipelineStatus,
    MarketWorkflowType,
)


# ---------------------------------------------------------------------------
# PipelineStage
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineStage:
    """
    Immutable record of a single pipeline execution stage.

    Fields
    ------
    stage_name :   Human-readable stage name.
    engine_state : Engine state this stage represents.
    status :       Completion status of the stage.
    started_at :   Wall-clock time the stage started.
    completed_at : Wall-clock time the stage completed (0.0 if not done).
    error :        Non-empty if the stage failed.
    metadata :     Supplementary stage metadata.
    """
    stage_name:   str
    engine_state: EngineState
    status:       PipelineStatus
    started_at:   float          = field(default_factory=time.time)
    completed_at: float          = 0.0
    error:        str            = ""
    metadata:     Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_s(self) -> float:
        end = self.completed_at if self.completed_at > 0 else time.time()
        return max(0.0, end - self.started_at)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name":   self.stage_name,
            "engine_state": self.engine_state.value,
            "status":       self.status.value,
            "started_at":   self.started_at,
            "completed_at": self.completed_at,
            "elapsed_s":    self.elapsed_s,
            "error":        self.error,
        }


# ---------------------------------------------------------------------------
# MarketPipeline
# ---------------------------------------------------------------------------

class MarketPipeline:
    """
    Mutable workflow pipeline tracking the execution of a market request.

    A pipeline is created for every :class:`MarketRequest` submitted to the
    engine.  It accumulates :class:`PipelineStage` records as the workflow
    progresses through the engine state machine.

    Attributes
    ----------
    pipeline_id :          Unique identifier.
    request_id :           Originating request identifier.
    market_analysis_id :   Market analysis identifier.
    exchange :             Target exchange.
    session_id :           Associated lifecycle session identifier.
    workflow_type :        Workflow classification.
    status :               Current pipeline status.
    stages :               Ordered list of completed and in-progress stages.
    created_at :           Wall-clock pipeline creation time.
    started_at :           Wall-clock first stage start time.
    completed_at :         Wall-clock pipeline completion time (0.0 if running).
    error :                Non-empty when the pipeline failed.
    """

    def __init__(
        self,
        request_id:         str,
        market_analysis_id: str,
        exchange:           str,
        workflow_type:      MarketWorkflowType,
        *,
        pipeline_id: Optional[str] = None,
        session_id:  str           = "",
    ) -> None:
        self._pipeline_id        = pipeline_id or str(uuid.uuid4())
        self._request_id         = request_id
        self._market_analysis_id = market_analysis_id
        self._exchange           = exchange
        self._session_id         = session_id
        self._workflow_type      = workflow_type
        self._status:   PipelineStatus      = PipelineStatus.PENDING
        self._stages:   List[PipelineStage] = []
        self._error:    str                 = ""
        self._created_at    = time.time()
        self._started_at:   float           = 0.0
        self._completed_at: float           = 0.0

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def pipeline_id(self) -> str:
        return self._pipeline_id

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def market_analysis_id(self) -> str:
        return self._market_analysis_id

    @property
    def exchange(self) -> str:
        return self._exchange

    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        self._session_id = value

    @property
    def workflow_type(self) -> MarketWorkflowType:
        return self._workflow_type

    @property
    def status(self) -> PipelineStatus:
        return self._status

    @property
    def stages(self) -> List[PipelineStage]:
        return list(self._stages)

    @property
    def error(self) -> str:
        return self._error

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def started_at(self) -> float:
        return self._started_at

    @property
    def completed_at(self) -> float:
        return self._completed_at

    @property
    def is_running(self) -> bool:
        return self._status == PipelineStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        return self._status == PipelineStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self._status == PipelineStatus.FAILED

    @property
    def elapsed_s(self) -> float:
        if self._started_at == 0.0:
            return 0.0
        end = self._completed_at if self._completed_at > 0 else time.time()
        return max(0.0, end - self._started_at)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Mark pipeline as RUNNING."""
        self._status     = PipelineStatus.RUNNING
        self._started_at = time.time()

    def add_stage(self, stage: PipelineStage) -> None:
        """Append a completed pipeline stage record."""
        self._stages.append(stage)

    def complete(self) -> None:
        """Mark pipeline as COMPLETED."""
        self._status       = PipelineStatus.COMPLETED
        self._completed_at = time.time()

    def fail(self, error: str = "") -> None:
        """Mark pipeline as FAILED."""
        self._status       = PipelineStatus.FAILED
        self._error        = error
        self._completed_at = time.time()

    def cancel(self) -> None:
        """Mark pipeline as CANCELLED."""
        self._status       = PipelineStatus.CANCELLED
        self._completed_at = time.time()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id":         self._pipeline_id,
            "request_id":          self._request_id,
            "market_analysis_id":  self._market_analysis_id,
            "exchange":            self._exchange,
            "session_id":          self._session_id,
            "workflow_type":       self._workflow_type.value,
            "status":              self._status.value,
            "stages":              len(self._stages),
            "error":               self._error,
            "created_at":          self._created_at,
            "started_at":          self._started_at,
            "completed_at":        self._completed_at,
            "elapsed_s":           self.elapsed_s,
            "version":             VERSION,
        }
