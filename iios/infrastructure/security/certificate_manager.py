"""
iios/infrastructure/security/certificate_manager.py
====================================================
Manages TLS certificate metadata, validation, and fingerprinting.
Actual X.509 operations use the ``cryptography`` package when available.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Optional

from .security_constants import CertificateType
from .security_exceptions import CertificateExpiredError, CertificateInvalidError, CertificateError
from .security_models import CertificateRecord

__all__ = ["CertificateManager", "get_certificate_manager", "reset_certificate_manager"]

_LOG = logging.getLogger("iios.security.certificate")
_mgr_lock = threading.Lock()
_manager: Optional["CertificateManager"] = None

_X509_OK = False
try:
    from cryptography import x509 as _x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes as _hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
    from cryptography.hazmat.backends import default_backend
    import datetime
    _X509_OK = True
except ImportError:
    pass


class CertificateManager:
    """Thread-safe certificate registry and validator.

    Stores CertificateRecord metadata. When ``cryptography`` is available,
    can generate self-signed certs and parse PEM data.

    Usage::

        mgr = get_certificate_manager()
        cert_id = mgr.register_pem(pem_bytes, name="tls_server")
        rec = mgr.get(cert_id)
        mgr.validate(cert_id)   # raises CertificateExpiredError if expired
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._certs: dict[str, CertificateRecord] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, record: CertificateRecord) -> str:
        with self._lock:
            self._certs[record.cert_id] = record
        _LOG.debug("Registered certificate: %s (%s)", record.name, record.cert_id[:8])
        return record.cert_id

    def register_pem(self, pem_data: bytes, name: str, cert_type: CertificateType = CertificateType.SERVER) -> str:
        """Parse PEM data and register the certificate. Requires ``cryptography``."""
        if not _X509_OK:
            # Fallback: store PEM as-is with minimal metadata
            fingerprint = hashlib.sha256(pem_data).hexdigest()
            record = CertificateRecord(
                name=name,
                cert_type=cert_type,
                fingerprint=fingerprint,
                pem_data=pem_data.decode("utf-8", errors="replace"),
            )
            return self.register(record)

        try:
            cert = _x509.load_pem_x509_certificate(pem_data, default_backend())
            fingerprint = cert.fingerprint(_hashes.SHA256()).hex()
            not_before = cert.not_valid_before_utc.timestamp()
            not_after = cert.not_valid_after_utc.timestamp()
            try:
                subject = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            except Exception:
                subject = str(cert.subject)
            try:
                issuer = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            except Exception:
                issuer = str(cert.issuer)

            record = CertificateRecord(
                name=name,
                cert_type=cert_type,
                subject=subject,
                issuer=issuer,
                fingerprint=fingerprint,
                not_before=not_before,
                not_after=not_after,
                pem_data=pem_data.decode("utf-8", errors="replace"),
            )
            return self.register(record)
        except Exception as exc:
            raise CertificateInvalidError(
                f"Failed to parse PEM certificate: {exc}",
                code="SEC-CERT-001",
            ) from exc

    # ── Self-signed generation ─────────────────────────────────────────────────

    def generate_self_signed(
        self,
        name: str,
        common_name: str = "iios.local",
        valid_days: int = 365,
    ) -> tuple[str, bytes, bytes]:
        """Generate a self-signed certificate. Returns (cert_id, cert_pem, key_pem).

        Requires ``cryptography`` package.
        """
        if not _X509_OK:
            raise CertificateError(
                "Self-signed certificate generation requires cryptography package",
                code="SEC-CERT-002",
            )
        private_key = _rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        subject = issuer = _x509.Name([
            _x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            _x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(_x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=valid_days))
            .add_extension(_x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(private_key, _hashes.SHA256(), default_backend())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        cert_id = self.register_pem(cert_pem, name=name, cert_type=CertificateType.SELF_SIGNED)
        return cert_id, cert_pem, key_pem

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, cert_id: str) -> CertificateRecord:
        with self._lock:
            r = self._certs.get(cert_id)
        if r is None:
            raise CertificateError(
                f"Certificate '{cert_id}' not found",
                code="SEC-CERT-003",
            )
        return r

    def get_optional(self, cert_id: str) -> Optional[CertificateRecord]:
        with self._lock:
            return self._certs.get(cert_id)

    def find_by_name(self, name: str) -> Optional[CertificateRecord]:
        with self._lock:
            for r in self._certs.values():
                if r.name == name:
                    return r
        return None

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self, cert_id: str) -> None:
        """Validate that the certificate is not expired. Raises on failure."""
        rec = self.get(cert_id)
        if rec.is_expired:
            raise CertificateExpiredError(
                f"Certificate '{rec.name}' has expired",
                code="SEC-CERT-004",
                context={"cert_id": cert_id, "expired_at": rec.not_after},
            )
        if not rec.is_valid:
            raise CertificateInvalidError(
                f"Certificate '{rec.name}' is not yet valid",
                code="SEC-CERT-005",
            )

    def list_all(self) -> list[CertificateRecord]:
        with self._lock:
            return list(self._certs.values())

    def list_expired(self) -> list[CertificateRecord]:
        with self._lock:
            return [r for r in self._certs.values() if r.is_expired]

    def delete(self, cert_id: str) -> bool:
        with self._lock:
            return self._certs.pop(cert_id, None) is not None

    def reset(self) -> None:
        with self._lock:
            self._certs.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_certificate_manager() -> CertificateManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = CertificateManager()
        return _manager


def reset_certificate_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
