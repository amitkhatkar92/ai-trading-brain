"""iios/execution/risk/rules/rule_factory.py
==================================================
RuleFactory — creates built-in rule instances with optional configuration.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from .base_rule import BaseRule
from .exceptions import RuleFrameworkError


# Registry of built-in rule classes by short name
_BUILTIN_REGISTRY: Dict[str, Type[BaseRule]] = {}


def _load_builtins() -> None:
    """Lazy-load built-in rule classes into _BUILTIN_REGISTRY."""
    if _BUILTIN_REGISTRY:
        return

    from .builtin import (
        ComplianceRule,
        DailyLossRule,
        DuplicateOrderRule,
        EmergencyStopRule,
        ExposureRule,
        LiquidityRule,
        MarginRule,
        OperationalHealthRule,
        OrderSizeRule,
        PositionLimitRule,
        PriceDeviationRule,
        SessionRule,
    )

    _BUILTIN_REGISTRY.update({
        "compliance":         ComplianceRule,
        "daily_loss":         DailyLossRule,
        "duplicate_order":    DuplicateOrderRule,
        "emergency_stop":     EmergencyStopRule,
        "exposure":           ExposureRule,
        "liquidity":          LiquidityRule,
        "margin":             MarginRule,
        "operational_health": OperationalHealthRule,
        "order_size":         OrderSizeRule,
        "position_limit":     PositionLimitRule,
        "price_deviation":    PriceDeviationRule,
        "session":            SessionRule,
    })


class RuleFactory:
    """
    Stateless factory for creating built-in and custom risk rules.

    Built-in rules can be created by name or via dedicated methods.
    Custom rules can be created by passing a class directly.
    """

    # ── Convenience constructors for each built-in ────────────────────────────

    @staticmethod
    def create_emergency_stop_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["emergency_stop"](**kw)

    @staticmethod
    def create_compliance_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["compliance"](**kw)

    @staticmethod
    def create_exposure_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["exposure"](**kw)

    @staticmethod
    def create_margin_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["margin"](**kw)

    @staticmethod
    def create_liquidity_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["liquidity"](**kw)

    @staticmethod
    def create_order_size_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["order_size"](**kw)

    @staticmethod
    def create_position_limit_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["position_limit"](**kw)

    @staticmethod
    def create_daily_loss_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["daily_loss"](**kw)

    @staticmethod
    def create_price_deviation_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["price_deviation"](**kw)

    @staticmethod
    def create_session_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["session"](**kw)

    @staticmethod
    def create_operational_health_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["operational_health"](**kw)

    @staticmethod
    def create_duplicate_order_rule(**kw) -> "BaseRule":
        _load_builtins()
        return _BUILTIN_REGISTRY["duplicate_order"](**kw)

    # ── Generic constructors ──────────────────────────────────────────────────

    @staticmethod
    def create_by_name(rule_name: str, **kw) -> "BaseRule":
        """Create a built-in rule by short name."""
        _load_builtins()
        cls = _BUILTIN_REGISTRY.get(rule_name)
        if cls is None:
            raise RuleFrameworkError(
                f"Unknown built-in rule '{rule_name}'. "
                f"Available: {sorted(_BUILTIN_REGISTRY)}"
            )
        return cls(**kw)

    @staticmethod
    def create_from_class(rule_class: Type["BaseRule"], **kw) -> "BaseRule":
        """Create a rule from an arbitrary BaseRule subclass."""
        if not issubclass(rule_class, BaseRule):
            raise RuleFrameworkError(
                f"'{rule_class}' is not a BaseRule subclass"
            )
        return rule_class(**kw)

    @staticmethod
    def create_all_builtin_rules(**kw) -> List["BaseRule"]:
        """
        Create one instance of every built-in rule with default configuration.

        Pass keyword arguments to override defaults for all rules that
        accept them (arguments are silently ignored by rules that don't).
        """
        _load_builtins()
        rules: List[BaseRule] = []
        for rule_class in _BUILTIN_REGISTRY.values():
            try:
                rules.append(rule_class(**kw))
            except TypeError:
                rules.append(rule_class())
        return rules

    @staticmethod
    def available_builtin_names() -> List[str]:
        """Return sorted list of available built-in rule names."""
        _load_builtins()
        return sorted(_BUILTIN_REGISTRY.keys())
