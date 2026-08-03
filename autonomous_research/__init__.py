"""
autonomous_research — ARS Phase 1 package.

Exports:
    KnowledgeProvider    — unified read-only knowledge access layer (Phase 1.1)
    HypothesisRegistry   — scientific hypothesis store (Phase 1.2)
"""
from .knowledge_provider import KnowledgeProvider
from .hypothesis_registry import HypothesisRegistry
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
    "HypothesisNotFoundError",
    "DuplicateHypothesisError",
    "InvalidTransitionError",
    "InvalidEvidenceError",
    "RegistryValidationError",
]
