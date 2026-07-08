"""iios/decision_governance/certification/certification_record.py

CertificationRecord dataclass.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.decision_governance.governance_constants import DEFAULT_CERT_TTL_SEC


@dataclass
class CertificationRecord:
    """Issued when a decision passes all governance checks."""

    cert_id:           str         = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id:       str         = ""
    subject_id:        str         = ""
    issued_at:         float       = field(default_factory=time.time)
    expires_at:        float | None = None
    issuer:            str         = "governance_engine"
    basis:             str         = ""     # brief justification
    revoked:           bool        = False
    revoked_at:        float | None = None
    revocation_reason: str         = ""
    metadata:          dict        = field(default_factory=dict)

    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at is not None and time.time() > self.expires_at:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "cert_id":           self.cert_id,
            "decision_id":       self.decision_id,
            "subject_id":        self.subject_id,
            "issued_at":         self.issued_at,
            "expires_at":        self.expires_at,
            "issuer":            self.issuer,
            "basis":             self.basis,
            "revoked":           self.revoked,
            "revoked_at":        self.revoked_at,
            "revocation_reason": self.revocation_reason,
            "is_valid":          self.is_valid(),
        }
