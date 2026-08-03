"""
market_learning — MLS (Market Learning System) package.

MLS Phase 1: MarketObserver.
MLS Phase 2: PopulationClassifier.

Exports:
    MarketObserver        — observation layer (Phase 1)
    PopulationClassifier  — classification layer (Phase 2)
    MLSConfig             — all configurable thresholds
    DailyMarketSnapshot   — immutable daily feature snapshot
    MarketObservation     — per-symbol pre-move feature vector
    ObservationMetadata   — capture run provenance
    ObservationStatistics — aggregate statistics across snapshots
    Population            — a named group of stocks (Phase 2)
    PopulationMember      — a stock with all population assignments
    ClassificationResult  — complete daily classification output
    PopulationStatistics  — aggregate statistics for one classification
    ClassifierType        — 8 classification dimensions
    GroupLabel            — all possible population labels

Exceptions:
    TemporalContractViolation    — feature_timestamp > 09:15 IST
    MarketObserverError          — general observer error
    SnapshotNotFoundError        — snapshot not found
    PopulationClassifierError    — general classifier error
    ClassificationNotFoundError  — classification not found
    OrphanStockError             — stock failed to be classified
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
from .population_classifier import PopulationClassifier
from .population_classifier_models import (
    ClassificationNotFoundError,
    ClassificationResult,
    ClassifierType,
    GroupLabel,
    OrphanStockError,
    Population,
    PopulationClassifierError,
    PopulationMember,
    PopulationStatistics,
)

__all__ = [
    "MarketObserver",
    "PopulationClassifier",
    "MLSConfig",
    "DailyMarketSnapshot",
    "MarketObservation",
    "MarketObserverError",
    "ObservationMetadata",
    "ObservationStatistics",
    "SnapshotNotFoundError",
    "TemporalContractViolation",
    "ClassificationNotFoundError",
    "ClassificationResult",
    "ClassifierType",
    "GroupLabel",
    "OrphanStockError",
    "Population",
    "PopulationClassifierError",
    "PopulationMember",
    "PopulationStatistics",
]
