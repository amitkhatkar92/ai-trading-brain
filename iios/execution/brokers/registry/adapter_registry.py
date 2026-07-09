"""iios/execution/brokers/registry/adapter_registry.py

Stores adapter CLASSES (types), not instances.  Think of this as the plugin
manifest: it knows which adapter classes exist and how to identify them.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Type

from iios.execution.brokers.broker_exceptions import (
    BrokerAlreadyExistsError,
    BrokerNotFoundError,
    BrokerRegistryOverflowError,
    InvalidAdapterError,
)
from iios.execution.brokers.broker_constants import DEFAULT_MAX_BROKERS

logger = logging.getLogger(__name__)


@dataclass
class AdapterEntry:
    """Registration record for a single adapter class."""

    broker_id:     str    = ""
    adapter_class: Any    = None     # type[BaseBrokerAdapter] — typed as Any to avoid circular
    version:       str    = "1.0.0"
    description:   str    = ""
    registered_at: float  = field(default_factory=time.time)
    entry_id:      str    = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:      dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":      self.entry_id,
            "broker_id":     self.broker_id,
            "adapter_class": self.adapter_class.__name__ if self.adapter_class else "",
            "version":       self.version,
            "description":   self.description,
            "registered_at": self.registered_at,
            "metadata":      self.metadata,
        }


class AdapterRegistry:
    """
    Registry of available adapter CLASSES.

    Supports registration, lookup, and version management.
    Thread-safe.
    """

    def __init__(self, max_adapters: int = DEFAULT_MAX_BROKERS) -> None:
        self._entries:      dict[str, AdapterEntry] = {}
        self._max_adapters  = max_adapters
        self._lock          = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        broker_id:     str,
        adapter_class: Any,   # type[BaseBrokerAdapter]
        version:       str  = "1.0.0",
        description:   str  = "",
        overwrite:     bool = False,
        metadata:      dict[str, Any] = {},
    ) -> AdapterEntry:
        # Validate that adapter_class is actually a subclass
        from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter
        if not (
            isinstance(adapter_class, type)
            and issubclass(adapter_class, BaseBrokerAdapter)
        ):
            raise InvalidAdapterError(
                f"'{adapter_class}' is not a subclass of BaseBrokerAdapter",
                "BAF-022",
            )
        with self._lock:
            if broker_id in self._entries and not overwrite:
                raise BrokerAlreadyExistsError(
                    f"Adapter '{broker_id}' already registered (use overwrite=True)",
                    "BAF-012",
                )
            if len(self._entries) >= self._max_adapters and broker_id not in self._entries:
                raise BrokerRegistryOverflowError(
                    f"AdapterRegistry capacity reached ({self._max_adapters})",
                    "BAF-081",
                )
            entry = AdapterEntry(
                broker_id=broker_id,
                adapter_class=adapter_class,
                version=version,
                description=description,
                metadata=dict(metadata),
            )
            self._entries[broker_id] = entry
            logger.debug(
                "Registered adapter %s v%s (%s)",
                broker_id, version, adapter_class.__name__,
            )
            return entry

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, broker_id: str) -> AdapterEntry:
        with self._lock:
            entry = self._entries.get(broker_id)
        if entry is None:
            raise BrokerNotFoundError(
                f"No adapter class registered for broker '{broker_id}'",
                "BAF-011",
            )
        return entry

    def get_class(self, broker_id: str) -> Any:  # type[BaseBrokerAdapter]
        return self.get(broker_id).adapter_class

    def has(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._entries

    def unregister(self, broker_id: str) -> None:
        with self._lock:
            removed = self._entries.pop(broker_id, None)
        if removed:
            logger.info("Unregistered adapter %s", broker_id)

    def all_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._entries.keys())

    def all_entries(self) -> list[AdapterEntry]:
        with self._lock:
            return list(self._entries.values())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_adapters": len(self._entries),
                "max_adapters":        self._max_adapters,
            }
