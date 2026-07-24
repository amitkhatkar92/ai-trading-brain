"""
knowledge_intelligence_context.py — iios.knowledge.intelligence
----------------------------------------------------------------
Execution context injected into an intelligence workflow.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import IntelligenceWorkflowType


@dataclass(frozen=True)
class KnowledgeIntelligenceContext:
    """Contextual metadata accompanying an intelligence processing request."""
    context_id:    str
    subsystem_id:  str
    workflow_type: IntelligenceWorkflowType
    priority:      int               # 0 = normal, 100 = highest
    metadata:      Dict[str, Any]
    created_at:    str               # ISO-8601

    @classmethod
    def create(
        cls,
        subsystem_id:  str,
        workflow_type: IntelligenceWorkflowType = IntelligenceWorkflowType.FULL_INTELLIGENCE,
        *,
        priority: int           = 0,
        metadata: Dict[str, Any] = None,
    ) -> "KnowledgeIntelligenceContext":
        return cls(
            context_id    = f"ctx-{uuid.uuid4().hex[:10]}",
            subsystem_id  = subsystem_id,
            workflow_type = workflow_type,
            priority      = priority,
            metadata      = dict(metadata or {}),
            created_at    = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":    self.context_id,
            "subsystem_id":  self.subsystem_id,
            "workflow_type": self.workflow_type.value,
            "priority":      self.priority,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }
