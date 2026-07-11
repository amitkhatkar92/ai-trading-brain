"""iios/investment/market/opportunity/market_opportunity_engine.py
Institutional Market Opportunity Engine — primary entry point.

  engine = InstitutionalMarketOpportunityEngine()
  snap   = engine.update(observations)
"""
from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

from iios.investment.market.opportunity.classification_engine import ClassificationEngine
from iios.investment.market.opportunity.explanation_engine import ExplanationEngine
from iios.investment.market.opportunity.market_opportunity import OpportunityRegistry
from iios.investment.market.opportunity.models import (
    AssetObservation,
    Opportunity,
    OpportunityAlert,
    OpportunityCategory,
    OpportunityEvent,
    OpportunityExplanation,
    OpportunityLifecycleStage,
    OpportunitySnapshotData,
    ScanScope,
)
from iios.investment.market.opportunity.opportunity_category import CategoryRule
from iios.investment.market.opportunity.opportunity_history import OpportunityHistory
from iios.investment.market.opportunity.opportunity_lifecycle import OpportunityLifecycleEngine
from iios.investment.market.opportunity.opportunity_monitor import OpportunityMonitor
from iios.investment.market.opportunity.opportunity_profile import ProfileStore
from iios.investment.market.opportunity.opportunity_scanner import OpportunityScanner
from iios.investment.market.opportunity.opportunity_snapshot import build_snapshot
from iios.investment.market.opportunity.ranking_engine import RankingEngine
from iios.investment.market.opportunity.ranking_history import RankingHistory
from iios.investment.market.opportunity.universe_scanner import Universe

log = logging.getLogger(__name__)


