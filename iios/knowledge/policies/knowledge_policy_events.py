"""
knowledge_policy_events.py — iios.knowledge.policies
------------------------------------------------------
GovernancePolicyEvent — immutable event emitted by the governance engine.
GovernancePolicyEventBus — thread-safe fan-out dispatcher.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import ACTOR_GOVERNANCE, GovernanceDecision, GovernanceEventType

_log = get_logger(__name__)


@dataclass(frozen=True)
class GovernancePolicyEvent:
    """
    Immutable event emitted by the governance policy engine.
    """
    event_id:     str
    event_type:   GovernanceEventType
    knowledge_id: str
    subsystem_id: str
    policy_id:    str
    decision:     Optional[GovernanceDecision]
    actor:        str
    reason:       str
    metadata:     Dict[str, Any]
    occurred_at:  str                  # ISO-8601

    @classmethod
    def create(
        cls,
        event_type:   GovernanceEventType,
        knowledge_id: str,
        subsystem_id: str,
        policy_id:    str,
        actor:        str = ACTOR_GOVERNANCE,
        *,
        decision:     Optional[GovernanceDecision] = None,
        reason:       str                          = "",
        metadata:     Optional[Dict[str, Any]]     = None,
    ) -> "GovernancePolicyEvent":
        return cls(
            event_id     = f"evt-{uuid.uuid4().hex[:12]}",
            event_type   = event_type,
            knowledge_id = knowledge_id,
            subsystem_id = subsystem_id,
            policy_id    = policy_id,
            decision     = decision,
            actor        = actor,
            reason       = reason,
            metadata     = dict(metadata or {}),
            occurred_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "knowledge_id": self.knowledge_id,
            "subsystem_id": self.subsystem_id,
            "policy_id":    self.policy_id,
            "decision":     self.decision.value if self.decision else None,
            "actor":        self.actor,
            "reason":       self.reason,
            "metadata":     self.metadata,
            "occurred_at":  self.occurred_at,
        }


# ---------------------------------------------------------------------------
# Factory functions — one per GovernanceEventType (9)
# ---------------------------------------------------------------------------

def make_policy_loaded(
    knowledge_id: str, subsystem_id: str, policy_id: str,
    actor: str = ACTOR_GOVERNANCE,
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.POLICY_LOADED, knowledge_id, subsystem_id, policy_id, actor,
    )


def make_policy_validated(
    knowledge_id: str, subsystem_id: str, policy_id: str,
    actor: str = ACTOR_GOVERNANCE,
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.POLICY_VALIDATED, knowledge_id, subsystem_id, policy_id, actor,
    )


def make_governance_started(
    knowledge_id: str, subsystem_id: str, policy_id: str = "",
    actor: str = ACTOR_GOVERNANCE,
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.GOVERNANCE_STARTED, knowledge_id, subsystem_id, policy_id, actor,
    )


def make_knowledge_approved(
    knowledge_id: str, subsystem_id: str, policy_id: str,
    actor: str = ACTOR_GOVERNANCE, reason: str = "",
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.KNOWLEDGE_APPROVED, knowledge_id, subsystem_id, policy_id, actor,
        decision=GovernanceDecision.APPROVED, reason=reason,
    )


def make_knowledge_rejected(
    knowledge_id: str, subsystem_id: str, policy_id: str,
    actor: str = ACTOR_GOVERNANCE, reason: str = "",
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.KNOWLEDGE_REJECTED, knowledge_id, subsystem_id, policy_id, actor,
        decision=GovernanceDecision.REJECTED, reason=reason,
    )


def make_knowledge_blocked(
    knowledge_id: str, subsystem_id: str, policy_id: str,
    actor: str = ACTOR_GOVERNANCE, reason: str = "",
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.KNOWLEDGE_BLOCKED, knowledge_id, subsystem_id, policy_id, actor,
        decision=GovernanceDecision.BLOCKED, reason=reason,
    )


def make_knowledge_escalated(
    knowledge_id: str, subsystem_id: str, policy_id: str,
    actor: str = ACTOR_GOVERNANCE, reason: str = "",
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.KNOWLEDGE_ESCALATED, knowledge_id, subsystem_id, policy_id, actor,
        decision=GovernanceDecision.ESCALATED, reason=reason,
    )


def make_review_requested(
    knowledge_id: str, subsystem_id: str, policy_id: str,
    actor: str = ACTOR_GOVERNANCE, reason: str = "",
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.REVIEW_REQUESTED, knowledge_id, subsystem_id, policy_id, actor,
        decision=GovernanceDecision.MANUAL_REVIEW, reason=reason,
    )


def make_governance_completed(
    knowledge_id: str,
    subsystem_id: str,
    policy_id:    str  = "",
    actor:        str  = ACTOR_GOVERNANCE,
    *,
    decision:     Optional[GovernanceDecision] = None,
    reason:       str  = "",
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent.create(
        GovernanceEventType.GOVERNANCE_COMPLETED, knowledge_id, subsystem_id, policy_id, actor,
        decision=decision, reason=reason,
    )


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


class GovernancePolicyEventBus:
    """
    Thread-safe fan-out event bus for governance policy events.

    Listeners are deduplicated by identity.
    Crashing listeners are isolated — other listeners still receive events.
    """

    def __init__(self) -> None:
        self._listeners: List[Callable[[GovernancePolicyEvent], None]] = []
        self._lock       = threading.Lock()

    def add_listener(self, fn: Callable[[GovernancePolicyEvent], None]) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[GovernancePolicyEvent], None]) -> bool:
        with self._lock:
            if fn in self._listeners:
                self._listeners.remove(fn)
                return True
            return False

    def emit(self, event: GovernancePolicyEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(f"Governance event listener error: {exc!r}")

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)
