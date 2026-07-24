"""
knowledge_policy_audit.py — iios.knowledge.policies
-----------------------------------------------------
Auditable trail of all knowledge governance decisions.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_AUDIT_ENTRIES, GovernanceDecision

_log = get_logger(__name__)


@dataclass(frozen=True)
class PolicyAuditEntry:
    """Immutable record of a single governance evaluation decision."""
    audit_id:        str
    knowledge_id:    str
    subsystem_id:    str
    policy_id:       str
    policy_name:     str
    decision:        GovernanceDecision
    actor:           str
    reason:          str
    evaluation_ms:   float
    artifacts_count: int
    created_at:      str              # ISO-8601

    @classmethod
    def create(
        cls,
        *,
        knowledge_id:    str,
        subsystem_id:    str,
        policy_id:       str,
        policy_name:     str,
        decision:        GovernanceDecision,
        actor:           str,
        reason:          str   = "",
        evaluation_ms:   float = 0.0,
        artifacts_count: int   = 0,
    ) -> "PolicyAuditEntry":
        return cls(
            audit_id        = f"aud-{uuid.uuid4().hex[:12]}",
            knowledge_id    = knowledge_id,
            subsystem_id    = subsystem_id,
            policy_id       = policy_id,
            policy_name     = policy_name,
            decision        = decision,
            actor           = actor,
            reason          = reason,
            evaluation_ms   = evaluation_ms,
            artifacts_count = artifacts_count,
            created_at      = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id":        self.audit_id,
            "knowledge_id":    self.knowledge_id,
            "subsystem_id":    self.subsystem_id,
            "policy_id":       self.policy_id,
            "policy_name":     self.policy_name,
            "decision":        self.decision.value,
            "actor":           self.actor,
            "reason":          self.reason,
            "evaluation_ms":   self.evaluation_ms,
            "artifacts_count": self.artifacts_count,
            "created_at":      self.created_at,
        }


class KnowledgePolicyAudit:
    """
    Thread-safe, bounded audit log of governance decisions.

    Oldest entries are evicted when capacity is reached.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_AUDIT_ENTRIES) -> None:
        self._max_entries = max_entries
        self._entries:    List[PolicyAuditEntry] = []
        self._lock        = threading.Lock()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, entry: PolicyAuditEntry) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                self._entries.pop(0)
            self._entries.append(entry)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def all(self) -> List[PolicyAuditEntry]:
        with self._lock:
            return list(self._entries)

    def recent(self, n: int = 100) -> List[PolicyAuditEntry]:
        with self._lock:
            return list(self._entries[-n:])

    def for_knowledge_id(self, knowledge_id: str) -> List[PolicyAuditEntry]:
        with self._lock:
            return [e for e in self._entries if e.knowledge_id == knowledge_id]

    def for_policy_id(self, policy_id: str) -> List[PolicyAuditEntry]:
        with self._lock:
            return [e for e in self._entries if e.policy_id == policy_id]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def summary(self) -> Dict[str, int]:
        """Return count of entries by decision value."""
        with self._lock:
            counts: Dict[str, int] = defaultdict(int)
            for e in self._entries:
                counts[e.decision.value] += 1
            return dict(counts)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
