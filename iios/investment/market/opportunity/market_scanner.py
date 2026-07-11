"""iios/investment/market/opportunity/market_scanner.py
Scans the full market universe each bar.
"""
from __future__ import annotations

import logging
from typing import List

from iios.investment.market.opportunity.models import AssetObservation
from iios.investment.market.opportunity.opportunity_classifier import classify_observation
from iios.investment.market.opportunity.opportunity_category import CategoryRule, BUILT_IN_RULES
from iios.investment.market.opportunity.models import Opportunity

log = logging.getLogger(__name__)


class MarketScanner:
    """Scans the full universe of :class:`AssetObservation` objects."""

    def __init__(self, rules: List[CategoryRule] | None = None) -> None:
        self._rules = rules or BUILT_IN_RULES

    def scan(self, observations: List[AssetObservation]) -> List[Opportunity]:
        """Return one :class:`Opportunity` per scanned asset."""
        results: List[Opportunity] = []
        for obs in observations:
            try:
                opp = classify_observation(obs, self._rules)
                if opp is not None:
                    results.append(opp)
            except Exception:
                log.exception("MarketScanner error for %s", obs.symbol)
        return results
