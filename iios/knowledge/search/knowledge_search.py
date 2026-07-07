"""
iios/knowledge/search/knowledge_search.py
==========================================
Multi-mode search engine for the Knowledge Engine.

Supports:
- Exact ID lookup
- Keyword (token intersection / union)
- Tag search
- Metadata field search
- Hybrid (keyword + metadata)
- Ranked results by relevance score
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from ..knowledge_constants import SearchMode, KnowledgeDomain, KnowledgeType
from ..knowledge_exceptions import KnowledgeSearchError
from ..models.knowledge_record import KnowledgeRecord
from ..models.knowledge_query import SearchQuery, PageResult, PageRequest
from ..repositories.knowledge_repository import KnowledgeRepository, get_knowledge_repository
from ..indexing.knowledge_index import KnowledgeIndex, get_knowledge_index

__all__ = [
    "SearchResult",
    "KnowledgeSearchEngine",
    "get_search_engine",
    "reset_search_engine",
]

_LOG = logging.getLogger("iios.knowledge.search")
_lock = threading.Lock()
_engine: Optional["KnowledgeSearchEngine"] = None

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


@dataclass
class SearchResult:
    """A ranked knowledge record returned by a search query."""
    record:    KnowledgeRecord
    score:     float  = 1.0
    highlights: list[str] = field(default_factory=list)

    def __lt__(self, other: "SearchResult") -> bool:
        return self.score < other.score


class KnowledgeSearchEngine:
    """Ranked multi-mode search over the knowledge repository.

    Usage::

        engine = get_search_engine()
        results = engine.search(SearchQuery(text="NIFTY 50 trend", mode=SearchMode.KEYWORD))
        for r in results:
            print(r.score, r.record.title)
    """

    def __init__(
        self,
        repository: Optional[KnowledgeRepository] = None,
        index: Optional[KnowledgeIndex] = None,
    ) -> None:
        self._repo  = repository or get_knowledge_repository()
        self._index = index      or get_knowledge_index()
        self._lock  = threading.RLock()

    # ── Main search entry-point ───────────────────────────────────────────────

    def search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute a search query. Returns scored results sorted by relevance."""
        if query.mode == SearchMode.EXACT:
            return self._exact_search(query)
        if query.mode == SearchMode.KEYWORD:
            return self._keyword_search(query)
        if query.mode == SearchMode.HYBRID:
            return self._hybrid_search(query)
        # Default: keyword
        return self._keyword_search(query)

    def search_paged(self, query: SearchQuery) -> PageResult:
        """Search and return a paginated PageResult."""
        results = self.search(query)
        # Apply filter.min_score
        results = [r for r in results if r.score >= query.min_score]
        # Paginate
        page = query.pagination
        total = len(results)
        start = page.offset
        end   = start + page.page_size
        return PageResult.build(
            items=[r.record for r in results[start:end]],
            total=total,
            req=page,
        )

    # ── Search modes ──────────────────────────────────────────────────────────

    def _exact_search(self, query: SearchQuery) -> list[SearchResult]:
        """Return the exact record matching the text as a knowledge_id."""
        rec = self._repo.get_optional(query.text.strip())
        if rec is None:
            return []
        return [SearchResult(record=rec, score=1.0, highlights=[query.text])]

    def _keyword_search(self, query: SearchQuery) -> list[SearchResult]:
        """Token intersection search over title + description indexes."""
        text = query.text.strip()
        if not text:
            return self._all_as_results(query)

        tokens = _tokenize(text)
        if not tokens:
            return []

        # ALL tokens must appear (AND) for a high score; fallback to ANY
        and_ids = self._index.by_keyword(text)
        any_ids = self._index.by_keyword_any(text)

        results: list[SearchResult] = []

        # Boost tags from query
        tag_ids = self._index.by_tags(query.boost_tags, match_all=False) if query.boost_tags else set()

        for rid in any_ids:
            rec = self._repo.get_optional(rid)
            if rec is None or rec.is_deleted:
                continue
            if not self._match_query_filter(rec, query):
                continue
            score = self._compute_keyword_score(rec, tokens, and_ids, tag_ids)
            highlights = self._extract_highlights(rec, tokens)
            results.append(SearchResult(record=rec, score=score, highlights=highlights))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _hybrid_search(self, query: SearchQuery) -> list[SearchResult]:
        """Combine keyword score with metadata relevance."""
        keyword_results = {r.record.id: r for r in self._keyword_search(query)}
        # Also run filter-only (no text) to catch metadata-only matches
        filter_q = SearchQuery(text="", filter=query.filter, pagination=query.pagination)
        for rid in self._index.all_ids():
            if rid in keyword_results:
                continue
            rec = self._repo.get_optional(rid)
            if rec is None or rec.is_deleted:
                continue
            if not self._match_query_filter(rec, query):
                continue
            # Lower base score for metadata-only match
            keyword_results[rid] = SearchResult(record=rec, score=0.3)

        results = sorted(keyword_results.values(), key=lambda r: r.score, reverse=True)
        return results

    def _all_as_results(self, query: SearchQuery) -> list[SearchResult]:
        results = []
        for rid in self._index.all_ids():
            rec = self._repo.get_optional(rid)
            if rec is None or rec.is_deleted:
                continue
            if not self._match_query_filter(rec, query):
                continue
            results.append(SearchResult(record=rec, score=1.0))
        return results

    # ── Convenience methods ───────────────────────────────────────────────────

    def find_by_id(self, knowledge_id: str) -> Optional[KnowledgeRecord]:
        return self._repo.get_optional(knowledge_id)

    def find_by_tags(self, tags: list[str], match_all: bool = False) -> list[KnowledgeRecord]:
        ids = self._index.by_tags(tags, match_all=match_all)
        records = []
        for rid in ids:
            rec = self._repo.get_optional(rid)
            if rec and not rec.is_deleted:
                records.append(rec)
        return records

    def find_by_type(self, kt: KnowledgeType) -> list[KnowledgeRecord]:
        ids = self._index.by_type(kt)
        return [r for rid in ids if (r := self._repo.get_optional(rid)) and not r.is_deleted]

    def find_by_domain(self, domain: KnowledgeDomain) -> list[KnowledgeRecord]:
        ids = self._index.by_domain(domain)
        return [r for rid in ids if (r := self._repo.get_optional(rid)) and not r.is_deleted]

    # ── Scoring helpers ───────────────────────────────────────────────────────

    def _compute_keyword_score(
        self,
        rec: KnowledgeRecord,
        tokens: list[str],
        and_ids: set[str],
        tag_ids: set[str],
    ) -> float:
        score = 0.0
        # Title match is worth more
        title_tokens = _tokenize(rec.title)
        for t in tokens:
            if t in title_tokens:
                score += 0.6
            else:
                score += 0.2
        # AND match bonus
        if rec.id in and_ids:
            score += 0.5
        # Tag boost
        if rec.id in tag_ids:
            score += 0.3
        # Confidence weight
        score *= rec.metadata.confidence
        return round(min(score, 10.0), 4)

    def _extract_highlights(self, rec: KnowledgeRecord, tokens: list[str]) -> list[str]:
        highlights = []
        title_lower = rec.title.lower()
        for t in tokens:
            if t in title_lower:
                highlights.append(rec.title)
                break
        return highlights

    def _match_query_filter(self, rec: KnowledgeRecord, query: SearchQuery) -> bool:
        filt = query.filter
        if filt.knowledge_types and rec.knowledge_type not in filt.knowledge_types:
            return False
        if filt.statuses and rec.status not in filt.statuses:
            return False
        if filt.domains and rec.metadata.domain not in filt.domains:
            return False
        if filt.tags and not any(rec.metadata.has_tag(t) for t in filt.tags):
            return False
        if filt.min_confidence is not None and rec.metadata.confidence < filt.min_confidence:
            return False
        return True


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_search_engine() -> KnowledgeSearchEngine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = KnowledgeSearchEngine()
        return _engine


def reset_search_engine() -> None:
    global _engine
    with _lock:
        _engine = None
