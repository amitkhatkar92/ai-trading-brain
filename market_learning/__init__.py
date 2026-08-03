"""
market_learning — MLS (Market Learning System) package.

MLS Phase 1: MarketObserver.
MLS Phase 2: PopulationClassifier.
MLS Phase 3: DNADiscoveryEngine.

Exports:
    MarketObserver        — observation layer (Phase 1)
    PopulationClassifier  — classification layer (Phase 2)
    DNADiscoveryEngine    — discovery layer (Phase 3)
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
    DNACharacteristic     — a verified pre-move feature characteristic
    DNAInteraction        — super-additive feature pair
    DNALifecycle          — lifecycle state of a characteristic
    FeatureEvidence       — raw statistical evidence
    FeatureType           — continuous/binary/ordinal/categorical
    SeparationDirection   — direction of feature separation
    WinnerDNA             — winner population DNA profile
    LoserDNA              — loser population DNA profile
    NeutralDNA            — neutral population DNA profile
    DiscoveryReport       — complete daily discovery output
    DNAStatistics         — aggregate statistics for one discovery

Exceptions:
    TemporalContractViolation    — feature_timestamp > 09:15 IST
    MarketObserverError          — general observer error
    SnapshotNotFoundError        — snapshot not found
    PopulationClassifierError    — general classifier error
    ClassificationNotFoundError  — classification not found
    OrphanStockError             — stock failed to be classified
    DNADiscoveryError            — general discovery error
    InsufficientDataError        — group too small for analysis
    DiscoveryNotFoundError       — discovery report not found
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
from .dna_discovery_engine import DNADiscoveryEngine
from .dna_discovery_models import (
    DNACharacteristic,
    DNADiscoveryError,
    DNAInteraction,
    DNALifecycle,
    DNAStatistics,
    DiscoveryNotFoundError,
    DiscoveryReport,
    FeatureEvidence,
    FeatureType,
    InsufficientDataError,
    LoserDNA,
    NeutralDNA,
    SeparationDirection,
    WinnerDNA,
)

__all__ = [
    "MarketObserver",
    "PopulationClassifier",
    "DNADiscoveryEngine",
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
    "DNACharacteristic",
    "DNADiscoveryError",
    "DNAInteraction",
    "DNALifecycle",
    "DNAStatistics",
    "DiscoveryNotFoundError",
    "DiscoveryReport",
    "FeatureEvidence",
    "FeatureType",
    "InsufficientDataError",
    "LoserDNA",
    "NeutralDNA",
    "SeparationDirection",
    "WinnerDNA",
]
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
