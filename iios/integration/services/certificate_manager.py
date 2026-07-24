"""
certificate_manager.py — iios.integration.services
----------------------------------------------------
CertificateManager — stores and manages TLS certificates and private keys
for mTLS integration connectors.

Certificates are validated structurally; private keys are NEVER logged.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)


@dataclass
class CertificateEntry:
    """
    A stored certificate with its associated private key.

    private_key is NEVER logged or included in safe representations.
    """
    cert_id:      str
    common_name:  str
    certificate:  str           # PEM-encoded certificate (public, may be logged safely)
    private_key:  str           # PEM-encoded private key (NEVER log)
    issuer:       str
    valid_from:   str
    valid_until:  str
    created_at:   str
    revoked:      bool = False

    def safe_repr(self) -> Dict[str, Any]:
        """Log-safe representation — private key omitted."""
        return {
            "cert_id":     self.cert_id,
            "common_name": self.common_name,
            "issuer":      self.issuer,
            "valid_from":  self.valid_from,
            "valid_until": self.valid_until,
            "revoked":     self.revoked,
        }

    @property
    def is_valid(self) -> bool:
        return not self.revoked


class CertificateManager:
    """
    Thread-safe in-process certificate store.

    In production, back this with an HSM or PKI service.
    """

    def __init__(self) -> None:
        self._lock   = threading.Lock()
        self._certs: Dict[str, CertificateEntry] = {}

    # ── Public ───────────────────────────────────────────────────────────

    def register(
        self,
        common_name:  str,
        certificate:  str,
        private_key:  str,
        issuer:       str        = "self-signed",
        valid_from:   Optional[str] = None,
        valid_until:  Optional[str] = None,
        cert_id:      Optional[str] = None,
    ) -> CertificateEntry:
        """Register a certificate. Returns the stored entry."""
        now = datetime.now(timezone.utc).isoformat()
        entry = CertificateEntry(
            cert_id     = cert_id or f"cert-{uuid.uuid4().hex[:12]}",
            common_name = common_name,
            certificate = certificate,
            private_key = private_key,
            issuer      = issuer,
            valid_from  = valid_from or now,
            valid_until = valid_until or now,
            created_at  = now,
        )
        with self._lock:
            self._certs[entry.cert_id] = entry
        return entry

    def get(self, cert_id: str) -> Optional[CertificateEntry]:
        with self._lock:
            return self._certs.get(cert_id)

    def revoke(self, cert_id: str) -> bool:
        with self._lock:
            entry = self._certs.get(cert_id)
            if entry:
                entry.revoked = True
                return True
        return False

    def delete(self, cert_id: str) -> bool:
        with self._lock:
            if cert_id in self._certs:
                del self._certs[cert_id]
                return True
        return False

    def list_certs(self, include_revoked: bool = False) -> List[CertificateEntry]:
        with self._lock:
            entries = list(self._certs.values())
        if not include_revoked:
            entries = [e for e in entries if not e.revoked]
        return entries

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._certs)

    @property
    def valid_count(self) -> int:
        with self._lock:
            return sum(1 for e in self._certs.values() if not e.revoked)
