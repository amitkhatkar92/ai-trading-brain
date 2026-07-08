"""
iios/intelligence/governance/certification/certification_engine.py
==================================================================
CertificationEngine — runs policies and issues / revokes certs.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from .certification_policy import (
    CertificationPolicy,
    MinQualityPolicy,
    ApprovalRequiredPolicy,
    NoRejectionReasonsPolicy,
)
from .certification_record import CertificationRecord
from .certification_registry import CertificationRegistry, get_certification_registry
from ..quality_constants import (
    AUTO_CERTIFIER_ID,
    CertificationStatus,
    CERTIFICATION_TTL_S,
)
from ..quality_exceptions import (
    CertificationFailedError,
    CertificationNotFoundError,
    CertificationRevokedError,
)
from ..quality_result import QualityRecord


class CertificationEngine:
    """
    Applies registered policies to QualityRecords and manages their
    certification lifecycle (issue, revoke, expire, recertify).
    """

    _DEFAULT_POLICIES: list[CertificationPolicy] = [
        MinQualityPolicy(),
        NoRejectionReasonsPolicy(),
    ]

    def __init__(self) -> None:
        self._registry: CertificationRegistry         = get_certification_registry()
        self._policies: list[CertificationPolicy]     = list(self._DEFAULT_POLICIES)
        self._lock:     threading.RLock               = threading.RLock()

    # -- Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy: CertificationPolicy) -> None:
        with self._lock:
            self._policies.append(policy)

    def clear_policies(self) -> None:
        with self._lock:
            self._policies = list(self._DEFAULT_POLICIES)

    def policy_names(self) -> list[str]:
        with self._lock:
            return [p.name for p in self._policies]

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def certify(
        self,
        record:      QualityRecord,
        certifier_id: str = AUTO_CERTIFIER_ID,
        ttl_s:        float = CERTIFICATION_TTL_S,
    ) -> CertificationRecord:
        with self._lock:
            policies = list(self._policies)

        passed_names:  list[str] = []
        failed_names:  list[str] = []

        for policy in policies:
            ok, _reason = policy.check(record)
            if ok:
                passed_names.append(policy.name)
            else:
                failed_names.append(policy.name)

        now  = time.time()
        cert = CertificationRecord(
            record_id      = record.record_id,
            product_id     = record.product_id,
            certifier_id   = certifier_id,
            quality_score  = record.quality_score,
            ttl_s          = ttl_s,
            issued_at      = now,
            expires_at     = now + ttl_s,
            policies_passed = passed_names,
            policies_failed = failed_names,
        )

        if failed_names:
            cert.status = CertificationStatus.FAILED
            record.certification_status = CertificationStatus.FAILED
            self._registry.add(cert)
            raise CertificationFailedError(
                record.product_id,
                f"Policies failed: {failed_names}",
            )

        cert.status                  = CertificationStatus.CERTIFIED
        record.certification_status  = CertificationStatus.CERTIFIED
        record.touch()
        self._registry.add(cert)
        return cert

    def revoke(self, cert_id: str, reason: str = "") -> None:
        cert = self._registry.get(cert_id)
        if cert.status == CertificationStatus.REVOKED:
            raise CertificationRevokedError(cert_id, reason)
        cert.status           = CertificationStatus.REVOKED
        cert.revoked_at       = time.time()
        cert.revocation_reason = reason
        self._registry.update(cert)

    def check_expiry(self) -> list[str]:
        """Mark expired certs and return their IDs."""
        expired: list[str] = []
        for cert in self._registry.all():
            if cert.status == CertificationStatus.CERTIFIED and cert.is_expired:
                cert.status = CertificationStatus.EXPIRED
                self._registry.update(cert)
                expired.append(cert.cert_id)
        return expired

    def valid_cert_for_product(self, product_id: str) -> CertificationRecord | None:
        return self._registry.valid_for_product(product_id)

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        s = self._registry.stats()
        s["policies_registered"] = len(self._policies)
        return s


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock              = threading.Lock()
_ENGINE: CertificationEngine | None = None


def get_certification_engine() -> CertificationEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = CertificationEngine()
    return _ENGINE


def reset_certification_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
