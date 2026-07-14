"""iios/investment/decision/evidence/evidence_constants.py
All enumerations, constants, and thresholds for the Evidence Collection Engine.
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, Set


class EvidenceSourceType(str, Enum):
    MARKET     = "market"
    COMPANY    = "company"
    STRATEGY   = "strategy"
    RISK       = "risk"
    KNOWLEDGE  = "knowledge"
    RESEARCH   = "research"
    HISTORICAL = "historical"
    EXTERNAL   = "external"

    @property
    def is_required(self) -> bool:
        return self in {
            EvidenceSourceType.MARKET,
            EvidenceSourceType.RISK,
        }

    @property
    def default_weight(self) -> float:
        _weights = {
            "market": 1.4, "company": 1.2, "strategy": 1.3,
            "risk": 1.5, "knowledge": 0.8, "research": 0.9,
            "historical": 0.7, "external": 0.6,
        }
        return _weights.get(self.value, 1.0)


class EvidenceCategory(str, Enum):
    FUNDAMENTAL  = "fundamental"
    TECHNICAL    = "technical"
    SENTIMENT    = "sentiment"
    QUANTITATIVE = "quantitative"
    QUALITATIVE  = "qualitative"
    MACRO        = "macro"
    REGULATORY   = "regulatory"
    HISTORICAL   = "historical"
    ALTERNATIVE  = "alternative"


class EvidencePriority(str, Enum):
    CRITICAL      = "critical"
    HIGH          = "high"
    MEDIUM        = "medium"
    LOW           = "low"
    SUPPLEMENTARY = "supplementary"

    @property
    def numeric(self) -> int:
        return {"critical": 5, "high": 4, "medium": 3, "low": 2, "supplementary": 1}[self.value]

    @property
    def blocks_decision(self) -> bool:
        return self == EvidencePriority.CRITICAL


class EvidenceStatus(str, Enum):
    PENDING    = "pending"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    RANKING    = "ranking"
    COMPLETE   = "complete"
    PARTIAL    = "partial"
    STALE      = "stale"
    FAILED     = "failed"

    @property
    def is_publishable(self) -> bool:
        return self in {EvidenceStatus.COMPLETE, EvidenceStatus.PARTIAL}


class EvidenceValidationStatus(str, Enum):
    PASSED           = "passed"
    PASSED_WITH_GAPS = "passed_with_gaps"
    FAILED           = "failed"
    INSUFFICIENT     = "insufficient"

    @property
    def allows_publishing(self) -> bool:
        return self in {
            EvidenceValidationStatus.PASSED,
            EvidenceValidationStatus.PASSED_WITH_GAPS,
        }


class EvidenceEventType(str, Enum):
    COLLECTION_STARTED  = "collection_started"
    EVIDENCE_COLLECTED  = "evidence_collected"
    COLLECTION_COMPLETE = "collection_complete"
    VALIDATION_COMPLETE = "validation_complete"
    RANKING_COMPLETE    = "ranking_complete"
    SNAPSHOT_PUBLISHED  = "snapshot_published"
    PROVIDER_REGISTERED = "provider_registered"
    PROVIDER_FAILED     = "provider_failed"
    ENGINE_STARTED      = "engine_started"
    ENGINE_STOPPED      = "engine_stopped"
    CACHE_HIT           = "cache_hit"
    QUALITY_COMPUTED    = "quality_computed"


class EvidenceEngineStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    COLLECTING   = "collecting"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {EvidenceEngineStatus.READY, EvidenceEngineStatus.COLLECTING}


# ---------------------------------------------------------------------------
# Quality dimensions + weights
# ---------------------------------------------------------------------------

class EvidenceQualityDimension(str, Enum):
    COVERAGE     = "coverage"
    FRESHNESS    = "freshness"
    CONSISTENCY  = "consistency"
    RELIABILITY  = "reliability"
    COMPLETENESS = "completeness"

    @property
    def default_weight(self) -> float:
        return {
            "coverage": 0.30, "freshness": 0.25, "consistency": 0.20,
            "reliability": 0.15, "completeness": 0.10,
        }[self.value]


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

EVIDENCE_FRESHNESS_WARN_SECONDS  = 3_600.0    # 1 hour
EVIDENCE_FRESHNESS_STALE_SECONDS = 86_400.0   # 24 hours
MIN_COVERAGE_FRACTION            = 0.50       # below this → INSUFFICIENT
MIN_CONFIDENCE_THRESHOLD         = 30.0       # min confidence to include item
MAX_EVIDENCE_ITEMS_PER_SOURCE    = 200
DEFAULT_COLLECTION_TIMEOUT_SECS  = 30.0
