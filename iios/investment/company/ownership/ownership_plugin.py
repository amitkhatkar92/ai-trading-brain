"""iios/investment/company/ownership/ownership_plugin.py
Pluggable ownership analysis framework.
Supports custom jurisdiction standards, ESG ownership criteria,
institutional filing formats, and AI-assisted ownership analytics.
"""
from __future__ import annotations

import abc
import threading
from typing import Any, Dict, List, Optional


class OwnershipPlugin(abc.ABC):
    """
    Abstract base class for custom ownership analysis plugins.

    Plugins may implement:
    - Jurisdiction-specific ownership disclosure standards (SEBI, SEC 13F, FCA, ASX)
    - ESG governance ownership criteria
    - AI-assisted analysis of regulatory filings
    - Proprietary institutional quality scoring
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""

    @property
    def jurisdiction(self) -> str:
        """Jurisdiction code: 'IN' | 'US' | 'UK' | 'AU' | 'generic'."""
        return "generic"

    @property
    def priority(self) -> int:
        """Execution priority — higher runs last (can override earlier plugins)."""
        return 10

    @abc.abstractmethod
    def evaluate(self, inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate ownership from extracted inputs.

        Returns a dict with optional keys:
            'ownership_adjustments'  : Dict[str, float] — score adjustments
                Keys: 'promoter_stability', 'institutional_quality',
                      'insider_alignment', 'overall'
            'risk_adjustments'       : Dict[str, float]
            'alerts'                 : List[str]
            'explanation'            : List[str]

        Returns None if the plugin cannot process the inputs.
        """


class OwnershipPluginRegistry:
    """Thread-safe registry for OwnershipPlugin instances."""

    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._plugins: Dict[str, OwnershipPlugin] = {}

    def register(self, plugin: OwnershipPlugin) -> None:
        if not isinstance(plugin, OwnershipPlugin):
            raise TypeError(
                f"Expected OwnershipPlugin, got {type(plugin).__name__}"
            )
        with self._lock:
            if plugin.name in self._plugins:
                raise ValueError(
                    f"OwnershipPlugin '{plugin.name}' is already registered. "
                    "Unregister it first or use a unique name."
                )
            self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        with self._lock:
            self._plugins.pop(name, None)

    def run_all(self, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all registered plugins sorted by priority. Return non-None results."""
        with self._lock:
            plugins = sorted(self._plugins.values(), key=lambda p: p.priority)
        results: List[Dict[str, Any]] = []
        for plugin in plugins:
            try:
                result = plugin.evaluate(inputs)
                if result is not None:
                    results.append(result)
            except Exception:
                pass   # plugin failures must not crash the core engine
        return results

    def plugin_count(self) -> int:
        with self._lock:
            return len(self._plugins)

    def plugin_names(self) -> List[str]:
        with self._lock:
            return list(self._plugins.keys())
