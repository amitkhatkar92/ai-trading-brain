"""iios/decision_policies/rules/rule_registry.py"""
from __future__ import annotations

import threading

from ..policy_constants import MAX_POLICIES_IN_REGISTRY
from ..policy_exceptions import (
    RegistryOverflowError,
    RuleAlreadyExistsError,
    RuleNotFoundError,
)
from .rule import Rule
from .rule_group import RuleGroup


class RuleRegistry:
    """Thread-safe registry for Rule and RuleGroup instances."""

    def __init__(self) -> None:
        self._rules:  dict[str, Rule]      = {}
        self._groups: dict[str, RuleGroup] = {}
        self._lock    = threading.RLock()

    # ── Rules ──────────────────────────────────────────────────────────────

    def register_rule(self, rule: Rule, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and rule.rule_id in self._rules:
                raise RuleAlreadyExistsError(rule.rule_id)
            if len(self._rules) >= MAX_POLICIES_IN_REGISTRY:
                raise RegistryOverflowError(MAX_POLICIES_IN_REGISTRY)
            self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Rule:
        with self._lock:
            if rule_id not in self._rules:
                raise RuleNotFoundError(rule_id)
            return self._rules[rule_id]

    def has_rule(self, rule_id: str) -> bool:
        with self._lock:
            return rule_id in self._rules

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                return True
            return False

    def all_rules(self) -> list[Rule]:
        with self._lock:
            return list(self._rules.values())

    def rules_by_tag(self, tag: str) -> list[Rule]:
        with self._lock:
            return [r for r in self._rules.values() if tag in r.tags]

    # ── Groups ─────────────────────────────────────────────────────────────

    def register_group(self, group: RuleGroup, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and group.group_id in self._groups:
                raise RuleAlreadyExistsError(group.group_id)
            self._groups[group.group_id] = group

    def get_group(self, group_id: str) -> RuleGroup:
        with self._lock:
            if group_id not in self._groups:
                raise RuleNotFoundError(group_id)
            return self._groups[group_id]

    def has_group(self, group_id: str) -> bool:
        with self._lock:
            return group_id in self._groups

    def all_groups(self) -> list[RuleGroup]:
        with self._lock:
            return list(self._groups.values())

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_rules":  len(self._rules),
                "total_groups": len(self._groups),
            }


# ── Module-level singleton ────────────────────────────────────────────────────

_registry: RuleRegistry | None = None
_registry_lock = threading.Lock()


def get_rule_registry() -> RuleRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = RuleRegistry()
    return _registry


def reset_rule_registry() -> None:
    global _registry
    with _registry_lock:
        _registry = None
