"""
knowledge_policy_request.py — iios.knowledge.policies
-------------------------------------------------------
KnowledgePolicyRequest — value object wrapping a governance evaluation request.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import ACTOR_GOVERNANCE, PolicyDomain, PolicyPriority, PolicyType
from .knowledge_policy_context import GovernancePolicyContext


@dataclass(frozen=True)
class KnowledgePolicyRequest:
    """
    Immutable request object for a knowledge governance evaluation.
    """
    request_id:     str
    knowledge_id:   str
    subsystem_id:   str
    policy_types:   tuple               # Tuple[PolicyType]
    policy_domains: tuple               # Tuple[PolicyDomain]
    actor:          str
    priority:       PolicyPriority
    context:        GovernancePolicyContext
    artifacts:      Dict[str, Any]      # knowledge artifacts to govern
    metadata:       Dict[str, Any]
    created_at:     str                 # ISO-8601

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        knowledge_id:   str,
        subsystem_id:   str,
        *,
        request_id:     str                           = "",
        actor:          str                           = ACTOR_GOVERNANCE,
        priority:       PolicyPriority                = PolicyPriority.MEDIUM,
        policy_types:   Optional[List[PolicyType]]    = None,
        policy_domains: Optional[List[PolicyDomain]]  = None,
        context:        Optional[GovernancePolicyContext] = None,
        artifacts:      Optional[Dict[str, Any]]      = None,
        metadata:       Optional[Dict[str, Any]]      = None,
    ) -> "KnowledgePolicyRequest":
        ctx = context or GovernancePolicyContext.create(
            knowledge_id   = knowledge_id,
            subsystem_id   = subsystem_id,
            actor          = actor,
            priority       = priority,
            policy_domains = policy_domains,
        )
        return cls(
            request_id     = request_id or f"req-{uuid.uuid4().hex[:12]}",
            knowledge_id   = knowledge_id,
            subsystem_id   = subsystem_id,
            policy_types   = tuple(policy_types or list(PolicyType)),
            policy_domains = tuple(policy_domains or list(PolicyDomain)),
            actor          = actor,
            priority       = priority,
            context        = ctx,
            artifacts      = dict(artifacts or {}),
            metadata       = dict(metadata or {}),
            created_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "knowledge_id":   self.knowledge_id,
            "subsystem_id":   self.subsystem_id,
            "policy_types":   [t.value for t in self.policy_types],
            "policy_domains": [d.value for d in self.policy_domains],
            "actor":          self.actor,
            "priority":       self.priority.name,
            "context":        self.context.to_dict(),
            "artifacts":      self.artifacts,
            "metadata":       self.metadata,
            "created_at":     self.created_at,
        }
