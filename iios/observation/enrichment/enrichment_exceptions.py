"""
iios/observation/enrichment/enrichment_exceptions.py
====================================================
Exception hierarchy for the Enrichment Engine.
"""
from __future__ import annotations

from ..observation_exceptions import ObservationError

__all__ = [
    "EnrichmentError",
    "EnricherNotFoundError",
    "EnricherAlreadyRegisteredError",
    "EnrichmentTimeoutError",
    "EnrichmentPipelineError",
    "OntologyEnrichmentError",
    "LinkingError",
    "SemanticEnrichmentError",
    "EnrichmentNotInitializedError",
]


class EnrichmentError(ObservationError):
    """Base for all enrichment engine errors."""
    def __init__(self, message: str, code: str = "ENR-000") -> None:
        super().__init__(message, code=code)


class EnricherNotFoundError(EnrichmentError):
    """Named enricher is not in the registry."""
    def __init__(self, name: str, code: str = "ENR-010") -> None:
        super().__init__(f"Enricher {name!r} not found", code=code)
        self.name = name


class EnricherAlreadyRegisteredError(EnrichmentError):
    """An enricher with this name is already registered."""
    def __init__(self, name: str, code: str = "ENR-020") -> None:
        super().__init__(f"Enricher {name!r} is already registered", code=code)
        self.name = name


class EnrichmentTimeoutError(EnrichmentError):
    """Enrichment did not complete within the time budget."""
    def __init__(self, message: str, timeout_s: float = 0.0, code: str = "ENR-030") -> None:
        super().__init__(message, code=code)
        self.timeout_s = timeout_s


class EnrichmentPipelineError(EnrichmentError):
    """Pipeline encountered an unrecoverable error."""
    def __init__(self, message: str, enricher: str = "", code: str = "ENR-040") -> None:
        super().__init__(message, code=code)
        self.enricher = enricher


class OntologyEnrichmentError(EnrichmentError):
    """Failed to enrich with ontology terms."""
    def __init__(self, message: str, code: str = "ENR-050") -> None:
        super().__init__(message, code=code)


class LinkingError(EnrichmentError):
    """Cross-reference linking failed."""
    def __init__(self, message: str, code: str = "ENR-060") -> None:
        super().__init__(message, code=code)


class SemanticEnrichmentError(EnrichmentError):
    """Semantic labelling / keyword extraction failed."""
    def __init__(self, message: str, code: str = "ENR-070") -> None:
        super().__init__(message, code=code)


class EnrichmentNotInitializedError(EnrichmentError):
    """Enrichment engine used before initialisation."""
    def __init__(self, code: str = "ENR-080") -> None:
        super().__init__("Enrichment engine not initialised", code=code)
