"""iios/execution/brokers/capabilities/capability_checker.py"""
from __future__ import annotations

from iios.execution.brokers.broker_constants import BrokerCapabilityType
from iios.execution.brokers.broker_exceptions import CapabilityNotSupportedError
from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter


class CapabilityChecker:
    """
    Validates that an adapter supports a required set of capabilities before
    a call is dispatched.
    """

    @staticmethod
    def check(
        adapter:  BaseBrokerAdapter,
        required: BrokerCapabilityType | list[BrokerCapabilityType],
    ) -> bool:
        """Return True if *adapter* supports all *required* capabilities."""
        caps = [required] if isinstance(required, BrokerCapabilityType) else required
        return all(adapter.supports(c) for c in caps)

    @staticmethod
    def assert_capability(
        adapter:    BaseBrokerAdapter,
        capability: BrokerCapabilityType,
    ) -> None:
        """Raise CapabilityNotSupportedError if *adapter* lacks *capability*."""
        if not adapter.supports(capability):
            raise CapabilityNotSupportedError(
                f"Broker '{adapter.broker_id}' does not support "
                f"capability '{capability.value}'",
                "BAF-041",
            )

    @staticmethod
    def assert_all(
        adapter:  BaseBrokerAdapter,
        required: list[BrokerCapabilityType],
    ) -> None:
        """Raise on the first missing capability."""
        for cap in required:
            CapabilityChecker.assert_capability(adapter, cap)
