"""iios/execution/oms/order_router/routing_validation.py
==================================================
RoutingValidator — validates RoutingRequest before routing begins.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

from typing import Any

from iios.execution.oms.order_router.constants import (
    ExecutionMode,
    RoutingValidationCode,
    VALIDATOR_SYSTEM_ID,
)
from iios.execution.oms.order_router.exceptions import RoutingValidationError
from iios.execution.oms.order_router.routing_context import BrokerCapabilities
from iios.execution.oms.order_router.routing_request import RoutingRequest


class RoutingValidator:
    """
    Validates a RoutingRequest for completeness and feasibility.

    Raises RoutingValidationError if any hard constraint is violated.
    validate() accumulates all errors and raises once at the end.
    """

    __slots__ = ("_system_id",)

    def __init__(self) -> None:
        self._system_id = VALIDATOR_SYSTEM_ID

    # ── Primary entry-point ───────────────────────────────────────────────────

    def validate(self, request: RoutingRequest) -> None:
        """
        Validate the request. Raises RoutingValidationError if invalid.
        """
        errors: list[str] = []

        if not request.order_id or not request.order_id.strip():
            errors.append(RoutingValidationCode.MISSING_ORDER_ID.value)

        if request.is_expired:
            errors.append(RoutingValidationCode.REQUEST_EXPIRED.value)

        if errors:
            raise RoutingValidationError(
                f"RoutingRequest validation failed: {', '.join(errors)}",
                errors=tuple(errors),
                context={"order_id": request.order_id},
            )

    def validate_capabilities(
        self,
        capabilities: BrokerCapabilities,
        request: RoutingRequest,
    ) -> list[str]:
        """
        Check whether a broker's capabilities satisfy the request.
        Returns list of failure codes (empty = all good).
        """
        failures: list[str] = []

        if not capabilities.is_available:
            failures.append(RoutingValidationCode.BROKER_UNAVAILABLE.value)

        if request.exchange and capabilities.supported_exchanges:
            if request.exchange not in capabilities.supported_exchanges:
                failures.append(RoutingValidationCode.EXCHANGE_UNSUPPORTED.value)

        if request.order_type and capabilities.supported_order_types:
            if request.order_type not in capabilities.supported_order_types:
                failures.append(RoutingValidationCode.ORDER_INCOMPATIBLE.value)

        if request.product_type and capabilities.supported_product_types:
            if request.product_type not in capabilities.supported_product_types:
                failures.append(RoutingValidationCode.PRODUCT_UNSUPPORTED.value)

        if capabilities.supported_execution_modes:
            if request.execution_mode not in capabilities.supported_execution_modes:
                failures.append(RoutingValidationCode.CAPABILITY_MISSING.value)

        return failures

    def validate_broker_available(self, capabilities: BrokerCapabilities) -> bool:
        return capabilities.is_available

    def validate_exchange_supported(
        self,
        capabilities: BrokerCapabilities,
        exchange: str,
    ) -> bool:
        if not exchange:
            return True
        if not capabilities.supported_exchanges:
            return True
        return exchange in capabilities.supported_exchanges

    def validate_order_type_compatible(
        self,
        capabilities: BrokerCapabilities,
        order_type: str,
    ) -> bool:
        if not order_type:
            return True
        if not capabilities.supported_order_types:
            return True
        return order_type in capabilities.supported_order_types

    def validate_execution_mode(
        self,
        capabilities: BrokerCapabilities,
        mode: ExecutionMode,
    ) -> bool:
        if not capabilities.supported_execution_modes:
            return True
        return mode in capabilities.supported_execution_modes
