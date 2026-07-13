"""iios/investment/strategy/opportunity/strategy_opportunity_engine.py
StrategyOpportunityEngine — authoritative strategy recommendation and
opportunity matching engine for the Investment Intelligence Operating System.

Responsibility:
  - Receive market/company opportunities from intelligence engines
  - Match registered strategies to those opportunities
  - Evaluate suitability, rank recommendations, generate explanations
  - Manage opportunity lifecycle (Discovered → Candidate → Recommended …)
  - Monitor active recommendations and raise alerts on change
  - Expose query APIs consumed by Decision Layer, Portfolio AI, Risk AI

This engine does NOT:
  - Generate Buy/Sell/Hold decisions
  - Independently analyse markets, companies, or strategies
  - Execute trades or allocate portfolio capital

Thread-safe — opportunity submission and queries may run concurrently.
"""
from __future__ import annotations

import logging
import threading
import uuid
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState
)
from iios.investment.strategy.opportunity.opportunity_event import (
    EventBus, EventType, OpportunityEvent
)
from iios.investment.strategy.opportunity.matching_profile import (
    MatchingProfile, DEFAULT_PROFILE
)
from iios.investment.strategy.opportunity.matching_engine import MatchingEngine
from iios.investment.strategy.opportunity.strategy_suitability import (
    SuitabilityEngine, SuitabilityResult
)
from iios.investment.strategy.opportunity.ranking_engine import RankingEngine
from iios.investment.strategy.opportunity.ranking_score import RankingScore
from iios.investment.strategy.opportunity.ranking_history import RankingHistory
from iios.investment.strategy.opportunity.strategy_ranking import (
    RankedOpportunity, StrategyRanking
)
from iios.investment.strategy.opportunity.lifecycle_engine import LifecycleEngine
from iios.investment.strategy.opportunity.lifecycle_history import LifecycleHistory
from iios.investment.strategy.opportunity.recommendation_engine import RecommendationEngine
from iios.investment.strategy.opportunity.recommendation_summary import RecommendationSummary
from iios.investment.strategy.opportunity.opportunity_monitor import OpportunityMonitor
from iios.investment.strategy.opportunity.strategy_alerts import StrategyAlert
from iios.investment.strategy.opportunity.strategy_matcher import MatchResult

logger = logging.getLogger(__name__)


