"""iios/execution/risk/rules/rule_registry.py
==================================================
RuleRegistry — LifecycleAwareMixin storage for registered risk rules.

Thread-safe. Supports filtering by category, priority, and enabled state.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .base_rule import BaseRule
from .constants import DEFAULT_MAX_RULES, REGISTRY_SYSTEM_ID, VERSION
from .exceptions import (
    DuplicateRuleError,
    RuleNotFoundError,
    RuleNotRunningError,
    RuleRegistrationError,
    RuleValidationError,
)
from .rule_category import RuleCategory
from .rule_events import RuleEvent, make_rule_registered_event, make_rule_unregistered_event
from .rule_priority import RulePriority
from .rule_validation import RuleFrameworkValidator

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class RuleRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry of ``BaseRule`` instances.

    Rules must be registered before they can be executed by the
    ``RuleExecutor``.  Registration validates structural integrity.
    """

    def __init__(self, max_rules: int = DEFAULT_MAX_RULES) -> None:
        super().__init__()
        self._max        = max(1, max_rules)
        self._rules:     Dict[str, BaseRule] = {}
        self._events:    List[RuleEvent]     = []
        self._validator  = RuleFrameworkValidator()
        self._lock       = threading.RLock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RuleNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("RuleRegistry started.", max_rules=self._max)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("RuleRegistry stopped.", rule_count=len(self._rules))

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, rule: BaseRule) -> None:
        """
        Register *rule*.

        Raises
        ------
        RuleNotRunningError    Registry not started.
        RuleRegistrationError  Rule fails structural validation.
        DuplicateRuleError     Rule ID already exists.
        """
        self._assert_running()

        # Structural validation
        vr = self._validator.validate_rule(rule)
        if not vr.is_valid:
            raise RuleRegistrationError(
                f"Rule '{getattr(rule, 'rule_id', '?')}' failed validation: "
                + "; ".join(vr.errors),
                rule_id=getattr(rule, "rule_id", ""),
            )

        with self._lock:
            if len(self._rules) >= self._max:
                raise RuleRegistrationError(
                    f"Registry at capacity ({self._max})",
                    rule_id=rule.rule_id,
                )

            # Duplicate ID check
            vr_dup = self._validator.validate_unique_id(rule, list(self._rules))
            if not vr_dup.is_valid:
                raise DuplicateRuleError(rule.rule_id)

            self._rules[rule.rule_id] = rule
            event = make_rule_registered_event(
                rule.rule_id, rule.rule_name, rule.category().value
            )
            self._events.append(event)

        _log.info("Rule registered.", rule_id=rule.rule_id, rule_name=rule.rule_name)

    def deregister(self, rule_id: str) -> None:
        """Remove a rule from the registry."""
        self._assert_running()
        with self._lock:
            rule = self._rules.pop(rule_id, None)
            if rule is None:
                raise RuleNotFoundError(rule_id)
            event = make_rule_unregistered_event(
                rule.rule_id, rule.rule_name, rule.category().value
            )
            self._events.append(event)
        _log.info("Rule deregistered.", rule_id=rule_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, rule_id: str) -> Optional[BaseRule]:
        with self._lock:
            return self._rules.get(rule_id)

    def require(self, rule_id: str) -> BaseRule:
        rule = self.get(rule_id)
        if rule is None:
            raise RuleNotFoundError(rule_id)
        return rule

    def contains(self, rule_id: str) -> bool:
        with self._lock:
            return rule_id in self._rules

    def all(self) -> List[BaseRule]:
        with self._lock:
            return list(self._rules.values())

    def enabled(self) -> List[BaseRule]:
        with self._lock:
            return [r for r in self._rules.values() if r.enabled()]

    def disabled(self) -> List[BaseRule]:
        with self._lock:
            return [r for r in self._rules.values() if not r.enabled()]

    def by_category(self, category: RuleCategory) -> List[BaseRule]:
        with self._lock:
            return [r for r in self._rules.values() if r.category() == category]

    def by_priority(self, priority: int) -> List[BaseRule]:
        with self._lock:
            return [r for r in self._rules.values() if int(r.priority()) == priority]

    def ordered_by_priority(self) -> List[BaseRule]:
        """Return all rules sorted by priority descending (highest first)."""
        with self._lock:
            return sorted(
                self._rules.values(),
                key=lambda r: int(r.priority()),
                reverse=True,
            )

    def events(self) -> List[RuleEvent]:
        with self._lock:
            return list(self._events)

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._rules)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._rules) == 0
