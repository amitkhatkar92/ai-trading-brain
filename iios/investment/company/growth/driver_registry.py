"""iios/investment/company/growth/driver_registry.py
Plugin registry for growth driver analysis.
Supports external DriverPlugin registrations via GrowthIntelligenceEngine.register_driver_plugin().
"""
from __future__ import annotations

import abc
import threading
from typing import Any, Dict, List, Optional


class DriverPlugin(abc.ABC):
    """Abstract base class for custom growth driver plugins."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique plugin name (e.g. 'pricing_power_v2')."""

    @abc.abstractmethod
    def compute(self, inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyse growth drivers from extracted inputs.
        Returns a dict with optional keys:
            'detected_drivers' : List[str]
            'primary_driver'   : Optional[str]
            'scores'           : Dict[str, float]   (0-100 each)
            'explanation'      : List[str]
        Returns None if the plugin cannot determine anything.
        """


class DriverRegistry:
    """Thread-safe registry of DriverPlugin instances."""

    def __init__(self) -> None:
        self._lock:    threading.RLock = threading.RLock()
        self._plugins: Dict[str, DriverPlugin] = {}

    def register(self, plugin: DriverPlugin) -> None:
        if not isinstance(plugin, DriverPlugin):
            raise TypeError(f"Expected DriverPlugin, got {type(plugin).__name__}")
        with self._lock:
            self._plugins[plugin.name] = plugin

    def run_all(self, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all registered plugins and return their results (non-None only)."""
        with self._lock:
            plugins = list(self._plugins.values())
        results = []
        for p in plugins:
            try:
                r = p.compute(inputs)
                if r is not None:
                    results.append(r)
            except Exception:
                pass  # plugin failures never break the core engine
        return results

    def plugin_count(self) -> int:
        with self._lock:
            return len(self._plugins)
