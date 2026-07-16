"""iios/execution/brokers/broker_validation.py
==================================================
BrokerValidator — stateless validation for broker registration,
requests, and responses.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from iios.execution.brokers.broker_request import BrokerRequest, OrderRequest
from iios.execution.brokers.broker_response import BrokerResponse
from iios.execution.brokers.broker_metadata import BrokerMetadata
from iios.execution.brokers.broker_capabilities import BrokerCapabilities
from iios.execution.brokers.constants import (
    BrokerConnectionState,
    BrokerValidationCode,
    Exchange,
    ProductType,
)
from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__, engine_id="iios:execution:brokers:validator")


# ── Validation result ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrokerValidationResult:
    """Outcome of a validation check."""

    passed:   bool
    errors:   tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(cls, *, warnings: tuple[str, ...] = ()) -> "BrokerValidationResult":
        return cls(passed=True, errors=(), warnings=warnings)

    @classmethod
    def fail(cls, *errors: str) -> "BrokerValidationResult":
        return cls(passed=False, errors=errors)

    def __bool__(self) -> bool:
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":   self.passed,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


# ── Validator ─────────────────────────────────────────────────────────────────

class BrokerValidator:
    """
    Stateless validator for broker registration, requests, and responses.

    Thread-safe (no mutable state).
    """

    # ── Metadata / registration ───────────────────────────────────────────────

    def validate_metadata(self, metadata: BrokerMetadata) -> BrokerValidationResult:
        """Validate broker metadata before registration."""
        errors: list[str] = []

        if not metadata.broker_id or not metadata.broker_id.strip():
            errors.append(
                f"[{BrokerValidationCode.MISSING_BROKER_ID.value}] "
                "broker_id must not be empty"
            )
        if not metadata.broker_name or not metadata.broker_name.strip():
            errors.append(
                f"[{BrokerValidationCode.MISSING_BROKER_NAME.value}] "
                "broker_name must not be empty"
            )

        if errors:
            return BrokerValidationResult.fail(*errors)
        return BrokerValidationResult.ok()

    # ── Request ───────────────────────────────────────────────────────────────

    def validate_request(
        self,
        request:          BrokerRequest,
        capabilities:     BrokerCapabilities | None = None,
        connection_state: BrokerConnectionState     = BrokerConnectionState.DISCONNECTED,
    ) -> BrokerValidationResult:
        """Validate a broker request."""
        errors:   list[str] = []
        warnings: list[str] = []

        if not request.request_id:
            errors.append(
                f"[{BrokerValidationCode.MISSING_REQUEST_ID.value}] "
                "request_id must not be empty"
            )
        if not request.broker_id:
            errors.append(
                f"[{BrokerValidationCode.MISSING_BROKER_ID.value}] "
                "broker_id must not be empty"
            )

        # Connection guard for non-health operations
        from iios.execution.brokers.constants import BrokerRequestType
        non_connection_types = {
            BrokerRequestType.ORDER,
            BrokerRequestType.MODIFY,
            BrokerRequestType.CANCEL,
            BrokerRequestType.POSITION,
            BrokerRequestType.BALANCE,
            BrokerRequestType.HEARTBEAT,
        }
        if (
            request.request_type in non_connection_types
            and connection_state != BrokerConnectionState.CONNECTED
        ):
            errors.append(
                f"[{BrokerValidationCode.BROKER_NOT_CONNECTED.value}] "
                "broker must be connected to perform this operation"
            )

        # Capability / exchange / product checks for order requests
        if isinstance(request, OrderRequest) and capabilities is not None:
            self._validate_order_request(request, capabilities, errors, warnings)

        if errors:
            return BrokerValidationResult.fail(*errors)
        return BrokerValidationResult.ok(warnings=tuple(warnings))

    def _validate_order_request(
        self,
        request:      "OrderRequest",
        capabilities: BrokerCapabilities,
        errors:       list[str],
        warnings:     list[str],
    ) -> None:
        from iios.execution.brokers.constants import BrokerCapabilityCode
        if not capabilities.has(request.capability):
            errors.append(
                f"[{BrokerValidationCode.UNSUPPORTED_CAPABILITY.value}] "
                f"Broker does not support capability '{request.capability.value}'"
            )
        if (
            request.exchange != Exchange.UNKNOWN
            and not capabilities.supports_exchange(request.exchange)
        ):
            errors.append(
                f"[{BrokerValidationCode.UNSUPPORTED_EXCHANGE.value}] "
                f"Broker does not support exchange '{request.exchange.value}'"
            )
        if (
            request.product != ProductType.UNKNOWN
            and not capabilities.supports_product(request.product)
        ):
            errors.append(
                f"[{BrokerValidationCode.UNSUPPORTED_PRODUCT.value}] "
                f"Broker does not support product '{request.product.value}'"
            )

    # ── Response ──────────────────────────────────────────────────────────────

    def validate_response(self, response: BrokerResponse) -> BrokerValidationResult:
        """Validate a broker response envelope."""
        errors: list[str] = []

        if not response.response_id:
            errors.append("[MISSING_RESPONSE_ID] response_id must not be empty")
        if not response.broker_id:
            errors.append(
                f"[{BrokerValidationCode.MISSING_BROKER_ID.value}] "
                "broker_id must not be empty in response"
            )

        if errors:
            return BrokerValidationResult.fail(*errors)
        return BrokerValidationResult.ok()

    # ── Capability check ──────────────────────────────────────────────────────

    def validate_capability(
        self,
        capabilities: BrokerCapabilities,
        metadata:     BrokerMetadata,
    ) -> BrokerValidationResult:
        """Check that the capabilities object is consistent with the metadata."""
        if capabilities.broker_id != metadata.broker_id:
            return BrokerValidationResult.fail(
                "[CAPABILITY_ID_MISMATCH] "
                "BrokerCapabilities.broker_id does not match BrokerMetadata.broker_id"
            )
        return BrokerValidationResult.ok()
