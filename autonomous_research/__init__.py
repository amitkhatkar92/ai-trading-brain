"""
autonomous_research — ARS package.

Exports:
    KnowledgeProvider      — unified read-only knowledge access layer (Phase 1.1)
    HypothesisRegistry     — scientific hypothesis store (Phase 1.2)
    CrossStudySynthesizer  — cross-study knowledge synthesis engine (Phase 1.3)
    GapDetector            — scientific knowledge gap detection engine (Phase 2A)
    RoadmapManager         — scientific research prioritization engine (Phase 2B)
"""
from .knowledge_provider import KnowledgeProvider
from .hypothesis_registry import HypothesisRegistry
from .cross_study_synthesizer import CrossStudySynthesizer
from .gap_detector import GapDetector
from .roadmap_manager import RoadmapManager
from .gap_models import (
    DetectionError,
    GapCategory,
    GapDetectionReport,
    GapDetectorConfig,
    GapDetectorError,
    GapSeverity,
    GapStatistics,
    GapStatus,
    KnowledgeGap,
)
from .roadmap_models import (
    KnowledgeGainEstimate,
    ResearchCostEstimate,
    ResearchDebt,
    ResearchPortfolio,
    ResearchRoadmap,
    RoadmapBuildError,
    RoadmapEntry,
    RoadmapEntryStatus,
    RoadmapManagerConfig,
    RoadmapManagerError,
    RoadmapStatistics,
    StudyCategory,
)
from .hypothesis_models import (
    DecisionEvent,
    DuplicateHypothesisError,
    EvidenceReference,
    EvidenceType,
    HypothesisClassification,
    HypothesisNotFoundError,
    HypothesisPriority,
    HypothesisStatus,
    InvalidEvidenceError,
    InvalidTransitionError,
    RegistryError,
    RegistryValidationError,
    ScientificHypothesis,
    ValidationResult,
    VALID_TRANSITIONS,
    OPEN_STATUSES,
)
from .models import (
    Certification,
    EdgeRecord,
    EdgeStatus,
    Evidence,
    FeatureRecord,
    Finding,
    FindingClassification,
    KnowledgeMetric,
    KnowledgeSnapshot,
    KnowledgeStore,
    LoadSeverity,
    LoadWarning,
    RegimeProbabilityRecord,
    ReplaySummary,
    ResearchStudy,
    StrategyRecord,
)

__all__ = [
    # Phase 1.1
    "KnowledgeProvider",
    "Certification",
    "EdgeRecord",
    "EdgeStatus",
    "Evidence",
    "FeatureRecord",
    "Finding",
    "FindingClassification",
    "KnowledgeMetric",
    "KnowledgeSnapshot",
    "KnowledgeStore",
    "LoadSeverity",
    "LoadWarning",
    "RegimeProbabilityRecord",
    "ReplaySummary",
    "ResearchStudy",
    "StrategyRecord",
    # Phase 1.2
    "HypothesisRegistry",
    "ScientificHypothesis",
    "HypothesisStatus",
    "HypothesisPriority",
    "HypothesisClassification",
    "EvidenceReference",
    "EvidenceType",
    "DecisionEvent",
    "ValidationResult",
    "VALID_TRANSITIONS",
    "OPEN_STATUSES",
    "RegistryError",
    # Phase 1.3
    "CrossStudySynthesizer",
    "HypothesisNotFoundError",
    "DuplicateHypothesisError",
    "InvalidTransitionError",
    "InvalidEvidenceError",
    "RegistryValidationError",
    # Phase 2A
    "GapDetector",
    "GapDetectorConfig",
    "GapCategory",
    "GapSeverity",
    "GapStatus",
    "KnowledgeGap",
    "GapDetectionReport",
    "GapStatistics",
    "GapDetectorError",
    "DetectionError",
    # Phase 2B
    "RoadmapManager",
    "RoadmapManagerConfig",
    "StudyCategory",
    "RoadmapEntry",
    "RoadmapEntryStatus",
    "KnowledgeGainEstimate",
    "ResearchCostEstimate",
    "ResearchDebt",
    "ResearchPortfolio",
    "ResearchRoadmap",
    "RoadmapStatistics",
    "RoadmapManagerError",
    "RoadmapBuildError",
]
