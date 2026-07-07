"""
iios/knowledge/governance/models/certification.py
==================================================
Certification — formal quality certification for a knowledge item,
granted by an authorised reviewer for a fixed validity period.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..governance_constants import (
    CertificationLevel,
    CertificationStatus,
    DEFAULT_CERTIFICATION_TTL_DAYS,
    DEFAULT_RENEWAL_NOTICE_DAYS,
    SYSTEM_GOVERNANCE_ACTOR,
    GOVERNANCE_SCHEMA_VERSION,
)

__all__ = ["Certification"]

_SEC_PER_DAY = 86_400.0


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Certification:
    """Knowledge certification record."""

    cert_id:           str                  = field(default_factory=_new_id)
    knowledge_id:      str                  = ""
    status:            CertificationStatus  = CertificationStatus.CERTIFIED
    level:             CertificationLevel   = CertificationLevel.STANDARD
    certified_by:      str                  = SYSTEM_GOVERNANCE_ACTOR
    certified_at:      float                = field(default_factory=time.time)
    expires_at:        float                = 0.0   # 0 = computed in __post_init__
    renewal_at:        float                = 0.0   # warn before expiry
    revoked_by:        Optional[str]        = None
    revoked_at:        Optional[float]      = None
    revocation_reason: str                  = ""
    notes:             str                  = ""
    kqi_at_cert:       float                = 0.0
    gov_id:            Optional[str]        = None  # linked governance record
    schema_version:    str                  = GOVERNANCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            self.expires_at = self.certified_at + DEFAULT_CERTIFICATION_TTL_DAYS * _SEC_PER_DAY
        if self.renewal_at == 0.0:
            self.renewal_at = self.expires_at - DEFAULT_RENEWAL_NOTICE_DAYS * _SEC_PER_DAY

    # ── Lifecycle helpers ─────────────────────────────────────────────────────

    @property
    def is_valid(self) -> bool:
        return (self.status == CertificationStatus.CERTIFIED
                and time.time() < self.expires_at)

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    @property
    def needs_renewal(self) -> bool:
        return (self.status == CertificationStatus.CERTIFIED
                and time.time() >= self.renewal_at)

    @property
    def days_until_expiry(self) -> float:
        return max(0.0, (self.expires_at - time.time()) / _SEC_PER_DAY)

    def refresh_expiry(self, ttl_days: int = DEFAULT_CERTIFICATION_TTL_DAYS) -> None:
        """Extend expiry from now by *ttl_days*."""
        now             = time.time()
        self.certified_at = now
        self.expires_at = now + ttl_days * _SEC_PER_DAY
        self.renewal_at = self.expires_at - DEFAULT_RENEWAL_NOTICE_DAYS * _SEC_PER_DAY
        self.status     = CertificationStatus.CERTIFIED

    def revoke(self, revoked_by: str, reason: str = "") -> None:
        self.status            = CertificationStatus.REVOKED
        self.revoked_by        = revoked_by
        self.revoked_at        = time.time()
        self.revocation_reason = reason

    def mark_expired(self) -> None:
        self.status = CertificationStatus.EXPIRED

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "cert_id":           self.cert_id,
            "knowledge_id":      self.knowledge_id,
            "status":            self.status.value,
            "level":             self.level.value,
            "certified_by":      self.certified_by,
            "certified_at":      self.certified_at,
            "expires_at":        self.expires_at,
            "renewal_at":        self.renewal_at,
            "revoked_by":        self.revoked_by,
            "revoked_at":        self.revoked_at,
            "revocation_reason": self.revocation_reason,
            "notes":             self.notes,
            "kqi_at_cert":       self.kqi_at_cert,
            "gov_id":            self.gov_id,
            "schema_version":    self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Certification":
        return cls(
            cert_id           = d.get("cert_id",          _new_id()),
            knowledge_id      = d.get("knowledge_id",     ""),
            status            = CertificationStatus(
                d.get("status", CertificationStatus.CERTIFIED.value)),
            level             = CertificationLevel(
                d.get("level",  CertificationLevel.STANDARD.value)),
            certified_by      = d.get("certified_by",     SYSTEM_GOVERNANCE_ACTOR),
            certified_at      = d.get("certified_at",     time.time()),
            expires_at        = d.get("expires_at",       0.0),
            renewal_at        = d.get("renewal_at",       0.0),
            revoked_by        = d.get("revoked_by"),
            revoked_at        = d.get("revoked_at"),
            revocation_reason = d.get("revocation_reason",""),
            notes             = d.get("notes",            ""),
            kqi_at_cert       = d.get("kqi_at_cert",      0.0),
            gov_id            = d.get("gov_id"),
            schema_version    = d.get("schema_version",   GOVERNANCE_SCHEMA_VERSION),
        )
