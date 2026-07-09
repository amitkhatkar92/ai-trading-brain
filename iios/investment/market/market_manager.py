"""iios/investment/market/market_manager.py
Central orchestrator for the Market Intelligence pipeline.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.investment.market.market_constants import (
    DEFAULT_SNAPSHOT_HISTORY,
    MarketRegime,
    MarketStatus,
)
from iios.investment.market.market_exceptions import SnapshotNotFoundError
from iios.investment.market.market_state.market_state import MarketState
from iios.investment.market.market_state.market_state_manager import MarketStateManager
from iios.investment.market.market_state.market_snapshot import MarketSnapshot
from iios.investment.market.market_state.market_statistics import MarketStatistics
from iios.investment.market.regime.market_regime_engine import MarketRegimeEngine
from iios.investment.market.analytics.market_structure_engine import MarketStructureEngine
from iios.investment.market.models.market_health import MarketHealth
from iios.investment.market.models.market_intelligence import MarketIntelligence
from iios.investment.market.models.market_summary import MarketSummary


class MarketManager:
    """
    Orchestrates the full Market Intelligence pipeline per analysis cycle.

    Pipeline:
    1. Auto-register market if unknown.
    2. Build MarketSnapshot from raw inputs.
    3. Run MarketStructureEngine  (trend → breadth → vol → liquidity → corr).
       Structure engine writes dimensions back onto the snapshot.
    4. Run MarketRegimeEngine.classify() (reads dimensions from snapshot).
    5. Compile MarketIntelligence.
    6. Generate human-readable observations.
    7. Update statistics and history.
    """

    def __init__(
        self,
        state_manager:    MarketStateManager   | None = None,
        regime_engine:    MarketRegimeEngine   | None = None,
        structure_engine: MarketStructureEngine | None = None,
    ) -> None:
        self._lock:           threading.RLock             = threading.RLock()
        self._state_mgr:      MarketStateManager          = state_manager    or MarketStateManager()
        self._regime_engine:  MarketRegimeEngine          = regime_engine    or MarketRegimeEngine()
        self._structure:      MarketStructureEngine        = structure_engine or MarketStructureEngine()

        # Latest snapshot / intelligence per market
        self._snapshots:      dict[str, MarketSnapshot]     = {}
        self._intelligence:   dict[str, MarketIntelligence] = {}

        # Per-market snapshot ring buffer (for regime history)
        self._snap_history:   dict[str, list[MarketSnapshot]] = {}

        # Global intelligence history (FIFO)
        self._history:        list[MarketIntelligence]      = []

        self._stats:          MarketStatistics              = MarketStatistics()

    # ── market lifecycle ──────────────────────────────────────────────────────

    def register_market(
        self,
        market_id: str,
        name:      str  = "",
        *,
        overwrite: bool = False,
    ) -> MarketState:
        return self._state_mgr.register(market_id, name=name, overwrite=overwrite)

    def get_market_state(self, market_id: str) -> MarketState:
        return self._state_mgr.get(market_id)

    def open_market(self, market_id: str, trading_date: str = "") -> MarketState:
        return self._state_mgr.open_market(market_id, trading_date)

    def close_market(self, market_id: str) -> MarketState:
        return self._state_mgr.close_market(market_id)

    # ── core analysis ─────────────────────────────────────────────────────────

    def analyze(
        self,
        market_id:      str,
        prices:         dict[str, float] | None         = None,
        volumes:        dict[str, float] | None         = None,
        changes:        dict[str, float] | None         = None,
        spreads:        dict[str, float] | None         = None,
        advances:       int                             = 0,
        declines:       int                             = 0,
        unchanged:      int                             = 0,
        status:         MarketStatus                    = MarketStatus.UNKNOWN,
        price_history:  list[float]              | None = None,
        return_history: list[float]              | None = None,
        return_series:  dict[str, list[float]]  | None = None,
        request_id:     str                             = "",
        **metadata: Any,
    ) -> MarketIntelligence:
        t0 = time.perf_counter()

        # Auto-register market
        if not self._state_mgr.has(market_id):
            self._state_mgr.register(market_id)

        # Build snapshot
        prices  = prices  or {}
        volumes = volumes or {}
        snapshot = MarketSnapshot(
            market_id    = market_id,
            status       = status,
            prices       = prices,
            volumes      = volumes,
            changes      = changes  or {},
            spreads      = spreads  or {},
            advances     = advances,
            declines     = declines,
            unchanged    = unchanged,
            symbols      = list(prices.keys()),
            total_volume = sum(volumes.values()),
            metadata     = dict(metadata),
        )

        # Structure analysis (writes trend/vol/liq/breadth into snapshot)
        struct = self._structure.analyze(
            snapshot       = snapshot,
            price_history  = price_history,
            return_history = return_history,
            return_series  = return_series,
        )

        # Regime classification (reads dimensions from snapshot)
        prev_snaps = self._get_snap_history(market_id)
        regime, regime_conf = self._regime_engine.classify(market_id, snapshot, prev_snaps)

        # Append to snapshot ring buffer
        self._push_snap_history(market_id, snapshot)

        # Store latest snapshot
        with self._lock:
            self._snapshots[market_id] = snapshot

        # Compile intelligence
        duration_ms = (time.perf_counter() - t0) * 1000
        intel = self._build_intelligence(
            market_id   = market_id,
            snapshot    = snapshot,
            struct      = struct,
            regime      = regime,
            regime_conf = regime_conf,
            request_id  = request_id,
            duration_ms = duration_ms,
        )

        # Update storage + stats
        with self._lock:
            self._intelligence[market_id] = intel
            self._history.append(intel)
            if len(self._history) > 10_000:
                self._history = self._history[-10_000:]
            self._stats.total_snapshots  += 1
            self._stats.record_analysis(intel.duration_ms)
            self._stats.regime_counts[regime.value] = (
                self._stats.regime_counts.get(regime.value, 0) + 1
            )
            self._stats.trend_counts[intel.trend.value] = (
                self._stats.trend_counts.get(intel.trend.value, 0) + 1
            )

        return intel

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get_latest(self, market_id: str) -> MarketIntelligence:
        with self._lock:
            if market_id not in self._intelligence:
                raise SnapshotNotFoundError(market_id)
            return self._intelligence[market_id]

    def get_snapshot(self, market_id: str) -> MarketSnapshot:
        with self._lock:
            if market_id not in self._snapshots:
                raise SnapshotNotFoundError(market_id)
            return self._snapshots[market_id]

    def recent(self, n: int = 10) -> list[MarketIntelligence]:
        with self._lock:
            items = self._history
            return list(items[-n:]) if len(items) >= n else list(items)

    def summary(self, market_id: str) -> MarketSummary:
        intel = self.get_latest(market_id)
        state = self._state_mgr.get(market_id) if self._state_mgr.has(market_id) else None
        return MarketSummary(
            market_id         = market_id,
            name              = state.name if state else market_id,
            status            = intel.status,
            regime            = intel.regime,
            regime_confidence = intel.regime_confidence,
            trend             = intel.trend,
            health_score      = intel.market_health_score,
            quality_score     = intel.market_quality_score,
            opportunities     = list(intel.opportunities),
            threats           = list(intel.threats),
            key_observations  = list(intel.key_observations),
        )

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            s = self._stats.to_dict()
            s["registered_markets"] = self._state_mgr.count()
            s["active_markets"]     = len(self._state_mgr.active_markets())
            return s

    def stats_object(self) -> MarketStatistics:
        return self._stats

    # ── internals ─────────────────────────────────────────────────────────────

    def _get_snap_history(self, market_id: str, n: int = 10) -> list[MarketSnapshot]:
        with self._lock:
            buf = self._snap_history.get(market_id, [])
            return list(buf[-n:])

    def _push_snap_history(self, market_id: str, snap: MarketSnapshot) -> None:
        with self._lock:
            buf = self._snap_history.setdefault(market_id, [])
            buf.append(snap)
            if len(buf) > DEFAULT_SNAPSHOT_HISTORY:
                del buf[:-DEFAULT_SNAPSHOT_HISTORY]

    def _build_intelligence(
        self,
        market_id:   str,
        snapshot:    MarketSnapshot,
        struct:      Any,
        regime:      MarketRegime,
        regime_conf: float,
        request_id:  str,
        duration_ms: float,
    ) -> MarketIntelligence:
        health = MarketHealth(
            overall_score    = struct.health_score,
            volatility_score = struct.volatility.score,
            liquidity_score  = struct.liquidity.score,
            breadth_score    = struct.breadth.score,
            trend_score      = struct.trend.score,
            sentiment_score  = 50.0,
        )

        intel = MarketIntelligence(
            market_id            = market_id,
            request_id           = request_id,
            status               = snapshot.status,
            regime               = regime,
            regime_confidence    = regime_conf,
            trend                = snapshot.trend,
            trend_strength       = snapshot.strength,
            trend_score          = struct.trend.score,
            volatility           = snapshot.volatility,
            volatility_score     = struct.volatility.score,
            liquidity            = snapshot.liquidity,
            liquidity_score      = struct.liquidity.score,
            breadth              = snapshot.breadth,
            breadth_score        = struct.breadth.score,
            correlation          = struct.correlation.regime,
            correlation_score    = struct.correlation.score,
            health               = health,
            market_health_score  = struct.health_score,
            market_quality_score = struct.quality_score,
            confidence           = regime_conf,
            duration_ms          = duration_ms,
        )

        self._generate_observations(intel, snapshot)
        return intel

    @staticmethod
    def _generate_observations(
        intel:    MarketIntelligence,
        snapshot: MarketSnapshot,
    ) -> None:
        from iios.investment.market.market_constants import (
            BreadthCondition, LiquidityLevel, TrendDirection, VolatilityLevel,
        )

        if snapshot.trend == TrendDirection.UP:
            intel.add_observation(
                f"Market trending upward ({snapshot.strength.value} strength)"
            )
            intel.add_opportunity("Uptrend momentum favours long exposure")
        elif snapshot.trend == TrendDirection.DOWN:
            intel.add_observation(
                f"Market trending downward ({snapshot.strength.value} strength)"
            )
            intel.add_threat("Downtrend momentum — risk-off conditions prevail")

        if snapshot.volatility == VolatilityLevel.EXTREME:
            intel.add_observation("Extreme volatility detected")
            intel.add_threat("Extreme volatility increases risk of sharp reversals")
        elif snapshot.volatility == VolatilityLevel.VERY_LOW:
            intel.add_observation("Very low volatility — complacency risk")

        if snapshot.breadth in (BreadthCondition.VERY_NARROW, BreadthCondition.NARROW):
            intel.add_observation("Narrow market breadth — few securities driving the move")
            intel.add_threat("Narrow breadth signals fragile conditions")
        elif snapshot.breadth in (BreadthCondition.VERY_BROAD, BreadthCondition.BROAD):
            intel.add_observation("Broad market participation confirms trend strength")
            intel.add_opportunity("Wide breadth supports sustained market move")

        if snapshot.liquidity == LiquidityLevel.ILLIQUID:
            intel.add_observation("Market liquidity is very poor")
            intel.add_threat("Poor liquidity amplifies price impact and spread costs")
        elif snapshot.liquidity in (LiquidityLevel.VERY_HIGH, LiquidityLevel.HIGH):
            intel.add_observation("High market liquidity — tight spreads")
            intel.add_opportunity("High liquidity supports efficient order execution")


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock       = threading.Lock()
_instance:       MarketManager | None = None


def get_market_manager() -> MarketManager:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = MarketManager()
    return _instance


def reset_market_manager() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
