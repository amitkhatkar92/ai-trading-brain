"""
iios/infrastructure/security/integrity_manager.py
==================================================
Data integrity verification: checksums, signed payloads, and hash verification.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import threading
from typing import Any, Optional

from .crypto_provider import get_crypto_provider
from .encryption_manager import get_encryption_manager
from .security_constants import HashAlgorithm
from .security_exceptions import TamperDetectedError, ChecksumMismatchError
from .security_models import IntegrityChecksum, SignedPayload
from .tamper_detector import get_tamper_detector

__all__ = ["IntegrityManager", "get_integrity_manager", "reset_integrity_manager"]

_LOG = logging.getLogger("iios.security.integrity")
_mgr_lock = threading.Lock()
_manager: Optional["IntegrityManager"] = None


class IntegrityManager:
    """Data integrity verification manager.

    Provides high-level methods for computing and verifying checksums,
    signing payloads, and detecting data corruption or tampering.

    Usage::

        im = get_integrity_manager()
        checksum = im.checksum(b"data to protect", "resource:123")
        im.verify_checksum(b"data to protect", "resource:123", checksum)

        sp = im.sign(b"payload")
        im.verify_signature(sp)   # raises TamperDetectedError if invalid
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    # ── Checksums ─────────────────────────────────────────────────────────────

    def checksum(
        self,
        data: bytes,
        resource_id: str = "",
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        store: bool = True,
    ) -> IntegrityChecksum:
        """Compute and optionally store a tamper-evident checksum."""
        return get_tamper_detector().compute(resource_id, data, algorithm, store=store)

    def verify_checksum(
        self,
        data: bytes,
        resource_id: str,
        expected: Optional[str] = None,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
    ) -> bool:
        """Verify data against a checksum.

        If *expected* is None, uses the stored checksum for *resource_id*.
        Returns True on success, raises TamperDetectedError on mismatch.
        """
        if expected is not None:
            ok = get_tamper_detector().verify(resource_id, data, expected, algorithm)
        else:
            ok = get_tamper_detector().verify_stored(resource_id, data)

        if not ok:
            _LOG.error("Integrity violation detected for '%s'", resource_id)
            raise TamperDetectedError(
                f"Integrity check failed for '{resource_id}'",
                code="SEC-INT-001",
                context={"resource_id": resource_id},
            )
        return True

    # ── Signing / Verification ─────────────────────────────────────────────────

    def sign(self, data: bytes, key_name: Optional[str] = None) -> SignedPayload:
        """Create a signed payload."""
        return get_encryption_manager().create_signed_payload(data, key_name)

    def verify_signature(self, signed: SignedPayload) -> bool:
        """Verify a signed payload. Raises TamperDetectedError on failure."""
        ok = get_encryption_manager().verify_signed_payload(signed)
        if not ok:
            raise TamperDetectedError(
                "Signature verification failed",
                code="SEC-INT-002",
            )
        return True

    # ── Content hashing ───────────────────────────────────────────────────────

    def hash(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Compute a hex digest of *data*."""
        return get_crypto_provider().hash(data, algorithm.value)

    def hash_file(self, filepath: str, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Compute the hash of a file. Returns hex digest."""
        h = hashlib.new(algorithm.value)
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ── Dictionary / JSON integrity ───────────────────────────────────────────

    def checksum_dict(self, data: dict[str, Any], resource_id: str = "") -> str:
        """Compute an HMAC checksum of a dict (JSON-canonical)."""
        import json
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return get_tamper_detector().sign_audit_record(data)

    def verify_dict(self, data: dict[str, Any], expected: str) -> bool:
        """Verify a dict's HMAC checksum."""
        return get_tamper_detector().verify_audit_record(data, expected)

    # ── String helpers ────────────────────────────────────────────────────────

    def sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def sha512(self, data: bytes) -> str:
        return hashlib.sha512(data).hexdigest()

    def constant_time_compare(self, a: str, b: str) -> bool:
        return hmac.compare_digest(a.encode(), b.encode())

    def reset(self) -> None:
        pass  # stateless


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_integrity_manager() -> IntegrityManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = IntegrityManager()
        return _manager


def reset_integrity_manager() -> None:
    global _manager
    with _mgr_lock:
        _manager = None
