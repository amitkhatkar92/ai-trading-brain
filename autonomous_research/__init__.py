"""
autonomous_research — ARS Phase 1 package.

Exports:
    KnowledgeProvider  — unified read-only knowledge access layer
"""
from .knowledge_provider import KnowledgeProvider
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
]
