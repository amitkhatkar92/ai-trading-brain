"""
knowledge_response.py — iios.knowledge.engine
-----------------------------------------------
Knowledge workflow response and snapshot value objects.

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
    ResponseStatus,
)


# ---------------------------------------------------------------------------
# KnowledgeSnapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KnowledgeSnapshot:
    """
    Immutable point-in-time snapshot of a knowledge workflow output.

    Published at the end of every successful knowledge pipeline.

    Fields
    ------
    snapshot_id :         Unique identifier.
    knowledge_id :        Knowledge workflow run identifier.
    subsystem_id :        Target subsystem identifier.
    session_id :          Owning lifecycle session.
    workflow_type :       Workflow that produced this snapshot.
    engine_state :        Engine state at publication time.
    sources_collected :   List of source identifiers that contributed.
    artifacts_collected : Count of artifacts collected.
    artifacts :           Collected artifact data keyed by source.
    governance_result :   Result from M3 Knowledge Governance (if invoked).
    intelligence_result : Result from M4 Knowledge Intelligence (if invoked).
    published_at :        Wall-clock publication time.
    framework_version :   Framework version string.
    """
    snapshot_id:          str
    knowledge_id:         str
    subsystem_id:         str
    session_id:           str
    workflow_type:        KnowledgeWorkflowType
    engine_state:         EngineState
    sources_collected:    List[str]      = field(default_factory=list)
    artifacts_collected:  int            = 0
    artifacts:            Dict[str, Any] = field(default_factory=dict)
    governance_result:    Dict[str, Any] = field(default_factory=dict)
    intelligence_result:  Dict[str, Any] = field(default_factory=dict)
    published_at:         float          = field(default_factory=time.time)
    framework_version:    str            = VERSION

    @classmethod
    def create(
        cls,
        knowledge_id:  str,
        subsystem_id:  str,
        session_id:    str,
        workflow_type: KnowledgeWorkflowType,
        engine_state:  EngineState,
        *,
        snapshot_id:          Optional[str]           = None,
        sources_collected:    Optional[List[str]]     = None,
        artifacts_collected:  int                     = 0,
        artifacts:            Optional[Dict[str, Any]] = None,
        governance_result:    Optional[Dict[str, Any]] = None,
        intelligence_result:  Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeSnapshot":
        return cls(
            snapshot_id         = snapshot_id or str(uuid.uuid4()),
            knowledge_id        = knowledge_id,
            subsystem_id        = subsystem_id,
            session_id          = session_id,
            workflow_type       = workflow_type,
            engine_state        = engine_state,
            sources_collected   = list(sources_collected or []),
            artifacts_collected = artifacts_collected,
            artifacts           = artifacts or {},
            governance_result   = governance_result or {},
            intelligence_result = intelligence_result or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "knowledge_id":        self.knowledge_id,
            "subsystem_id":        self.subsystem_id,
            "session_id":          self.session_id,
            "workflow_type":       self.workflow_type.value,
            "engine_state":        self.engine_state.value,
            "sources_collected":   self.sources_collected,
            "artifacts_collected": self.artifacts_collected,
            "published_at":        self.published_at,
            "framework_version":   self.framework_version,
        }


# ---------------------------------------------------------------------------
# KnowledgeResponse
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KnowledgeResponse:
    """
    Immutable knowledge workflow response returned to the caller.

    Fields
    ------
    response_id :    Unique response identifier.
    request_id :     Identifier of the originating request.
    knowledge_id :   Knowledge workflow run identifier.
    status :         Overall workflow outcome.
    engine_state :   Engine state at response creation time.
    snapshot :       Published snapshot (None on failure).
    errors :         List of error messages.
    warnings :       List of warning messages.
    pipeline_id :    Internal pipeline identifier.
    processing_ms :  Total wall-clock processing time in ms.
    responded_at :   Wall-clock response creation time.
    framework_version : Framework version string.
    """
    response_id:       str
    request_id:        str
    knowledge_id:      str
    status:            ResponseStatus
    engine_state:      EngineState
    snapshot:          Optional[KnowledgeSnapshot] = None
    errors:            List[str]      = field(default_factory=list)
    warnings:          List[str]      = field(default_factory=list)
    pipeline_id:       str            = ""
    processing_ms:     float          = 0.0
    responded_at:      float          = field(default_factory=time.time)
    framework_version: str            = VERSION

    @classmethod
    def success(
        cls,
        request_id:    str,
        knowledge_id:  str,
        engine_state:  EngineState,
        snapshot:      KnowledgeSnapshot,
        *,
        response_id:   Optional[str] = None,
        pipeline_id:   str           = "",
        processing_ms: float         = 0.0,
        warnings:      Optional[List[str]] = None,
    ) -> "KnowledgeResponse":
        return cls(
            response_id    = response_id or str(uuid.uuid4()),
            request_id     = request_id,
            knowledge_id   = knowledge_id,
            status         = ResponseStatus.SUCCESS,
            engine_state   = engine_state,
            snapshot       = snapshot,
            warnings       = list(warnings or []),
            pipeline_id    = pipeline_id,
            processing_ms  = processing_ms,
        )

    @classmethod
    def failure(
        cls,
        request_id:    str,
        knowledge_id:  str,
        engine_state:  EngineState,
        errors:        List[str],
        *,
        response_id:   Optional[str]  = None,
        pipeline_id:   str            = "",
        processing_ms: float          = 0.0,
        warnings:      Optional[List[str]] = None,
    ) -> "KnowledgeResponse":
        return cls(
            response_id    = response_id or str(uuid.uuid4()),
            request_id     = request_id,
            knowledge_id   = knowledge_id,
            status         = ResponseStatus.FAILURE,
            engine_state   = engine_state,
            errors         = list(errors),
            warnings       = list(warnings or []),
            pipeline_id    = pipeline_id,
            processing_ms  = processing_ms,
        )

    @property
    def succeeded(self) -> bool:
        return self.status == ResponseStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "knowledge_id":  self.knowledge_id,
            "status":        self.status.value,
            "engine_state":  self.engine_state.value,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "pipeline_id":   self.pipeline_id,
            "processing_ms": self.processing_ms,
            "responded_at":  self.responded_at,
        }
