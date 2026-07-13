"""iios/investment/company/business_quality/assessment_context.py
AssessmentContext — bundles all inputs passed to every analyzer.
Also defines the plugin extension interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AssessmentContext:
    """
    All data available to an analyzer during a quality assessment cycle.
    Every analyzer receives this context; it extracts what it needs.
    """
    ticker:             str
    financial_snapshot: Any = None    # iios.investment.company.financials.FinancialSnapshot
    earnings_snapshot:  Any = None    # iios.investment.company.earnings.EarningsSnapshot
    sector:             Optional[str] = None
    industry:           Optional[str] = None
    peer_snapshots:     List[Any] = field(default_factory=list)  # List[BusinessQualitySnapshot]
    metadata:           Dict[str, Any] = field(default_factory=dict)

    # Convenience accessors

    def ratio(self, key: str) -> Optional[float]:
        """Pull a ratio from financial_snapshot.ratios."""
        try:
            return (self.financial_snapshot.ratios or {}).get(key)
        except Exception:
            return None

    def fs_metric(self, attr: str) -> Optional[float]:
        """Pull a top-level attribute from financial_snapshot."""
        try:
            return getattr(self.financial_snapshot, attr, None)
        except Exception:
            return None

    def income_metric(self, key: str) -> Optional[float]:
        try:
            return (getattr(self.financial_snapshot, "income_metrics", None) or {}).get(key)
        except Exception:
            return None

    def cashflow_metric(self, key: str) -> Optional[float]:
        try:
            return (getattr(self.financial_snapshot, "cashflow_metrics", None) or {}).get(key)
        except Exception:
            return None

    def balance_metric(self, key: str) -> Optional[float]:
        try:
            return (getattr(self.financial_snapshot, "balance_sheet_metrics", None) or {}).get(key)
        except Exception:
            return None

    def earnings_metric(self, attr: str) -> Optional[float]:
        """Pull a metric from earnings_snapshot.profitability or similar."""
        try:
            return getattr(self.earnings_snapshot, attr, None)
        except Exception:
            return None


# ─────────────────────────── Plugin interface ──────────────────────────────────

@dataclass
class PluginResult:
    """Result returned by a BusinessQualityPlugin."""
    plugin_name:  str
    score:        float          # 0-100 quality contribution
    confidence:   float          # 0-1
    signals:      List[str] = field(default_factory=list)
    metadata:     Dict[str, Any] = field(default_factory=dict)


class BusinessQualityPlugin(ABC):
    """
    Extension point for qualitative analysis modules.

    Future modules that can implement this interface:
      - ESG analysis
      - Management quality assessment
      - Annual report NLP analysis
      - Patent/IP analysis
      - Supply-chain intelligence
      - Alternative data sources
      - Governance scoring
      - AI-based qualitative assessment
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""
        ...

    @property
    def weight(self) -> float:
        """Contribution weight (0-1) to overall score blending."""
        return 0.0

    @abstractmethod
    def assess(self, context: AssessmentContext) -> PluginResult:
        """
        Assess business quality from the provided context.
        Must be deterministic and not raise exceptions.
        If assessment is not possible, return score=50.0, confidence=0.0.
        """
        ...


class PluginRegistry:
    """Thread-safe registry for BusinessQualityPlugin instances."""

    def __init__(self) -> None:
        import threading
        self._lock    = threading.RLock()
        self._plugins: Dict[str, BusinessQualityPlugin] = {}

    def register(self, plugin: BusinessQualityPlugin) -> None:
        with self._lock:
            self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        with self._lock:
            self._plugins.pop(name, None)

    def get_plugins(self) -> List[BusinessQualityPlugin]:
        with self._lock:
            return list(self._plugins.values())

    def run_all(self, context: AssessmentContext) -> List[PluginResult]:
        results = []
        for plugin in self.get_plugins():
            try:
                result = plugin.assess(context)
                results.append(result)
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "Plugin %s raised an exception during assessment", plugin.name,
                    exc_info=True,
                )
        return results