class InstitutionalMarketOpportunityEngine:
    """Authoritative opportunity discovery system for IIOS.

    Responsibilities:
    - Continuously scan the market universe
    - Classify assets into opportunity categories
    - Rank, score and prioritise opportunities
    - Track opportunity lifecycle
    - Generate explanations
    - Publish alerts on material changes
    - Provide search and query APIs

    This engine does NOT generate buy/sell decisions.
    """

    def __init__(
        self,
        rules:               Optional[List[CategoryRule]] = None,
        scan_scope:          ScanScope = ScanScope.FULL_MARKET,
        snapshot_history_len: int = 250,
        ranking_history_len:  int = 100,
    ) -> None:
        self._lock        = threading.Lock()
        self._scan_scope  = scan_scope
        self._n_bars      = 0

        # Sub-systems
        self._scanner          = OpportunityScanner(rules)
        self._classifier       = ClassificationEngine(rules)
        self._registry         = OpportunityRegistry()
        self._lifecycle_engine = OpportunityLifecycleEngine()
        self._ranking_engine   = RankingEngine()
        self._ranking_history  = RankingHistory(ranking_history_len)
        self._monitor          = OpportunityMonitor()
        self._explanation_engine = ExplanationEngine()
        self._profile_store    = ProfileStore()
        self._history          = OpportunityHistory(snapshot_history_len)

        # Callbacks
        self.on_new_opportunity: Optional[Callable[[Opportunity], None]] = None
        self.on_alert:           Optional[Callable[[OpportunityAlert], None]] = None
        self.on_update:          Optional[Callable[[OpportunitySnapshotData], None]] = None
        self.on_new_critical:    Optional[Callable[[List[str]], None]] = None

        # Wire up monitor callbacks
        self._monitor.on_alert        = self._dispatch_alert
        self._monitor.on_new_critical = self._dispatch_critical

        self._executor: Optional[ThreadPoolExecutor] = None

    # ── primary update ────────────────────────────────────────────────────────

    def update(
        self,
        observations:    List[AssetObservation],
        *,
        market_regime:   Optional[str] = None,
        breadth_regime:  Optional[str] = None,
        universe_name:   Optional[str] = None,
    ) -> OpportunitySnapshotData:
        with self._lock:
            return self._process(
                observations,
                market_regime=market_regime,
                breadth_regime=breadth_regime,
                universe_name=universe_name,
            )

    def _process(
        self,
        observations: List[AssetObservation],
        *,
        market_regime:  Optional[str],
        breadth_regime: Optional[str],
        universe_name:  Optional[str],
    ) -> OpportunitySnapshotData:
        if not observations:
            return self._empty_snapshot(0, 0.0, market_regime, breadth_regime)

        self._n_bars += 1
        bar_index = observations[0].bar_index
        timestamp = observations[0].timestamp

        # ── 1. Update explanation context ─────────────────────────────────────
        for obs in observations:
            self._explanation_engine.update_context(obs.symbol, obs.intelligence)

        # ── 2. Scan + classify all observations ───────────────────────────────
        scanned: List[Opportunity] = self._scanner.scan(
            observations, self._scan_scope, universe_name
        )

        # ── 3. Register / update in registry ─────────────────────────────────
        new_discoveries: List[Opportunity] = []
        for new_opp in scanned:
            existing = self._registry.get_by_symbol(new_opp.symbol)
            if existing is None:
                self._registry.register(new_opp)
                new_discoveries.append(new_opp)
                if self.on_new_opportunity:
                    try:
                        self.on_new_opportunity(new_opp)
                    except Exception:
                        log.exception("on_new_opportunity callback error")
            else:
                # Update scores from new classification
                existing.composite_score      = new_opp.composite_score
                existing.confidence           = new_opp.confidence
                existing.secondary_categories = new_opp.secondary_categories
                existing.last_updated_bar     = bar_index
                existing.market_regime        = market_regime
                self._registry.update(existing)

        # ── 4. Rank all active opportunities ──────────────────────────────────
        all_active = self._registry.all_active()
        ranked_opps = self._ranking_engine.update(all_active, observations)
        self._ranking_history.append(
            {rs.opportunity_id: rs for rs in self._ranking_engine.top_n(len(ranked_opps))}
        )

        # ── 5. Lifecycle advancement ──────────────────────────────────────────
        active_opps, lifecycle_events = self._lifecycle_engine.update(
            ranked_opps, bar_index
        )

        # Expire opportunities that left the active set
        expired_opps: List[Opportunity] = []
        active_ids = {o.opportunity_id for o in active_opps}
        for opp in ranked_opps:
            if opp.opportunity_id not in active_ids:
                expired_opps.append(opp)
                self._registry.expire(opp.opportunity_id)

        # ── 6. Monitor + alerts ───────────────────────────────────────────────
        alerts = self._monitor.update(active_opps, bar_index)

        # ── 7. Record profiles ────────────────────────────────────────────────
        self._profile_store.record_batch(active_opps)

        # ── 8. Build snapshot ─────────────────────────────────────────────────
        snap = build_snapshot(
            bar_index=bar_index,
            timestamp=timestamp,
            active_opps=active_opps,
            new_discoveries=new_discoveries,
            expired_opps=expired_opps,
            alerts=alerts,
            events=lifecycle_events,
            market_regime=market_regime,
            breadth_regime=breadth_regime,
            scan_scope=self._scan_scope.value,
        )
        self._history.append(snap)

        if self.on_update:
            try:
                self.on_update(snap)
            except Exception:
                log.exception("on_update callback error")

        return snap

    # ── async update ──────────────────────────────────────────────────────────

    async def async_update(
        self,
        observations: List[AssetObservation],
        **kwargs,
    ) -> OpportunitySnapshotData:
        loop = asyncio.get_event_loop()
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1)
        return await loop.run_in_executor(
            self._executor,
            lambda: self.update(observations, **kwargs),
        )

    # ── query APIs ────────────────────────────────────────────────────────────

    def top_opportunities(self, n: int = 10) -> List[Opportunity]:
        """Top N active opportunities by composite score."""
        active = sorted(
            self._registry.all_active(),
            key=lambda o: o.rank if o.rank > 0 else 9999,
        )
        return active[:n]

    def search(
        self,
        *,
        sector:   Optional[str] = None,
        industry: Optional[str] = None,
        category: Optional[OpportunityCategory] = None,
        stage:    Optional[OpportunityLifecycleStage] = None,
        min_score: float = 0.0,
    ) -> List[Opportunity]:
        """Filter active opportunities by one or more criteria."""
        results = self._registry.all_active()
        if sector:
            results = [o for o in results if o.sector == sector]
        if industry:
            results = [o for o in results if o.industry == industry]
        if category:
            results = [o for o in results if o.primary_category is category]
        if stage:
            results = [o for o in results if o.lifecycle_stage is stage]
        results = [o for o in results if o.composite_score >= min_score]
        return sorted(results, key=lambda o: o.rank if o.rank > 0 else 9999)

    def explain(self, symbol: str) -> Optional[OpportunityExplanation]:
        opp = self._registry.get_by_symbol(symbol)
        if opp is None:
            return None
        return self._explanation_engine.explain(opp)

    def opportunity_for(self, symbol: str) -> Optional[Opportunity]:
        return self._registry.get_by_symbol(symbol)

    def add_to_watchlist(self, symbol: str) -> None:
        self._scanner.add_to_watchlist(symbol)

    def register_universe(self, universe: Universe) -> None:
        self._scanner.register_universe(universe)

    def recent_alerts(self, n: int = 20) -> List[OpportunityAlert]:
        return self._monitor.recent_alerts(n)

    def recent_history(self, n: int = 10) -> List[OpportunitySnapshotData]:
        return self._history.recent(n)

    def latest(self) -> Optional[OpportunitySnapshotData]:
        return self._history.latest()

    def ranking_engine(self) -> RankingEngine:
        return self._ranking_engine

    def registry(self) -> OpportunityRegistry:
        return self._registry

    def profile_store(self) -> ProfileStore:
        return self._profile_store

    @property
    def bars_processed(self) -> int:
        return self._n_bars

    @property
    def scan_scope(self) -> ScanScope:
        return self._scan_scope

    # ── helpers ───────────────────────────────────────────────────────────────

    def _empty_snapshot(
        self,
        bar_index: int,
        timestamp: float,
        market_regime: Optional[str],
        breadth_regime: Optional[str],
    ) -> OpportunitySnapshotData:
        return build_snapshot(
            bar_index=bar_index,
            timestamp=timestamp,
            active_opps=[],
            new_discoveries=[],
            expired_opps=[],
            alerts=[],
            events=[],
            market_regime=market_regime,
            breadth_regime=breadth_regime,
        )

    def _dispatch_alert(self, alert: OpportunityAlert) -> None:
        if self.on_alert:
            try:
                self.on_alert(alert)
            except Exception:
                log.exception("on_alert callback error")

    def _dispatch_critical(self, symbols: List[str]) -> None:
        if self.on_new_critical:
            try:
                self.on_new_critical(symbols)
            except Exception:
                log.exception("on_new_critical callback error")
