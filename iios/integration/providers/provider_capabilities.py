"""iios/integration/providers/provider_capabilities.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderCapabilities:
    """
    Declares what a provider can do.

    Registered alongside the provider and used by the engine for routing.
    """

    # Data offering
    categories:        list[str]  = field(default_factory=list)   # DataCategory values
    frequencies:       list[str]  = field(default_factory=list)   # DataFrequency values
    symbol_spaces:     list[str]  = field(default_factory=list)   # e.g. "NSE", "GLOBAL"

    # Fetch modes
    supports_streaming:  bool = False
    supports_batch:      bool = True
    supports_historical: bool = True
    supports_realtime:   bool = False
    supports_options:    bool = False

    # Rate limiting
    max_symbols_per_request: int   = 100
    requests_per_minute:     int   = 60
    max_history_days:        int   = 365 * 5

    # Quality claims
    max_latency_ms: float = 2_000.0
    coverage_pct:   float = 1.0   # 0–1 fraction of symbols covered

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports_category(self, category: str) -> bool:
        return category in self.categories

    def supports_frequency(self, frequency: str) -> bool:
        return frequency in self.frequencies

    def supports_symbol_space(self, symbol_space: str) -> bool:
        return symbol_space in self.symbol_spaces

    def to_dict(self) -> dict[str, Any]:
        return {
            "categories":            self.categories,
            "frequencies":           self.frequencies,
            "symbol_spaces":         self.symbol_spaces,
            "supports_streaming":    self.supports_streaming,
            "supports_batch":        self.supports_batch,
            "supports_historical":   self.supports_historical,
            "supports_realtime":     self.supports_realtime,
            "supports_options":      self.supports_options,
            "max_symbols_per_request": self.max_symbols_per_request,
            "requests_per_minute":   self.requests_per_minute,
            "max_history_days":      self.max_history_days,
            "max_latency_ms":        self.max_latency_ms,
            "coverage_pct":          self.coverage_pct,
        }
