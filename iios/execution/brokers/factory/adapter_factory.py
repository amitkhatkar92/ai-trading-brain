"""iios/execution/brokers/factory/adapter_factory.py"""
from __future__ import annotations

import logging
from typing import Any

from iios.execution.brokers.broker_exceptions import AdapterLoadFailedError
from iios.execution.brokers.core.base_broker_adapter import (
    BaseBrokerAdapter,
    BrokerAdapterConfig,
)
from iios.execution.brokers.registry.adapter_registry import AdapterRegistry

logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    Creates BaseBrokerAdapter instances from registered adapter classes.

    The factory resolves the class from the AdapterRegistry and injects the
    BrokerAdapterConfig via the constructor.
    """

    def __init__(self, adapter_registry: AdapterRegistry) -> None:
        self._registry = adapter_registry

    def create(
        self,
        broker_id: str,
        config:    BrokerAdapterConfig | None = None,
        **kwargs:  Any,
    ) -> BaseBrokerAdapter:
        """
        Instantiate the adapter for *broker_id*.

        If *config* is None, a minimal BrokerAdapterConfig is constructed
        from *broker_id* and any *kwargs*.
        """
        adapter_class = self._registry.get_class(broker_id)
        if config is None:
            config = BrokerAdapterConfig(broker_id=broker_id, **kwargs)
        try:
            adapter = adapter_class(config)
            logger.info(
                "Created adapter %s (%s)",
                broker_id, adapter_class.__name__,
            )
            return adapter
        except Exception as exc:
            raise AdapterLoadFailedError(
                f"Failed to instantiate adapter '{broker_id}': {exc}",
                "BAF-021",
            ) from exc

    def create_with_defaults(self, broker_id: str) -> BaseBrokerAdapter:
        """Convenience: create with a default config."""
        return self.create(broker_id)
