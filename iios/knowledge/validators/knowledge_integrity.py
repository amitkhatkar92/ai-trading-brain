"""
iios/knowledge/validators/knowledge_integrity.py
=================================================
Content integrity checks — checksum computation and tamper detection.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from typing import Optional

from ..knowledge_exceptions import KnowledgeIntegrityError
from ..models.knowledge_record import KnowledgeRecord

__all__ = [
    "KnowledgeIntegrityChecker",
    "get_integrity_checker",
    "reset_integrity_checker",
]

_LOG = logging.getLogger("iios.knowledge.integrity")
_lock = threading.Lock()
_checker: Optional["KnowledgeIntegrityChecker"] = None


class KnowledgeIntegrityChecker:
    """Computes and verifies SHA-256 checksums of knowledge record content."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def compute_checksum(self, record: KnowledgeRecord) -> str:
        """Return SHA-256 hex digest of the record's content."""
        try:
            payload = json.dumps(record.content, sort_keys=True, default=str)
        except (TypeError, ValueError):
            payload = str(record.content)
        return hashlib.sha256(payload.encode()).hexdigest()

    def stamp(self, record: KnowledgeRecord) -> None:
        """Compute and store a checksum on the record (mutates record.checksum)."""
        record.checksum = self.compute_checksum(record)

    def verify(self, record: KnowledgeRecord) -> bool:
        """Return True if stored checksum matches recomputed checksum."""
        if not record.checksum:
            return True  # No checksum set → skip
        return self.compute_checksum(record) == record.checksum

    def verify_or_raise(self, record: KnowledgeRecord) -> None:
        """Raise KnowledgeIntegrityError if checksum mismatch detected."""
        if not self.verify(record):
            raise KnowledgeIntegrityError(
                f"Checksum mismatch for '{record.id}' — content may have been tampered",
                code="KI-001",
                context={"knowledge_id": record.id},
            )

    def compute_metadata_hash(self, record: KnowledgeRecord) -> str:
        """Return a hash of the record's metadata (not content)."""
        data = {
            "knowledge_id":  record.id,
            "version":       record.version,
            "version_seq":   record.version_sequence,
            "status":        record.status.value,
            "title":         record.title,
            "knowledge_type": record.knowledge_type.value,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def get_integrity_checker() -> KnowledgeIntegrityChecker:
    global _checker
    with _lock:
        if _checker is None:
            _checker = KnowledgeIntegrityChecker()
        return _checker


def reset_integrity_checker() -> None:
    global _checker
    with _lock:
        _checker = None
