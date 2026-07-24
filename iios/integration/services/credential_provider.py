"""
credential_provider.py — iios.integration.services
----------------------------------------------------
CredentialProvider — stores and retrieves credentials for connector auth.

Credentials are stored in-memory (keyed by credential_id) and are
NEVER logged. Real deployments back this with SecretManager.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import AuthScheme

_log = get_logger(__name__)


@dataclass
class CredentialEntry:
    """
    A stored credential entry.

    The ``secret_fields`` set marks which keys must not be logged.
    """
    credential_id:  str
    scheme:         AuthScheme
    principal:      str
    credentials:    Dict[str, Any]    # NEVER log this
    secret_fields:  frozenset         # field names to redact in any repr
    created_at:     str
    last_used:      Optional[str] = None

    def safe_repr(self) -> Dict[str, Any]:
        """Return a log-safe dict with secrets replaced by ***."""
        return {
            k: ("***" if k in self.secret_fields else v)
            for k, v in self.credentials.items()
        }


class CredentialProvider:
    """
    Thread-safe in-process credential store.

    Use ``store()`` to register credentials; use ``retrieve()`` at
    connector auth time. Credentials are never written to disk or logs.
    """

    # Fields that must always be redacted
    _ALWAYS_SECRET = frozenset({
        "password", "secret", "token", "api_key", "private_key",
        "client_secret", "passphrase", "access_token", "refresh_token",
        "api_secret", "signature",
    })

    def __init__(self) -> None:
        self._lock    = threading.Lock()
        self._store:  Dict[str, CredentialEntry] = {}

    # ── Public ───────────────────────────────────────────────────────────

    def store(
        self,
        scheme:        AuthScheme,
        principal:     str,
        credentials:   Dict[str, Any],
        credential_id: Optional[str] = None,
    ) -> str:
        """
        Store credentials. Returns the credential_id.

        ``credential_id`` may be supplied for deterministic IDs (e.g. tests).
        """
        cid    = credential_id or f"cred-{uuid.uuid4().hex[:12]}"
        secret = self._ALWAYS_SECRET | frozenset(
            k for k in credentials
            if any(s in k.lower() for s in ("secret", "key", "token", "pass"))
        )
        entry = CredentialEntry(
            credential_id = cid,
            scheme        = scheme,
            principal     = principal,
            credentials   = dict(credentials),
            secret_fields = secret,
            created_at    = datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._store[cid] = entry
        return cid

    def retrieve(self, credential_id: str) -> Optional[CredentialEntry]:
        """Return the credential entry, or None if not found."""
        with self._lock:
            entry = self._store.get(credential_id)
            if entry:
                entry.last_used = datetime.now(timezone.utc).isoformat()
        return entry

    def delete(self, credential_id: str) -> bool:
        """Delete a credential. Returns True if found."""
        with self._lock:
            if credential_id in self._store:
                del self._store[credential_id]
                return True
        return False

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)
