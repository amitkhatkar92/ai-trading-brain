"""
iios/knowledge/search/search_exceptions.py
==========================================
Exception hierarchy for the Knowledge Indexing & Search Engine.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "SearchError",
    "SearchValidationError",
    "SearchIndexError",
    "SearchIndexNotFoundError",
    "SearchIndexAlreadyExistsError",
    "SearchQueryError",
    "SearchQueryParseError",
    "SearchQueryValidationError",
    "SearchExecutionError",
    "SearchRankingError",
    "SearchCacheError",
    "SearchEngineError",
    "SearchEngineNotInitializedError",
    "SearchRegistryError",
    "SearchContextError",
    "SearchIntegrationError",
]


class SearchError(Exception):
    """Base exception for the Knowledge Indexing & Search Engine."""

    def __init__(
        self,
        message: str,
        code:    str             = "SE-000",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code    = code
        self.context = context or {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self.message})"


class SearchValidationError(SearchError):
    """A search request failed business-rule validation."""


class SearchIndexError(SearchError):
    """Base class for index management errors."""


class SearchIndexNotFoundError(SearchIndexError):
    """A requested index does not exist."""


class SearchIndexAlreadyExistsError(SearchIndexError):
    """Attempted to create an index that already exists."""


class SearchQueryError(SearchError):
    """Base class for query-level errors."""


class SearchQueryParseError(SearchQueryError):
    """Failed to parse a query string."""


class SearchQueryValidationError(SearchQueryError):
    """A parsed query failed validation constraints."""

    def __init__(
        self,
        message: str,
        violations: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.violations = violations or []


class SearchExecutionError(SearchError):
    """An error occurred during query execution."""


class SearchRankingError(SearchError):
    """An error occurred during result ranking."""


class SearchCacheError(SearchError):
    """An error occurred in the search result cache."""


class SearchEngineError(SearchError):
    """General search engine failure."""


class SearchEngineNotInitializedError(SearchEngineError):
    """The search engine was used before being initialized."""


class SearchRegistryError(SearchError):
    """Component registry error."""


class SearchContextError(SearchError):
    """Search context error."""


class SearchIntegrationError(SearchError):
    """Integration with Knowledge Engine or Graph Engine failed."""
