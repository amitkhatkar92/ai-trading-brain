"""
knowledge_pipeline.py — iios.knowledge.engine
-----------------------------------------------
Knowledge workflow pipeline and stage tracking value objects.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    VERSION,
    EngineState,
    KnowledgeWorkflowType,
    PipelineStatus,
    SchedulerPriority,
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
# KnowledgePipeline
# ---------------------------------------------------------------------------

class KnowledgePipeline:
    """
    Mutable workflow pipeline tracking the execution of a knowledge request.

    A pipeline is created for every :class:`KnowledgeRequest` submitted to
    the engine.  It accumulates :class:`PipelineStage` records as the
    workflow progresses.
    """

    def __init__(
        self,
        pipeline_id:   str,
        request_id:    str,
        knowledge_id:  str,
        subsystem_id:  str,
        workflow_type: KnowledgeWorkflowType,
        priority:      SchedulerPriority = SchedulerPriority.NORMAL,
    ) -> None:
        self._pipeline_id   = pipeline_id
        self._request_id    = request_id
        self._knowledge_id  = knowledge_id
        self._subsystem_id  = subsystem_id
        self._workflow_type = workflow_type
        self._priority      = priority
        self._status        = PipelineStatus.PENDING
        self._stages:       List[PipelineStage] = []
        self._created_at    = time.time()
        self._completed_at: Optional[float] = None
        self._error:        str = ""

    # Read-only properties
    @property
    def pipeline_id(self) -> str:       return self._pipeline_id
    @property
    def request_id(self) -> str:        return self._request_id
    @property
    def knowledge_id(self) -> str:      return self._knowledge_id
    @property
    def subsystem_id(self) -> str:      return self._subsystem_id
    @property
    def workflow_type(self) -> KnowledgeWorkflowType: return self._workflow_type
    @property
    def priority(self) -> SchedulerPriority: return self._priority
    @property
    def status(self) -> PipelineStatus: return self._status
    @property
    def stages(self) -> List[PipelineStage]: return list(self._stages)
    @property
    def created_at(self) -> float:      return self._created_at
    @property
    def completed_at(self) -> Optional[float]: return self._completed_at
    @property
    def error(self) -> str:             return self._error
    @property
    def is_terminal(self) -> bool:
        return self._status in (
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELLED,
        )

    @property
    def elapsed_s(self) -> float:
        end = self._completed_at or time.time()
        return max(0.0, end - self._created_at)

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_s * 1_000.0

    # Mutation
    def mark_running(self) -> None:
        self._status = PipelineStatus.RUNNING

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages.append(stage)

    def mark_completed(self) -> None:
        self._status       = PipelineStatus.COMPLETED
        self._completed_at = time.time()

    def mark_failed(self, error: str = "") -> None:
        self._status       = PipelineStatus.FAILED
        self._completed_at = time.time()
        self._error        = error

    def mark_cancelled(self) -> None:
        self._status       = PipelineStatus.CANCELLED
        self._completed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id":   self._pipeline_id,
            "request_id":    self._request_id,
            "knowledge_id":  self._knowledge_id,
            "subsystem_id":  self._subsystem_id,
            "workflow_type": self._workflow_type.value,
            "priority":      int(self._priority),
            "status":        self._status.value,
            "stage_count":   len(self._stages),
            "created_at":    self._created_at,
            "completed_at":  self._completed_at,
            "elapsed_s":     self.elapsed_s,
            "error":         self._error,
        }

    @classmethod
    def from_request(cls, request: Any) -> "KnowledgePipeline":
        """Convenience constructor from a KnowledgeRequest."""
        return cls(
            pipeline_id   = str(uuid.uuid4()),
            request_id    = request.request_id,
            knowledge_id  = request.knowledge_id,
            subsystem_id  = request.subsystem_id,
            workflow_type = request.workflow_type,
            priority      = request.priority,
        )
