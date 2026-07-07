"""iios/observation/enrichment/__init__.py"""
from __future__ import annotations

# ── Baseline (keep — imported by observation_engine.py) ───────────────────────
from .observation_enricher import (
    EnrichmentResult,
    ObservationEnricher,
    get_observation_enricher,
    reset_observation_enricher,
)

# ── Classification & Enrichment Engine ───────────────────────────────────────
from .enrichment_constants import (
    EnricherCategory, EnricherStage, SemanticLabel, LinkType, ContextType,
    ENRICHMENT_ATTR_KEY, ENRICHMENT_NAMESPACE,
    MAX_TAGS, MAX_KEYWORDS, MAX_LINKS,
)
from .enrichment_exceptions import (
    EnrichmentError, EnricherNotFoundError, EnricherAlreadyRegisteredError,
    EnrichmentTimeoutError, EnrichmentPipelineError,
    OntologyEnrichmentError, LinkingError, SemanticEnrichmentError,
    EnrichmentNotInitializedError,
)
from .enrichment_context import (
    EnrichmentContext, get_enrichment_context, reset_enrichment_context,
    enrichment_operation, current_obs_id, current_stage,
)
from .enrichment_registry import (
    EnrichmentRecord, BaseEnricher, EnricherRegistry,
    get_enricher_registry, reset_enricher_registry,
)
from .enrichment_engine import (
    EnrichmentOutput, EnrichmentEngine,
    DEFAULT_ENRICHERS,
    get_enrichment_engine, reset_enrichment_engine,
)
from .enrichment_manager import (
    ProcessingResult, EnrichmentManager,
    get_enrichment_manager, reset_enrichment_manager,
)

__all__ = [
    # Baseline
    "EnrichmentResult", "ObservationEnricher",
    "get_observation_enricher", "reset_observation_enricher",
    # Constants
    "EnricherCategory", "EnricherStage", "SemanticLabel", "LinkType", "ContextType",
    "ENRICHMENT_ATTR_KEY", "ENRICHMENT_NAMESPACE",
    "MAX_TAGS", "MAX_KEYWORDS", "MAX_LINKS",
    # Exceptions
    "EnrichmentError", "EnricherNotFoundError", "EnricherAlreadyRegisteredError",
    "EnrichmentTimeoutError", "EnrichmentPipelineError",
    "OntologyEnrichmentError", "LinkingError", "SemanticEnrichmentError",
    "EnrichmentNotInitializedError",
    # Context
    "EnrichmentContext", "get_enrichment_context", "reset_enrichment_context",
    "enrichment_operation", "current_obs_id", "current_stage",
    # Registry
    "EnrichmentRecord", "BaseEnricher", "EnricherRegistry",
    "get_enricher_registry", "reset_enricher_registry",
    # Engine
    "EnrichmentOutput", "EnrichmentEngine", "DEFAULT_ENRICHERS",
    "get_enrichment_engine", "reset_enrichment_engine",
    # Manager
    "ProcessingResult", "EnrichmentManager",
    "get_enrichment_manager", "reset_enrichment_manager",
]
