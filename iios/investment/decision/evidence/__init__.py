"""iios/investment/decision/evidence/__init__.py
Public surface of the Evidence Collection Engine.
"""
from iios.investment.decision.evidence.evidence_constants import (
    EvidenceSourceType,
    EvidenceCategory,
    EvidencePriority,
    EvidenceStatus,
    EvidenceValidationStatus,
    EvidenceEventType,
    EvidenceEngineStatus,
    EvidenceQualityDimension,
    EVIDENCE_FRESHNESS_WARN_SECONDS,
    EVIDENCE_FRESHNESS_STALE_SECONDS,
    MIN_COVERAGE_FRACTION,
    MIN_CONFIDENCE_THRESHOLD,
    DEFAULT_COLLECTION_TIMEOUT_SECS,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.evidence_package import EvidencePackage
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot, build_snapshot
from iios.investment.decision.evidence.evidence_history import EvidenceHistory
from iios.investment.decision.evidence.evidence_statistics import (
    EvidenceStatistics,
    EvidenceStatisticsTracker,
)
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider
from iios.investment.decision.evidence.provider_registry import ProviderRegistry, DuplicateProviderError, UnknownProviderError
from iios.investment.decision.evidence.market_evidence import MarketEvidenceProvider
from iios.investment.decision.evidence.company_evidence import CompanyEvidenceProvider
from iios.investment.decision.evidence.strategy_evidence import StrategyEvidenceProvider
from iios.investment.decision.evidence.risk_evidence import RiskEvidenceProvider
from iios.investment.decision.evidence.knowledge_evidence import KnowledgeEvidenceProvider
from iios.investment.decision.evidence.research_evidence import ResearchEvidenceProvider
from iios.investment.decision.evidence.freshness_validator import FreshnessValidator, FreshnessReport
from iios.investment.decision.evidence.consistency_checker import ConsistencyChecker, ConsistencyReport, Conflict
from iios.investment.decision.evidence.coverage_validator import CoverageValidator, CoverageReport
from iios.investment.decision.evidence.evidence_validator import EvidenceValidator, ValidationResult
from iios.investment.decision.evidence.priority_engine import PriorityEngine
from iios.investment.decision.evidence.relevance_engine import RelevanceEngine
from iios.investment.decision.evidence.confidence_engine import ConfidenceEngine
from iios.investment.decision.evidence.evidence_ranker import EvidenceRanker
from iios.investment.decision.evidence.event_timeline import EventTimeline, TimelineEvent
from iios.investment.decision.evidence.historical_evidence import HistoricalEvidence
from iios.investment.decision.evidence.change_tracker import ChangeTracker, ChangeReport, ValueChange
from iios.investment.decision.evidence.timeline_engine import TimelineEngine
from iios.investment.decision.evidence.quality_score import QualityScore, compute_quality_score
from iios.investment.decision.evidence.quality_statistics import QualityStatistics, QualityStatisticsTracker
from iios.investment.decision.evidence.quality_history import QualityHistory
from iios.investment.decision.evidence.evidence_quality import EvidenceQuality
from iios.investment.decision.evidence.evidence_collection_engine import EvidenceCollectionEngine

__all__ = [
    # constants / enums
    "EvidenceSourceType", "EvidenceCategory", "EvidencePriority", "EvidenceStatus",
    "EvidenceValidationStatus", "EvidenceEventType", "EvidenceEngineStatus",
    "EvidenceQualityDimension",
    "EVIDENCE_FRESHNESS_WARN_SECONDS", "EVIDENCE_FRESHNESS_STALE_SECONDS",
    "MIN_COVERAGE_FRACTION", "MIN_CONFIDENCE_THRESHOLD", "DEFAULT_COLLECTION_TIMEOUT_SECS",
    # models
    "EvidenceItem", "make_evidence_item", "EvidencePackage",
    "EvidenceSnapshot", "build_snapshot",
    "EvidenceHistory", "EvidenceStatistics", "EvidenceStatisticsTracker",
    # providers
    "BaseEvidenceProvider", "ProviderRegistry",
    "DuplicateProviderError", "UnknownProviderError",
    "MarketEvidenceProvider", "CompanyEvidenceProvider",
    "StrategyEvidenceProvider", "RiskEvidenceProvider",
    "KnowledgeEvidenceProvider", "ResearchEvidenceProvider",
    # validation
    "FreshnessValidator", "FreshnessReport",
    "ConsistencyChecker", "ConsistencyReport", "Conflict",
    "CoverageValidator", "CoverageReport",
    "EvidenceValidator", "ValidationResult",
    # ranking
    "PriorityEngine", "RelevanceEngine", "ConfidenceEngine", "EvidenceRanker",
    # timeline
    "EventTimeline", "TimelineEvent",
    "HistoricalEvidence",
    "ChangeTracker", "ChangeReport", "ValueChange",
    "TimelineEngine",
    # quality
    "QualityScore", "compute_quality_score",
    "QualityStatistics", "QualityStatisticsTracker",
    "QualityHistory", "EvidenceQuality",
    # facade
    "EvidenceCollectionEngine",
]
