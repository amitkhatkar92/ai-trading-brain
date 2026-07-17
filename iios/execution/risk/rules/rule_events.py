"""iios/execution/risk/rules/rule_events.py
==================================================
RuleEvent — immutable domain events emitted by the Rules Framework.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import ACTOR_FRAMEWORK, RuleEventType, VERSION


@dataclass(frozen=True)
class RuleEvent:
    """Immutable domain event emitted by the rule framework lifecycle."""

    event_id:      str
    event_type:    RuleEventType
    rule_id:       str
    rule_name:     str
    evaluation_id: str
    category:      str    # RuleCategory.value, empty for framework events
    actor:         str
    occurred_at:   float
    version:       str = VERSION
    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "rule_id":       self.rule_id,
            "rule_name":     self.rule_name,
            "evaluation_id": self.evaluation_id,
            "category":      self.category,
            "actor":         self.actor,
            "occurred_at":   self.occurred_at,
            "version":       self.version,
            "metadata":      dict(self.metadata),
        }


def _make_event(
    event_type:    RuleEventType,
    rule_id:       str = "",
    rule_name:     str = "",
    evaluation_id: str = "",
    category:      str = "",
    actor:         str = ACTOR_FRAMEWORK,
    metadata:      Dict[str, Any] | None = None,
) -> RuleEvent:
    return RuleEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        rule_id=rule_id,
        rule_name=rule_name,
        evaluation_id=evaluation_id,
        category=category,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


def make_rule_registered_event(rule_id: str, rule_name: str, category: str = "", **kw) -> RuleEvent:
    return _make_event(RuleEventType.RULE_REGISTERED, rule_id=rule_id, rule_name=rule_name, category=category, **kw)


def make_rule_unregistered_event(rule_id: str, rule_name: str, category: str = "", **kw) -> RuleEvent:
    return _make_event(RuleEventType.RULE_UNREGISTERED, rule_id=rule_id, rule_name=rule_name, category=category, **kw)


def make_rule_started_event(rule_id: str, rule_name: str, evaluation_id: str, category: str = "", **kw) -> RuleEvent:
    return _make_event(RuleEventType.RULE_STARTED, rule_id=rule_id, rule_name=rule_name,
                       evaluation_id=evaluation_id, category=category, **kw)


def make_rule_completed_event(rule_id: str, rule_name: str, evaluation_id: str, outcome: str, **kw) -> RuleEvent:
    meta = {"outcome": outcome, **kw.pop("metadata", {})}
    return _make_event(RuleEventType.RULE_COMPLETED, rule_id=rule_id, rule_name=rule_name,
                       evaluation_id=evaluation_id, metadata=meta, **kw)


def make_rule_passed_event(rule_id: str, rule_name: str, evaluation_id: str, **kw) -> RuleEvent:
    return _make_event(RuleEventType.RULE_PASSED, rule_id=rule_id, rule_name=rule_name,
                       evaluation_id=evaluation_id, **kw)


def make_rule_warning_event(rule_id: str, rule_name: str, evaluation_id: str, **kw) -> RuleEvent:
    return _make_event(RuleEventType.RULE_WARNING, rule_id=rule_id, rule_name=rule_name,
                       evaluation_id=evaluation_id, **kw)


def make_rule_blocked_event(rule_id: str, rule_name: str, evaluation_id: str, **kw) -> RuleEvent:
    return _make_event(RuleEventType.RULE_BLOCKED, rule_id=rule_id, rule_name=rule_name,
                       evaluation_id=evaluation_id, **kw)


def make_rule_failed_event(rule_id: str, rule_name: str, evaluation_id: str, reason: str = "", **kw) -> RuleEvent:
    meta = {"reason": reason, **kw.pop("metadata", {})}
    return _make_event(RuleEventType.RULE_FAILED, rule_id=rule_id, rule_name=rule_name,
                       evaluation_id=evaluation_id, metadata=meta, **kw)
