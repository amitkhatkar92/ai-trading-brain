"""
iios/intelligence/governance/quality_result.py
===============================================
Core output models: QualityRecord and QualityApproval.
These live at package root to avoid circular imports.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .quality_constants import (
    IntelligenceType,
    QualityLevel,
    ApprovalStatus,
    CertificationStatus,
    QUALITY_SCORE_EXCELLENT,
    QUALITY_SCORE_GOOD,
    QUALITY_SCORE_ACCEPTABLE,
    APPROVAL_TTL_S,
)


def _level_from_score(score: float) -> QualityLevel:
    if score >= QUALITY_SCORE_EXCELLENT:
        return QualityLevel.EXCELLENT
    if score >= QUALITY_SCORE_GOOD:
        return QualityLevel.GOOD
    if score >= QUALITY_SCORE_ACCEPTABLE:
        return QualityLevel.ACCEPTABLE
    if score >= 0.40:
        return QualityLevel.POOR
    return QualityLevel.REJECTED


@dataclass
class QualityRecord:
    """
    The evaluated quality state of one intelligence product.

    Attributes
    ----------
    record_id            : Unique governance evaluation identifier.
    product_id           : The intelligence product being governed.
    product_type         : Category of intelligence product.
    source_id            : Engine/module that produced the product.
    quality_score        : Composite quality [0, 1].
    quality_level        : Ordinal band.
    dimension_scores     : Per-dimension scores (EvaluationDimension → float).
    approval_status      : Decision-Layer gate state.
    certification_status : Certification lifecycle state.
    explanation_id       : ID of the attached Explanation object.
    audit_ids            : Audit event IDs that reference this record.
    warnings             : Non-blocking quality warnings.
    rejection_reasons    : Reasons for rejection (if applicable).
    metadata             : Caller-supplied extras.
    created_at           : Unix timestamp.
    updated_at           : Last mutation timestamp.
    """

    record_id:            str                  = field(default_factory=lambda: str(uuid.uuid4()))
    product_id:           str                  = ""
    product_type:         IntelligenceType     = IntelligenceType.GENERIC
    source_id:            str                  = ""
    quality_score:        float                = 0.0
    quality_level:        QualityLevel         = QualityLevel.REJECTED
    dimension_scores:     dict[str, float]     = field(default_factory=dict)
    approval_status:      ApprovalStatus       = ApprovalStatus.PENDING
    certification_status: CertificationStatus  = CertificationStatus.UNCERTIFIED
    explanation_id:       str | None           = None
    audit_ids:            list[str]            = field(default_factory=list)
    warnings:             list[str]            = field(default_factory=list)
    rejection_reasons:    list[str]            = field(default_factory=list)
    metadata:             dict[str, Any]       = field(default_factory=dict)
    created_at:           float                = field(default_factory=time.time)
    updated_at:           float                = field(default_factory=time.time)

    def __post_init__(self) -> None:
        # Derive quality level from score if not explicitly set
        if self.quality_score > 0 and self.quality_level == QualityLevel.REJECTED:
            self.quality_level = _level_from_score(self.quality_score)

    def touch(self) -> None:
        self.updated_at = time.time()

    @property
    def is_approved(self) -> bool:
        return self.approval_status == ApprovalStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.approval_status == ApprovalStatus.REJECTED

    @property
    def is_certified(self) -> bool:
        return self.certification_status == CertificationStatus.CERTIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":            self.record_id,
            "product_id":           self.product_id,
            "product_type":         self.product_type.value,
            "source_id":            self.source_id,
            "quality_score":        round(self.quality_score, 4),
            "quality_level":        self.quality_level.value,
            "dimension_scores":     {k: round(v, 4) for k, v in self.dimension_scores.items()},
            "approval_status":      self.approval_status.value,
            "certification_status": self.certification_status.value,
            "explanation_id":       self.explanation_id,
            "audit_count":          len(self.audit_ids),
            "warnings":             list(self.warnings),
            "rejection_reasons":    list(self.rejection_reasons),
            "metadata":             self.metadata,
            "created_at":           self.created_at,
            "updated_at":           self.updated_at,
        }


@dataclass
class QualityApproval:
    """
    Approval decision forwarded to the Decision Layer.
    Carries a short TTL — expired approvals require re-evaluation.
    """

    approval_id:   str               = field(default_factory=lambda: str(uuid.uuid4()))
    record_id:     str               = ""
    product_id:    str               = ""
    approved:      bool              = False
    approver_id:   str               = ""
    reason:        str               = ""
    quality_score: float             = 0.0
    quality_level: QualityLevel      = QualityLevel.REJECTED
    ttl_s:         float             = APPROVAL_TTL_S
    metadata:      dict[str, Any]    = field(default_factory=dict)
    created_at:    float             = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        if self.ttl_s <= 0:
            return False
        return time.time() - self.created_at > self.ttl_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id":   self.approval_id,
            "record_id":     self.record_id,
            "product_id":    self.product_id,
            "approved":      self.approved,
            "approver_id":   self.approver_id,
            "reason":        self.reason,
            "quality_score": round(self.quality_score, 4),
            "quality_level": self.quality_level.value,
            "is_expired":    self.is_expired,
            "ttl_s":         self.ttl_s,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }
