"""
iios/configuration/configuration_schema.py
============================================
Schema definitions for every configuration section.

A ``FieldSpec`` declares the expected type, optionality, default, and
validation rules for one configuration field. A ``SectionSchema`` groups
``FieldSpec`` objects for one configuration section. ``IIOS_SCHEMA``
aggregates all section schemas.

Validators are plain callables: ``(value) -> None`` — raise
``FieldValidationError`` on failure.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

from .configuration_exception import FieldValidationError

__all__ = [
    "FieldSpec",
    "SectionSchema",
    "IIOS_SCHEMA",
]


# ---------------------------------------------------------------------------
# Field specification
# ---------------------------------------------------------------------------


@dataclass
class FieldSpec:
    """Specification for a single configuration field."""

    name: str
    type: type
    required: bool = False
    default: Any = None
    description: str = ""
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[list[Any]] = None
    sensitive: bool = False       # Redact in logs
    invariant: bool = False       # Architecture constant — warn if changed
    validators: list[Callable[[Any], None]] = field(default_factory=list)

    def validate(self, value: Any, section: str = "") -> None:
        """Run all validation checks for ``value``. Raises ``FieldValidationError``."""
        # Type check
        if value is not None and not isinstance(value, self.type):
            try:
                # Attempt coercion
                value = self.type(value)
            except (TypeError, ValueError):
                raise FieldValidationError(
                    section, self.name,
                    f"expected {self.type.__name__}, got {type(value).__name__}",
                    value,
                )

        # Required check
        if self.required and (value is None or value == ""):
            raise FieldValidationError(section, self.name, "required field is missing")

        if value is None:
            return

        # Range check
        if self.min_value is not None and value < self.min_value:
            raise FieldValidationError(
                section, self.name,
                f"value {value!r} below minimum {self.min_value!r}",
                value,
            )
        if self.max_value is not None and value > self.max_value:
            raise FieldValidationError(
                section, self.name,
                f"value {value!r} above maximum {self.max_value!r}",
                value,
            )

        # Allowed values check
        if self.allowed_values is not None and value not in self.allowed_values:
            raise FieldValidationError(
                section, self.name,
                f"value {value!r} not in allowed values {self.allowed_values!r}",
                value,
            )

        # Custom validators
        for v in self.validators:
            v(value)


# ---------------------------------------------------------------------------
# Section schema
# ---------------------------------------------------------------------------


@dataclass
class SectionSchema:
    """Schema for one configuration section."""

    section: str
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    cross_validators: list[Callable[[dict[str, Any]], None]] = field(default_factory=list)

    def add_field(self, spec: FieldSpec) -> "SectionSchema":
        self.fields[spec.name] = spec
        return self

    def validate(self, data: dict[str, Any]) -> list[FieldValidationError]:
        """Validate ``data`` against this schema. Returns list of errors (empty = pass)."""
        errors: list[FieldValidationError] = []
        for name, spec in self.fields.items():
            value = data.get(name, spec.default)
            try:
                spec.validate(value, section=self.section)
            except FieldValidationError as exc:
                errors.append(exc)

        # Cross-section validators
        for xv in self.cross_validators:
            try:
                xv(data)
            except FieldValidationError as exc:
                errors.append(exc)

        return errors


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _pct_range(name: str) -> FieldSpec:
    """Create a [0.0, 1.0] percentage field."""
    return FieldSpec(name=name, type=float, min_value=0.0, max_value=1.0)


def _pos_float(name: str, max_val: Optional[float] = None) -> FieldSpec:
    return FieldSpec(name=name, type=float, min_value=0.0, max_value=max_val)


def _pos_int(name: str, max_val: Optional[int] = None) -> FieldSpec:
    return FieldSpec(name=name, type=int, min_value=0, max_value=max_val)


# ---------------------------------------------------------------------------
# IIOS Schema — all section schemas
# ---------------------------------------------------------------------------


def _build_system_schema() -> SectionSchema:
    s = SectionSchema("system")
    s.add_field(FieldSpec("env", str, allowed_values=["development", "testing", "production"]))
    s.add_field(FieldSpec("paper_trading", bool))
    s.add_field(FieldSpec("layers", int, invariant=True,
                          description="Must equal 17 (FC-RULE-001)",
                          min_value=17, max_value=17))
    s.add_field(FieldSpec("debug", bool))
    s.add_field(FieldSpec("timezone", str))
    s.add_field(FieldSpec("market", str, allowed_values=["NSE", "BSE", "NSE_BSE"]))
    s.add_field(FieldSpec("cycle_interval_seconds", float, min_value=10.0, max_value=3600.0))
    s.add_field(FieldSpec("startup_timeout_seconds", float, min_value=30.0))
    return s


def _build_database_schema() -> SectionSchema:
    s = SectionSchema("database")
    s.add_field(FieldSpec("path", str))
    s.add_field(FieldSpec("wal_mode", bool))
    s.add_field(FieldSpec("synchronous", str, allowed_values=["OFF", "NORMAL", "FULL", "EXTRA"]))
    s.add_field(_pos_int("cache_size_kb", max_val=512_000))
    s.add_field(FieldSpec("timeout_seconds", float, min_value=1.0, max_value=300.0))
    s.add_field(_pos_int("max_connections", max_val=100))
    s.add_field(FieldSpec("backup_enabled", bool))
    return s


def _build_decision_schema() -> SectionSchema:
    s = SectionSchema("decision")
    s.add_field(FieldSpec(
        "decision_threshold", float,
        invariant=True,
        description="Architecture constant FC-RULE-017 — certified value 6.5",
        min_value=0.0, max_value=10.0,
    ))
    s.add_field(FieldSpec(
        "debate_agents", int,
        invariant=True,
        description="Exactly 5 debate agents — architecture invariant",
        min_value=1, max_value=20,
    ))
    s.add_field(FieldSpec("debate_timeout_seconds", float, min_value=1.0, max_value=300.0))
    s.add_field(_pos_int("cooldown_seconds", max_val=3600))
    s.add_field(_pos_int("max_concurrent_decisions", max_val=100))
    return s


def _build_risk_schema() -> SectionSchema:
    s = SectionSchema("risk")
    s.add_field(FieldSpec(
        "vix_threshold", float,
        invariant=True,
        description="Architecture constant FC-RULE-018 — certified value 45.0",
        min_value=5.0, max_value=200.0,
    ))
    s.add_field(FieldSpec(
        "daily_loss_pct", float,
        invariant=True,
        description="Architecture constant FC-RULE-018 — certified value 0.02",
        min_value=0.001, max_value=0.20,
    ))
    s.add_field(_pct_range("max_risk_per_trade_pct"))
    s.add_field(_pct_range("kelly_fraction"))
    s.add_field(FieldSpec("atr_multiplier", float, min_value=0.5, max_value=10.0))
    s.add_field(_pct_range("max_portfolio_var_pct"))
    s.add_field(_pct_range("max_portfolio_cvar_pct"))
    s.add_field(_pct_range("max_drawdown_pct"))
    s.add_field(FieldSpec("max_correlation", float, min_value=0.0, max_value=1.0))
    return s


def _build_execution_schema() -> SectionSchema:
    s = SectionSchema("execution")
    s.add_field(FieldSpec("broker_primary", str, allowed_values=["dhan", "kiteconnect", "zerodha", "paper"]))
    s.add_field(FieldSpec("broker_fallback", str))
    s.add_field(FieldSpec("dhan_client_id", str, sensitive=True))
    s.add_field(FieldSpec("dhan_access_token", str, sensitive=True))
    s.add_field(FieldSpec("paper_trades_path", str))
    s.add_field(FieldSpec("live_trading_enabled", bool))
    s.add_field(FieldSpec("order_timeout_seconds", float, min_value=5.0, max_value=300.0))
    s.add_field(_pct_range("max_slippage_pct"))
    s.add_field(FieldSpec("use_limit_orders", bool))
    s.add_field(_pos_int("max_orders_per_minute", max_val=100))
    # Cross-validator: live trading requires credentials
    def _check_live_trading(data: dict[str, Any]) -> None:
        if data.get("live_trading_enabled") and not data.get("dhan_access_token"):
            raise FieldValidationError(
                "execution", "dhan_access_token",
                "live_trading_enabled=True requires dhan_access_token to be set",
            )
    s.cross_validators.append(_check_live_trading)
    return s


def _build_logging_schema() -> SectionSchema:
    s = SectionSchema("logging")
    s.add_field(FieldSpec("level", str,
                          allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]))
    s.add_field(FieldSpec("file", str))
    s.add_field(FieldSpec("console_enabled", bool))
    s.add_field(FieldSpec("file_enabled", bool))
    s.add_field(FieldSpec("sensitive_redaction", bool))
    return s


def _build_notification_schema() -> SectionSchema:
    s = SectionSchema("notification")
    s.add_field(FieldSpec("enabled", bool))
    s.add_field(FieldSpec("telegram_bot_token", str, sensitive=True))
    s.add_field(FieldSpec("telegram_chat_id", str, sensitive=True))
    s.add_field(_pos_int("rate_limit_per_minute", max_val=1000))
    # Cross-validator: enabled requires token
    def _check_telegram(data: dict[str, Any]) -> None:
        if data.get("enabled") and not data.get("telegram_bot_token"):
            raise FieldValidationError(
                "notification", "telegram_bot_token",
                "notification.enabled=True requires telegram_bot_token",
            )
    s.cross_validators.append(_check_telegram)
    return s


def _build_monitoring_schema() -> SectionSchema:
    s = SectionSchema("monitoring")
    s.add_field(FieldSpec("dashboard_enabled", bool))
    s.add_field(FieldSpec("streamlit_port", int, min_value=1024, max_value=65535))
    s.add_field(FieldSpec("telemetry_enabled", bool))
    s.add_field(_pos_int("metrics_interval_seconds", max_val=3600))
    return s


def _build_portfolio_schema() -> SectionSchema:
    s = SectionSchema("portfolio")
    s.add_field(FieldSpec("initial_capital", float, min_value=10_000.0))
    s.add_field(_pos_int("max_positions", max_val=100))
    s.add_field(_pct_range("max_sector_exposure_pct"))
    s.add_field(_pct_range("max_single_position_pct"))
    s.add_field(_pct_range("min_cash_reserve_pct"))
    return s


def _build_strategy_schema() -> SectionSchema:
    s = SectionSchema("strategy")
    s.add_field(_pos_int("max_active_strategies", max_val=100))
    s.add_field(FieldSpec("min_signal_rr_ratio", float, min_value=0.5, max_value=20.0))
    s.add_field(FieldSpec("evolution_enabled", bool))
    s.add_field(_pos_int("evolution_generations", max_val=10_000))
    s.add_field(FieldSpec("continuous_scan", bool))
    s.add_field(_pos_int("scan_interval_seconds", max_val=3600))
    return s


# ---------------------------------------------------------------------------
# Master schema registry
# ---------------------------------------------------------------------------


IIOS_SCHEMA: dict[str, SectionSchema] = {
    "system":         _build_system_schema(),
    "database":       _build_database_schema(),
    "decision":       _build_decision_schema(),
    "risk":           _build_risk_schema(),
    "execution":      _build_execution_schema(),
    "logging":        _build_logging_schema(),
    "notification":   _build_notification_schema(),
    "monitoring":     _build_monitoring_schema(),
    "portfolio":      _build_portfolio_schema(),
    "strategy":       _build_strategy_schema(),
}
