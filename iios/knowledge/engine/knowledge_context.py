"""
knowledge_context.py — iios.knowledge.engine
----------------------------------------------
Immutable engine-level operational context for knowledge workflows.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    ACTOR_SYSTEM,
    VERSION,
    KnowledgeSource,
    KnowledgeWorkflowType,
    SchedulerMode,
    SchedulerPriority,
)


@dataclass(frozen=True)
class KnowledgeEngineContext:
    """
    Immutable operational context accompanying each knowledge workflow request.

    Fields
    ------
    context_id :     Unique context identifier.
    knowledge_id :   Identifier for the knowledge workflow run.
    subsystem_id :   Target subsystem identifier.
    workflow_type :  Workflow classification.
    priority :       Scheduling priority.
    scheduler_mode : How the request was triggered.
    actor :          Identity that submitted the request.
    workflow_id :    Optional workflow or batch identifier.
    correlation_id : Optional cross-system correlation token.
    sources :        Enterprise sources targeted for collection.
    created_at :     Wall-clock context creation time.
    metadata :       Supplementary key-value metadata.
    framework_version : Framework version string.
    """
    context_id:       str
    knowledge_id:     str
    subsystem_id:     str
    workflow_type:    KnowledgeWorkflowType
    priority:         SchedulerPriority
    scheduler_mode:   SchedulerMode
    actor:            str
    workflow_id:      str              = ""
    correlation_id:   str              = ""
    sources:          List[str]        = field(default_factory=list)
    created_at:       float            = field(default_factory=time.time)
    metadata:         Dict[str, Any]   = field(default_factory=dict)
    framework_version: str             = VERSION

    @classmethod
    def create(
        cls,
        knowledge_id:   str,
        subsystem_id:   str,
        workflow_type:  KnowledgeWorkflowType  = KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
        *,
        context_id:     Optional[str]          = None,
        priority:       SchedulerPriority      = SchedulerPriority.NORMAL,
        scheduler_mode: SchedulerMode          = SchedulerMode.CONTINUOUS,
        actor:          str                    = ACTOR_SYSTEM,
        workflow_id:    str                    = "",
        correlation_id: str                    = "",
        sources:        Optional[List[str]]    = None,
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeEngineContext":
        return cls(
            context_id      = context_id or str(uuid.uuid4()),
            knowledge_id    = knowledge_id,
            subsystem_id    = subsystem_id,
            workflow_type   = workflow_type,
            priority        = priority,
            scheduler_mode  = scheduler_mode,
            actor           = actor,
            workflow_id     = workflow_id,
            correlation_id  = correlation_id,
            sources         = list(sources or []),
            metadata        = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":      self.context_id,
            "knowledge_id":    self.knowledge_id,
            "subsystem_id":    self.subsystem_id,
            "workflow_type":   self.workflow_type.value,
            "priority":        int(self.priority),
            "scheduler_mode":  self.scheduler_mode.value,
            "actor":           self.actor,
            "workflow_id":     self.workflow_id,
            "correlation_id":  self.correlation_id,
            "sources":         list(self.sources),
        }
