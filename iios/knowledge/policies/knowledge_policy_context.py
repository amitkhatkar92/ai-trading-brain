"""
knowledge_policy_context.py — iios.knowledge.policies
-------------------------------------------------------
GovernancePolicyContext — immutable context for a governance evaluation.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import ACTOR_GOVERNANCE, PolicyDomain, PolicyPriority


@dataclass(frozen=True)
class GovernancePolicyContext:
    """
    Immutable context for a knowledge governance evaluation.

    Carries all contextual metadata needed by policy evaluators to make
    informed, reproducible, and auditable governance decisions.
    """
    context_id:     str
    knowledge_id:   str
    subsystem_id:   str
    policy_domains: tuple           # Tuple[PolicyDomain]
    actor:          str
    priority:       PolicyPriority
    classification: str
    workflow_type:  str
    metadata:       Dict[str, Any]
    created_at:     str             # ISO-8601

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        knowledge_id:   str,
        subsystem_id:   str,
        *,
        context_id:     str                  = "",
        actor:          str                  = ACTOR_GOVERNANCE,
        priority:       PolicyPriority       = PolicyPriority.MEDIUM,
        policy_domains: Optional[List[PolicyDomain]] = None,
        classification: str                  = "unclassified",
        workflow_type:  str                  = "",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "GovernancePolicyContext":
        return cls(
            context_id     = context_id or f"ctx-{uuid.uuid4().hex[:12]}",
            knowledge_id   = knowledge_id,
            subsystem_id   = subsystem_id,
            policy_domains = tuple(policy_domains or list(PolicyDomain)),
            actor          = actor,
            priority       = priority,
            classification = classification,
            workflow_type  = workflow_type,
            metadata       = dict(metadata or {}),
            created_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "knowledge_id":   self.knowledge_id,
            "subsystem_id":   self.subsystem_id,
            "policy_domains": [d.value for d in self.policy_domains],
            "actor":          self.actor,
            "priority":       self.priority.name,
            "classification": self.classification,
            "workflow_type":  self.workflow_type,
            "metadata":       self.metadata,
            "created_at":     self.created_at,
        }
