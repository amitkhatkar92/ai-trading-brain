"""
iios/knowledge/search/index_manager.py
========================================
In-memory multi-index store for the Knowledge Indexing & Search Engine.

Maintains seven index types in a single thread-safe class:
  • Primary   — item_id → UnifiedSearchResult (template)
  • Keyword   — token → set[item_id]
  • Tag       — tag → set[item_id]
  • Metadata  — "field:value" → set[item_id]
  • Ontology  — type/domain key → set[item_id]
  • ItemType  — ItemType.value → set[item_id]
  • Temporal  — item_id → (created_at, updated_at)
"""
from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict
from typing import Any, Optional

from .search_constants import (
    ItemType, SearchIndexType, MIN_TOKEN_LENGTH,
    TITLE_BOOST, TAG_BOOST, CONTENT_BOOST, EXACT_TITLE_BONUS, ALL_TOKENS_BONUS,
)
from .models.unified_result import UnifiedSearchResult

__all__ = ["IndexManager", "get_index_manager", "reset_index_manager"]

_LOG  = logging.getLogger("iios.knowledge.search.index")
_lock = threading.Lock()
_mgr: Optional["IndexManager"] = None

_WORD_RE = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in _WORD_RE.findall(text.lower()) if len(t) >= MIN_TOKEN_LENGTH]


def _ratio(a: str, b: str) -> float:
    """Simple character-level overlap ratio for fuzzy matching."""
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    if la == lb and a == b:
        return 1.0
    shorter, longer = (a, b) if la <= lb else (b, a)
    matches = sum(1 for c in shorter if c in longer)
    return matches / len(longer)


