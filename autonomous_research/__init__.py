"""
autonomous_research — ARS package.

Exports:
    KnowledgeProvider      — unified read-only knowledge access layer (Phase 1.1)
    HypothesisRegistry     — scientific hypothesis store (Phase 1.2)
    CrossStudySynthesizer  — cross-study knowledge synthesis engine (Phase 1.3)
    GapDetector            — scientific knowledge gap detection engine (Phase 2A)
    RoadmapManager         — scientific research prioritization engine (Phase 2B)
    EvidenceValidator      — scientific quality gate engine (Phase 2C)
    StudyPlanner           — scientific experiment design engine (Phase 2D)
    ResearchCoordinator    — operational research orchestrator (Phase 3A)
    RCConfig               — ResearchCoordinator configuration (Phase 3A)
    ScientificDirector     — apex scientific authority (Phase 3C)
    SDConfig               — ScientificDirector configuration (Phase 3C)
    ScientificJournal      — structured scientific memory (Phase 3C)
    PointInTimeUniverseEngine — historical universe provider (R-006)
    PTUEConfig             — PTUE configuration (R-006)
    MethodologyAuditor     — mandatory methodology audit stage (IRP-002A)
    AuditResult            — audit result data model (IRP-002A)
"""
from .knowledge_provider import KnowledgeProvider
from .hypothesis_registry import HypothesisRegistry
from .cross_study_synthesizer import CrossStudySynthesizer
from .gap_detector import GapDetector
from .roadmap_manager import RoadmapManager
from .evidence_validator import EvidenceValidator
from .study_planner import StudyPlanner
from .methodology_auditor import MethodologyAuditor, AuditResult, AuditVerdict, AuditCheck
from .study_planner_models import (
    ApprovalClass,
    DatasetRequirement,
    ExecutionEstimate,
    PlanningStatistics,
    PlanStatus,
    RiskClass,
    StudyDependency,
    StudyPlan,
    StudyPlannerConfig,
    StudyPlannerError,
    StudyPlanNotFoundError,
    StudyPortfolio,
    StudyTask,
    StudyType,
    ValidationPlan,
)
from .evidence_validator_models import (
    EvidenceQualityScore,
    EvidenceValidation,
    EvidenceValidatorConfig,
    EvidenceValidatorError,
    GateResult,
    GateStatus,
    ValidationOutcome,
    ValidationStatistics,
    ValidationSubjectNotFoundError,
    ValidationSummary,
)
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
    # Phase 2C
    "EvidenceValidator",
    "EvidenceValidatorConfig",
    "EvidenceValidation",
    "EvidenceQualityScore",
    "GateResult",
    "GateStatus",
    "ValidationOutcome",
    "ValidationStatistics",
    "ValidationSummary",
    "EvidenceValidatorError",
    "ValidationSubjectNotFoundError",
    # Phase 3A — ResearchCoordinator
    "ResearchCoordinator",
    "RCConfig",
    "ResearchHealth",
    "ResearchRun",
    "ResearchStage",
    "ResearchStageState",
    "ResearchSummary",
    "ResearchTelemetry",
    "RCStatus",
    "RCError",
    "RCStageError",
    "make_rc_run_id",
    "RC_ALL_STAGES",
    "RC_ALWAYS_RUN",
    "STAGE_STUDY_PLAN",
    "STAGE_REPLAY",
    "STAGE_VALIDATION",
    "STAGE_EVIDENCE",
    "STAGE_KNOWLEDGE",
    "STAGE_SYNTHESIS",
    "STAGE_REPOSITORY",
    "STAGE_REPORT",
    # Phase 3C — ScientificDirector
    "ScientificDirector",
    "SDConfig",
    "ScientificJournal",
    "JournalEntry",
    "DecisionClass",
    "DecisionType",
    "ReviewType",
    "SDError",
    "SDHealth",
    "SDObservationError",
    "ScientificDecision",
    "ScientificHealth",
    "ScientificObservation",
    "ScientificReasoning",
    "ScientificRecommendation",
    "ScientificReview",
    "ScientificRoadmap",
    "SignificanceLevel",
    "UrgencyLevel",
    "make_decision_id",
    "make_observation_id",
    "make_recommendation_id",
    "make_review_id",
    # R-006 — PointInTimeUniverseEngine
    "PointInTimeUniverseEngine",
    "PTUEConfig",
    "Constituent",
    "UniverseVersion",
    "HistoricalUniverse",
    "UniverseStatistics",
    "CoverageReport",
    "PTUEError",
    "UniverseNotFoundError",
    "InvalidDateError",
    "UNIVERSE_NIFTY500",
    "UNIVERSE_NIFTY100",
    "UNIVERSE_NIFTY50",
    "SOURCE_HISTORY_FILE",
    "SOURCE_STATIC_FALLBACK",
    "SOURCE_EMPTY",
]
from .research_coordinator import ResearchCoordinator
from .rc_config import RCConfig
from .rc_models import (
    ResearchHealth,
    ResearchRun,
    ResearchStage,
    ResearchStageState,
    ResearchSummary,
    ResearchTelemetry,
    RCStatus,
    RCError,
    RCStageError,
    make_rc_run_id,
    RC_ALL_STAGES,
    RC_ALWAYS_RUN,
    STAGE_STUDY_PLAN,
    STAGE_REPLAY,
    STAGE_VALIDATION,
    STAGE_EVIDENCE,
    STAGE_KNOWLEDGE,
    STAGE_SYNTHESIS,
    STAGE_REPOSITORY,
    STAGE_REPORT,
)
# Phase 3C — ScientificDirector (apex scientific authority)
from .scientific_director import ScientificDirector
from .sd_config import SDConfig
from .scientific_journal import ScientificJournal, JournalEntry
from .sd_models import (
    DecisionClass,
    DecisionType,
    ReviewType,
    SDError,
    SDHealth,
    SDObservationError,
    ScientificDecision,
    ScientificHealth,
    ScientificObservation,
    ScientificReasoning,
    ScientificRecommendation,
    ScientificReview,
    ScientificRoadmap,
    SignificanceLevel,
    UrgencyLevel,
    make_decision_id,
    make_observation_id,
    make_recommendation_id,
    make_review_id,
)
# R-006 — Point-in-Time Universe Engine
from .ptue import PointInTimeUniverseEngine
from .ptue_config import PTUEConfig
from .ptue_models import (
    Constituent,
    CoverageReport,
    HistoricalUniverse,
    InvalidDateError,
    PTUEError,
    SOURCE_EMPTY,
    SOURCE_HISTORY_FILE,
    SOURCE_STATIC_FALLBACK,
    UNIVERSE_NIFTY100,
    UNIVERSE_NIFTY50,
    UNIVERSE_NIFTY500,
    UniverseNotFoundError,
    UniverseStatistics,
    UniverseVersion,
)
