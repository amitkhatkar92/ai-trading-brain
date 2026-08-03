"""
market_observer_models.py — Typed models for the MLS MarketObserver.

MLS Phase 1.

Pure data.  No business logic.  All fields JSON-serialisable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─── exceptions ───────────────────────────────────────────────────────────────

class TemporalContractViolation(Exception):
    """
    Raised when feature_timestamp > 09:15 IST.

    The temporal contract (INV-01 in MLS_DATAFLOW.md) requires every feature
    vector to carry a timestamp at or before 09:15 IST on trading day T.
    The measured outcome is Close(T) vs Close(T-1).
    Violating this ordering means features are not pre-move.
    """


class MarketObserverError(Exception):
    """General MarketObserver error."""


class SnapshotNotFoundError(MarketObserverError):
    """Snapshot for the requested trading date does not exist in storage."""


# ─── observation ──────────────────────────────────────────────────────────────

@dataclass
class MarketObservation:
    """Pre-move feature vector for one symbol captured before market open."""

    symbol:            str                # NSE ticker
    feature_timestamp: str                # ISO datetime ≤ 09:15 IST
    features:          Dict[str, float]   # feature_name → normalised value
    feature_count:     int                # len(features)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":            self.symbol,
            "feature_timestamp": self.feature_timestamp,
            "features":          self.features,
            "feature_count":     self.feature_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MarketObservation:
        return cls(
            symbol=d["symbol"],
            feature_timestamp=d["feature_timestamp"],
            features=d["features"],
            feature_count=int(d["feature_count"]),
        )


# ─── metadata ─────────────────────────────────────────────────────────────────

@dataclass
class ObservationMetadata:
    """Provenance record for a single MarketObserver capture run."""

    run_id:                     str         # MLS-OBS-YYYYMMDD-HHMMSS
    trading_date:               str         # ISO date
    capture_time:               str         # ISO datetime (wall-clock start)
    universe_size:              int         # symbols observed
    feature_count:              int         # features per symbol
    snapshot_id:                str         # MLS-SNAP-YYYYMMDD
    temporal_contract_verified: bool        # always True — violations are rejected
    regime:                     str
    volatility:                 str
    vix:                        float
    pcr:                        float
    breadth:                    float
    global_bias:                float
    mls_config_hash:            str         # sha256[:16] of MLSConfig at capture time
    warnings:                   List[str]   = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":                     self.run_id,
            "trading_date":               self.trading_date,
            "capture_time":               self.capture_time,
            "universe_size":              self.universe_size,
            "feature_count":              self.feature_count,
            "snapshot_id":                self.snapshot_id,
            "temporal_contract_verified": self.temporal_contract_verified,
            "regime":                     self.regime,
            "volatility":                 self.volatility,
            "vix":                        self.vix,
            "pcr":                        self.pcr,
            "breadth":                    self.breadth,
            "global_bias":                self.global_bias,
            "mls_config_hash":            self.mls_config_hash,
            "warnings":                   self.warnings,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ObservationMetadata:
        return cls(
            run_id=d["run_id"],
            trading_date=d["trading_date"],
            capture_time=d["capture_time"],
            universe_size=int(d["universe_size"]),
            feature_count=int(d["feature_count"]),
            snapshot_id=d["snapshot_id"],
            temporal_contract_verified=bool(d["temporal_contract_verified"]),
            regime=d["regime"],
            volatility=d["volatility"],
            vix=float(d["vix"]),
            pcr=float(d["pcr"]),
            breadth=float(d["breadth"]),
            global_bias=float(d["global_bias"]),
            mls_config_hash=d.get("mls_config_hash", ""),
            warnings=list(d.get("warnings", [])),
        )


# ─── daily snapshot ───────────────────────────────────────────────────────────

@dataclass
class DailyMarketSnapshot:
    """
    Complete immutable daily observation: all symbols, all features, one timestamp.

    Temporal contract:
        feature_timestamp (ISO datetime) ≤ 09:15 IST on trading_date.
        Measured outcome = Close(trading_date) vs Close(trading_date − 1 day).

    Every DNA discovery in subsequent MLS phases must originate from a
    DailyMarketSnapshot that has been validated by MarketObserver.
    """

    snapshot_id:       str                    # MLS-SNAP-YYYYMMDD
    trading_date:      str                    # ISO date
    feature_timestamp: str                    # ISO datetime ≤ 09:15 IST
    regime:            str
    volatility:        str
    vix:               float
    pcr:               float
    breadth:           float
    global_bias:       float
    universe_size:     int
    symbols:           List[str]
    observations:      List[MarketObservation]
    metadata:          ObservationMetadata
    created_at:        str                    # ISO datetime (wall-clock)

    # ── convenience ──────────────────────────────────────────────────────

    def get_observation(self, symbol: str) -> Optional[MarketObservation]:
        """Return the observation for *symbol*, or None if not present."""
        for obs in self.observations:
            if obs.symbol == symbol:
                return obs
        return None

    # ── serialisation ────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "trading_date":      self.trading_date,
            "feature_timestamp": self.feature_timestamp,
            "regime":            self.regime,
            "volatility":        self.volatility,
            "vix":               self.vix,
            "pcr":               self.pcr,
            "breadth":           self.breadth,
            "global_bias":       self.global_bias,
            "universe_size":     self.universe_size,
            "symbols":           self.symbols,
            "observations":      [o.to_dict() for o in self.observations],
            "metadata":          self.metadata.to_dict(),
            "created_at":        self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DailyMarketSnapshot:
        return cls(
            snapshot_id=d["snapshot_id"],
            trading_date=d["trading_date"],
            feature_timestamp=d["feature_timestamp"],
            regime=d["regime"],
            volatility=d["volatility"],
            vix=float(d["vix"]),
            pcr=float(d["pcr"]),
            breadth=float(d["breadth"]),
            global_bias=float(d["global_bias"]),
            universe_size=int(d["universe_size"]),
            symbols=list(d["symbols"]),
            observations=[MarketObservation.from_dict(o) for o in d["observations"]],
            metadata=ObservationMetadata.from_dict(d["metadata"]),
            created_at=d["created_at"],
        )


# ─── aggregate statistics ─────────────────────────────────────────────────────

@dataclass
class ObservationStatistics:
    """Aggregate statistics across all stored snapshots."""

    total_snapshots:              int
    date_range_start:             Optional[str]
    date_range_end:               Optional[str]
    total_observations:           int           # sum of universe_size across snapshots
    avg_universe_size:            float
    avg_feature_count:            float
    regimes_observed:             List[str]     # deduplicated, sorted
    temporal_violations_detected: int           # session-level violations caught

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_snapshots":              self.total_snapshots,
            "date_range_start":             self.date_range_start,
            "date_range_end":               self.date_range_end,
            "total_observations":           self.total_observations,
            "avg_universe_size":            self.avg_universe_size,
            "avg_feature_count":            self.avg_feature_count,
            "regimes_observed":             self.regimes_observed,
            "temporal_violations_detected": self.temporal_violations_detected,
        }