class IndexManager:
    """Multi-index store for unified knowledge + graph node search.

    Completely in-memory. Thread-safe via a single RLock.

    Usage::

        mgr = get_index_manager()
        mgr.index_item(UnifiedSearchResult.from_knowledge_record(record))
        ids = mgr.search_keyword(["nifty", "trend"], operator="OR")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        # Primary (item_id → result template, score=0.0)
        self._primary: dict[str, UnifiedSearchResult] = {}

        # Keyword (token → set of item_ids)
        self._keyword: defaultdict[str, set[str]] = defaultdict(set)

        # Tag (tag.lower() → set of item_ids)
        self._tags: defaultdict[str, set[str]] = defaultdict(set)

        # Metadata ("field:value" → set of item_ids)
        self._metadata: defaultdict[str, set[str]] = defaultdict(set)

        # Ontology (type/domain value → set of item_ids)
        self._ontology: defaultdict[str, set[str]] = defaultdict(set)

        # Item type (ItemType.value → set of item_ids)
        self._by_type: defaultdict[str, set[str]] = defaultdict(set)

        # Temporal
        self._created_at: dict[str, float] = {}
        self._updated_at: dict[str, float] = {}

        # Token document-frequency for TF-IDF scoring
        self._df: defaultdict[str, int] = defaultdict(int)  # token → doc count

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_item(self, result: UnifiedSearchResult) -> None:
        """Add or update a single item across all indexes."""
        with self._lock:
            item_id = result.item_id
            # Remove old entry first (avoids stale index entries)
            if item_id in self._primary:
                self._deindex_item_locked(item_id)

            self._primary[item_id] = result

            # ── Keyword ──────────────────────────────────────────────────────
            title_tokens   = _tokenize(result.title)
            content_tokens = _tokenize(result.content[:2000])
            all_tokens     = set(title_tokens + content_tokens)
            for tok in all_tokens:
                self._keyword[tok].add(item_id)
                self._df[tok] += 1

            # ── Tags ─────────────────────────────────────────────────────────
            for tag in result.tags:
                self._tags[tag.lower()].add(item_id)

            # ── Metadata ─────────────────────────────────────────────────────
            for key, val in result.metadata.items():
                if isinstance(val, (str, int, float, bool)) and val not in ("", None):
                    mk = f"{key}:{str(val).lower()}"
                    self._metadata[mk].add(item_id)

            # ── Ontology ─────────────────────────────────────────────────────
            if "knowledge_type" in result.metadata:
                self._ontology[f"knowledge_type:{result.metadata['knowledge_type']}"].add(item_id)
            if "domain" in result.metadata:
                self._ontology[f"domain:{result.metadata['domain']}"].add(item_id)
            if "node_type" in result.metadata:
                self._ontology[f"node_type:{result.metadata['node_type']}"].add(item_id)

            # ── Item type ────────────────────────────────────────────────────
            self._by_type[result.item_type].add(item_id)

            # ── Temporal ─────────────────────────────────────────────────────
            self._created_at[item_id] = result.created_at
            self._updated_at[item_id] = result.updated_at

    def _deindex_item_locked(self, item_id: str) -> None:
        """Remove item from all indexes (caller holds lock)."""
        old = self._primary.pop(item_id, None)
        if old is None:
            return

        # Keyword
        title_tokens   = _tokenize(old.title)
        content_tokens = _tokenize(old.content[:2000])
        for tok in set(title_tokens + content_tokens):
            ids = self._keyword.get(tok)
            if ids:
                ids.discard(item_id)
                self._df[tok] = max(0, self._df[tok] - 1)
                if not ids:
                    del self._keyword[tok]

        # Tags
        for tag in old.tags:
            ids = self._tags.get(tag.lower())
            if ids:
                ids.discard(item_id)

        # Metadata
        for key, val in old.metadata.items():
            if isinstance(val, (str, int, float, bool)) and val not in ("", None):
                mk = f"{key}:{str(val).lower()}"
                ids = self._metadata.get(mk)
                if ids:
                    ids.discard(item_id)

        # Ontology
        for mk in [
            f"knowledge_type:{old.metadata.get('knowledge_type', '')}",
            f"domain:{old.metadata.get('domain', '')}",
            f"node_type:{old.metadata.get('node_type', '')}",
        ]:
            ids = self._ontology.get(mk)
            if ids:
                ids.discard(item_id)

        # Item type
        ids = self._by_type.get(old.item_type)
        if ids:
            ids.discard(item_id)

        # Temporal
        self._created_at.pop(item_id, None)
        self._updated_at.pop(item_id, None)

    def deindex_item(self, item_id: str) -> bool:
        with self._lock:
            if item_id not in self._primary:
                return False
            self._deindex_item_locked(item_id)
            return True

    def update_item(self, result: UnifiedSearchResult) -> None:
        """Re-index an item (deindex + index)."""
        self.index_item(result)

    # ── Read operations ───────────────────────────────────────────────────────

    def get_item(self, item_id: str) -> Optional[UnifiedSearchResult]:
        with self._lock:
            return self._primary.get(item_id)

    def item_exists(self, item_id: str) -> bool:
        with self._lock:
            return item_id in self._primary

    def item_count(self) -> int:
        with self._lock:
            return len(self._primary)

    def all_item_ids(self, item_type: Optional[str] = None) -> set[str]:
        with self._lock:
            if item_type:
                return set(self._by_type.get(item_type, set()))
            return set(self._primary.keys())

    def all_items(self) -> list[UnifiedSearchResult]:
        with self._lock:
            return list(self._primary.values())

    # ── Search operations ─────────────────────────────────────────────────────

    def search_by_id(self, item_id: str) -> Optional[UnifiedSearchResult]:
        with self._lock:
            return self._primary.get(item_id)

    def search_keyword(
        self,
        tokens:   list[str],
        operator: str = "OR",    # "AND" | "OR"
        fuzzy:    bool = False,
        fuzzy_threshold: float = 0.75,
    ) -> dict[str, float]:
        """
        Returns {item_id: relevance_score} for keyword matches.
        Score is a simplified TF-weighted relevance.
        """
        if not tokens:
            return {}
        with self._lock:
            total_docs = len(self._primary)
            if total_docs == 0:
                return {}

            # Resolve matching item_id sets per token
            token_sets: list[set[str]] = []
            for tok in tokens:
                ids: set[str] = set()
                # Exact match
                ids.update(self._keyword.get(tok, set()))
                # Fuzzy match
                if fuzzy and not ids:
                    for indexed_tok, indexed_ids in self._keyword.items():
                        if _ratio(tok, indexed_tok) >= fuzzy_threshold:
                            ids.update(indexed_ids)
                token_sets.append(ids)

            if operator.upper() == "AND":
                if not token_sets:
                    return {}
                and_ids = token_sets[0].copy()
                for s in token_sets[1:]:
                    and_ids &= s
            else:
                and_ids = set()
                for s in token_sets:
                    and_ids |= s

            # Compute per-item score
            import math
            scores: dict[str, float] = {}
            for item_id in and_ids:
                result = self._primary.get(item_id)
                if result is None:
                    continue
                score = 0.0
                title_tokens   = _tokenize(result.title)
                content_tokens = _tokenize(result.content[:2000])
                all_match_count = 0

                for tok in tokens:
                    # Title matches
                    tc = title_tokens.count(tok)
                    # IDF
                    df = self._df.get(tok, 1)
                    idf = math.log(1.0 + total_docs / df)
                    if tc > 0:
                        score += TITLE_BOOST * tc * idf
                        all_match_count += 1
                    # Content matches
                    cc = content_tokens.count(tok)
                    if cc > 0:
                        score += CONTENT_BOOST * cc * idf
                        all_match_count += 1

                # All-tokens bonus
                if all_match_count == len(tokens) * 2 and len(tokens) > 1:
                    score += ALL_TOKENS_BONUS

                # Exact title match bonus
                if result.title.lower() == " ".join(tokens):
                    score += EXACT_TITLE_BONUS

                scores[item_id] = score
            return scores

    def search_by_tags(
        self,
        tags:      list[str],
        match_all: bool = False,
    ) -> set[str]:
        with self._lock:
            if not tags:
                return set(self._primary.keys())
            tag_sets = [self._tags.get(t.lower(), set()) for t in tags]
            if match_all:
                result = tag_sets[0].copy() if tag_sets else set()
                for s in tag_sets[1:]:
                    result &= s
                return result
            else:
                result = set()
                for s in tag_sets:
                    result |= s
                return result

    def search_by_metadata(
        self, filters: dict[str, Any],
    ) -> set[str]:
        """Intersect all filter conditions (AND semantics)."""
        with self._lock:
            if not filters:
                return set(self._primary.keys())
            first = True
            result: set[str] = set()
            for key, val in filters.items():
                mk = f"{key}:{str(val).lower()}"
                ids = self._metadata.get(mk, set())
                if first:
                    result = ids.copy()
                    first = False
                else:
                    result &= ids
            return result

    def search_by_ontology(self, keys: list[str]) -> set[str]:
        """
        keys examples: ["knowledge_type:fact", "domain:equity", "node_type:signal"]
        """
        with self._lock:
            if not keys:
                return set(self._primary.keys())
            result: set[str] = set()
            for key in keys:
                result |= self._ontology.get(key.lower(), set())
            return result

    def search_by_item_type(self, item_types: list[str]) -> set[str]:
        with self._lock:
            result: set[str] = set()
            for it in item_types:
                result |= self._by_type.get(it, set())
            return result

    def get_created_at(self, item_id: str) -> float:
        return self._created_at.get(item_id, 0.0)

    def get_updated_at(self, item_id: str) -> float:
        return self._updated_at.get(item_id, 0.0)

    def keyword_token_count(self) -> int:
        with self._lock:
            return len(self._keyword)

    def clear(self) -> None:
        with self._lock:
            self._primary.clear()
            self._keyword.clear()
            self._tags.clear()
            self._metadata.clear()
            self._ontology.clear()
            self._by_type.clear()
            self._created_at.clear()
            self._updated_at.clear()
            self._df.clear()

    def reset(self) -> None:
        self.clear()

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "item_count":        len(self._primary),
                "keyword_count":     len(self._keyword),
                "tag_count":         len(self._tags),
                "metadata_key_count": len(self._metadata),
                "ontology_key_count": len(self._ontology),
                "items_by_type":     {k: len(v) for k, v in self._by_type.items()},
            }


def get_index_manager() -> IndexManager:
    global _mgr
    with _lock:
        if _mgr is None:
            _mgr = IndexManager()
        return _mgr


def reset_index_manager() -> None:
    global _mgr
    with _lock:
        _mgr = None
