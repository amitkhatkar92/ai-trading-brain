"""
knowledge_intelligence_request.py — iios.knowledge.intelligence
-----------------------------------------------------------------
KnowledgeIntelligenceRequest — entry point value object.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import IntelligenceWorkflowType
from .knowledge_intelligence_context import KnowledgeIntelligenceContext


@dataclass(frozen=True)
class KnowledgeIntelligenceRequest:
    """
    Input payload for a knowledge intelligence processing cycle.

    artifacts      — list of knowledge artifact dicts (must each have 'artifact_id')
    governance_result — optional raw dict from the M3 governance engine
    context        — execution context
    """
    request_id:       str
    knowledge_id:     str
    subsystem_id:     str
    workflow_type:    IntelligenceWorkflowType
    artifacts:        tuple                     # Tuple[Dict[str, Any]]
    governance_result: Optional[Dict[str, Any]]
    context:          KnowledgeIntelligenceContext
    created_at:       str                       # ISO-8601

    @classmethod
    def create(
        cls,
        knowledge_id:     str,
        subsystem_id:     str,
        artifacts:        List[Dict[str, Any]],
        *,
        workflow_type:    IntelligenceWorkflowType = IntelligenceWorkflowType.FULL_INTELLIGENCE,
        governance_result: Optional[Dict[str, Any]] = None,
        context:          Optional[KnowledgeIntelligenceContext] = None,
        request_id:       str = "",
    ) -> "KnowledgeIntelligenceRequest":
        ctx = context or KnowledgeIntelligenceContext.create(
            subsystem_id  = subsystem_id,
            workflow_type = workflow_type,
        )
        return cls(
            request_id        = request_id or f"req-{uuid.uuid4().hex[:12]}",
            knowledge_id      = knowledge_id,
            subsystem_id      = subsystem_id,
            workflow_type     = workflow_type,
            artifacts         = tuple(artifacts),
            governance_result = governance_result,
            context           = ctx,
            created_at        = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":       self.request_id,
            "knowledge_id":     self.knowledge_id,
            "subsystem_id":     self.subsystem_id,
            "workflow_type":    self.workflow_type.value,
            "artifact_count":   len(self.artifacts),
            "context":          self.context.to_dict(),
            "created_at":       self.created_at,
        }
