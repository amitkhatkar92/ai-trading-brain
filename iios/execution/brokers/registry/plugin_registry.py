"""iios/execution/brokers/registry/plugin_registry.py

Discovers adapter classes from the adapters/ package at import time.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any

logger = logging.getLogger(__name__)

# Map of well-known broker_id → module name within iios.execution.brokers.adapters
_KNOWN_ADAPTERS: dict[str, str] = {
    "paper":                "paper_broker_adapter",
    "dhan":                 "dhan_adapter",
    "zerodha":              "zerodha_adapter",
    "angelone":             "angelone_adapter",
    "interactive_brokers":  "interactive_brokers_adapter",
    "alpaca":               "alpaca_adapter",
    "binance":              "binance_adapter",
}

_ADAPTER_PACKAGE = "iios.execution.brokers.adapters"


class PluginRegistry:
    """
    Discovers and loads adapter classes from the adapters/ subpackage.

    Usage:
        pr = PluginRegistry()
        cls = pr.load("dhan")
        adapter_registry.register("dhan", cls)
    """

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}    # broker_id → adapter class

    def discover_all(self) -> list[str]:
        """
        Attempt to import every known adapter module and return broker_ids
        that loaded successfully.
        """
        discovered = []
        for broker_id, module_name in _KNOWN_ADAPTERS.items():
            try:
                cls = self._load_from_module(module_name)
                self._discovered[broker_id] = cls
                discovered.append(broker_id)
            except Exception as exc:
                logger.debug(
                    "Plugin discovery skipped %s: %s", broker_id, exc
                )
        return discovered

    def load(self, broker_id: str) -> Any:  # type[BaseBrokerAdapter]
        """Load and return the adapter class for *broker_id*."""
        if broker_id in self._discovered:
            return self._discovered[broker_id]
        module_name = _KNOWN_ADAPTERS.get(broker_id)
        if module_name is None:
            raise ImportError(f"Unknown broker plugin '{broker_id}'")
        cls = self._load_from_module(module_name)
        self._discovered[broker_id] = cls
        return cls

    def load_custom(self, broker_id: str, full_class_path: str) -> Any:
        """
        Load an adapter class from a dotted import path, e.g.
        "mypackage.brokers.my_adapter.MyAdapter".
        """
        module_path, _, class_name = full_class_path.rpartition(".")
        module = importlib.import_module(module_path)
        cls    = getattr(module, class_name)
        self._discovered[broker_id] = cls
        return cls

    def known_broker_ids(self) -> list[str]:
        return list(_KNOWN_ADAPTERS.keys())

    def discovered_broker_ids(self) -> list[str]:
        return list(self._discovered.keys())

    @staticmethod
    def _load_from_module(module_name: str) -> Any:
        full = f"{_ADAPTER_PACKAGE}.{module_name}"
        module = importlib.import_module(full)
        # Convention: the adapter class is the only non-private class that
        # ends with "Adapter" in the module
        from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseBrokerAdapter)
                and obj is not BaseBrokerAdapter
            ):
                return obj
        raise ImportError(
            f"No BaseBrokerAdapter subclass found in module '{full}'"
        )
