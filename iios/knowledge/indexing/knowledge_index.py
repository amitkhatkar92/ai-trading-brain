"""
iios/knowledge/indexing/knowledge_index.py
==========================================
In-memory multi-field index for fast knowledge lookups.

Maintains inverted indexes keyed by:
  - ID (exact)
  - knowledge_type
  - status
  - domain
  - owner_id
  - tags (each tag → set of IDs)
  - keywords (lowercased title/description tokens → set of IDs)
"""

from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict
from typing import Optional, Set

from ..knowledge_constants import (
    IndexType,
    KnowledgeDomain,
    KnowledgeStatus,
    KnowledgeType,
)
from ..models.knowledge_record import KnowledgeRecord

__all__ = ["KnowledgeIndex", "get_knowledge_index", "reset_knowledge_index"]

_LOG = logging.getLogger("iios.knowledge.index")
_lock = threading.Lock()
_index: Optional["KnowledgeIndex"] = None

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


class KnowledgeIndex:
    """Thread-safe multi-field inverted index for knowledge records.

    All index operations are O(1) amortised per field (hash-set lookup).
    Keyword search is O(k) where k is the number of query tokens.

    Usage::

        idx = get_knowledge_index()
        idx.index(record)
        ids = idx.by_tag("nifty")
        ids = idx.by_type(KnowledgeType.FACT)
        ids = idx.by_keyword("nifty 50")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # id → record reference (weak registry)
        self._id_set: set[str] = set()
        # type → set[id]
        self._by_type: dict[str, set[str]] = defaultdict(set)
        # status → set[id]
        self._by_status: dict[str, set[str]] = defaultdict(set)
        # domain → set[id]
        self._by_domain: dict[str, set[str]] = defaultdict(set)
        # owner_id → set[id]
        self._by_owner: dict[str, set[str]] = defaultdict(set)
        # tag → set[id]
        self._by_tag: dict[str, set[str]] = defaultdict(set)
        # keyword_token → set[id]
        self._by_keyword: dict[str, set[str]] = defaultdict(set)

    # ── Index / De-index ──────────────────────────────────────────────────────

    def index(self, record: KnowledgeRecord) -> None:
        """Add or update *record* in the index."""
        rid = record.id
        with self._lock:
            # Remove stale entries first
            self._deindex_unsafe(rid)
            self._id_set.add(rid)
            self._by_type[record.knowledge_type.value].add(rid)
            self._by_status[record.status.value].add(rid)
            self._by_domain[record.metadata.domain.value].add(rid)
            self._by_owner[record.metadata.owner_id].add(rid)
            for tag in record.metadata.tags:
                self._by_tag[tag.lower()].add(rid)
            for token in _tokenize(record.title):
                self._by_keyword[token].add(rid)
            for token in _tokenize(record.metadata.description):
                self._by_keyword[token].add(rid)

    def deindex(self, knowledge_id: str) -> None:
        """Remove all index entries for *knowledge_id*."""
        with self._lock:
            self._deindex_unsafe(knowledge_id)

    def _deindex_unsafe(self, rid: str) -> None:
        """Must be called with self._lock held."""
        if rid not in self._id_set:
            return
        self._id_set.discard(rid)
        for mapping in (self._by_type, self._by_status, self._by_domain,
                        self._by_owner, self._by_tag, self._by_keyword):
            for s in mapping.values():
                s.discard(rid)

    # ── Lookups ───────────────────────────────────────────────────────────────

    def by_type(self, knowledge_type: KnowledgeType) -> set[str]:
        with self._lock:
            return set(self._by_type.get(knowledge_type.value, set()))

    def by_status(self, status: KnowledgeStatus) -> set[str]:
        with self._lock:
            return set(self._by_status.get(status.value, set()))

    def by_domain(self, domain: KnowledgeDomain) -> set[str]:
        with self._lock:
            return set(self._by_domain.get(domain.value, set()))

    def by_owner(self, owner_id: str) -> set[str]:
        with self._lock:
            return set(self._by_owner.get(owner_id, set()))

    def by_tag(self, tag: str) -> set[str]:
        with self._lock:
            return set(self._by_tag.get(tag.lower(), set()))

    def by_tags(self, tags: list[str], match_all: bool = False) -> set[str]:
        """Return IDs matching any (match_all=False) or all (match_all=True) tags."""
        with self._lock:
            sets = [set(self._by_tag.get(t.lower(), set())) for t in tags]
        if not sets:
            return set()
        if match_all:
            result = sets[0]
            for s in sets[1:]:
                result = result & s
            return result
        result = set()
        for s in sets:
            result |= s
        return result

    def by_keyword(self, text: str) -> set[str]:
        """Return IDs where any token from *text* appears in title/description."""
        tokens = _tokenize(text)
        if not tokens:
            return set()
        with self._lock:
            result: Optional[set[str]] = None
            for token in tokens:
                matches = set(self._by_keyword.get(token, set()))
                result = matches if result is None else (result & matches)
        return result or set()

    def by_keyword_any(self, text: str) -> set[str]:
        """Return IDs where ANY token from *text* matches."""
        tokens = _tokenize(text)
        result: set[str] = set()
        with self._lock:
            for token in tokens:
                result |= set(self._by_keyword.get(token, set()))
        return result

    def all_ids(self) -> set[str]:
        with self._lock:
            return set(self._id_set)

    def count(self) -> int:
        with self._lock:
            return len(self._id_set)

    def reset(self) -> None:
        with self._lock:
            self._id_set.clear()
            for d in (self._by_type, self._by_status, self._by_domain,
                      self._by_owner, self._by_tag, self._by_keyword):
                d.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_knowledge_index() -> KnowledgeIndex:
    global _index
    with _lock:
        if _index is None:
            _index = KnowledgeIndex()
        return _index


def reset_knowledge_index() -> None:
    global _index
    with _lock:
        if _index is not None:
            _index.reset()
        _index = None
