"""
iios/observation/validators/validation_registry.py
===================================================
RuleRegistry — thread-safe store for validation rules.

Provides lookup by name, category, and pipeline stage.
Supports custom rules alongside the built-in defaults.
"""
from __future__ import annotations

import threading
from typing import Optional

from .validation_constants import RuleCategory, ValidationStage
from .validation_exceptions import ValidationRegistryError
from .validation_rules import ValidationRule, DEFAULT_RULES

__all__ = [
    "RuleRegistry",
    "get_rule_registry",
    "reset_rule_registry",
]

_lock:     threading.Lock                  = threading.Lock()
_registry: Optional["RuleRegistry"]        = None


class RuleRegistry:
    """Thread-safe registry of validation rules.

    Rules are stored by name.  A rule name must be unique unless
    ``overwrite=True`` is passed to :meth:`register`.
    """

    def __init__(self) -> None:
        self._rules: dict[str, ValidationRule] = {}
        self._lock  = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, rule: ValidationRule, overwrite: bool = False) -> None:
        """Add *rule* to the registry."""
        with self._lock:
            if rule.name in self._rules and not overwrite:
                raise ValidationRegistryError(
                    f"Rule {rule.name!r} is already registered; pass overwrite=True to replace it"
                )
            self._rules[rule.name] = rule

    def register_many(self, rules: list[ValidationRule], overwrite: bool = False) -> None:
        for r in rules:
            self.register(r, overwrite=overwrite)

    def unregister(self, name: str) -> None:
        """Remove the rule with the given *name*."""
        with self._lock:
            if name not in self._rules:
                raise ValidationRegistryError(f"Rule {name!r} not found in registry")
            del self._rules[name]

    def register_defaults(self, overwrite: bool = False) -> None:
        """Register all built-in rules."""
        self.register_many(DEFAULT_RULES(), overwrite=overwrite)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, name: str) -> ValidationRule:
        with self._lock:
            if name not in self._rules:
                raise ValidationRegistryError(f"Rule {name!r} not found")
            return self._rules[name]

    def get_or_none(self, name: str) -> Optional[ValidationRule]:
        with self._lock:
            return self._rules.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._rules

    def all(self) -> list[ValidationRule]:
        with self._lock:
            return list(self._rules.values())

    def enabled(self) -> list[ValidationRule]:
        with self._lock:
            return [r for r in self._rules.values() if r.enabled]

    def by_category(self, category: RuleCategory) -> list[ValidationRule]:
        with self._lock:
            return [r for r in self._rules.values() if r.category == category]

    def by_stage(self, stage: ValidationStage) -> list[ValidationRule]:
        with self._lock:
            return [r for r in self._rules.values() if r.stage == stage and r.enabled]

    # ── Bulk operations ───────────────────────────────────────────────────────

    def enable(self, name: str) -> None:
        self.get(name).enabled = True

    def disable(self, name: str) -> None:
        self.get(name).enabled = False

    def clear(self) -> None:
        with self._lock:
            self._rules.clear()

    # ── Introspection ─────────────────────────────────────────────────────────

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._rules.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._rules)

    def count_by_stage(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {s.value: 0 for s in ValidationStage}
            for r in self._rules.values():
                if r.enabled:
                    counts[r.stage.value] += 1
            return counts

    def summary(self) -> dict[str, object]:
        with self._lock:
            return {
                "total":        len(self._rules),
                "enabled":      sum(1 for r in self._rules.values() if r.enabled),
                "by_stage":     self.count_by_stage(),
                "rule_names":   sorted(self._rules.keys()),
            }

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def __iter__(self):
        return iter(self.all())


# ── Singletons ────────────────────────────────────────────────────────────────

def get_rule_registry() -> RuleRegistry:
    """Return the global :class:`RuleRegistry`, creating and seeding it if needed."""
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = RuleRegistry()
                _registry.register_defaults()
    return _registry


def reset_rule_registry() -> None:
    """Reset the global registry (use in tests)."""
    global _registry
    with _lock:
        _registry = None
