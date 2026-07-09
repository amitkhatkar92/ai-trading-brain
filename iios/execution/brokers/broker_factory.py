"""iios/execution/brokers/broker_factory.py"""
from __future__ import annotations

import logging
from typing import Any

from iios.execution.brokers.broker_exceptions import AdapterLoadFailedError
from iios.execution.brokers.core.base_broker_adapter import (
    BaseBrokerAdapter,
    BrokerAdapterConfig,
)
from iios.execution.brokers.models.broker_metadata import BrokerMetadata

logger = logging.getLogger(__name__)


class BrokerFactory:
    """
    Constructs adapter instances from metadata or config objects.

    Acts as a higher-level wrapper over AdapterFactory; also maintains
    a metadata catalogue for registered brokers.
    """

    def __init__(self) -> None:
        self._metadata: dict[str, BrokerMetadata]                       = {}
        self._classes:  dict[str, type[BaseBrokerAdapter]]              = {}

    # ── Class registration ────────────────────────────────────────────────────

    def register_class(
        self,
        broker_id:     str,
        adapter_class: type[BaseBrokerAdapter],
        metadata:      BrokerMetadata | None = None,
    ) -> None:
        self._classes[broker_id] = adapter_class
        if metadata:
            self._metadata[broker_id] = metadata
        logger.debug("BrokerFactory: registered class for '%s'", broker_id)

    # ── Creation ──────────────────────────────────────────────────────────────

    def create(
        self,
        broker_id: str,
        config:    BrokerAdapterConfig | None = None,
        **kwargs:  Any,
    ) -> BaseBrokerAdapter:
        adapter_class = self._classes.get(broker_id)
        if adapter_class is None:
            raise AdapterLoadFailedError(
                f"No class registered in BrokerFactory for '{broker_id}'",
                "BAF-021",
            )
        resolved_config = config or BrokerAdapterConfig(broker_id=broker_id, **kwargs)
        try:
            adapter = adapter_class(resolved_config)
            logger.info("BrokerFactory: created %s", broker_id)
            return adapter
        except Exception as exc:
            raise AdapterLoadFailedError(
                f"Failed to create adapter '{broker_id}': {exc}",
                "BAF-021",
            ) from exc

    # ── Metadata ──────────────────────────────────────────────────────────────

    def get_metadata(self, broker_id: str) -> BrokerMetadata | None:
        return self._metadata.get(broker_id)

    def all_metadata(self) -> list[BrokerMetadata]:
        return list(self._metadata.values())

    def has(self, broker_id: str) -> bool:
        return broker_id in self._classes

    def registered_broker_ids(self) -> list[str]:
        return list(self._classes.keys())
