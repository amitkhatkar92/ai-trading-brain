"""iios/investment/market/opportunity/universe_scanner.py
Scans a named custom universe (sector, theme, portfolio slice, etc.).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from iios.investment.market.opportunity.models import AssetObservation, Opportunity, ScanScope
from iios.investment.market.opportunity.opportunity_classifier import classify_observation
from iios.investment.market.opportunity.opportunity_category import CategoryRule, BUILT_IN_RULES

log = logging.getLogger(__name__)


@dataclass
class Universe:
    name:    str
    scope:   ScanScope
    symbols: Set[str] = field(default_factory=set)
    sectors: Set[str] = field(default_factory=set)
    tags:    Dict[str, str] = field(default_factory=dict)

    def matches(self, obs: AssetObservation) -> bool:
        if self.symbols and obs.symbol in self.symbols:
            return True
        if self.sectors and obs.sector in self.sectors:
            return True
        return False


class UniverseScanner:
    """Manages named universes and scans them independently."""

    def __init__(self, rules: Optional[List[CategoryRule]] = None) -> None:
        self._universes: Dict[str, Universe] = {}
        self._rules = rules or BUILT_IN_RULES

    # ── universe management ───────────────────────────────────────────────────

    def register(self, universe: Universe) -> None:
        self._universes[universe.name] = universe

    def deregister(self, name: str) -> None:
        self._universes.pop(name, None)

    def universe_names(self) -> List[str]:
        return list(self._universes.keys())

    # ── scan ─────────────────────────────────────────────────────────────────

    def scan(
        self,
        observations: List[AssetObservation],
        universe_name: Optional[str] = None,
    ) -> List[Opportunity]:
        """Scan one named universe or all registered universes."""
        names = [universe_name] if universe_name else list(self._universes.keys())
        seen: Set[str] = set()
        results: List[Opportunity] = []

        for name in names:
            universe = self._universes.get(name)
            if universe is None:
                continue
            for obs in observations:
                if obs.symbol in seen:
                    continue
                if not universe.matches(obs):
                    continue
                try:
                    opp = classify_observation(obs, self._rules)
                    if opp is not None:
                        opp.metadata["universe"] = name
                        opp.metadata["scan_scope"] = universe.scope.value
                        results.append(opp)
                        seen.add(obs.symbol)
                except Exception:
                    log.exception("UniverseScanner error for %s", obs.symbol)

        return results
