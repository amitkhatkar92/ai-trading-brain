"""
semantic_analysis_engine.py — iios.knowledge.intelligence
----------------------------------------------------------
Lightweight semantic feature extraction from text artifacts.

No ML dependency. Produces a structured semantic feature dict that
downstream engines (retrieval, hybrid search) can use.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)

# Finance domain stop-words to filter out
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "with", "of", "by", "is", "are", "was", "were", "be",
    "has", "have", "had", "do", "does", "did", "will", "would", "can",
    "could", "should", "may", "might", "must", "not", "no", "it",
    "its", "that", "this", "these", "those", "from", "as", "if", "so",
})


def _tokenize(text: str) -> List[str]:
    """Split on non-alphanumeric, lowercase, drop stop-words."""
    tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 2 and t not in _STOP_WORDS]


@runtime_checkable
class SemanticAnalysisAdapter(Protocol):
    """Protocol for ML-based semantic analysis backends."""
    def analyze(self, text: str) -> Dict[str, Any]: ...


class SemanticAnalysisEngine:
    """
    Extracts semantic features from text.

    Stub mode: keyword extraction, character + token counts.
    Adapter mode: delegates to an injected SemanticAnalysisAdapter.
    """

    def __init__(
        self,
        adapter:          Optional[SemanticAnalysisAdapter] = None,
        max_keywords:     int                               = 20,
    ) -> None:
        self._adapter    = adapter
        self._max_keywords = max_keywords

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text; return semantic feature dict. Never raises."""
        if not text or not isinstance(text, str):
            return {"keywords": [], "char_count": 0, "token_count": 0}
        try:
            if self._adapter:
                return self._adapter.analyze(text)
            return self._stub_analyze(text)
        except Exception as exc:
            _log.warning(f"Semantic analysis failed: {exc!r}")
            return {"keywords": [], "char_count": len(text), "token_count": 0}

    def _stub_analyze(self, text: str) -> Dict[str, Any]:
        tokens = _tokenize(text)
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        top_keywords = sorted(freq, key=lambda k: freq[k], reverse=True)[
            :self._max_keywords
        ]
        return {
            "keywords":    top_keywords,
            "keyword_freq": {k: freq[k] for k in top_keywords},
            "char_count":  len(text),
            "token_count": len(tokens),
            "unique_tokens": len(freq),
        }

    def artifact_text(self, artifact: Dict[str, Any]) -> str:
        """Extract a concatenated text representation of an artifact dict."""
        parts = []
        for v in artifact.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, (int, float)):
                parts.append(str(v))
        return " ".join(parts)

    def set_adapter(self, adapter: SemanticAnalysisAdapter) -> None:
        self._adapter = adapter
        _log.info("SemanticAnalysisAdapter registered")