class StrategyOpportunityEngine:
    """
    Institutional Strategy Opportunity Engine.

    Usage::

        engine = StrategyOpportunityEngine()
        engine.register_strategy(candidate)

        ranking = engine.submit_market_opportunity(market_opp)
        top     = engine.get_top_opportunities(n=5)
        recs    = engine.get_recommendations(strategy_id="s1")
        explain = engine.explain_recommendation(opportunity_id="...")
    """

    def __init__(
        self,
        matching_profile: Optional[MatchingProfile] = None,
        available_capital: float = 0.0,
        min_suitability: float = 40.0,
        min_confidence: float = 0.20,
        max_workers: int = 8,
        max_history_per_strategy: int = 500,
        ranking_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._matching   = MatchingEngine(
            profile=matching_profile or DEFAULT_PROFILE,
            max_workers=max_workers,
        )
        self._suitability = SuitabilityEngine(
            available_capital=available_capital,
            min_confidence=min_confidence,
            min_suitability_score=min_suitability,
        )
        self._ranking     = RankingEngine(weights=ranking_weights)
        self._rank_hist   = RankingHistory(max_per_strategy=max_history_per_strategy)
        self._lifecycle   = LifecycleEngine()
        self._lc_history  = LifecycleHistory()
        self._reco_engine = RecommendationEngine()
        self._monitor     = OpportunityMonitor()
        self._events      = EventBus()

        # Opportunity registry: opportunity_id → StrategyOpportunity
        self._opportunities: Dict[str, StrategyOpportunity] = {}
        # Recommendation registry: opportunity_id → RecommendationSummary
        self._recommendations: Dict[str, RecommendationSummary] = {}
        # Per-strategy opportunity index: strategy_id → [opportunity_id, …]
        self._strategy_index: Dict[str, Deque[str]] = {}

        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="opp-"
        )

        logger.info("StrategyOpportunityEngine initialised (workers=%d)", max_workers)

    # ── strategy registration ─────────────────────────────────────────────────

    def register_strategy(self, candidate: StrategyCandidate) -> None:
        """Register a strategy for opportunity matching."""
        self._matching.register(candidate)
        logger.debug("Registered strategy %s", candidate.strategy_id)

    def deregister_strategy(self, strategy_id: str) -> None:
        self._matching.deregister(strategy_id)

    def registered_strategy_ids(self) -> List[str]:
        return self._matching.registered_ids()

    # ── opportunity submission ────────────────────────────────────────────────

    def submit_market_opportunity(
        self,
        opportunity: MarketOpportunity,
        profile: Optional[MatchingProfile] = None,
    ) -> StrategyRanking:
        """
        Process an incoming market opportunity.
        Returns a StrategyRanking with the best strategy matches, ranked.
        """
        self._monitor.update_market(opportunity)
        return self._process(opportunity, profile)

    def submit_company_opportunity(
        self,
        opportunity: CompanyOpportunity,
        profile: Optional[MatchingProfile] = None,
    ) -> StrategyRanking:
        """Process an incoming company opportunity."""
        self._monitor.update_company(opportunity)
        return self._process(opportunity, profile)

    def submit_async(
        self, opportunity: Union[MarketOpportunity, CompanyOpportunity]
    ) -> Future:
        """Non-blocking submission. Returns Future[StrategyRanking]."""
        if isinstance(opportunity, MarketOpportunity):
            return self._pool.submit(self.submit_market_opportunity, opportunity)
        return self._pool.submit(self.submit_company_opportunity, opportunity)

    # ── query APIs (Task 8) ───────────────────────────────────────────────────

    def get_top_opportunities(
        self, n: int = 10, state: Optional[OpportunityState] = None
    ) -> List[RankedOpportunity]:
        """Return the top-N active opportunities sorted by composite score."""
        with self._lock:
            opps = list(self._opportunities.values())

        if state is not None:
            opps = [o for o in opps if o.state == state]
        else:
            opps = [o for o in opps if o.is_active()]

        scored = sorted(opps, key=lambda o: o.composite_score(), reverse=True)[:n]
        result = []
        for i, o in enumerate(scored, 1):
            hist_score = self._rank_hist.avg_score(o.strategy_id)
            dummy_ranking = RankingScore(
                strategy_id=o.strategy_id,
                opportunity_id=o.opportunity_id,
                strategy_score=0.0,
                opportunity_score=0.0,
                risk_score=0.0,
                robustness_score=0.0,
                confidence_score=0.0,
                historical_score=hist_score,
                overall_score=o.composite_score(),
                rank=i,
            )
            result.append(RankedOpportunity(opportunity=o, ranking_score=dummy_ranking))
        return result

    def get_recommendations(self, strategy_id: str) -> List[RecommendationSummary]:
        """Return all recommendations for a given strategy."""
        with self._lock:
            opp_ids = list(self._strategy_index.get(strategy_id, []))
            return [
                self._recommendations[oid]
                for oid in opp_ids
                if oid in self._recommendations
            ]

    def get_opportunity(self, opportunity_id: str) -> Optional[StrategyOpportunity]:
        with self._lock:
            return self._opportunities.get(opportunity_id)

    def search_opportunities(
        self,
        state: Optional[OpportunityState] = None,
        strategy_id: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[StrategyOpportunity]:
        with self._lock:
            opps = list(self._opportunities.values())
        if state is not None:
            opps = [o for o in opps if o.state == state]
        if strategy_id is not None:
            opps = [o for o in opps if o.strategy_id == strategy_id]
        if min_score > 0.0:
            opps = [o for o in opps if o.composite_score() >= min_score]
        return sorted(opps, key=lambda o: o.composite_score(), reverse=True)

    def explain_recommendation(
        self, opportunity_id: str
    ) -> Optional[RecommendationSummary]:
        """Return the full recommendation explanation for an opportunity."""
        with self._lock:
            return self._recommendations.get(opportunity_id)

    def compare_strategies(
        self, strategy_ids: List[str]
    ) -> Dict[str, List[RankedOpportunity]]:
        """Compare multiple strategies by their active opportunity rankings."""
        result = {}
        for sid in strategy_ids:
            result[sid] = [
                r for r in self.get_top_opportunities(n=50)
                if r.strategy_id == sid
            ]
        return result

    def get_history(
        self, strategy_id: str, n: int = 20
    ) -> List[StrategyOpportunity]:
        """Return the last N opportunities for a strategy (most recent first)."""
        with self._lock:
            opp_ids = list(self._strategy_index.get(strategy_id, []))
        opps = []
        for oid in reversed(opp_ids[-n:]):
            with self._lock:
                o = self._opportunities.get(oid)
            if o:
                opps.append(o)
        return opps

    def get_timeline(self, opportunity_id: str):
        """Return the full lifecycle event timeline for an opportunity."""
        return self._lc_history.timeline(opportunity_id)

    # ── lifecycle control (for Decision Layer / Execution Engine) ─────────────

    def approve_opportunity(
        self, opportunity_id: str, triggered_by: str = "decision_layer"
    ) -> bool:
        with self._lock:
            opp = self._opportunities.get(opportunity_id)
        if opp is None:
            return False
        ok = self._lifecycle.advance_to_approved(
            opp, reason="approved_by_decision_layer", triggered_by=triggered_by
        )
        if ok:
            self._record_lifecycle(opp)
            self._monitor.register(opp)
        return ok

    def start_monitoring(
        self, opportunity_id: str, triggered_by: str = "execution_engine"
    ) -> bool:
        with self._lock:
            opp = self._opportunities.get(opportunity_id)
        if opp is None:
            return False
        ok = self._lifecycle.advance_to_monitoring(opp, triggered_by=triggered_by)
        if ok:
            self._record_lifecycle(opp)
        return ok

    def expire_opportunity(self, opportunity_id: str, reason: str = "manual") -> bool:
        with self._lock:
            opp = self._opportunities.get(opportunity_id)
        if opp is None:
            return False
        ok = self._lifecycle.expire(opp, reason=reason)
        if ok:
            self._record_lifecycle(opp)
            self._monitor.deregister(opportunity_id)
        return ok

    def run_expiry_sweep(self) -> int:
        """Expire all opportunities whose TTL has elapsed. Returns count expired."""
        with self._lock:
            opps = [o for o in self._opportunities.values() if o.is_active()]
        count = 0
        for opp in opps:
            if self._lifecycle.check_and_expire(opp):
                self._record_lifecycle(opp)
                self._monitor.deregister(opp.opportunity_id)
                count += 1
        if count:
            logger.info("Expiry sweep: expired %d opportunities", count)
        return count

    # ── monitoring ────────────────────────────────────────────────────────────

    def check_opportunity_health(
        self, opportunity_id: str
    ) -> List[StrategyAlert]:
        with self._lock:
            opp = self._opportunities.get(opportunity_id)
        if opp is None:
            return []
        return self._monitor.check_opportunity(opp)

    def check_expiring(self, warn_minutes: int = 30) -> List[StrategyAlert]:
        with self._lock:
            opps = list(self._opportunities.values())
        return self._monitor.check_expiring(opps, warn_minutes)

    @property
    def alert_registry(self):
        return self._monitor.alert_registry

    # ── event subscriptions ───────────────────────────────────────────────────

    def subscribe(self, listener: Callable[[OpportunityEvent], None]) -> None:
        self._events.subscribe(listener)

    def subscribe_alerts(self, callback: Callable[[StrategyAlert], None]) -> None:
        self._monitor.subscribe_alerts(callback)

    # ── stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._opportunities)
            by_state: Dict[str, int] = {}
            for o in self._opportunities.values():
                k = o.state.value
                by_state[k] = by_state.get(k, 0) + 1
        return {
            "total_opportunities":   total,
            "by_state":              by_state,
            "registered_strategies": len(self._matching.registered_ids()),
            "total_recommendations": len(self._recommendations),
            "total_alerts":          self._monitor.alert_registry.count(),
        }

    # ── shutdown ──────────────────────────────────────────────────────────────

    def shutdown(self, wait: bool = True) -> None:
        self._matching.shutdown(wait=wait)
        self._pool.shutdown(wait=wait)
        logger.info("StrategyOpportunityEngine shut down")

    # ── internal pipeline ─────────────────────────────────────────────────────

    def _process(
        self,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
        profile: Optional[MatchingProfile],
    ) -> StrategyRanking:
        n_candidates = len(self._matching.registered_ids())

        # 1. Match
        match_results: List[MatchResult] = self._matching.match(opportunity, profile)

        if not match_results:
            return StrategyRanking(
                source_opportunity_id=opportunity.opportunity_id,
                ranked_at=datetime.now(timezone.utc),
                total_candidates=n_candidates,
                total_matched=0,
                total_suitable=0,
            )

        # 2. Suitability (parallel for large candidate sets)
        suit_results: List[SuitabilityResult] = []
        if len(match_results) <= 4:
            for mr in match_results:
                c = self._get_candidate(mr.strategy_id)
                if c:
                    suit_results.append(
                        self._suitability.evaluate(c, opportunity)
                    )
        else:
            futs = {}
            for mr in match_results:
                c = self._get_candidate(mr.strategy_id)
                if c:
                    futs[self._pool.submit(self._suitability.evaluate, c, opportunity)] = mr
            for fut in as_completed(futs):
                try:
                    suit_results.append(fut.result())
                except Exception:
                    logger.exception("Suitability evaluation failed")

        suitable = [s for s in suit_results if s.suitable]

        if not suitable:
            return StrategyRanking(
                source_opportunity_id=opportunity.opportunity_id,
                ranked_at=datetime.now(timezone.utc),
                total_candidates=n_candidates,
                total_matched=len(match_results),
                total_suitable=0,
            )

        # 3. Rank
        # Build lookup maps
        match_by_sid  = {mr.strategy_id: mr for mr in match_results}
        suit_by_sid   = {sr.strategy_id: sr for sr in suitable}

        raw_scores: List[RankingScore] = []
        for sr in suitable:
            c  = self._get_candidate(sr.strategy_id)
            mr = match_by_sid.get(sr.strategy_id)
            if c is None or mr is None:
                continue
            hist = self._rank_hist.avg_score(sr.strategy_id) / 100.0
            rs   = self._ranking.score(c, mr, sr, historical_pass_rate=hist)
            raw_scores.append(rs)

        ranked_scores = self._ranking.rank(raw_scores)

        # 4. Build StrategyOpportunity objects + recommendations
        ranked_opps: List[RankedOpportunity] = []
        for rs in ranked_scores:
            self._rank_hist.record(rs)
            c   = self._get_candidate(rs.strategy_id)
            mr  = match_by_sid[rs.strategy_id]
            sr  = suit_by_sid[rs.strategy_id]
            if c is None:
                continue

            opp_id = str(uuid.uuid4())
            mkt_id = opportunity.opportunity_id if isinstance(opportunity, MarketOpportunity) else None
            co_id  = opportunity.opportunity_id if isinstance(opportunity, CompanyOpportunity) else None

            strat_opp = StrategyOpportunity(
                opportunity_id=opp_id,
                strategy_id=rs.strategy_id,
                strategy_name=c.strategy_name,
                market_opportunity_id=mkt_id,
                company_opportunity_id=co_id,
                matching_score=mr.score,
                suitability_score=sr.score,
                ranking_score=rs.overall_score,
            )

            # Lifecycle: DISCOVERED → CANDIDATE → RECOMMENDED (if top-ranked)
            self._lifecycle.advance_to_candidate(strat_opp, "matched_and_suitable")
            if rs.rank <= 10:
                self._lifecycle.advance_to_recommended(strat_opp, f"rank={rs.rank}")

            # Recommendation
            rec = self._reco_engine.generate(
                candidate=c,
                opportunity=opportunity,
                match=mr,
                suitability=sr,
                ranking=rs,
                overall_score=strat_opp.composite_score(),
            )
            strat_opp.recommendation_id = rec.recommendation_id

            # Store
            with self._lock:
                self._opportunities[opp_id]      = strat_opp
                self._recommendations[opp_id]    = rec
                idx = self._strategy_index.setdefault(
                    rs.strategy_id, deque(maxlen=500)
                )
                idx.append(opp_id)

            self._record_lifecycle(strat_opp)
            self._events.publish(OpportunityEvent.create(
                EventType.RECOMMENDATION_GENERATED,
                opportunity_id=opp_id,
                strategy_id=rs.strategy_id,
                payload={"rank": rs.rank, "score": strat_opp.composite_score()},
            ))

            ranked_opps.append(RankedOpportunity(opportunity=strat_opp, ranking_score=rs))

        return StrategyRanking(
            source_opportunity_id=opportunity.opportunity_id,
            ranked_at=datetime.now(timezone.utc),
            total_candidates=n_candidates,
            total_matched=len(match_results),
            total_suitable=len(suitable),
            entries=ranked_opps,
        )

    def _get_candidate(self, strategy_id: str) -> Optional[StrategyCandidate]:
        """Retrieve candidate from MatchingEngine's registry."""
        with self._matching._lock:
            return self._matching._candidates.get(strategy_id)

    def _record_lifecycle(self, opp: StrategyOpportunity) -> None:
        for rec in opp.state_history[-2:]:  # record latest transitions
            self._lc_history.record(
                opportunity_id=opp.opportunity_id,
                strategy_id=opp.strategy_id,
                transition=rec,
            )
