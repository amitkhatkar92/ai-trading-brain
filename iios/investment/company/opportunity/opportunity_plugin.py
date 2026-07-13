"""iios/investment/company/opportunity/opportunity_plugin.py
Plugin ABC and registry for extending the Opportunity Engine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class OpportunityPlugin(ABC):
    """
    Abstract base for Opportunity Engine plugins.

    Plugins can adjust scores, add alerts, override classifications,
    or inject custom intelligence from domain-specific sources.

    Plugins are called AFTER the core evaluation is complete.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique, stable identifier for this plugin."""

    @abstractmethod
    def evaluate(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate opportunity inputs and return adjustments.

        *inputs* contains:
        - ticker, overall_score, primary_category, lifecycle, confidence
        - score_breakdown (OpportunityScoreBreakdown)
        - financial_snapshot, earnings_snapshot, business_quality,
          valuation_snapshot, growth_snapshot, management_snapshot,
          ownership_snapshot, market_intelligence, risk_snapshot

        Return dict may contain any of:
        - "score_adjustment": float       — added to final_score (±)
        - "alerts": List[str]             — additional alert messages
        - "category_override": str        — override primary category value
        - "custom_metadata": Dict         — arbitrary metadata to attach
        """

    def on_error(self, exc: Exception) -> None:
        """
        Called when evaluate() raises. Default: silently ignore.
        Override to add logging or metrics.
        """


class OpportunityPluginRegistry:
    """Maintains a list of registered OpportunityPlugins."""

    def __init__(self) -> None:
        self._plugins: List[OpportunityPlugin] = []
        self._names: set = set()

    def register(self, plugin: OpportunityPlugin) -> None:
        if plugin.name in self._names:
            raise ValueError(f"Opportunity plugin '{plugin.name}' is already registered")
        self._plugins.append(plugin)
        self._names.add(plugin.name)

    def run_all(self, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute all registered plugins against *inputs*.
        Plugin errors are caught and forwarded to on_error(); they do not crash the engine.
        Returns a list of non-empty result dicts.
        """
        results: List[Dict[str, Any]] = []
        for plugin in self._plugins:
            try:
                result = plugin.evaluate(inputs)
                if result:
                    results.append(result)
            except Exception as exc:
                try:
                    plugin.on_error(exc)
                except Exception:
                    pass
        return results

    @property
    def plugin_names(self) -> List[str]:
        return [p.name for p in self._plugins]

    def __len__(self) -> int:
        return len(self._plugins)
