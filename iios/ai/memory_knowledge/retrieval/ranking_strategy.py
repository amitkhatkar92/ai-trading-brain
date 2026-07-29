"""
ranking_strategy.py -- iios.ai.memory_knowledge.retrieval
==========================================================
:class:`RankingStrategy` — ABC for result ranking algorithms.

Bundled implementations
-----------------------
* :class:`KeywordRankingStrategy`  — token-overlap score
* :class:`SemanticRankingStrategy` — stub for future vector similarity
* :class:`HybridRankingStrategy`   — weighted combination of keyword + semantic
* :class:`RecencyRankingStrategy`  — ranks by recency (newest first)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple


class RankingStrategy(ABC):
    """Abstract base for ranking strategies."""
    STRATEGY_NAME: str = "base"

    @abstractmethod
    def score(self, query: str, content: Any, title: str = "") -> float:
        """Return a relevance score in [0.0, 1.0]."""

    def rank(
        self,
        query:     str,
        candidates: List[Tuple[str, str, Any, str, Any]],  # (id, source, content, title, tags)
        min_score:  float = 0.0,
        top_k:     int   = 10,
    ) -> List[Tuple[str, str, Any, str, Any, float]]:  # (id, source, content, title, tags, score)
        """Score, filter, and sort candidates; return top_k."""
        scored = []
        for (hit_id, source, content, title, tags) in candidates:
            s = self.score(query, content, title)
            if s >= min_score:
                scored.append((hit_id, source, content, title, tags, s))
        scored.sort(key=lambda x: x[5], reverse=True)
        return scored[:top_k]


# ─────────────────────────────────────────────────────────────────────────────
# Keyword ranking  (simple token overlap)
# ─────────────────────────────────────────────────────────────────────────────

class KeywordRankingStrategy(RankingStrategy):
    """Rank by keyword overlap between query tokens and title/content text."""
    STRATEGY_NAME = "keyword"

    def score(self, query: str, content: Any, title: str = "") -> float:
        if not query:
            return 0.0
        q_tokens  = set(query.lower().split())
        haystack  = f"{title} {content}".lower() if not isinstance(content, dict) else title.lower()
        h_tokens  = set(haystack.split())
        if not h_tokens:
            return 0.0
        return len(q_tokens & h_tokens) / len(q_tokens)


# ─────────────────────────────────────────────────────────────────────────────
# Semantic ranking  (provider-independent stub)
# ─────────────────────────────────────────────────────────────────────────────

class SemanticRankingStrategy(RankingStrategy):
    """
    Stub for semantic / embedding-based ranking.

    Returns 0.5 for every candidate until a real :class:`EmbeddingService`
    is injected.  Concrete implementations replace ``score()`` with a
    cosine-similarity computation against embedded vectors.
    """
    STRATEGY_NAME = "semantic"

    def score(self, query: str, content: Any, title: str = "") -> float:
        # Stub: no embedding provider wired — return neutral score
        return 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Hybrid ranking  (keyword + semantic, weighted)
# ─────────────────────────────────────────────────────────────────────────────

class HybridRankingStrategy(RankingStrategy):
    """Weighted combination of keyword and semantic scores."""
    STRATEGY_NAME = "hybrid"

    def __init__(
        self,
        keyword_weight:  float = 0.6,
        semantic_weight: float = 0.4,
    ) -> None:
        if abs((keyword_weight + semantic_weight) - 1.0) > 1e-6:
            raise ValueError("keyword_weight + semantic_weight must equal 1.0")
        self._keyword  = KeywordRankingStrategy()
        self._semantic = SemanticRankingStrategy()
        self._kw = keyword_weight
        self._sw = semantic_weight

    def score(self, query: str, content: Any, title: str = "") -> float:
        kw_score  = self._keyword.score(query, content, title)
        sem_score = self._semantic.score(query, content, title)
        return self._kw * kw_score + self._sw * sem_score


# ─────────────────────────────────────────────────────────────────────────────
# Recency ranking
# ─────────────────────────────────────────────────────────────────────────────

class RecencyRankingStrategy(RankingStrategy):
    """
    Ranks results by recency; ``content`` is expected to carry a
    ``created_at`` float attribute (or dict key).  Falls back to 0.5.
    """
    STRATEGY_NAME = "recency"

    def score(self, query: str, content: Any, title: str = "") -> float:
        import time
        now = time.time()
        created_at: Optional[float] = None
        if hasattr(content, "created_at"):
            created_at = float(content.created_at)
        elif isinstance(content, dict) and "created_at" in content:
            created_at = float(content["created_at"])
        if created_at is None:
            return 0.5
        # decay: score = 1 / (1 + age_in_days)
        age_days = max(0.0, (now - created_at) / 86400.0)
        return 1.0 / (1.0 + age_days)
