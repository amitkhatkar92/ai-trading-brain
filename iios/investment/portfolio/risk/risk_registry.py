"""iios/investment/portfolio/risk/risk_registry.py
Stores named risk rules and limit sets that apply across portfolios.
"""
from __future__ import annotations

import threading
from typing import Any


class RiskRegistry:
    """Thread-safe registry for named risk rules and limit configs."""

    def __init__(self) -> None:
        self._lock:  threading.RLock       = threading.RLock()
        self._rules: dict[str, Any]        = {}
        self._limits: dict[str, Any]       = {}

    def register_rule(self, rule_id: str, rule: Any, *, overwrite: bool = False) -> None:
        with self._lock:
            if rule_id in self._rules and not overwrite:
                raise KeyError(f"Risk rule already registered: {rule_id!r}")
            self._rules[rule_id] = rule

    def get_rule(self, rule_id: str) -> Any:
        with self._lock:
            if rule_id not in self._rules:
                raise KeyError(f"Risk rule not found: {rule_id!r}")
            return self._rules[rule_id]

    def has_rule(self, rule_id: str) -> bool:
        with self._lock:
            return rule_id in self._rules

    def register_limits(self, limit_id: str, limits: Any, *, overwrite: bool = False) -> None:
        with self._lock:
            if limit_id in self._limits and not overwrite:
                raise KeyError(f"Risk limits already registered: {limit_id!r}")
            self._limits[limit_id] = limits

    def get_limits(self, limit_id: str) -> Any:
        with self._lock:
            if limit_id not in self._limits:
                raise KeyError(f"Risk limits not found: {limit_id!r}")
            return self._limits[limit_id]

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_rules":  len(self._rules),
                "registered_limits": len(self._limits),
            }
