"""iios/execution/gateway/brokers/broker_validation.py
==================================================
BrokerValidationResult and BrokerValidator — validation logic for
the Broker Abstraction Layer.

All methods return a BrokerValidationResult; none raise exceptions
directly.  Use raise_if_invalid() to convert a failed result into
a BrokerValidationError.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import BrokerCapability
from .exceptions import BrokerValidationError


# ── BrokerValidationResult ────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrokerValidationResult:
    """
    Immutable result of a validation check.

    ``is_valid`` is True only when ``errors`` is empty.
    """

    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":     self.is_valid,
            "errors":       list(self.errors),
            "warnings":     list(self.warnings),
            "validated_at": self.validated_at,
        }

    def __repr__(self) -> str:
        return (
            f"BrokerValidationResult("
            f"is_valid={self.is_valid}, "
            f"errors={list(self.errors)!r}"
            f")"
        )


def _result(errors: List[str], warnings: List[str]) -> BrokerValidationResult:
    return BrokerValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        validated_at=time.time(),
    )


# ── BrokerValidator ───────────────────────────────────────────────────────────

class BrokerValidator:
    """
    Stateless validator for Broker Abstraction Layer objects.

    All methods are pure functions that accept objects and return
    BrokerValidationResult instances.
    """

    # ── Interface compliance ──────────────────────────────────────────────────

    def validate_interface_compliance(
        self,
        broker: Any,
    ) -> BrokerValidationResult:
        """
        Verify that *broker* is a fully compliant BrokerInterface subclass.

        Checks:
        - Is it an instance of BrokerInterface.
        - Has non-empty broker_id.
        - Has non-empty broker_name.
        """
        from .broker_interface import BrokerInterface

        errors:   List[str] = []
        warnings: List[str] = []

        if not isinstance(broker, BrokerInterface):
            errors.append(
                f"{broker.__class__.__name__!r} does not implement BrokerInterface. "
                "Broker plugins must subclass BrokerInterface."
            )
            return _result(errors, warnings)

        try:
            bid = broker.broker_id
            if not bid:
                errors.append("broker_id must not be empty.")
        except Exception as exc:
            errors.append(f"broker_id raised an exception: {exc}")

        try:
            bname = broker.broker_name
            if not bname:
                errors.append("broker_name must not be empty.")
        except Exception as exc:
            errors.append(f"broker_name raised an exception: {exc}")

        return _result(errors, warnings)

    # ── Registration validation ───────────────────────────────────────────────

    def validate_registration(
        self,
        broker:             Any,
        existing_broker_ids: List[str],
        max_brokers:         int,
    ) -> BrokerValidationResult:
        """
        Validate a broker before registration.

        Checks:
        - Interface compliance.
        - Duplicate broker_id.
        - Registry capacity.
        """
        from .broker_interface import BrokerInterface

        errors:   List[str] = []
        warnings: List[str] = []

        compliance = self.validate_interface_compliance(broker)
        if not compliance.is_valid:
            errors.extend(compliance.errors)
            return _result(errors, warnings)

        if broker.broker_id in existing_broker_ids:
            errors.append(
                f"Broker '{broker.broker_id}' is already registered. "
                "Remove the existing registration first."
            )

        if len(existing_broker_ids) >= max_brokers:
            errors.append(
                f"Registry is at capacity ({max_brokers} brokers). "
                "Remove a broker before registering a new one."
            )

        return _result(errors, warnings)

    # ── Capability consistency ────────────────────────────────────────────────

    def validate_capability_consistency(
        self,
        broker: Any,
    ) -> BrokerValidationResult:
        """
        Validate the capability set returned by broker.capabilities()
        for internal consistency.

        Consistency rules:
        - MARGIN_TRADING requires at least one of: MIS, NRML.
        - BRACKET_ORDERS requires CASH_TRADING or MARGIN_TRADING.
        - COVER_ORDERS requires CASH_TRADING or MARGIN_TRADING.
        - GTT requires ORDER_MODIFICATION.
        """
        from .broker_capabilities import BrokerCapabilities

        errors:   List[str] = []
        warnings: List[str] = []

        try:
            caps: BrokerCapabilities = broker.capabilities()
        except Exception as exc:
            errors.append(f"capabilities() raised an exception: {exc}")
            return _result(errors, warnings)

        if caps.has(BrokerCapability.MARGIN_TRADING):
            if not caps.supports_any(BrokerCapability.MIS, BrokerCapability.NRML):
                warnings.append(
                    "MARGIN_TRADING is declared but neither MIS nor NRML is present."
                )

        if caps.has(BrokerCapability.BRACKET_ORDERS):
            if not caps.supports_any(
                BrokerCapability.CASH_TRADING, BrokerCapability.MARGIN_TRADING
            ):
                warnings.append(
                    "BRACKET_ORDERS declared without CASH_TRADING or MARGIN_TRADING."
                )

        if caps.has(BrokerCapability.COVER_ORDERS):
            if not caps.supports_any(
                BrokerCapability.CASH_TRADING, BrokerCapability.MARGIN_TRADING
            ):
                warnings.append(
                    "COVER_ORDERS declared without CASH_TRADING or MARGIN_TRADING."
                )

        if caps.has(BrokerCapability.GTT):
            if not caps.has(BrokerCapability.ORDER_MODIFICATION):
                warnings.append(
                    "GTT is declared but ORDER_MODIFICATION is absent; GTT requires modification support."
                )

        if not caps.has(BrokerCapability.ORDER_CANCELLATION):
            warnings.append(
                "ORDER_CANCELLATION is not declared; cancellation operations will fail."
            )

        return _result(errors, warnings)

    # ── Configuration validation ──────────────────────────────────────────────

    def validate_configuration(
        self,
        config: Any,
    ) -> BrokerValidationResult:
        """Validate a BrokerConfiguration object."""
        from .broker_configuration import BrokerConfiguration

        errors:   List[str] = []
        warnings: List[str] = []

        if not isinstance(config, BrokerConfiguration):
            errors.append(
                f"config must be a BrokerConfiguration instance, "
                f"got {type(config).__name__!r}."
            )
            return _result(errors, warnings)

        if not config.broker_id:
            errors.append("broker_id must not be empty.")
        if not config.broker_name:
            errors.append("broker_name must not be empty.")
        if config.environment not in ("live", "paper"):
            errors.append(
                f"environment must be 'live' or 'paper', got {config.environment!r}."
            )
        if config.timeout_secs <= 0:
            errors.append(f"timeout_secs must be > 0, got {config.timeout_secs}.")
        if config.max_reconnect_attempts < 0:
            errors.append(
                f"max_reconnect_attempts must be >= 0, got {config.max_reconnect_attempts}."
            )
        if config.max_retries < 0:
            errors.append(f"max_retries must be >= 0, got {config.max_retries}.")

        if config.environment == "live":
            warnings.append(
                "Broker is configured for live trading. "
                "Ensure risk controls are active before connecting."
            )

        return _result(errors, warnings)

    # ── Session validation ────────────────────────────────────────────────────

    def validate_session(
        self,
        session: Any,
    ) -> BrokerValidationResult:
        """Validate a BrokerSession is active and not expired."""
        from .broker_session import BrokerSession

        errors:   List[str] = []
        warnings: List[str] = []

        if not isinstance(session, BrokerSession):
            errors.append(
                f"session must be a BrokerSession instance, "
                f"got {type(session).__name__!r}."
            )
            return _result(errors, warnings)

        if session.is_expired:
            errors.append(
                f"Session for broker '{session.broker_id}' has expired. "
                "Call refresh_session() before submitting orders."
            )
        elif not session.is_authenticated:
            errors.append(
                f"Broker '{session.broker_id}' is not authenticated. "
                "Call authenticate() first."
            )
        elif session.seconds_until_expiry < 300:
            warnings.append(
                f"Session for broker '{session.broker_id}' expires in "
                f"{session.seconds_until_expiry:.0f} seconds. Consider refreshing."
            )

        return _result(errors, warnings)

    # ── Connection validation ─────────────────────────────────────────────────

    def validate_connection(
        self,
        connection: Any,
    ) -> BrokerValidationResult:
        """Validate a BrokerConnection is ready for operations."""
        from .broker_connection import BrokerConnection

        errors:   List[str] = []
        warnings: List[str] = []

        if not isinstance(connection, BrokerConnection):
            errors.append(
                f"connection must be a BrokerConnection instance, "
                f"got {type(connection).__name__!r}."
            )
            return _result(errors, warnings)

        if connection.is_terminal:
            errors.append(
                f"Connection for broker '{connection.broker_id}' is in a "
                f"terminal state ({connection.state.value}). Re-registration required."
            )
        elif not connection.is_connected:
            errors.append(
                f"Broker '{connection.broker_id}' is not connected "
                f"(state={connection.state.value}). Call connect() first."
            )
        elif not connection.is_ready:
            warnings.append(
                f"Broker '{connection.broker_id}' is connected but not fully ready "
                f"(state={connection.state.value})."
            )

        return _result(errors, warnings)

    # ── Raise helper ──────────────────────────────────────────────────────────

    def raise_if_invalid(
        self,
        result: BrokerValidationResult,
        context: str = "",
    ) -> None:
        """Raise BrokerValidationError when result is invalid."""
        if not result.is_valid:
            msg = "Broker validation failed."
            if context:
                msg = f"Broker validation failed [{context}]."
            raise BrokerValidationError(msg, result.errors)
