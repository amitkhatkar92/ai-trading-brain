"""
market_learning — MLS (Market Learning System) package.

MLS Phase 1: MarketObserver.
MLS Phase 2: PopulationClassifier.
MLS Phase 3: DNADiscoveryEngine.
MLS Phase 4: DNAConsensusEngine.
MLS Phase 5: PMCIEngine.
MLS Phase 5A: MCIEngine.
MLS Phase 5A.1: CDSEngine.
MLS Phase 5B: CAPMCIEngine.
R-013: IDRRepository.
R-001 Phase 1: PlatformIntelligenceGateway.

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

Phase 5 models:
    PMCIResult, PMCIComponent, PMCIEvidence, PMCIBreakdown, PMCIStatistics

Phase 5A models:
    MarketContext, ContextComponent, ContextHistory, ContextDrift, ContextStatistics

Phase 5A.1 models:
    ContextualDNAScore, DNAContextContribution, DNAContextEvidence, DNAContextSimilarity,
    DNAContextProfile, DNAContextHistory, CDSLibraryResult, DNAContextStatistics,
    DNARelevance, ContextStabilityLabel

Phase 5B models:
    CAPMCIResult, CAPMCIStatistics, ContextAdjustment

R-013 IDR models:
    InstitutionalDNA, DNARevision, DNAEvidence, DNAHistory, DNAContext,
    DNARepositoryStatistics

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
from .pmci_engine import PMCIEngine
from .pmci_models import (
    PMCIBreakdown,
    PMCIComponent,
    PMCIError,
    PMCIEvidence,
    PMCIInputError,
    PMCIResult,
    PMCIStatistics,
)
from .mcie_engine import MCIEngine
from .mcie_models import (
    ContextComponent,
    ContextDrift,
    ContextHistory,
    ContextStatistics,
    MarketContext,
    MCIEError,
    MCIEInputError,
)
from .cds_engine import CDSEngine
from .cds_models import (
    CDSError,
    CDSInputError,
    CDSLibraryResult,
    ContextStabilityLabel,
    ContextualDNAScore,
    DNAContextContribution,
    DNAContextEvidence,
    DNAContextHistory,
    DNAContextProfile,
    DNAContextSimilarity,
    DNAContextStatistics,
    DNARelevance,
)
from .ca_pmci_engine import CAPMCIEngine
from .ca_pmci_models import (
    CAPMCIError,
    CAPMCIInputError,
    CAPMCIResult,
    CAPMCIStatistics,
    ContextAdjustment,
)
from .idr_repository import IDRRepository
from .idr_models import (
    DNAContext,
    DNAEvidence,
    DNAHistory,
    DNARepositoryStatistics,
    DNARevision,
    IDRError,
    IDRIntegrityError,
    IDRNotFoundError,
    IDRVersionError,
    InstitutionalDNA,
)
from .pig_gateway import PlatformIntelligenceGateway
from .pig_models import (
    PlatformConfidence,
    PlatformEvidence,
    PlatformGatewayError,
    PlatformGatewayInputError,
    PlatformGatewayStatistics,
    PlatformGatewaySymbolNotFoundError,
    PlatformIntelligence,
    PlatformRecommendationContext,
)
from .pig_integration import (
    PIGCallRecord,
    PIGInfluencePolicy,
    PIGTelemetry,
    PIGTradingAdapter,
    pig_build_vote,
    pig_enrich_signals,
)
from .amls import AutonomousMarketLearningScheduler
from .amls_config import AMLSConfig
from .amls_models import (

    ALL_STAGES,
    STAGE_SNAPSHOT,
    STAGE_CLASSIFY,
    STAGE_DISCOVER,
    STAGE_CONSENSUS,
    STAGE_IDR_SYNC,
    STAGE_PIG_REFRESH,
    STAGE_REPORT,
    MLSPipelineRun,
    PipelineFailure,
    PipelineHealth,
    PipelineStage,
    PipelineState,
    PipelineStatistics,
    PipelineTelemetry,
)
from .dre_engine import DNAReinforcementEngine
from .dre_config import DREConfig
from .dre_models import (

    DNAReinforcement,
    DNAConfidenceUpdate,
    DNAReinforcementHistory,
    DREError,
    DREInputError,
    DREProcessingError,
    OutcomeQuality,
    ReinforcementEvidence,
    ReinforcementStatistics,
    ReinforcementType,
)
from .mlc_config import MLCConfig
from .mlc_models import (
    LearningHealth,
    LearningRun,
    LearningSummary,
    LearningStage,
    LearningStageStatus,
    LearningStageType,
    LearningTelemetry,
    MLCError,
    MLCStageError,
)
from .market_learning_coordinator import MarketLearningCoordinator

__all__ = [
    # engines
    "MarketObserver",
    "PopulationClassifier",
    "DNADiscoveryEngine",
    "DNAConsensusEngine",
    "PMCIEngine",
    "MCIEngine",
    "CAPMCIEngine",
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
    # Phase 5
    "PMCIEngine",
    "PMCIBreakdown",
    "PMCIComponent",
    "PMCIError",
    "PMCIEvidence",
    "PMCIInputError",
    "PMCIResult",
    "PMCIStatistics",
    # Phase 5A
    "MCIEngine",
    "ContextComponent",
    "ContextDrift",
    "ContextHistory",
    "ContextStatistics",
    "MarketContext",
    "MCIEError",
    "MCIEInputError",
    # Phase 5A.1
    "CDSEngine",
    "CDSError",
    "CDSInputError",
    "CDSLibraryResult",
    "ContextStabilityLabel",
    "ContextualDNAScore",
    "DNAContextContribution",
    "DNAContextEvidence",
    "DNAContextHistory",
    "DNAContextProfile",
    "DNAContextSimilarity",
    "DNAContextStatistics",
    "DNARelevance",
    # Phase 5B
    "CAPMCIEngine",
    "CAPMCIError",
    "CAPMCIInputError",
    "CAPMCIResult",
    "CAPMCIStatistics",
    "ContextAdjustment",
    # R-013 — IDRRepository
    "IDRRepository",
    "DNAContext",
    "DNAEvidence",
    "DNAHistory",
    "DNARepositoryStatistics",
    "DNARevision",
    "IDRError",
    "IDRIntegrityError",
    "IDRNotFoundError",
    "IDRVersionError",
    "InstitutionalDNA",
    # R-001 — PlatformIntelligenceGateway
    "PlatformIntelligenceGateway",
    "PlatformConfidence",
    "PlatformEvidence",
    "PlatformGatewayError",
    "PlatformGatewayInputError",
    "PlatformGatewayStatistics",
    "PlatformGatewaySymbolNotFoundError",
    "PlatformIntelligence",
    "PlatformRecommendationContext",
    # R-001 Phase 2 — PIG Integration
    "PIGCallRecord",
    "PIGInfluencePolicy",
    "PIGTelemetry",
    "PIGTradingAdapter",
    "pig_build_vote",
    "pig_enrich_signals",
    # MLS Phase 6 — AMLS
    "AutonomousMarketLearningScheduler",
    "AMLSConfig",
    "ALL_STAGES",
    "STAGE_SNAPSHOT",
    "STAGE_CLASSIFY",
    "STAGE_DISCOVER",
    "STAGE_CONSENSUS",
    "STAGE_IDR_SYNC",
    "STAGE_PIG_REFRESH",
    "STAGE_REPORT",
    "MLSPipelineRun",
    "PipelineFailure",
    "PipelineHealth",
    "PipelineStage",
    "PipelineState",
    "PipelineStatistics",
    "PipelineTelemetry",
    # O-002 — DNA Reinforcement Engine
    "DNAReinforcementEngine",
    "DREConfig",
    "DNAReinforcement",
    "DNAConfidenceUpdate",
    "DNAReinforcementHistory",
    "DREError",
    "DREInputError",
    "DREProcessingError",
    "OutcomeQuality",
    "ReinforcementEvidence",
    "ReinforcementStatistics",
    "ReinforcementType",
    # MarketLearningCoordinator
    "MarketLearningCoordinator",
    "MLCConfig",
    "LearningHealth",
    "LearningRun",
    "LearningSummary",
    "LearningStage",
    "LearningStageStatus",
    "LearningStageType",
    "LearningTelemetry",
    "MLCError",
    "MLCStageError",
]
