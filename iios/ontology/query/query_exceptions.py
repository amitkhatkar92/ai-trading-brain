"""
iios/ontology/query/query_exceptions.py
========================================
Structured exception hierarchy for the IIOS Ontology Query &
Semantic Resolution Engine.

Error-code prefix: QRY-
"""

from __future__ import annotations

__all__ = [
    # Base
    "QueryError",
    # Query execution
    "QueryNotFoundError",
    "QueryTimeoutError",
    "QuerySyntaxError",
    "QueryLimitExceededError",
    # Resolution
    "ResolutionError",
    "AliasResolutionError",
    "InheritanceResolutionError",
    "CircularResolutionError",
    "ReferenceResolutionError",
    # Navigation
    "NavigationError",
    "TraversalDepthError",
    "NavigationDeadEndError",
    # Semantic
    "SemanticError",
    "SemanticDistanceError",
    # Cache
    "QueryCacheError",
    # Registry
    "NamedQueryError",
    "DuplicateNamedQueryError",
    "UnknownNamedQueryError",
    # Engine
    "QueryEngineError",
    "QueryEngineNotInitializedError",
]


# ── Base ──────────────────────────────────────────────────────────────────────

class QueryError(RuntimeError):
    """QRY-000: Base exception for all query engine errors."""
    code = "QRY-000"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Query execution ───────────────────────────────────────────────────────────

class QueryNotFoundError(QueryError):
    """QRY-010: Query produced no results for the given reference."""
    code = "QRY-010"

    def __init__(self, ref: str) -> None:
        super().__init__(f"No results found for: {ref!r}")
        self.ref = ref


class QueryTimeoutError(QueryError):
    """QRY-011: Query exceeded the configured timeout."""
    code = "QRY-011"

    def __init__(self, query_id: str, elapsed_ms: float) -> None:
        super().__init__(
            f"Query {query_id!r} timed out after {elapsed_ms:.1f} ms"
        )
        self.query_id  = query_id
        self.elapsed_ms = elapsed_ms


class QuerySyntaxError(QueryError):
    """QRY-012: Query specification contains a syntax or structural error."""
    code = "QRY-012"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Query syntax error: {detail}")


class QueryLimitExceededError(QueryError):
    """QRY-013: Result set exceeds the maximum allowed size."""
    code = "QRY-013"

    def __init__(self, limit: int, actual: int) -> None:
        super().__init__(
            f"Result count {actual} exceeds limit {limit}"
        )
        self.limit  = limit
        self.actual = actual


# ── Resolution ────────────────────────────────────────────────────────────────

class ResolutionError(QueryError):
    """QRY-020: Base for resolution failures."""
    code = "QRY-020"


class AliasResolutionError(ResolutionError):
    """QRY-021: Alias could not be resolved to a canonical URI."""
    code = "QRY-021"

    def __init__(self, alias: str) -> None:
        super().__init__(f"Cannot resolve alias: {alias!r}")
        self.alias = alias


class InheritanceResolutionError(ResolutionError):
    """QRY-022: Inheritance chain traversal failed."""
    code = "QRY-022"

    def __init__(self, type_uri: str, reason: str) -> None:
        super().__init__(
            f"Inheritance resolution failed for {type_uri!r}: {reason}"
        )
        self.type_uri = type_uri


class CircularResolutionError(ResolutionError):
    """QRY-023: Circular reference detected during resolution."""
    code = "QRY-023"

    def __init__(self, cycle: list[str]) -> None:
        chain = " → ".join(cycle)
        super().__init__(f"Circular resolution detected: {chain}")
        self.cycle = cycle


class ReferenceResolutionError(ResolutionError):
    """QRY-024: A cross-reference URI could not be resolved."""
    code = "QRY-024"

    def __init__(self, ref_uri: str) -> None:
        super().__init__(f"Cross-reference not found: {ref_uri!r}")
        self.ref_uri = ref_uri


# ── Navigation ────────────────────────────────────────────────────────────────

class NavigationError(QueryError):
    """QRY-030: Base for navigation / traversal failures."""
    code = "QRY-030"


class TraversalDepthError(NavigationError):
    """QRY-031: Traversal exceeded the maximum allowed depth."""
    code = "QRY-031"

    def __init__(self, depth: int, max_depth: int) -> None:
        super().__init__(
            f"Traversal depth {depth} exceeds maximum {max_depth}"
        )
        self.depth     = depth
        self.max_depth = max_depth


class NavigationDeadEndError(NavigationError):
    """QRY-032: Navigation reached a node with no further paths."""
    code = "QRY-032"

    def __init__(self, uri: str) -> None:
        super().__init__(f"Navigation dead-end at: {uri!r}")
        self.uri = uri


# ── Semantic ──────────────────────────────────────────────────────────────────

class SemanticError(QueryError):
    """QRY-040: Base for semantic reasoning failures."""
    code = "QRY-040"


class SemanticDistanceError(SemanticError):
    """QRY-041: Cannot compute semantic distance between the given URIs."""
    code = "QRY-041"

    def __init__(self, uri_a: str, uri_b: str, reason: str) -> None:
        super().__init__(
            f"Cannot compute distance between {uri_a!r} and {uri_b!r}: {reason}"
        )


# ── Cache ─────────────────────────────────────────────────────────────────────

class QueryCacheError(QueryError):
    """QRY-050: Query cache operation failed."""
    code = "QRY-050"


# ── Named query registry ──────────────────────────────────────────────────────

class NamedQueryError(QueryError):
    """QRY-060: Base for named query registry errors."""
    code = "QRY-060"


class DuplicateNamedQueryError(NamedQueryError):
    """QRY-061: A named query with the same ID already exists."""
    code = "QRY-061"

    def __init__(self, query_id: str) -> None:
        super().__init__(f"Named query already registered: {query_id!r}")
        self.query_id = query_id


class UnknownNamedQueryError(NamedQueryError):
    """QRY-062: No named query found for the given ID."""
    code = "QRY-062"

    def __init__(self, query_id: str) -> None:
        super().__init__(f"Unknown named query: {query_id!r}")
        self.query_id = query_id


# ── Engine ────────────────────────────────────────────────────────────────────

class QueryEngineError(QueryError):
    """QRY-070: Base for engine-level errors."""
    code = "QRY-070"


class QueryEngineNotInitializedError(QueryEngineError):
    """QRY-071: Query engine used before initialization."""
    code = "QRY-071"

    def __init__(self) -> None:
        super().__init__(
            "QueryEngine has not been initialized — call initialize() first"
        )
