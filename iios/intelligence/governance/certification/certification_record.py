"""
iios/intelligence/governance/certification/certification_record.py
=================================================================
CertificationRecord — immutable record of a certification decision.
Lives here (not in quality_result.py) to keep imports clean.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..quality_constants import CertificationStatus, CERTIFICATION_TTL_S


@dataclass
class CertificationRecord:
    """
    Permanent record of a certification event.

    Attributes
    ----------
    cert_id          : Unique identifier.
    record_id        : Associated QualityRecord.
    product_id       : Intelligence product.
    status           : Current certification status.
    certifier_id     : Entity that performed certification.
    policies_passed  : Names of policies that succeeded.
    policies_failed  : Names of policies that failed.
    quality_score    : Score at time of certification.
    ttl_s            : Validity window in seconds.
    issued_at        : Unix timestamp of issuance.
    expires_at       : Unix timestamp of expiry.
    revoked_at       : Unix timestamp of revocation (or 0.0).
    revocation_reason: Reason for revocation, if any.
    metadata         : Caller-supplied extras.
    """

    cert_id:           str                 = field(default_factory=lambda: str(uuid.uuid4()))
    record_id:         str                 = ""
    product_id:        str                 = ""
    status:            CertificationStatus = CertificationStatus.PENDING
    certifier_id:      str                 = ""
    policies_passed:   list[str]           = field(default_factory=list)
    policies_failed:   list[str]           = field(default_factory=list)
    quality_score:     float               = 0.0
    ttl_s:             float               = CERTIFICATION_TTL_S
    issued_at:         float               = field(default_factory=time.time)
    expires_at:        float               = 0.0
    revoked_at:        float               = 0.0
    revocation_reason: str                 = ""
    metadata:          dict[str, Any]      = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            self.expires_at = self.issued_at + self.ttl_s

    @property
    def is_expired(self) -> bool:
        return self.status == CertificationStatus.CERTIFIED and time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return (
            self.status == CertificationStatus.CERTIFIED
            and not self.is_expired
            and self.revoked_at == 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cert_id":           self.cert_id,
            "record_id":         self.record_id,
            "product_id":        self.product_id,
            "status":            self.status.value,
            "certifier_id":      self.certifier_id,
            "policies_passed":   list(self.policies_passed),
            "policies_failed":   list(self.policies_failed),
            "quality_score":     round(self.quality_score, 4),
            "ttl_s":             self.ttl_s,
            "issued_at":         self.issued_at,
            "expires_at":        self.expires_at,
            "revoked_at":        self.revoked_at,
            "revocation_reason": self.revocation_reason,
            "is_valid":          self.is_valid,
        }
