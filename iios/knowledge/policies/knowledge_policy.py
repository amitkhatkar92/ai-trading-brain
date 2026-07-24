"""
knowledge_policy.py — iios.knowledge.policies
----------------------------------------------
KnowledgePolicy — mutable domain object representing a governance policy.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import ACTOR_GOVERNANCE, PolicyDomain, PolicyPriority, PolicyStatus, PolicyType
from .knowledge_policy_rule import PolicyRule


class KnowledgePolicy:
    """
    A versioned, auditable governance policy.

    Policies are mutable domain objects.  Their status advances through
    PENDING → ACTIVE → (INACTIVE | DEPRECATED | ARCHIVED).

    Only ACTIVE policies are evaluated by the governance engine.
    """

    def __init__(
        self,
        *,
        policy_id:   str                           = "",
        name:        str,
        description: str                           = "",
        policy_type: PolicyType,
        domain:      PolicyDomain,
        priority:    PolicyPriority                = PolicyPriority.MEDIUM,
        rules:       Optional[List[PolicyRule]]    = None,
        version:     str                           = "1.0",
        author:      str                           = ACTOR_GOVERNANCE,
        metadata:    Optional[Dict[str, Any]]      = None,
    ) -> None:
        self._policy_id   = policy_id or f"pol-{uuid.uuid4().hex[:12]}"
        self._name        = name
        self._description = description
        self._policy_type = policy_type
        self._domain      = domain
        self._priority    = priority
        self._rules:      List[PolicyRule] = list(rules or [])
        self._status      = PolicyStatus.PENDING
        self._version     = version
        self._author      = author
        self._metadata    = dict(metadata or {})
        self._created_at  = datetime.now(tz=timezone.utc).isoformat()
        self._updated_at  = self._created_at

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def policy_id(self) -> str:           return self._policy_id
    @property
    def name(self) -> str:                return self._name
    @property
    def description(self) -> str:         return self._description
    @property
    def policy_type(self) -> PolicyType:  return self._policy_type
    @property
    def domain(self) -> PolicyDomain:     return self._domain
    @property
    def priority(self) -> PolicyPriority: return self._priority
    @property
    def rules(self) -> List[PolicyRule]:  return list(self._rules)
    @property
    def status(self) -> PolicyStatus:     return self._status
    @property
    def version(self) -> str:             return self._version
    @property
    def author(self) -> str:              return self._author
    @property
    def metadata(self) -> Dict[str, Any]: return dict(self._metadata)
    @property
    def created_at(self) -> str:          return self._created_at
    @property
    def updated_at(self) -> str:          return self._updated_at
    @property
    def is_active(self) -> bool:          return self._status == PolicyStatus.ACTIVE
    @property
    def rule_count(self) -> int:          return len(self._rules)

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: PolicyRule) -> None:
        """Append a rule to this policy."""
        self._rules.append(rule)
        self._touch()

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if removed."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        if len(self._rules) < before:
            self._touch()
            return True
        return False

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def activate(self) -> None:
        self._status = PolicyStatus.ACTIVE
        self._touch()

    def deactivate(self) -> None:
        self._status = PolicyStatus.INACTIVE
        self._touch()

    def deprecate(self) -> None:
        self._status = PolicyStatus.DEPRECATED
        self._touch()

    def archive(self) -> None:
        self._status = PolicyStatus.ARCHIVED
        self._touch()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        self._updated_at = datetime.now(tz=timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":   self._policy_id,
            "name":        self._name,
            "description": self._description,
            "policy_type": self._policy_type.value,
            "domain":      self._domain.value,
            "priority":    self._priority.name,
            "rules":       [r.to_dict() for r in self._rules],
            "status":      self._status.value,
            "version":     self._version,
            "author":      self._author,
            "metadata":    self._metadata,
            "created_at":  self._created_at,
            "updated_at":  self._updated_at,
        }

    def __repr__(self) -> str:
        return (
            f"KnowledgePolicy(id={self._policy_id!r}, "
            f"name={self._name!r}, "
            f"type={self._policy_type.value!r}, "
            f"status={self._status.value!r})"
        )
