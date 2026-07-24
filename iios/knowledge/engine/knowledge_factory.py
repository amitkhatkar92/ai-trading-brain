"""
knowledge_factory.py — iios.knowledge.engine
----------------------------------------------
Factory for knowledge engine value objects.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import (
    ACTOR_ENGINE,
    EngineState,
    KnowledgeWorkflowType,
    SchedulerMode,
    SchedulerPriority,
)
from .knowledge_context import KnowledgeEngineContext
from .knowledge_pipeline import KnowledgePipeline
from .knowledge_request import KnowledgeRequest
from .knowledge_response import KnowledgeResponse, KnowledgeSnapshot


class KnowledgeEngineFactory:
    """
    Factory for constructing Knowledge Engine value objects consistently.
    """

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    def create_request(
        self,
        knowledge_id:      str,
        subsystem_id:      str,
        workflow_type:     KnowledgeWorkflowType = KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
        *,
        priority:          SchedulerPriority      = SchedulerPriority.NORMAL,
        scheduler_mode:    SchedulerMode          = SchedulerMode.CONTINUOUS,
        actor:             str                    = ACTOR_ENGINE,
        inputs:            Optional[Dict[str, Any]] = None,
        sources_requested: Optional[List[str]]    = None,
        metadata:          Optional[Dict[str, Any]] = None,
    ) -> KnowledgeRequest:
        return KnowledgeRequest.create(
            knowledge_id      = knowledge_id,
            subsystem_id      = subsystem_id,
            workflow_type     = workflow_type,
            priority          = priority,
            scheduler_mode    = scheduler_mode,
            actor             = actor,
            inputs            = inputs,
            sources_requested = sources_requested,
            metadata          = metadata,
        )

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def create_pipeline(self, request: KnowledgeRequest) -> KnowledgePipeline:
        return KnowledgePipeline.from_request(request)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        knowledge_id:        str,
        subsystem_id:        str,
        session_id:          str,
        workflow_type:       KnowledgeWorkflowType,
        engine_state:        EngineState,
        *,
        sources_collected:   Optional[List[str]]     = None,
        artifacts_collected: int                     = 0,
        artifacts:           Optional[Dict[str, Any]] = None,
        governance_result:   Optional[Dict[str, Any]] = None,
        intelligence_result: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeSnapshot:
        return KnowledgeSnapshot.create(
            knowledge_id        = knowledge_id,
            subsystem_id        = subsystem_id,
            session_id          = session_id,
            workflow_type       = workflow_type,
            engine_state        = engine_state,
            sources_collected   = sources_collected,
            artifacts_collected = artifacts_collected,
            artifacts           = artifacts,
            governance_result   = governance_result,
            intelligence_result = intelligence_result,
        )

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------

    def success_response(
        self,
        request:       KnowledgeRequest,
        snapshot:      KnowledgeSnapshot,
        engine_state:  EngineState,
        pipeline_id:   str,
        processing_ms: float,
        warnings:      Optional[List[str]] = None,
    ) -> KnowledgeResponse:
        return KnowledgeResponse.success(
            request_id    = request.request_id,
            knowledge_id  = request.knowledge_id,
            engine_state  = engine_state,
            snapshot      = snapshot,
            pipeline_id   = pipeline_id,
            processing_ms = processing_ms,
            warnings      = warnings,
        )

    def failure_response(
        self,
        request:       KnowledgeRequest,
        errors:        List[str],
        engine_state:  EngineState,
        pipeline_id:   str,
        processing_ms: float,
    ) -> KnowledgeResponse:
        return KnowledgeResponse.failure(
            request_id    = request.request_id,
            knowledge_id  = request.knowledge_id,
            engine_state  = engine_state,
            errors        = errors,
            pipeline_id   = pipeline_id,
            processing_ms = processing_ms,
        )
