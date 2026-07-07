"""
iios/knowledge/governance/quality_engine.py
============================================
QualityEngine — stateless scorer that computes a KnowledgeQualityIndex
(KQI) for any KnowledgeRecord by evaluating 8 quality dimensions.

The engine does NOT modify records; it returns a QualityScore that callers
may inspect and act on.

Usage::

    from iios.knowledge.governance.quality_engine import get_quality_engine

    qe     = get_quality_engine()
    score  = qe.score(record)
    print(score.overall_kqi, score.tier)
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Optional

from ..knowledge_constants import KnowledgeStatus, KnowledgeSource, KnowledgeDomain
from ..models.knowledge_record import KnowledgeRecord
from .quality_constants import (
    DEFAULT_MIN_CONFIDENCE,
    DIMENSION_WEIGHTS,
    QualityDimension,
    QualityTier,
    ViolationSeverity,
    ViolationType,
)
from .quality_exceptions import QualityScoreError
from .models.quality_score import DimensionScore, QualityScore, compute_kqi, compute_tier
from .models.quality_violation import QualityViolation

__all__ = ["QualityEngine", "get_quality_engine", "reset_quality_engine"]

_LOG = logging.getLogger("iios.knowledge.governance.quality")
_lock = threading.Lock()
_engine: Optional["QualityEngine"] = None

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_SEC_PER_DAY = 86_400.0


class QualityEngine:
    """Stateless multi-dimensional quality scorer."""

    # ── Public API ────────────────────────────────────────────────────────────

    def score(
        self,
        record: KnowledgeRecord,
        governance_approved: bool = False,
        is_certified: bool = False,
    ) -> QualityScore:
        """Compute and return a QualityScore for *record*.

        *governance_approved* and *is_certified* are supplied by the
        KnowledgeGovernor so the governance dimension reflects real state.
        """
        try:
            dim_scores = [
                self._score_completeness(record),
                self._score_freshness(record),
                self._score_confidence(record),
                self._score_consistency(record),
                self._score_integrity(record),
                self._score_provenance(record),
                self._score_coverage(record),
                self._score_governance(record, governance_approved, is_certified),
            ]
        except Exception as exc:
            raise QualityScoreError(
                f"KQI computation failed for '{record.id}': {exc}", code="QE-002"
            ) from exc

        kqi  = compute_kqi(dim_scores)
        tier = compute_tier(kqi)

        return QualityScore(
            knowledge_id     = record.id,
            dimension_scores = dim_scores,
            overall_kqi      = kqi,
            tier             = tier,
        )

    # ── Dimension scorers ─────────────────────────────────────────────────────

    def _score_completeness(self, record: KnowledgeRecord) -> DimensionScore:
        violations: list[str] = []
        raw = 0.0

        # title (weight 0.20)
        if record.title and len(record.title.strip()) >= 3:
            raw += 0.20
        else:
            violations.append("title is empty or too short")

        # content (weight 0.25)
        if record.content is not None:
            raw += 0.25
        else:
            violations.append("content is None")

        # knowledge_type (weight 0.10)
        from ..knowledge_constants import KnowledgeType
        if record.knowledge_type != KnowledgeType.UNKNOWN:
            raw += 0.10
        else:
            violations.append("knowledge_type is UNKNOWN")

        # tags (weight 0.10)
        if record.metadata.tags:
            raw += 0.10
        else:
            violations.append("no tags set")

        # domain (weight 0.10)
        if record.metadata.domain != KnowledgeDomain.GENERAL:
            raw += 0.10
        else:
            violations.append("domain is GENERAL (unclassified)")

        # description (weight 0.10)
        if record.metadata.description:
            raw += 0.10
        else:
            violations.append("description is empty")

        # references or source_uri (weight 0.10)
        if record.references or record.metadata.source_uri:
            raw += 0.10
        else:
            violations.append("no references or source_uri")

        # explicit authorship (weight 0.05)
        from ..knowledge_constants import SYSTEM_OWNER
        if record.metadata.created_by != SYSTEM_OWNER:
            raw += 0.05
        else:
            violations.append("no explicit author (created_by = system)")

        return DimensionScore(
            dimension  = QualityDimension.COMPLETENESS,
            score      = min(1.0, raw),
            weight     = DIMENSION_WEIGHTS[QualityDimension.COMPLETENESS.value],
            passed     = raw >= 0.50,
            violations = violations,
        )

    def _score_freshness(self, record: KnowledgeRecord) -> DimensionScore:
        violations: list[str] = []
        ttl = record.metadata.ttl_seconds
        if ttl == 0:
            # No expiry configured → always fresh
            raw = 1.0
        else:
            age   = record.metadata.age_seconds
            ratio = age / ttl
            raw   = max(0.0, 1.0 - ratio)
            if ratio >= 1.0:
                violations.append(f"record is expired (age={age/3600:.1f}h, ttl={ttl/3600:.1f}h)")
            elif ratio >= 0.80:
                violations.append("record is approaching expiry (>80% TTL used)")

        return DimensionScore(
            dimension  = QualityDimension.FRESHNESS,
            score      = raw,
            weight     = DIMENSION_WEIGHTS[QualityDimension.FRESHNESS.value],
            passed     = raw > 0.0,
            violations = violations,
        )

    def _score_confidence(self, record: KnowledgeRecord) -> DimensionScore:
        conf = record.metadata.confidence
        violations: list[str] = []
        if conf < DEFAULT_MIN_CONFIDENCE:
            violations.append(
                f"confidence {conf:.2f} below minimum {DEFAULT_MIN_CONFIDENCE}"
            )
        return DimensionScore(
            dimension  = QualityDimension.CONFIDENCE,
            score      = conf,
            weight     = DIMENSION_WEIGHTS[QualityDimension.CONFIDENCE.value],
            passed     = conf >= DEFAULT_MIN_CONFIDENCE,
            violations = violations,
        )

    def _score_consistency(self, record: KnowledgeRecord) -> DimensionScore:
        violations: list[str] = []
        raw = 0.0

        # semver format (0.25)
        if _SEMVER_RE.match(record.version):
            raw += 0.25
        else:
            violations.append(f"version '{record.version}' is not valid semver")

        # status not INVALID (0.25)
        if record.status != KnowledgeStatus.INVALID:
            raw += 0.25
        else:
            violations.append("record status is INVALID")

        # content not empty (0.25)
        if record.content is not None and record.content != "" and record.content != {}:
            raw += 0.25
        else:
            violations.append("content is empty or None")

        # knowledge_id is a valid non-empty string (0.25)
        if record.id and len(record.id) >= 4:
            raw += 0.25
        else:
            violations.append("knowledge_id is missing or too short")

        return DimensionScore(
            dimension  = QualityDimension.CONSISTENCY,
            score      = raw,
            weight     = DIMENSION_WEIGHTS[QualityDimension.CONSISTENCY.value],
            passed     = raw >= 0.50,
            violations = violations,
        )

    def _score_integrity(self, record: KnowledgeRecord) -> DimensionScore:
        violations: list[str] = []
        raw = 0.0

        # Not deleted (0.30)
        if not record.is_deleted:
            raw += 0.30
        else:
            violations.append("record is soft-deleted")

        # Status is not INVALID (0.30)
        if record.status != KnowledgeStatus.INVALID:
            raw += 0.30
        else:
            violations.append("record has INVALID status")

        # Has checksum (0.20)
        if record.checksum or record.metadata.checksum:
            raw += 0.20
        else:
            violations.append("no content checksum (integrity cannot be verified)")

        # References are all active / not broken (0.20)
        broken = [r for r in record.references if r.is_deleted if hasattr(r, "is_deleted")]
        if not broken:
            raw += 0.20
        else:
            violations.append(f"{len(broken)} broken reference(s)")

        return DimensionScore(
            dimension  = QualityDimension.INTEGRITY,
            score      = raw,
            weight     = DIMENSION_WEIGHTS[QualityDimension.INTEGRITY.value],
            passed     = raw >= 0.50,
            violations = violations,
        )

    def _score_provenance(self, record: KnowledgeRecord) -> DimensionScore:
        from ..knowledge_constants import SYSTEM_OWNER
        violations: list[str] = []
        raw = 0.0

        # Explicit author (0.30)
        if record.metadata.created_by != SYSTEM_OWNER:
            raw += 0.30
        else:
            violations.append("no explicit author (created_by = system)")

        # Source is not SYSTEM (0.25)
        if record.metadata.source != KnowledgeSource.SYSTEM:
            raw += 0.25
        else:
            violations.append("source is SYSTEM (no external origin documented)")

        # Has source_uri (0.20)
        if record.metadata.source_uri:
            raw += 0.20
        else:
            violations.append("source_uri is empty")

        # Has references (0.25)
        if record.references:
            raw += 0.25
        else:
            violations.append("no references")

        return DimensionScore(
            dimension  = QualityDimension.PROVENANCE,
            score      = raw,
            weight     = DIMENSION_WEIGHTS[QualityDimension.PROVENANCE.value],
            passed     = raw >= 0.30,
            violations = violations,
        )

    def _score_coverage(self, record: KnowledgeRecord) -> DimensionScore:
        from ..knowledge_constants import KnowledgeType
        violations: list[str] = []
        raw = 0.0

        # Tags: 0.1 per tag up to 5 (total 0.50)
        tag_score = min(0.50, len(record.metadata.tags) * 0.10)
        raw += tag_score
        if not record.metadata.tags:
            violations.append("no tags assigned")

        # Domain (0.25)
        if record.metadata.domain != KnowledgeDomain.GENERAL:
            raw += 0.25

        # Type (0.25)
        if record.knowledge_type != KnowledgeType.UNKNOWN:
            raw += 0.25

        return DimensionScore(
            dimension  = QualityDimension.COVERAGE,
            score      = min(1.0, raw),
            weight     = DIMENSION_WEIGHTS[QualityDimension.COVERAGE.value],
            passed     = raw >= 0.25,
            violations = violations,
        )

    def _score_governance(
        self,
        record: KnowledgeRecord,
        governance_approved: bool,
        is_certified: bool,
    ) -> DimensionScore:
        violations: list[str] = []
        raw = 0.0

        # Status is ACTIVE (0.30)
        if record.status == KnowledgeStatus.ACTIVE:
            raw += 0.30
        else:
            violations.append(f"record status is {record.status.value} (not active)")

        # Governance approved (0.40)
        if governance_approved:
            raw += 0.40
        else:
            violations.append("not yet approved by governance")

        # Certified (0.30)
        if is_certified:
            raw += 0.30
        else:
            violations.append("not certified")

        return DimensionScore(
            dimension  = QualityDimension.GOVERNANCE,
            score      = min(1.0, raw),
            weight     = DIMENSION_WEIGHTS[QualityDimension.GOVERNANCE.value],
            passed     = governance_approved,
            violations = violations,
        )


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_quality_engine() -> QualityEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = QualityEngine()
    return _engine


def reset_quality_engine() -> None:
    global _engine
    with _lock:
        _engine = None
