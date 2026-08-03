"""
market_learning — MLS (Market Learning System) package.

MLS Phase 1: MarketObserver.
MLS Phase 2: PopulationClassifier.
MLS Phase 3: DNADiscoveryEngine.
MLS Phase 4: DNAConsensusEngine.

Exports:
    MarketObserver        — observation layer (Phase 1)
    PopulationClassifier  — classification layer (Phase 2)
    DNADiscoveryEngine    — discovery layer (Phase 3)
    DNAConsensusEngine    — consensus layer (Phase 4)
    MLSConfig             — all configurable thresholds

Phase 1 models:
    DailyMarketSnapshot, MarketObservation, ObservationMetadata,
    ObservationStatistics

Phase 2 models:
    Population, PopulationMember, ClassificationResult, PopulationStatistics,
    ClassifierType, GroupLabel

Phase 3 models:
    DNACharacteristic, DNAInteraction, DNALifecycle, FeatureEvidence,
    FeatureType, SeparationDirection, WinnerDNA, LoserDNA, NeutralDNA,
    DiscoveryReport, DNAStatistics

Phase 4 models:
    ConsensusDNA, ConsensusLibrary, ConsensusLevel, ConsensusState,
    ConfidenceEvolution, ConfidencePoint, DriftReport, DriftMeasurement,
    DriftType, DNAStability, ConsensusStatistics

Exceptions:
    TemporalContractViolation, MarketObserverError, SnapshotNotFoundError,
    PopulationClassifierError, ClassificationNotFoundError, OrphanStockError,
    DNADiscoveryError, InsufficientDataError, DiscoveryNotFoundError,
    DNAConsensusError, ConsensusLibraryNotFoundError
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
from .dna_consensus_engine import DNAConsensusEngine
from .dna_consensus_models import (
    ConsensusDNA,
    ConsensusLevel,
    ConsensusLibrary,
    ConsensusState,
    ConsensusStatistics,
    ConfidenceEvolution,
    ConfidencePoint,
    DNAConsensusError,
    DNAStability,
    DriftMeasurement,
    DriftReport,
    DriftType,
    ConsensusLibraryNotFoundError,
)

__all__ = [
    # engines
    "MarketObserver",
    "PopulationClassifier",
    "DNADiscoveryEngine",
    "DNAConsensusEngine",
    "MLSConfig",
    # Phase 1
    "DailyMarketSnapshot",
    "MarketObservation",
    "MarketObserverError",
    "ObservationMetadata",
    "ObservationStatistics",
    "SnapshotNotFoundError",
    "TemporalContractViolation",
    # Phase 2
    "ClassificationNotFoundError",
    "ClassificationResult",
    "ClassifierType",
    "GroupLabel",
    "OrphanStockError",
    "Population",
    "PopulationClassifierError",
    "PopulationMember",
    "PopulationStatistics",
    # Phase 3
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
    # Phase 4
    "ConsensusDNA",
    "ConsensusLevel",
    "ConsensusLibrary",
    "ConsensusState",
    "ConsensusStatistics",
    "ConfidenceEvolution",
    "ConfidencePoint",
    "DNAConsensusError",
    "DNAStability",
    "DriftMeasurement",
    "DriftReport",
    "DriftType",
    "ConsensusLibraryNotFoundError",
]
