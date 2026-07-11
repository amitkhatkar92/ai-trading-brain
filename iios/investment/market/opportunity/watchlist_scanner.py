"""iios/investment/market/opportunity/watchlist_scanner.py
Scans a user-defined watchlist of symbols.
"""
from __future__ import annotations

import logging
from typing import List, Set

from iios.investment.market.opportunity.models import AssetObservation, Opportunity
from iios.investment.market.opportunity.opportunity_classifier import classify_observation
from iios.investment.market.opportunity.opportunity_category import CategoryRule, BUILT_IN_RULES

log = logging.getLogger(__name__)


class WatchlistScanner:
    """Scans only those assets whose symbols are on the watchlist."""

    def __init__(self, symbols: List[str] | None = None, rules: List[CategoryRule] | None = None) -> None:
        self._watchlist: Set[str] = set(symbols or [])
        self._rules = rules or BUILT_IN_RULES

    # ── watchlist management ──────────────────────────────────────────────────

    def add(self, symbol: str) -> None:
        self._watchlist.add(symbol)

    def remove(self, symbol: str) -> None:
        self._watchlist.discard(symbol)

    def set_watchlist(self, symbols: List[str]) -> None:
        self._watchlist = set(symbols)

    @property
    def symbols(self) -> List[str]:
        return sorted(self._watchlist)

    # ── scan ─────────────────────────────────────────────────────────────────

    def scan(self, observations: List[AssetObservation]) -> List[Opportunity]:
        results: List[Opportunity] = []
        for obs in observations:
            if obs.symbol not in self._watchlist:
                continue
            try:
                opp = classify_observation(obs, self._rules)
                if opp is not None:
                    results.append(opp)
            except Exception:
                log.exception("WatchlistScanner error for %s", obs.symbol)
        return results
