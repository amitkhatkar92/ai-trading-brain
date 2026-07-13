"""iios/investment/strategy/opportunity/matching_engine.py
MatchingEngine — orchestrates matching of all registered strategies
against incoming opportunities, with optional parallel execution.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.matching_profile import (
    MatchingProfile, DEFAULT_PROFILE
)
from iios.investment.strategy.opportunity.strategy_matcher import (
    StrategyMatcher, MatchResult
)
from iios.investment.strategy.opportunity.matching_history import MatchingHistory

logger = logging.getLogger(__name__)


class MatchingEngine:
    """
    Runs StrategyMatcher across all registered candidates for each opportunity.
    Returns only matches that pass the profile threshold.

    Thread-safe — multiple threads may submit opportunities concurrently.
    Parallel evaluation is used when max_workers > 1.
    """

    def __init__(
        self,
        profile: Optional[MatchingProfile] = None,
        matcher: Optional[StrategyMatcher] = None,
        max_workers: int = 8,
        history_size: int = 500,
    ) -> None:
        self._profile  = profile or DEFAULT_PROFILE
        self._matcher  = matcher or StrategyMatcher()
        self._pool     = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="match-"
        )
        self._history  = MatchingHistory(max_per_strategy=history_size)
        self._lock     = threading.RLock()

        # Registry of candidates
        self._candidates: Dict[str, StrategyCandidate] = {}

        logger.info(
            "MatchingEngine ready (workers=%d, policy=%s)",
            max_workers, self._profile.policy_name,
        )

    # ── candidate registry ───────────────────────────────────────────────────

    def register(self, candidate: StrategyCandidate) -> None:
        with self._lock:
            self._candidates[candidate.strategy_id] = candidate

    def deregister(self, strategy_id: str) -> None:
        with self._lock:
            self._candidates.pop(strategy_id, None)

    def registered_ids(self) -> List[str]:
        with self._lock:
            return list(self._candidates.keys())

    # ── matching ─────────────────────────────────────────────────────────────

    def match(
        self,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
        profile: Optional[MatchingProfile] = None,
    ) -> List[MatchResult]:
        """
        Match all eligible candidates against the opportunity.
        Returns only results where result.passed is True, sorted by score desc.
        """
        p = profile or self._profile
        with self._lock:
            candidates = list(self._candidates.values())

        if not candidates:
            return []

        results: List[MatchResult] = []

        if len(candidates) <= 4:
            # Avoid thread-pool overhead for small registries
            for c in candidates:
                r = self._safe_match(c, opportunity, p)
                self._history.record(r)
                if r.passed:
                    results.append(r)
        else:
            futures = {
                self._pool.submit(self._safe_match, c, opportunity, p): c
                for c in candidates
            }
            for fut in as_completed(futures):
                try:
                    r = fut.result()
                    self._history.record(r)
                    if r.passed:
                        results.append(r)
                except Exception:
                    cand = futures[fut]
                    logger.exception("Match failed for %s", cand.strategy_id)

        results.sort(key=lambda r: r.score, reverse=True)
        logger.debug(
            "Matched %d/%d candidates for opp %s",
            len(results), len(candidates), _opp_id(opportunity),
        )
        return results

    # ── history queries ──────────────────────────────────────────────────────

    def history(self, strategy_id: str, n: int = 20) -> List[MatchResult]:
        return self._history.history(strategy_id, n)

    def avg_match_score(self, strategy_id: str) -> float:
        return self._history.avg_score(strategy_id)

    def match_pass_rate(self, strategy_id: str) -> float:
        return self._history.pass_rate(strategy_id)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)

    # ── internals ────────────────────────────────────────────────────────────

    def _safe_match(
        self,
        candidate: StrategyCandidate,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
        profile: MatchingProfile,
    ) -> MatchResult:
        try:
            return self._matcher.match(candidate, opportunity, profile)
        except Exception:
            logger.exception("Matcher raised for %s", candidate.strategy_id)
            return MatchResult(
                strategy_id=candidate.strategy_id,
                opportunity_id=_opp_id(opportunity),
                score=0.0,
                passed=False,
                hard_rejected=True,
                rejection_reason="internal_error",
            )


def _opp_id(opp: Union[MarketOpportunity, CompanyOpportunity]) -> str:
    return opp.opportunity_id
