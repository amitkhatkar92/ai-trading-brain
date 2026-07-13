"""iios/investment/company/governance/governance_plugin.py
Pluggable governance assessment framework.
Supports custom governance standards, ESG frameworks, and AI-assisted qualitative analysis.
"""
from __future__ import annotations

import abc
import threading
from typing import Any, Dict, List, Optional


class GovernancePlugin(abc.ABC):
    """
    Abstract base class for custom governance assessment plugins.

    Plugins can implement jurisdiction-specific standards (SEBI, SEC, FCA),
    ESG governance criteria, proxy advisory methodologies, or AI-assisted
    qualitative analysis of annual reports and proxy statements.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique plugin name (e.g. 'sebi_listing_obligations_v2')."""

    @property
    def standard(self) -> str:
        """Governance standard: 'sebi' | 'sec' | 'fca' | 'asx' | 'generic'."""
        return "generic"

    @property
    def priority(self) -> int:
        """Higher priority plugins are applied last (override earlier plugins)."""
        return 10

    @abc.abstractmethod
    def evaluate(self, inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate governance from extracted inputs.

        Returns a dict with optional keys:
            'governance_adjustments' : Dict[str, float]
                Score adjustments for any GovernanceProfile sub-scores.
                Keys: 'board_independence', 'board_diversity', 'committee_quality',
                      'shareholder_protection', 'overall'
                Values: adjustment in points (-100 to +100).
            'risk_adjustments'       : Dict[str, float]
                Risk score adjustments.
            'flags'                  : List[str]
            'alerts'                 : List[str]
            'explanation'            : List[str]

        Returns None if the plugin cannot evaluate from the provided inputs.
        """


class GovernancePluginRegistry:
    """Thread-safe registry of GovernancePlugin instances."""

    def __init__(self) -> None:
        self._lock:    threading.RLock = threading.RLock()
        self._plugins: Dict[str, GovernancePlugin] = {}

    def register(self, plugin: GovernancePlugin) -> None:
        if not isinstance(plugin, GovernancePlugin):
            raise TypeError(f"Expected GovernancePlugin, got {type(plugin).__name__}")
        with self._lock:
            if plugin.name in self._plugins:
                raise ValueError(
                    f"GovernancePlugin '{plugin.name}' is already registered. "
                    "Unregister it first or use a unique name."
                )
            self._plugins[plugin.name] = plugin

    def run_all(self, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all registered plugins sorted by priority, return non-None results."""
        with self._lock:
            plugins = sorted(self._plugins.values(), key=lambda p: p.priority)
        results = []
        for p in plugins:
            try:
                r = p.evaluate(inputs)
                if r is not None:
                    results.append(r)
            except Exception:
                pass   # plugin failures never crash the core engine
        return results

    def plugin_count(self) -> int:
        with self._lock:
            return len(self._plugins)
