"""
knowledge_request.py — iios.knowledge.engine
----------------------------------------------
Immutable knowledge workflow request value object.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    VERSION,
    KnowledgeWorkflowType,
    SchedulerMode,
    SchedulerPriority,
)
from .knowledge_context import KnowledgeEngineContext


@dataclass(frozen=True)
class KnowledgeRequest:
    """
    Immutable knowledge workflow request.

    Wraps all inputs required to execute a single knowledge workflow pipeline.

    Fields
    ------
    request_id :        Unique request identifier.
    knowledge_id :      Knowledge workflow run identifier.
    subsystem_id :      Target subsystem identifier.
    workflow_type :     Knowledge workflow classification.
    priority :          Scheduling priority.
    context :           Engine-level operational context.
    inputs :            Collected enterprise snapshots and metadata.
                        Keys may include any of:
                        "execution_snapshot", "execution_recovery_snapshot",
                        "execution_analytics_snapshot", "decision_snapshot",
                        "portfolio_snapshot", "risk_snapshot",
                        "market_snapshot", "supervisor_snapshot",
                        "platform_metadata", "enterprise_events".
    sources_requested : List of source identifiers to collect from.
    requested_at :      Wall-clock request creation time.
    metadata :          Supplementary request metadata.
    framework_version : Framework version string.
    """
    request_id:        str
    knowledge_id:      str
    subsystem_id:      str
    workflow_type:     KnowledgeWorkflowType
    priority:          SchedulerPriority
    context:           KnowledgeEngineContext
    inputs:            Dict[str, Any] = field(default_factory=dict)
    sources_requested: List[str]      = field(default_factory=list)
    requested_at:      float          = field(default_factory=time.time)
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        knowledge_id:  str,
        subsystem_id:  str,
        workflow_type: KnowledgeWorkflowType  = KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
        *,
        request_id:        Optional[str]             = None,
        priority:          SchedulerPriority          = SchedulerPriority.NORMAL,
        context:           Optional[KnowledgeEngineContext] = None,
        scheduler_mode:    SchedulerMode              = SchedulerMode.CONTINUOUS,
        workflow_id:       str                       = "",
        actor:             str                       = "iios:system",
        inputs:            Optional[Dict[str, Any]]  = None,
        sources_requested: Optional[List[str]]       = None,
        metadata:          Optional[Dict[str, Any]]  = None,
    ) -> "KnowledgeRequest":
        rid = request_id or str(uuid.uuid4())
        ctx = context or KnowledgeEngineContext.create(
            knowledge_id,
            subsystem_id,
            workflow_type,
            priority       = priority,
            scheduler_mode = scheduler_mode,
            workflow_id    = workflow_id,
            actor          = actor,
            sources        = sources_requested,
        )
        return cls(
            request_id        = rid,
            knowledge_id      = knowledge_id,
            subsystem_id      = subsystem_id,
            workflow_type     = workflow_type,
            priority          = priority,
            context           = ctx,
            inputs            = inputs or {},
            sources_requested = list(sources_requested or []),
            metadata          = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "knowledge_id":      self.knowledge_id,
            "subsystem_id":      self.subsystem_id,
            "workflow_type":     self.workflow_type.value,
            "priority":          int(self.priority),
            "sources_requested": list(self.sources_requested),
            "requested_at":      self.requested_at,
        }
