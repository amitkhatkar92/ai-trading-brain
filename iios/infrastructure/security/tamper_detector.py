"""
iios/infrastructure/security/tamper_detector.py
================================================
Tamper detection via HMAC-SHA256 signed checksums on data payloads.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import threading
from typing import Any, Optional

from .crypto_provider import get_crypto_provider
from .security_constants import HashAlgorithm
from .security_exceptions import TamperDetectedError, ChecksumMismatchError
from .security_models import IntegrityChecksum

__all__ = ["TamperDetector", "get_tamper_detector", "reset_tamper_detector"]

_LOG = logging.getLogger("iios.security.tamper")
_mgr_lock = threading.Lock()
_detector: Optional["TamperDetector"] = None

# HMAC uses SHA-256 for all keyed operations (most portable)
_HMAC_DIGEST = "sha256"


def _hmac_hex(secret: bytes, data: bytes) -> str:
    """Compute HMAC-SHA256 of *data* using *secret*. Returns hex digest."""
    mac = hmac.new(secret, data, _HMAC_DIGEST)
    return mac.hexdigest()


class TamperDetector:
    """Detects data tampering via HMAC-SHA256 checksums.

    Usage::

        td = get_tamper_detector()
        checksum = td.compute("record:123", b"important data")
        td.verify("record:123", b"important data", checksum.checksum)
    """

    def __init__(self, secret: Optional[bytes] = None) -> None:
        self._lock = threading.RLock()
        self._secret = secret or os.urandom(32)
        # resource_id → IntegrityChecksum
        self._checksums: dict[str, IntegrityChecksum] = {}

    # ── Compute ───────────────────────────────────────────────────────────────

    def compute(
        self,
        resource_id: str,
        data: bytes,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        store: bool = True,
    ) -> IntegrityChecksum:
        """Compute a tamper-evident checksum for *data* and optionally store it."""
        checksum = _hmac_hex(self._secret, data)

        record = IntegrityChecksum(
            resource_id=resource_id,
            algorithm=_HMAC_DIGEST,
            checksum=checksum,
            metadata={"data_length": len(data)},
        )

        if store:
            with self._lock:
                self._checksums[resource_id] = record

        return record

    def compute_hash(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Compute a plain (non-keyed) hash of *data*."""
        return get_crypto_provider().hash(data, algorithm.value)

    # ── Verify ────────────────────────────────────────────────────────────────

    def verify(
        self,
        resource_id: str,
        data: bytes,
        expected_checksum: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
    ) -> bool:
        """Verify data integrity. Returns True on match."""
        actual = _hmac_hex(self._secret, data)
        return hmac.compare_digest(actual, expected_checksum)

    def verify_or_raise(
        self,
        resource_id: str,
        data: bytes,
        expected_checksum: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
    ) -> None:
        """Like verify() but raises TamperDetectedError on mismatch."""
        if not self.verify(resource_id, data, expected_checksum, algorithm):
            _LOG.error("Tamper detected on resource '%s'", resource_id)
            raise TamperDetectedError(
                f"Tamper detected on resource '{resource_id}'",
                code="SEC-TD-001",
                context={"resource_id": resource_id},
            )

    def verify_stored(self, resource_id: str, data: bytes) -> bool:
        """Verify *data* against the stored checksum for *resource_id*."""
        with self._lock:
            record = self._checksums.get(resource_id)
        if record is None:
            raise ChecksumMismatchError(
                f"No stored checksum for '{resource_id}'",
                code="SEC-TD-002",
                context={"resource_id": resource_id},
            )
        return self.verify(resource_id, data, record.checksum)

    # ── Audit record integrity ────────────────────────────────────────────────

    def sign_audit_record(self, record_dict: dict[str, Any]) -> str:
        """Create an HMAC-SHA256 checksum of an audit record dict."""
        import json
        # Exclude the checksum field itself from signing
        clean = {k: v for k, v in record_dict.items() if k != "checksum"}
        canonical = json.dumps(clean, sort_keys=True, separators=(",", ":"))
        return _hmac_hex(self._secret, canonical.encode())

    def verify_audit_record(self, record_dict: dict[str, Any], expected: str) -> bool:
        """Verify an audit record's HMAC checksum."""
        actual = self.sign_audit_record(record_dict)
        return hmac.compare_digest(actual, expected)

    # ── Storage ───────────────────────────────────────────────────────────────

    def get_stored(self, resource_id: str) -> Optional[IntegrityChecksum]:
        with self._lock:
            return self._checksums.get(resource_id)

    def remove_stored(self, resource_id: str) -> bool:
        with self._lock:
            return self._checksums.pop(resource_id, None) is not None

    def list_stored(self) -> list[IntegrityChecksum]:
        with self._lock:
            return list(self._checksums.values())

    def reset(self) -> None:
        with self._lock:
            self._checksums.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_tamper_detector() -> TamperDetector:
    global _detector
    with _mgr_lock:
        if _detector is None:
            _detector = TamperDetector()
        return _detector


def reset_tamper_detector() -> None:
    global _detector
    with _mgr_lock:
        if _detector is not None:
            _detector.reset()
        _detector = None
