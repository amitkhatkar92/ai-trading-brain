"""
market_observer.py — MLS Phase 1: Market Observation Layer.

Responsibilities:
    Capture the complete NSE universe state BEFORE price movement analysis.
    Enforce the temporal contract: feature_timestamp ≤ 09:15 IST.
    Persist immutable daily snapshots atomically (tmp → os.replace).

Explicitly NOT responsible for:
    Learning.  Comparison.  DNA discovery.  Prediction.
    Writing to ARS knowledge stores.
    Trade execution or signal generation.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from models.market_data import MarketSnapshot
from edge_discovery.feature_extractor import FeatureExtractor

from .mls_config import MLSConfig
from .market_observer_models import (
    DailyMarketSnapshot,
    MarketObservation,
    MarketObserverError,
    ObservationMetadata,
    ObservationStatistics,
    TemporalContractViolation,
)

log = logging.getLogger(__name__)

# IST = UTC+5:30
_IST = timezone(timedelta(hours=5, minutes=30))

# default storage root relative to project data/
_DEFAULT_MLS_DIR = Path(__file__).resolve().parent.parent / "data" / "mls"


class MarketObserver:
    """
    MLS Phase 1 — observation layer.

    Captures the complete market state for every trading day before any
    movement analysis begins.  Every future DNA discovery must originate
    from a MarketObserver snapshot.

    Temporal contract (INV-01):
        feature_timestamp ≤ 09:15 IST on trading day T
        Measured outcome = Close(T) vs Close(T-1)
        Violation → TemporalContractViolation

    Thread safety: capture() and list_snapshots() are safe for concurrent use.
    load_snapshot() and statistics() are read-only and intrinsically safe.
    """

    def __init__(
        self,
        config: Optional[MLSConfig] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        self._config        = config or MLSConfig()
        root                = Path(data_dir) if data_dir else _DEFAULT_MLS_DIR
        self._snapshots_dir = root / "snapshots"
        self._lock          = threading.Lock()
        self._fe            = FeatureExtractor()
        self._violation_count = 0          # session-level violations caught
        log.info("[MarketObserver] Initialised. storage=%s", root)

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════

    def capture(
        self,
        snapshot: MarketSnapshot,
        symbols: Optional[List[str]] = None,
    ) -> DailyMarketSnapshot:
        """
        Capture the complete market state into an immutable daily snapshot.

        Args:
            snapshot: MarketSnapshot. snapshot.timestamp MUST be ≤ 09:15 IST.
            symbols:  Optional symbol subset. None → FeatureExtractor.SYMBOL_UNIVERSE.

        Returns:
            DailyMarketSnapshot — persisted atomically to disk.

        Raises:
            TemporalContractViolation: snapshot.timestamp > 09:15 IST
            MarketObserverError: universe_size < MLSConfig.min_universe_size
        """
        self._verify_temporal_contract(snapshot.timestamp)
        t_start = datetime.now()

        symbol_features = self._fe.extract(snapshot, symbols)

        if len(symbol_features) < self._config.min_universe_size:
            raise MarketObserverError(
                f"Universe size {len(symbol_features)} is below "
                f"min_universe_size={self._config.min_universe_size}"
            )

        trading_date  = snapshot.timestamp.date().isoformat()
        feature_ts    = snapshot.timestamp.isoformat()
        snapshot_id   = f"MLS-SNAP-{trading_date.replace('-', '')}"
        run_id        = (
            f"MLS-OBS-{trading_date.replace('-', '')}"
            f"-{snapshot.timestamp.strftime('%H%M%S')}"
        )
        feature_count = len(symbol_features[0].features) if symbol_features else 0

        observations = [
            MarketObservation(
                symbol=sf.symbol,
                feature_timestamp=feature_ts,
                features=sf.features,
                feature_count=len(sf.features),
            )
            for sf in symbol_features
        ]

        metadata = ObservationMetadata(
            run_id=run_id,
            trading_date=trading_date,
            capture_time=t_start.isoformat(),
            universe_size=len(observations),
            feature_count=feature_count,
            snapshot_id=snapshot_id,
            temporal_contract_verified=True,
            regime=snapshot.regime.value if snapshot.regime else "unknown",
            volatility=snapshot.volatility.value if snapshot.volatility else "unknown",
            vix=float(snapshot.vix or 0.0),
            pcr=float(snapshot.pcr or 1.0),
            breadth=float(snapshot.market_breadth or 0.5),
            global_bias=float(snapshot.global_sentiment_score or 0.0),
            mls_config_hash=self._config.config_hash(),
        )

        daily = DailyMarketSnapshot(
            snapshot_id=snapshot_id,
            trading_date=trading_date,
            feature_timestamp=feature_ts,
            regime=snapshot.regime.value if snapshot.regime else "unknown",
            volatility=snapshot.volatility.value if snapshot.volatility else "unknown",
            vix=float(snapshot.vix or 0.0),
            pcr=float(snapshot.pcr or 1.0),
            breadth=float(snapshot.market_breadth or 0.5),
            global_bias=float(snapshot.global_sentiment_score or 0.0),
            universe_size=len(observations),
            symbols=[o.symbol for o in observations],
            observations=observations,
            metadata=metadata,
            created_at=t_start.isoformat(),
        )

        self._persist(daily)
        log.info(
            "[MarketObserver] %s captured: %d symbols, %d features/symbol",
            snapshot_id, len(observations), feature_count,
        )
        return daily

    def load_snapshot(self, trading_date: str) -> Optional[DailyMarketSnapshot]:
        """
        Load a previously captured snapshot by trading date.

        Args:
            trading_date: ISO date string, e.g. "2026-08-03"

        Returns:
            DailyMarketSnapshot, or None if no snapshot exists for that date.
        """
        path = self._path_for(trading_date)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return DailyMarketSnapshot.from_dict(json.load(fh))

    def list_snapshots(self) -> List[str]:
        """
        Return all available snapshot dates as sorted ISO strings.

        Returns:
            List[str] of ISO date strings, ascending.
        """
        self._ensure_dirs()
        dates = [
            p.stem.removeprefix("snapshot_")
            for p in self._snapshots_dir.glob("snapshot_*.json")
        ]
        return sorted(dates)

    def statistics(self) -> ObservationStatistics:
        """
        Return aggregate statistics across all stored snapshots.

        Also includes session-level temporal_violations_detected count.
        """
        dates = self.list_snapshots()
        if not dates:
            return ObservationStatistics(
                total_snapshots=0,
                date_range_start=None,
                date_range_end=None,
                total_observations=0,
                avg_universe_size=0.0,
                avg_feature_count=0.0,
                regimes_observed=[],
                temporal_violations_detected=self._violation_count,
            )

        total_obs  = 0
        total_feat = 0
        regimes: set[str] = set()

        for d in dates:
            snap = self.load_snapshot(d)
            if snap is None:
                continue
            total_obs  += snap.universe_size
            total_feat += snap.metadata.feature_count
            if snap.regime:
                regimes.add(snap.regime)

        n = len(dates)
        return ObservationStatistics(
            total_snapshots=n,
            date_range_start=dates[0],
            date_range_end=dates[-1],
            total_observations=total_obs,
            avg_universe_size=round(total_obs / n, 2),
            avg_feature_count=round(total_feat / n, 2),
            regimes_observed=sorted(regimes),
            temporal_violations_detected=self._violation_count,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE
    # ═══════════════════════════════════════════════════════════════════════

    def _verify_temporal_contract(self, ts: datetime) -> None:
        """Raise TemporalContractViolation if ts > deadline IST."""
        ts_ist = ts.astimezone(_IST) if ts.tzinfo is not None else ts
        deadline = dtime(
            self._config.feature_deadline_hour,
            self._config.feature_deadline_minute,
            self._config.feature_deadline_second,
        )
        if ts_ist.time() > deadline:
            self._violation_count += 1
            raise TemporalContractViolation(
                f"Feature timestamp {ts_ist.strftime('%H:%M:%S')} IST "
                f"exceeds deadline {deadline} IST. "
                "All features must be captured at or before market open."
            )

    def _persist(self, snap: DailyMarketSnapshot) -> None:
        """Atomic write: write to .tmp then os.replace; keep .bak of previous."""
        self._ensure_dirs()
        path = self._path_for(snap.trading_date)
        tmp  = path.with_suffix(".tmp")
        with self._lock:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(snap.to_dict(), fh, indent=2)
            if path.exists():
                path.with_suffix(".bak").write_bytes(path.read_bytes())
            os.replace(tmp, path)

    def _path_for(self, trading_date: str) -> Path:
        return self._snapshots_dir / f"snapshot_{trading_date}.json"

    def _ensure_dirs(self) -> None:
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)
