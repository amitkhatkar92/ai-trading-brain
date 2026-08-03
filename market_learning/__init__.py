"""
market_learning — MLS (Market Learning System) package.

MLS Phase 1: MarketObserver.

Exports:
    MarketObserver        — observation layer (Phase 1)
    MLSConfig             — all configurable thresholds
    DailyMarketSnapshot   — immutable daily feature snapshot
    MarketObservation     — per-symbol pre-move feature vector
    ObservationMetadata   — capture run provenance
    ObservationStatistics — aggregate statistics across snapshots

Exceptions:
    TemporalContractViolation — feature_timestamp > 09:15 IST
    MarketObserverError       — general observer error
    SnapshotNotFoundError     — requested snapshot does not exist
"""
from .mls_config import MLSConfig
from .market_observer import MarketObserver
from .market_observer_models import (
    DailyMarketSnapshot,
    MarketObservation,
    MarketObserverError,
    ObservationMetadata,
    ObservationStatistics,
    SnapshotNotFoundError,
    TemporalContractViolation,
)

__all__ = [
    "MarketObserver",
    "MLSConfig",
    "DailyMarketSnapshot",
    "MarketObservation",
    "MarketObserverError",
    "ObservationMetadata",
    "ObservationStatistics",
    "SnapshotNotFoundError",
    "TemporalContractViolation",
]
