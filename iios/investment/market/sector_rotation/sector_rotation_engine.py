"""iios/investment/market/sector_rotation/sector_rotation_engine.py
Institutional Sector Rotation Intelligence Engine — primary entry point.

  engine = InstitutionalSectorRotationEngine()
  snap   = engine.update(market_snapshot)
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

from iios.investment.market.sector_rotation.capital_flow_engine import CapitalFlowEngine
from iios.investment.market.sector_rotation.industry_engine import IndustryEngine
from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    IndustryProfile,
    MarketSnapshot,
    RelativeStrengthScore,
    RotationSignal,
    RotationType,
    SectorConfidenceScore,
    SectorEvent,
    SectorEventType,
    SectorIntelligenceSnapshot,
    SectorLifecycleProfile,
    SectorPerformance,
    SectorRankEntry,
    SectorStage,
)
from iios.investment.market.sector_rotation.relative_strength_engine import (
    RelativeStrengthEngine,
)
from iios.investment.market.sector_rotation.rotation_detector import RotationDetector
from iios.investment.market.sector_rotation.rotation_history import RotationHistory
from iios.investment.market.sector_rotation.sector_confidence import compute_confidence
from iios.investment.market.sector_rotation.sector_history import SectorHistory
from iios.investment.market.sector_rotation.sector_lifecycle import SectorLifecycleEngine
from iios.investment.market.sector_rotation.sector_score import compute_composite_score
from iios.investment.market.sector_rotation.sector_snapshot import SectorSnapshotBuilder
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

log = logging.getLogger(__name__)


class InstitutionalSectorRotationEngine:
    """Authoritative source of sector, industry and capital-rotation intelligence
    across the Investment Intelligence Operating System.

    Usage::

        from iios.investment.market.sector_rotation import InstitutionalSectorRotationEngine
        from iios.investment.market.sector_rotation.models import MarketSnapshot, SecurityData

        engine = InstitutionalSectorRotationEngine()
        snap   = engine.update(market_snapshot)

    Cross-engine context (optional kwargs to ``update``)::

        snap = engine.update(
            snapshot,
            market_regime="bull",
            breadth_regime="expanding",
            volatility_regime="low",
            correlation_regime="low_correlation",
        )
    """

    def __init__(
        self,
        taxonomy: Optional[SectorTaxonomy] = None,
        window: int = 120,
        rotation_history_len: int = 100,
        sector_history_len: int = 250,
    ) -> None:
        self._taxonomy   = taxonomy or SectorTaxonomy()
        self._window     = window
        self._lock       = threading.Lock()
        self._n_bars     = 0

        # Sub-engines
        self._sector_builder  = SectorSnapshotBuilder(self._taxonomy, window)
        self._industry_engine = IndustryEngine(self._taxonomy, window)
        self._rs_engine       = RelativeStrengthEngine()
        self._flow_engine     = CapitalFlowEngine(self._taxonomy, window)
        self._lifecycle_engine = SectorLifecycleEngine()
        self._rotation_detector = RotationDetector(self._taxonomy)

        # History
        self._rotation_history = RotationHistory(rotation_history_len)
        self._sector_history   = SectorHistory(sector_history_len)

        # Previous ranks for rank_change computation
        self._prev_ranks: Dict[str, int] = {}

        # Async executor
        self._executor: Optional[ThreadPoolExecutor] = None

        # Callbacks
        self.on_rotation_detected: Optional[Callable[[RotationSignal], None]] = None
        self.on_leadership_change:  Optional[Callable[[SectorEvent], None]] = None
        self.on_lifecycle_change:   Optional[Callable[[SectorEvent], None]] = None
        self.on_update:             Optional[Callable[[SectorIntelligenceSnapshot], None]] = None

    # ── primary update ────────────────────────────────────────────────────────

    def update(
        self,
        snapshot: MarketSnapshot,
        *,
        market_regime:     Optional[str] = None,
        breadth_regime:    Optional[str] = None,
        volatility_regime: Optional[str] = None,
        correlation_regime: Optional[str] = None,
    ) -> SectorIntelligenceSnapshot:
        """Process one market bar and return a :class:`SectorIntelligenceSnapshot`."""
        with self._lock:
            return self._process(
                snapshot,
                market_regime=market_regime,
                breadth_regime=breadth_regime,
                volatility_regime=volatility_regime,
                correlation_regime=correlation_regime,
            )

    def _process(
        self,
        snapshot: MarketSnapshot,
        *,
        market_regime:     Optional[str],
        breadth_regime:    Optional[str],
        volatility_regime: Optional[str],
        correlation_regime: Optional[str],
    ) -> SectorIntelligenceSnapshot:
        self._n_bars += 1

        # ── Layer 1: sector performance ───────────────────────────────────────
        sector_perfs: Dict[str, SectorPerformance] = self._sector_builder.update(snapshot)

        # ── Layer 2: industry performance ─────────────────────────────────────
        industry_profiles: Dict[str, IndustryProfile] = self._industry_engine.update(
            snapshot, sector_perfs
        )

        # ── Layer 3: relative strength ────────────────────────────────────────
        self._rs_engine.update(sector_perfs, industry_profiles)
        rs_scores: Dict[str, RelativeStrengthScore] = self._rs_engine.sector_rs()

        # ── Layer 4: capital flows ────────────────────────────────────────────
        capital_flows: Dict[str, CapitalFlowProfile] = self._flow_engine.update(snapshot)

        # ── Layer 5: lifecycle ────────────────────────────────────────────────
        lifecycle_profiles, lifecycle_events = self._lifecycle_engine.update(
            sector_perfs, rs_scores, snapshot.bar_index
        )

        # ── Layer 6: rotation detection ───────────────────────────────────────
        rotation_signal = self._rotation_detector.update(sector_perfs, capital_flows)

        rotation_signals: List[RotationSignal] = []
        if rotation_signal is not None:
            self._rotation_history.append(rotation_signal)
            rotation_signals.append(rotation_signal)

        # ── Layer 7: composite scores + rankings ──────────────────────────────
        rankings = self._build_rankings(
            sector_perfs, rs_scores, capital_flows, lifecycle_profiles
        )

        # ── Layer 8: confidence ───────────────────────────────────────────────
        confidence = compute_confidence(
            sector_rankings=rankings,
            sector_perfs=sector_perfs,
            lifecycle_profiles=lifecycle_profiles,
            capital_flows=capital_flows,
            rotation_signals=rotation_signals,
            n_bars_warm=self._n_bars,
        )

        # ── Layer 9: events ───────────────────────────────────────────────────
        all_events = list(lifecycle_events)
        if rotation_signal is not None and rotation_signal.confirmed:
            all_events.append(
                SectorEvent(
                    event_type=SectorEventType.ROTATION_CONFIRMED,
                    sector="market",
                    bar_index=snapshot.bar_index,
                    severity=rotation_signal.confidence,
                    description=rotation_signal.description,
                    related_sectors=rotation_signal.to_sectors,
                )
            )

        last_event = all_events[-1] if all_events else None

        # ── Build summary lists ───────────────────────────────────────────────
        leaders  = [e.sector for e in rankings[:3]]
        laggards = [e.sector for e in rankings[-3:]] if len(rankings) >= 3 else []
        emerging = self._lifecycle_engine.emerging()

        intelligence_snap = SectorIntelligenceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            bar_index=snapshot.bar_index,
            timestamp=snapshot.timestamp,
            taxonomy=snapshot.taxonomy,
            sector_rankings=rankings,
            sector_perf=sector_perfs,
            industry_profiles=industry_profiles,
            rotation_signals=rotation_signals,
            rs_scores=rs_scores,
            capital_flows=capital_flows,
            lifecycle_profiles=lifecycle_profiles,
            confidence=confidence,
            active_events=all_events,
            last_event=last_event,
            leaders=leaders,
            laggards=laggards,
            emerging=emerging,
            market_regime=market_regime,
            breadth_regime=breadth_regime,
            volatility_regime=volatility_regime,
            correlation_regime=correlation_regime,
        )

        self._sector_history.append(intelligence_snap)

        # ── Callbacks ─────────────────────────────────────────────────────────
        self._fire_callbacks(intelligence_snap, rotation_signal, lifecycle_events)

        return intelligence_snap

    # ── ranking builder ───────────────────────────────────────────────────────

    def _build_rankings(
        self,
        sector_perfs:     Dict[str, SectorPerformance],
        rs_scores:        Dict[str, RelativeStrengthScore],
        capital_flows:    Dict[str, CapitalFlowProfile],
        lifecycle_profiles: Dict[str, SectorLifecycleProfile],
    ) -> List[SectorRankEntry]:
        scored: List[tuple[float, str]] = []

        for sector, perf in sector_perfs.items():
            rs        = rs_scores.get(sector)
            flow      = capital_flows.get(sector)
            lifecycle = lifecycle_profiles.get(sector)
            if rs is None or flow is None or lifecycle is None:
                continue
            composite = compute_composite_score(perf, rs, flow, lifecycle)
            scored.append((composite, sector))

        scored.sort(key=lambda t: t[0], reverse=True)

        current_ranks = {s: i + 1 for i, (_, s) in enumerate(scored)}
        entries: List[SectorRankEntry] = []
        for rank, (composite, sector) in enumerate(scored, start=1):
            prev_rank   = self._prev_ranks.get(sector, rank)
            rank_change = prev_rank - rank   # positive = improved
            lc          = lifecycle_profiles.get(sector)
            rs          = rs_scores.get(sector)
            flow        = capital_flows.get(sector)
            entries.append(SectorRankEntry(
                rank=rank,
                sector=sector,
                composite_score=composite,
                relative_strength=rs.composite if rs else 50.0,
                momentum=sector_perfs[sector].momentum_score,
                flow_signal=flow.net_flow_signal if flow else 0.0,
                lifecycle_stage=lc.stage if lc else SectorStage.UNKNOWN,
                rank_change=rank_change,
            ))

        self._prev_ranks = current_ranks
        return entries

    # ── callbacks ─────────────────────────────────────────────────────────────

    def _fire_callbacks(
        self,
        snap:              SectorIntelligenceSnapshot,
        rotation_signal:   Optional[RotationSignal],
        lifecycle_events:  List[SectorEvent],
    ) -> None:
        try:
            if rotation_signal is not None and self.on_rotation_detected:
                self.on_rotation_detected(rotation_signal)

            for event in lifecycle_events:
                if event.event_type in (
                    SectorEventType.EMERGING_LEADER,
                    SectorEventType.FALLING_LEADER,
                ):
                    if self.on_leadership_change:
                        self.on_leadership_change(event)
                if event.event_type == SectorEventType.STAGE_TRANSITION:
                    if self.on_lifecycle_change:
                        self.on_lifecycle_change(event)

            if self.on_update:
                self.on_update(snap)
        except Exception:
            log.exception("Callback error in sector rotation engine")

    # ── async update ──────────────────────────────────────────────────────────

    async def async_update(
        self,
        snapshot: MarketSnapshot,
        **kwargs,
    ) -> SectorIntelligenceSnapshot:
        loop = asyncio.get_event_loop()
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1)
        return await loop.run_in_executor(
            self._executor,
            lambda: self.update(snapshot, **kwargs),
        )

    # ── query APIs ────────────────────────────────────────────────────────────

    def current_sector_rankings(self) -> List[SectorRankEntry]:
        snap = self._sector_history.latest()
        return snap.sector_rankings if snap else []

    def sector_leaders(self, n: int = 3) -> List[str]:
        return [e.sector for e in self.current_sector_rankings()[:n]]

    def sector_laggards(self, n: int = 3) -> List[str]:
        return [e.sector for e in self.current_sector_rankings()[-n:]]

    def current_rotation_signals(self) -> List[RotationSignal]:
        snap = self._sector_history.latest()
        return snap.rotation_signals if snap else []

    def rotation_timeline(self, n: int = 20) -> List[RotationSignal]:
        return self._rotation_history.recent(n)

    def sector_performance(self, sector: str) -> Optional[SectorPerformance]:
        snap = self._sector_history.latest()
        return snap.sector_perf.get(sector) if snap else None

    def capital_flow(self, sector: str) -> Optional[CapitalFlowProfile]:
        snap = self._sector_history.latest()
        return snap.capital_flows.get(sector) if snap else None

    def relative_strength(self, sector: str) -> Optional[RelativeStrengthScore]:
        snap = self._sector_history.latest()
        return snap.rs_scores.get(sector) if snap else None

    def lifecycle_profile(self, sector: str) -> Optional[SectorLifecycleProfile]:
        snap = self._sector_history.latest()
        return snap.lifecycle_profiles.get(sector) if snap else None

    def latest(self) -> Optional[SectorIntelligenceSnapshot]:
        return self._sector_history.latest()

    def history(self, n: int = 20) -> List[SectorIntelligenceSnapshot]:
        return self._sector_history.recent(n)

    def rank_change_since(self, lookback: int = 5) -> Dict[str, int]:
        return self._rotation_detector.rank_changes(lookback)

    @property
    def bars_processed(self) -> int:
        return self._n_bars

    @property
    def taxonomy(self) -> SectorTaxonomy:
        return self._taxonomy
