"""
iios/intelligence/governance/certification/certification_registry.py
====================================================================
Thread-safe store for CertificationRecord objects.
"""
from __future__ import annotations

import threading
from typing import Any

from .certification_record import CertificationRecord
from ..quality_constants import MAX_CERT_RECORDS
from ..quality_exceptions import CertificationNotFoundError


class CertificationRegistry:
    """
    Append-only thread-safe store for CertificationRecord entries.
    """

    def __init__(self, max_records: int = MAX_CERT_RECORDS) -> None:
        self._records:    dict[str, CertificationRecord]  = {}
        self._ordered:    list[str]                        = []
        self._by_record:  dict[str, list[str]]             = {}
        self._by_product: dict[str, list[str]]             = {}
        self._max:        int                              = max_records
        self._lock:       threading.RLock                  = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def add(self, cert: CertificationRecord) -> None:
        with self._lock:
            if len(self._ordered) >= self._max:
                oldest = self._ordered.pop(0)
                self._records.pop(oldest, None)
            self._records[cert.cert_id] = cert
            self._ordered.append(cert.cert_id)
            self._by_record.setdefault(cert.record_id, []).append(cert.cert_id)
            self._by_product.setdefault(cert.product_id, []).append(cert.cert_id)

    def update(self, cert: CertificationRecord) -> None:
        """Replace an existing cert in-place (for revocations/expiry updates)."""
        with self._lock:
            if cert.cert_id not in self._records:
                raise CertificationNotFoundError(cert.cert_id)
            self._records[cert.cert_id] = cert

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, cert_id: str) -> CertificationRecord:
        with self._lock:
            c = self._records.get(cert_id)
        if c is None:
            raise CertificationNotFoundError(cert_id)
        return c

    def has(self, cert_id: str) -> bool:
        with self._lock:
            return cert_id in self._records

    def for_record(self, record_id: str) -> list[CertificationRecord]:
        with self._lock:
            ids = list(self._by_record.get(record_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def for_product(self, product_id: str) -> list[CertificationRecord]:
        with self._lock:
            ids = list(self._by_product.get(product_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def valid_for_product(self, product_id: str) -> CertificationRecord | None:
        """Return the most-recently issued valid cert for a product, or None."""
        certs = self.for_product(product_id)
        valid = [c for c in certs if c.is_valid]
        return max(valid, key=lambda c: c.issued_at) if valid else None

    def all(self) -> list[CertificationRecord]:
        with self._lock:
            return [self._records[i] for i in self._ordered if i in self._records]

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            all_certs = [self._records[i] for i in self._ordered if i in self._records]
        return {
            "total":    len(all_certs),
            "valid":    sum(1 for c in all_certs if c.is_valid),
            "expired":  sum(1 for c in all_certs if c.is_expired),
            "revoked":  sum(1 for c in all_certs if c.revoked_at > 0.0),
            "products": len(self._by_product),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock                   = threading.Lock()
_REGISTRY: CertificationRegistry | None    = None


def get_certification_registry() -> CertificationRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = CertificationRegistry()
    return _REGISTRY


def reset_certification_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
