"""
iios/knowledge/search/query_validator.py
==========================================
Validates UnifiedSearchQuery objects before execution.
"""
from __future__ import annotations

import threading
from typing import Optional

from .search_constants import (
    SearchType, MAX_SEARCH_PAGE_SIZE, DEFAULT_MAX_RESULTS, MAX_QUERY_TEXT_LENGTH,
)
from .search_exceptions import SearchQueryValidationError
from .models.unified_query import UnifiedSearchQuery

__all__ = ["QueryValidator", "get_query_validator", "reset_query_validator"]

_lock:      threading.Lock              = threading.Lock()
_validator: Optional["QueryValidator"] = None


class QueryValidator:
    """
    Validates a UnifiedSearchQuery and returns a list of violation strings.
    Raises SearchQueryValidationError if strict=True (default in search engine).

    Usage::

        validator = get_query_validator()
        violations = validator.validate(query)
        if violations:
            raise SearchQueryValidationError("Invalid query", violations=violations)
    """

    def validate(self, query: UnifiedSearchQuery) -> list[str]:
        """Returns a list of validation error messages. Empty list = valid."""
        violations: list[str] = []

        # ── Text length ───────────────────────────────────────────────────────
        if len(query.text) > MAX_QUERY_TEXT_LENGTH:
            violations.append(
                f"Query text exceeds {MAX_QUERY_TEXT_LENGTH} characters "
                f"(got {len(query.text)})"
            )

        # ── Page ─────────────────────────────────────────────────────────────
        if query.page < 1:
            violations.append(f"page must be ≥ 1 (got {query.page})")

        # ── Page size ─────────────────────────────────────────────────────────
        if query.page_size < 1:
            violations.append(f"page_size must be ≥ 1 (got {query.page_size})")
        if query.page_size > MAX_SEARCH_PAGE_SIZE:
            violations.append(
                f"page_size must be ≤ {MAX_SEARCH_PAGE_SIZE} (got {query.page_size})"
            )

        # ── Confidence range ──────────────────────────────────────────────────
        if not (0.0 <= query.min_confidence <= 1.0):
            violations.append(
                f"min_confidence must be in [0.0, 1.0] (got {query.min_confidence})"
            )

        # ── Fuzzy threshold ───────────────────────────────────────────────────
        if query.fuzzy and not (0.0 < query.fuzzy_threshold <= 1.0):
            violations.append(
                f"fuzzy_threshold must be in (0.0, 1.0] (got {query.fuzzy_threshold})"
            )

        # ── Search-type specific ──────────────────────────────────────────────
        if query.search_type == SearchType.ID_LOOKUP and not query.text.strip():
            violations.append("ID_LOOKUP search requires non-empty text (item ID)")

        if query.search_type == SearchType.GRAPH_TRAVERSAL:
            if not query.start_node_id:
                violations.append(
                    "GRAPH_TRAVERSAL search requires start_node_id"
                )
            if query.traversal_depth < 1:
                violations.append(
                    f"traversal_depth must be ≥ 1 (got {query.traversal_depth})"
                )
            if query.traversal_depth > 20:
                violations.append(
                    f"traversal_depth must be ≤ 20 (got {query.traversal_depth})"
                )

        if query.search_type == SearchType.TAG and not query.tags:
            violations.append("TAG search requires at least one tag")

        if query.search_type == SearchType.METADATA and not query.filters:
            violations.append("METADATA search requires at least one filter")

        return violations

    def validate_or_raise(self, query: UnifiedSearchQuery) -> None:
        violations = self.validate(query)
        if violations:
            raise SearchQueryValidationError(
                f"Query validation failed ({len(violations)} violations)",
                violations=violations,
                code="QV-001",
            )


def get_query_validator() -> QueryValidator:
    global _validator
    with _lock:
        if _validator is None:
            _validator = QueryValidator()
        return _validator


def reset_query_validator() -> None:
    global _validator
    with _lock:
        _validator = None
