"""iios/investment/portfolio/core/parameter_registry.py

Parameter definition registry for the Institutional Portfolio Framework.
Parameters are typed, bounded, and self-documenting definitions that
drive the configuration engine and validation layer.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, FrozenSet, Optional


class ParameterType(str, Enum):
    """Supported parameter value types."""

    STRING   = "string"
    INTEGER  = "integer"
    FLOAT    = "float"
    BOOLEAN  = "boolean"
    ENUM     = "enum"
    LIST     = "list"
    DICT     = "dict"


@dataclass(frozen=True)
class ParameterDefinition:
    """
    Self-describing parameter definition.

    Contains type information, default value, valid range, and any
    custom validation callable.  Used by the configuration engine to
    build and validate configuration objects.
    """

    name:          str
    param_type:    ParameterType
    default:       Any                 = None
    required:      bool                = False
    description:   str                 = ""
    section:       str                 = ""           # e.g. "capital_limits", "risk_policy"

    # Numeric bounds (for FLOAT / INTEGER)
    min_value:     Optional[float]     = None
    max_value:     Optional[float]     = None

    # String constraints
    min_length:    Optional[int]       = None
    max_length:    Optional[int]       = None

    # Enum constraints (valid string values)
    allowed_values: FrozenSet[str]     = field(default_factory=frozenset)

    # List / collection constraints
    min_items:     Optional[int]       = None
    max_items:     Optional[int]       = None

    # Custom validator: called with (value) → raises ValueError on failure
    validator:     Optional[Callable[[Any], None]] = field(default=None, compare=False, hash=False)

    # Whether zero is allowed for numeric types
    allow_zero:    bool                = True

    def coerce(self, value: Any) -> Any:
        """Coerce a raw value to the expected Python type."""
        if value is None:
            return self.default
        if self.param_type == ParameterType.INTEGER:
            return int(value)
        if self.param_type == ParameterType.FLOAT:
            return float(value)
        if self.param_type == ParameterType.BOOLEAN:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        if self.param_type == ParameterType.STRING:
            return str(value)
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":          self.name,
            "param_type":    self.param_type.value,
            "default":       self.default,
            "required":      self.required,
            "description":   self.description,
            "section":       self.section,
            "min_value":     self.min_value,
            "max_value":     self.max_value,
            "allowed_values":sorted(self.allowed_values),
            "allow_zero":    self.allow_zero,
        }


class ParameterRegistry:
    """
    Thread-safe, per-domain registry of parameter definitions.

    Provides: register, get, list, by-section lookups.
    """

    def __init__(self) -> None:
        self._lock:   threading.RLock                    = threading.RLock()
        self._params: dict[str, ParameterDefinition]     = {}
        self._register_built_ins()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, defn: ParameterDefinition, *, overwrite: bool = False) -> None:
        with self._lock:
            if defn.name in self._params and not overwrite:
                raise ValueError(f"Parameter already registered: {defn.name!r}")
            self._params[defn.name] = defn

    def get(self, name: str) -> ParameterDefinition:
        with self._lock:
            if name not in self._params:
                raise KeyError(f"Unknown parameter: {name!r}")
            return self._params[name]

    def all_names(self) -> list[str]:
        with self._lock:
            return sorted(self._params.keys())

    def by_section(self, section: str) -> list[ParameterDefinition]:
        with self._lock:
            return [p for p in self._params.values() if p.section == section]

    def required_params(self) -> list[ParameterDefinition]:
        with self._lock:
            return [p for p in self._params.values() if p.required]

    def count(self) -> int:
        with self._lock:
            return len(self._params)

    # ------------------------------------------------------------------
    # Built-in parameter definitions for standard portfolio config
    # ------------------------------------------------------------------

    def _register_built_ins(self) -> None:
        defs = [
            # ── Capital Limits ──────────────────────────────────────────
            ParameterDefinition(
                name="initial_capital", param_type=ParameterType.FLOAT,
                default=100_000.0, required=False, section="capital_limits",
                min_value=0.0, description="Initial capital in base currency",
            ),
            ParameterDefinition(
                name="min_capital", param_type=ParameterType.FLOAT,
                default=0.0, required=False, section="capital_limits",
                min_value=0.0, description="Minimum capital floor",
            ),
            ParameterDefinition(
                name="max_capital", param_type=ParameterType.FLOAT,
                default=1e12, required=False, section="capital_limits",
                min_value=1.0, description="Maximum capital ceiling",
            ),
            ParameterDefinition(
                name="min_cash_reserve_pct", param_type=ParameterType.FLOAT,
                default=0.02, required=False, section="capital_limits",
                min_value=0.0, max_value=1.0,
                description="Minimum cash reserve as a fraction of NAV",
            ),
            ParameterDefinition(
                name="allow_leverage", param_type=ParameterType.BOOLEAN,
                default=False, required=False, section="capital_limits",
                description="Whether leverage is permitted",
            ),
            ParameterDefinition(
                name="max_leverage_ratio", param_type=ParameterType.FLOAT,
                default=1.0, required=False, section="capital_limits",
                min_value=1.0, max_value=10.0,
                description="Maximum gross leverage ratio",
            ),

            # ── Allocation Policy ───────────────────────────────────────
            ParameterDefinition(
                name="max_single_position_pct", param_type=ParameterType.FLOAT,
                default=0.10, required=False, section="allocation_policy",
                min_value=0.001, max_value=1.0,
                description="Max weight of a single position as fraction of NAV",
            ),
            ParameterDefinition(
                name="max_sector_pct", param_type=ParameterType.FLOAT,
                default=0.30, required=False, section="allocation_policy",
                min_value=0.0, max_value=1.0,
                description="Max weight of any single sector",
            ),
            ParameterDefinition(
                name="min_positions", param_type=ParameterType.INTEGER,
                default=3, required=False, section="allocation_policy",
                min_value=1, description="Minimum number of positions",
            ),
            ParameterDefinition(
                name="max_positions", param_type=ParameterType.INTEGER,
                default=100, required=False, section="allocation_policy",
                min_value=1, max_value=10_000,
                description="Maximum number of open positions",
            ),

            # ── Risk Policy ─────────────────────────────────────────────
            ParameterDefinition(
                name="max_drawdown_pct", param_type=ParameterType.FLOAT,
                default=0.20, required=False, section="risk_policy",
                min_value=0.001, max_value=1.0,
                description="Maximum drawdown tolerance",
            ),
            ParameterDefinition(
                name="max_daily_loss_pct", param_type=ParameterType.FLOAT,
                default=0.03, required=False, section="risk_policy",
                min_value=0.001, max_value=1.0,
                description="Maximum intraday loss tolerance",
            ),

            # ── Rebalancing Policy ──────────────────────────────────────
            ParameterDefinition(
                name="rebalance_trigger", param_type=ParameterType.ENUM,
                default="calendar", required=False, section="rebalancing_policy",
                allowed_values=frozenset({"calendar", "drift", "signal", "manual"}),
                description="What triggers a portfolio rebalance",
            ),
            ParameterDefinition(
                name="rebalance_frequency_days", param_type=ParameterType.INTEGER,
                default=30, required=False, section="rebalancing_policy",
                min_value=1, description="Rebalance frequency for calendar trigger",
            ),

            # ── Environment ─────────────────────────────────────────────
            ParameterDefinition(
                name="environment", param_type=ParameterType.ENUM,
                default="production", required=False, section="framework",
                allowed_values=frozenset({"production", "paper", "backtest", "simulation"}),
                description="Deployment environment",
            ),
        ]
        for d in defs:
            self._params[d.name] = d


# Module-level shared registry
PARAMETER_REGISTRY = ParameterRegistry()
