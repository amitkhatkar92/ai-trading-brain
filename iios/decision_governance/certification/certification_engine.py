"""iios/decision_governance/certification/certification_engine.py

Issues and manages CertificationRecords.
"""
from __future__ import annotations

import threading
import time

from iios.decision_governance.governance_constants import DEFAULT_CERT_TTL_SEC
from iios.decision_governance.governance_exceptions import (
    CertificationNotFoundError,
    CertificationRevokedError,
)
from iios.decision_governance.certification.certification_record import CertificationRecord


class CertificationEngine:
    """Issues, retrieves, and revokes governance certificates."""

    def __init__(self) -> None:
        self._lock:  threading.RLock                 = threading.RLock()
        self._certs: dict[str, CertificationRecord]  = {}

    def issue(
        self,
        decision_id: str,
        subject_id:  str,
        basis:       str  = "governance_approved",
        ttl_seconds: float = DEFAULT_CERT_TTL_SEC,
        issuer:      str  = "governance_engine",
        metadata:    dict | None = None,
    ) -> CertificationRecord:
        cert = CertificationRecord(
            decision_id=decision_id,
            subject_id=subject_id,
            issued_at=time.time(),
            expires_at=time.time() + ttl_seconds if ttl_seconds > 0 else None,
            issuer=issuer,
            basis=basis,
            metadata=metadata or {},
        )
        with self._lock:
            self._certs[cert.cert_id] = cert
        return cert

    def get(self, cert_id: str) -> CertificationRecord:
        with self._lock:
            cert = self._certs.get(cert_id)
        if cert is None:
            raise CertificationNotFoundError(cert_id)
        return cert

    def by_decision(self, decision_id: str) -> list[CertificationRecord]:
        with self._lock:
            return [c for c in self._certs.values() if c.decision_id == decision_id]

    def revoke(
        self,
        cert_id: str,
        reason:  str = "",
    ) -> CertificationRecord:
        cert = self.get(cert_id)
        if cert.revoked:
            raise CertificationRevokedError(cert_id)
        cert.revoked           = True
        cert.revoked_at        = time.time()
        cert.revocation_reason = reason
        return cert

    def is_valid(self, cert_id: str) -> bool:
        try:
            return self.get(cert_id).is_valid()
        except CertificationNotFoundError:
            return False

    def statistics(self) -> dict:
        with self._lock:
            total   = len(self._certs)
            valid   = sum(1 for c in self._certs.values() if c.is_valid())
            revoked = sum(1 for c in self._certs.values() if c.revoked)
        return {"total": total, "valid": valid, "revoked": revoked}
