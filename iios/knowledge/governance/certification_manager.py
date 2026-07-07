"""
iios/knowledge/governance/certification_manager.py
===================================================
CertificationManager — grants, renews, revokes, and queries knowledge
certifications.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .governance_constants import (
    CertificationLevel,
    CertificationStatus,
    DEFAULT_CERTIFICATION_TTL_DAYS,
    SYSTEM_GOVERNANCE_ACTOR,
)
from .governance_exceptions import (
    CertificationExpiredError,
    CertificationNotFoundError,
)
from .models.certification import Certification

__all__ = ["CertificationManager", "get_certification_manager",
           "reset_certification_manager"]

_LOG = logging.getLogger("iios.knowledge.governance.certification")
_lock = threading.Lock()
_manager: Optional["CertificationManager"] = None


class CertificationManager:
    """Thread-safe store for knowledge certifications."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # cert_id → Certification
        self._certs: dict[str, Certification] = {}
        # knowledge_id → cert_id (latest active)
        self._active: dict[str, str] = {}

    # ── Certify ───────────────────────────────────────────────────────────────

    def certify(
        self,
        knowledge_id: str,
        certified_by: str   = SYSTEM_GOVERNANCE_ACTOR,
        level:        CertificationLevel = CertificationLevel.STANDARD,
        ttl_days:     int   = DEFAULT_CERTIFICATION_TTL_DAYS,
        notes:        str   = "",
        kqi:          float = 0.0,
        gov_id:       Optional[str] = None,
    ) -> Certification:
        """Grant a new certification for *knowledge_id*."""
        cert = Certification(
            knowledge_id  = knowledge_id,
            status        = CertificationStatus.CERTIFIED,
            level         = level,
            certified_by  = certified_by,
            notes         = notes,
            kqi_at_cert   = kqi,
            gov_id        = gov_id,
        )
        cert.refresh_expiry(ttl_days)

        with self._lock:
            # Revoke previous active cert if any
            prev_id = self._active.get(knowledge_id)
            if prev_id and prev_id in self._certs:
                self._certs[prev_id].status = CertificationStatus.REVOKED

            self._certs[cert.cert_id] = cert
            self._active[knowledge_id] = cert.cert_id

        _LOG.info(
            "Certified: '%s' (cert_id=%s, level=%s, ttl=%dd)",
            knowledge_id[:16], cert.cert_id[:8], level.value, ttl_days,
        )
        return cert

    # ── Revoke ────────────────────────────────────────────────────────────────

    def revoke(
        self,
        knowledge_id: str,
        revoked_by:   str = SYSTEM_GOVERNANCE_ACTOR,
        reason:       str = "",
    ) -> Certification:
        with self._lock:
            cert_id = self._active.get(knowledge_id)
            if cert_id is None:
                raise CertificationNotFoundError(
                    f"No active certification for '{knowledge_id}'.", code="GE-301"
                )
            cert = self._certs.get(cert_id)
            if cert is None:
                raise CertificationNotFoundError(
                    f"Certification '{cert_id}' missing.", code="GE-301"
                )
            cert.revoke(revoked_by, reason)
            del self._active[knowledge_id]

        _LOG.info("Certification revoked: '%s'", knowledge_id[:16])
        return cert

    def revoke_by_cert_id(
        self,
        cert_id:    str,
        revoked_by: str = SYSTEM_GOVERNANCE_ACTOR,
        reason:     str = "",
    ) -> Certification:
        with self._lock:
            cert = self._certs.get(cert_id)
            if cert is None:
                raise CertificationNotFoundError(
                    f"Certification '{cert_id}' not found.", code="GE-301"
                )
            cert.revoke(revoked_by, reason)
            self._active.pop(cert.knowledge_id, None)
        return cert

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, knowledge_id: str) -> Certification:
        with self._lock:
            cert_id = self._active.get(knowledge_id)
            if cert_id and cert_id in self._certs:
                return self._certs[cert_id]
        raise CertificationNotFoundError(
            f"No active certification for '{knowledge_id}'.", code="GE-301"
        )

    def get_by_id(self, cert_id: str) -> Certification:
        with self._lock:
            cert = self._certs.get(cert_id)
        if cert is None:
            raise CertificationNotFoundError(
                f"Certification '{cert_id}' not found.", code="GE-301"
            )
        return cert

    def is_certified(self, knowledge_id: str) -> bool:
        try:
            cert = self.get(knowledge_id)
            return cert.is_valid
        except CertificationNotFoundError:
            return False

    def needs_renewal(self, knowledge_id: str) -> bool:
        try:
            return self.get(knowledge_id).needs_renewal
        except CertificationNotFoundError:
            return False

    def get_history(self, knowledge_id: str) -> list[Certification]:
        with self._lock:
            return [c for c in self._certs.values()
                    if c.knowledge_id == knowledge_id]

    # ── Expiry sweep ──────────────────────────────────────────────────────────

    def expire_stale(self) -> list[Certification]:
        """Mark all expired-but-not-yet-marked certifications as EXPIRED."""
        expired: list[Certification] = []
        with self._lock:
            for cert in self._certs.values():
                if (cert.status == CertificationStatus.CERTIFIED
                        and cert.is_expired):
                    cert.mark_expired()
                    self._active.pop(cert.knowledge_id, None)
                    expired.append(cert)
        return expired

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for c in self._certs.values():
                k = c.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total_certifications": len(self._certs),
                "active_certs":         len(self._active),
                "by_status":            by_status,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_certification_manager() -> CertificationManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = CertificationManager()
    return _manager


def reset_certification_manager() -> None:
    global _manager
    with _lock:
        _manager = None
