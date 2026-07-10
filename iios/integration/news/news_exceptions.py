"""iios/integration/news/news_exceptions.py

Exception hierarchy for the News & Alternative Data Framework.
Error code prefix: ND-
"""
from __future__ import annotations


class NewsDataError(Exception):
    """Root exception for all News Framework errors. [ND-000]"""

    def __init__(self, message: str, code: str = "ND-000") -> None:
        super().__init__(message)
        self.code    = code
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self.message})"


# ── Provider errors ───────────────────────────────────────────────────────────

class NewsProviderConnectionError(NewsDataError):
    """Cannot connect to provider. [ND-011]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-011")


class NewsProviderAuthenticationError(NewsDataError):
    """Provider authentication failed. [ND-012]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-012")


class NewsProviderNotConnectedError(NewsDataError):
    """Operation attempted before provider connect(). [ND-013]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-013")


class NewsProviderNotFoundError(NewsDataError):
    """Provider not registered. [ND-014]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-014")


class NewsProviderAlreadyRegisteredError(NewsDataError):
    """Provider already registered under the same ID. [ND-015]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-015")


class NoNewsProviderAvailableError(NewsDataError):
    """No active provider can satisfy the request. [ND-016]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-016")


# ── Fetch errors ──────────────────────────────────────────────────────────────

class NewsFetchError(NewsDataError):
    """Generic fetch failure from provider. [ND-020]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-020")


class NewsFetchTimeoutError(NewsDataError):
    """Provider fetch timed out. [ND-021]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-021")


class NewsArticleNotFoundError(NewsDataError):
    """Article not found. [ND-022]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-022")


# ── Streaming errors ──────────────────────────────────────────────────────────

class NewsStreamError(NewsDataError):
    """Streaming failure. [ND-030]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-030")


class NewsStreamBufferOverflowError(NewsDataError):
    """News stream buffer full. [ND-031]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-031")


# ── Validation errors ─────────────────────────────────────────────────────────

class NewsValidationError(NewsDataError):
    """Article or event failed validation. [ND-040]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-040")


class NewsDuplicateArticleError(NewsDataError):
    """Duplicate article detected. [ND-041]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-041")


# ── Classification errors ─────────────────────────────────────────────────────

class ClassificationError(NewsDataError):
    """Classification pipeline failure. [ND-050]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-050")


# ── Alternative data errors ───────────────────────────────────────────────────

class AlternativeDataError(NewsDataError):
    """Alternative data framework error. [ND-060]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-060")


class AlternativeDatasetNotFoundError(NewsDataError):
    """Dataset not found. [ND-061]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-061")


# ── Engine errors ─────────────────────────────────────────────────────────────

class NewsEngineNotRunningError(NewsDataError):
    """Engine called before start(). [ND-070]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-070")


class NewsEngineAlreadyRunningError(NewsDataError):
    """Engine.start() called while already running. [ND-071]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-071")


class NewsRegistryError(NewsDataError):
    """Registry inconsistency. [ND-072]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "ND-072")
