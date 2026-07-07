"""
iios/knowledge/governance/quality_validator.py
===============================================
QualityValidator — rule-based validator that produces QualityViolation
objects for every rule breached by a KnowledgeRecord.

Validators fire before the QualityEngine scorer; critical violations are
surfaced immediately and may block approval without scoring.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Optional

from ..knowledge_constants import (
    KnowledgeDomain,
    KnowledgeSource,
    KnowledgeStatus,
    KnowledgeType,
    SYSTEM_OWNER,
    DEFAULT_CONFIDENCE,
)
from ..models.knowledge_record import KnowledgeRecord
from .quality_constants import (
    DEFAULT_MIN_CONFIDENCE,
    QualityDimension,
    ViolationSeverity,
    ViolationType,
)
from .models.quality_violation import QualityViolation

__all__ = ["QualityValidator", "get_quality_validator", "reset_quality_validator"]

_LOG = logging.getLogger("iios.knowledge.governance.validator")
_lock = threading.Lock()
_validator: Optional["QualityValidator"] = None
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _v(
    knowledge_id: str,
    vtype: ViolationType,
    severity: ViolationSeverity,
    dimension: QualityDimension,
    field: str,
    message: str,
    suggestion: str = "",
) -> QualityViolation:
    return QualityViolation(
        knowledge_id   = knowledge_id,
        violation_type = vtype,
        severity       = severity,
        dimension      = dimension,
        field_name     = field,
        message        = message,
        suggestion     = suggestion,
    )


class QualityValidator:
    """Rule-based validator — stateless; safe for concurrent use."""

    def validate(self, record: KnowledgeRecord) -> list[QualityViolation]:
        """Run all validation rules and return all detected violations."""
        kid = record.id
        out: list[QualityViolation] = []

        out.extend(self._check_title(record, kid))
        out.extend(self._check_content(record, kid))
        out.extend(self._check_type(record, kid))
        out.extend(self._check_version(record, kid))
        out.extend(self._check_status(record, kid))
        out.extend(self._check_confidence(record, kid))
        out.extend(self._check_domain(record, kid))
        out.extend(self._check_provenance(record, kid))
        out.extend(self._check_deletion(record, kid))

        return out

    def validate_strict(self, record: KnowledgeRecord) -> list[QualityViolation]:
        """Validate and raise on CRITICAL violations."""
        violations = self.validate(record)
        critical   = [v for v in violations if v.is_critical]
        if critical:
            from .quality_exceptions import QualityValidationError
            msgs = [v.message for v in critical]
            raise QualityValidationError(
                f"Critical quality violations: {msgs}",
                violations = msgs,
                code       = "QE-001",
            )
        return violations

    def has_blocking_violations(self, violations: list[QualityViolation]) -> bool:
        return any(v.blocks_approval for v in violations)

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_title(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if not r.title or len(r.title.strip()) < 3:
            out.append(_v(kid, ViolationType.EMPTY_TITLE, ViolationSeverity.HIGH,
                          QualityDimension.COMPLETENESS, "title",
                          "title is empty or shorter than 3 characters",
                          "Set a descriptive title of at least 3 characters"))
        return out

    def _check_content(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if not r.content:
            out.append(_v(kid, ViolationType.EMPTY_CONTENT, ViolationSeverity.CRITICAL,
                          QualityDimension.COMPLETENESS, "content",
                          "content is empty or None — knowledge record has no payload",
                          "Populate the content field with the knowledge payload"))
        return out

    def _check_type(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if r.knowledge_type == KnowledgeType.UNKNOWN:
            out.append(_v(kid, ViolationType.UNKNOWN_TYPE, ViolationSeverity.MEDIUM,
                          QualityDimension.COMPLETENESS, "knowledge_type",
                          "knowledge_type is UNKNOWN",
                          "Assign an appropriate knowledge type"))
        return out

    def _check_version(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if not _SEMVER_RE.match(r.version):
            out.append(_v(kid, ViolationType.INVALID_VERSION, ViolationSeverity.HIGH,
                          QualityDimension.CONSISTENCY, "version",
                          f"version '{r.version}' is not valid semver (expected N.N.N)",
                          "Use semantic versioning: MAJOR.MINOR.PATCH"))
        return out

    def _check_status(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if r.status == KnowledgeStatus.INVALID:
            out.append(_v(kid, ViolationType.INVALID_STATUS, ViolationSeverity.CRITICAL,
                          QualityDimension.INTEGRITY, "status",
                          "record has INVALID status",
                          "Fix the underlying issue and reset the record status"))
        return out

    def _check_confidence(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        conf = r.metadata.confidence
        if conf < DEFAULT_MIN_CONFIDENCE:
            out.append(_v(kid, ViolationType.LOW_CONFIDENCE, ViolationSeverity.MEDIUM,
                          QualityDimension.CONFIDENCE, "metadata.confidence",
                          f"confidence {conf:.2f} is below minimum {DEFAULT_MIN_CONFIDENCE}",
                          "Increase confidence or document why low confidence is appropriate"))
        return out

    def _check_domain(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if r.metadata.domain == KnowledgeDomain.GENERAL:
            out.append(_v(kid, ViolationType.GENERAL_DOMAIN, ViolationSeverity.LOW,
                          QualityDimension.COVERAGE, "metadata.domain",
                          "domain is GENERAL — knowledge is unclassified",
                          "Assign a specific domain (market, trading, risk, …)"))
        return out

    def _check_provenance(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if r.metadata.created_by == SYSTEM_OWNER and not r.metadata.source_uri:
            out.append(_v(kid, ViolationType.MISSING_PROVENANCE, ViolationSeverity.LOW,
                          QualityDimension.PROVENANCE, "metadata.created_by",
                          "no explicit author and no source_uri — provenance is unknown",
                          "Set created_by to the author or add a source_uri"))
        return out

    def _check_deletion(self, r: KnowledgeRecord, kid: str) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if r.is_deleted:
            out.append(_v(kid, ViolationType.INVALID_STATUS, ViolationSeverity.CRITICAL,
                          QualityDimension.INTEGRITY, "is_deleted",
                          "record is soft-deleted and cannot be approved",
                          "Restore the record before submitting for approval"))
        return out


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_quality_validator() -> QualityValidator:
    global _validator
    if _validator is None:
        with _lock:
            if _validator is None:
                _validator = QualityValidator()
    return _validator


def reset_quality_validator() -> None:
    global _validator
    with _lock:
        _validator = None
