"""iios/investment/market/opportunity/opportunity_scanner.py
Orchestrates all scanner types for a single scan pass.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from iios.investment.market.opportunity.market_scanner import MarketScanner
from iios.investment.market.opportunity.models import AssetObservation, Opportunity, ScanScope
from iios.investment.market.opportunity.opportunity_category import CategoryRule, BUILT_IN_RULES
from iios.investment.market.opportunity.universe_scanner import Universe, UniverseScanner
from iios.investment.market.opportunity.watchlist_scanner import WatchlistScanner

log = logging.getLogger(__name__)


class OpportunityScanner:
    """Orchestrates market, watchlist, and custom universe scanners.

    By default runs a full-market scan; additional scanners are additive
    (de-duplicated by symbol).
    """

    def __init__(self, rules: Optional[List[CategoryRule]] = None) -> None:
        self._rules            = rules or BUILT_IN_RULES
        self._market_scanner   = MarketScanner(self._rules)
        self._watchlist_scanner = WatchlistScanner(rules=self._rules)
        self._universe_scanner  = UniverseScanner(self._rules)

    # ── configuration ─────────────────────────────────────────────────────────

    def set_rules(self, rules: List[CategoryRule]) -> None:
        self._rules = rules
        self._market_scanner   = MarketScanner(rules)
        self._watchlist_scanner = WatchlistScanner(
            self._watchlist_scanner.symbols, rules
        )
        self._universe_scanner  = UniverseScanner(rules)

    def add_to_watchlist(self, symbol: str) -> None:
        self._watchlist_scanner.add(symbol)

    def remove_from_watchlist(self, symbol: str) -> None:
        self._watchlist_scanner.remove(symbol)

    def register_universe(self, universe: Universe) -> None:
        self._universe_scanner.register(universe)

    # ── scan ─────────────────────────────────────────────────────────────────

    def scan(
        self,
        observations: List[AssetObservation],
        scope: ScanScope = ScanScope.FULL_MARKET,
        universe_name: Optional[str] = None,
    ) -> List[Opportunity]:
        """Run the appropriate scanner and return de-duplicated opportunities."""
        if scope is ScanScope.FULL_MARKET:
            results = self._market_scanner.scan(observations)
        elif scope is ScanScope.WATCHLIST:
            results = self._watchlist_scanner.scan(observations)
        elif scope in (ScanScope.SECTOR, ScanScope.INDUSTRY, ScanScope.THEME, ScanScope.CUSTOM):
            results = self._universe_scanner.scan(observations, universe_name)
        else:
            results = self._market_scanner.scan(observations)

        # Deduplicate by symbol (first occurrence wins)
        seen: Dict[str, Opportunity] = {}
        for opp in results:
            if opp.symbol not in seen:
                seen[opp.symbol] = opp
        return list(seen.values())

    @property
    def watchlist_scanner(self) -> WatchlistScanner:
        return self._watchlist_scanner

    @property
    def universe_scanner(self) -> UniverseScanner:
        return self._universe_scanner
