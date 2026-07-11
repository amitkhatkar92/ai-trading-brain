"""iios/investment/market/opportunity/classification_engine.py
Orchestrates classification for a batch of asset observations.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from iios.investment.market.opportunity.models import (
    AssetObservation,
    Opportunity,
)
from iios.investment.market.opportunity.opportunity_category import CategoryRule, BUILT_IN_RULES
from iios.investment.market.opportunity.opportunity_classifier import classify_observation

log = logging.getLogger(__name__)


class ClassificationEngine:
    """Classifies a batch of :class:`AssetObservation` objects per bar.

    Supports pluggable rule sets via ``register_rules``.
    """

    def __init__(self, rules: Optional[List[CategoryRule]] = None) -> None:
        self._rules: List[CategoryRule] = list(rules or BUILT_IN_RULES)

    # ── configuration ─────────────────────────────────────────────────────────

    def register_rules(self, rules: List[CategoryRule]) -> None:
        """Replace the active rule set."""
        self._rules = list(rules)

    def add_rule(self, rule: CategoryRule) -> None:
        self._rules.append(rule)

    # ── batch classification ───────────────────────────────────────────────────

    def classify_batch(
        self, observations: List[AssetObservation]
    ) -> Dict[str, Opportunity]:
        """Classify each observation; return symbol → Opportunity map.

        Assets that do not meet any rule are still included as
        ``OBSERVATION_ONLY`` opportunities.
        """
        result: Dict[str, Opportunity] = {}
        for obs in observations:
            try:
                opp = classify_observation(obs, self._rules)
                if opp is not None:
                    result[obs.symbol] = opp
            except Exception:
                log.exception("Classification error for symbol %s", obs.symbol)
        return result

    @property
    def rules(self) -> List[CategoryRule]:
        return list(self._rules)
