"""
iios/observation/__init__.py
=============================
Public surface of the Observation Layer.

Preferred import paths::

    from iios.observation import get_observation_engine, ObservationType
    from iios.observation.observation_constants import ObservationStatus
    from iios.observation.models import Observation
"""

from __future__ import annotations

# ── Constants ──────────────────────────────────────────────────────────────────
from .observation_constants import (
    ObservationType,
    ObservationStatus,
    ObservationPriority,
    ObservationSource,
    ObservationDomain,
    ObservationQuality,
    ValidationOutcome,
    ClassificationMethod,
    EnrichmentType,
    LifecycleEvent,
    DuplicatePolicy,
    ConflictResolution,
    CollectorType,
    PipelineStage,
    SortOrder,
    # scalar constants
    DEFAULT_CONFIDENCE,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
    DEFAULT_TTL_SECONDS,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MAX_BATCH_SIZE,
    MAX_TAGS,
    OBSERVATION_NAMESPACE,
    SYSTEM_OBSERVER,
    ANONYMOUS_SOURCE,
    OBSERVATION_SCHEMA_VERSION,
)

# ── Exceptions ─────────────────────────────────────────────────────────────────
from .observation_exceptions import (
    ObservationError,
    ObservationNotFoundError,
    ObservationAlreadyExistsError,
    ObservationValidationError,
    ObservationLifecycleError,
    ObservationRejectedError,
    ObservationDuplicateError,
    ObservationPipelineError,
    ObservationStorageError,
    ObservationEngineError,
    ObservationEngineNotInitializedError,
    ObservationConfigError,
    ObservationCollectorError,
    ObservationClassifierError,
    ObservationEnricherError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .models import (
    ObservationId,
    ObservationSourceInfo,
    ObservationMetadata,
    ObservationContext as ObservationContextModel,   # dataclass context snapshot
    Observation,
    ObservationRecord,
    ObservationStatistics,
)

# ── Repositories ──────────────────────────────────────────────────────────────
from .repositories.observation_query      import ObservationQuery
from .repositories.observation_storage    import ObservationStorage, get_observation_storage
from .repositories.observation_cache      import ObservationCache, get_observation_cache
from .repositories.observation_repository import ObservationRepository, get_observation_repository

# ── Subsystems ────────────────────────────────────────────────────────────────
from .validators.observation_validator    import ObservationValidator, get_observation_validator
from .classifiers.observation_classifier  import ObservationClassifier, get_observation_classifier
from .enrichment.observation_enricher     import ObservationEnricher, get_observation_enricher
from .pipeline.observation_pipeline       import ObservationPipeline, get_observation_pipeline
from .quality.observation_quality         import ObservationQualityAssessor, get_quality_assessor
from .storage.observation_store           import ObservationStore, get_observation_store

# ── High-level API ─────────────────────────────────────────────────────────────
from .observation_factory    import ObservationFactory, get_observation_factory
from .observation_manager    import ObservationManager, get_observation_manager
from .observation_context    import (
    observation_operation,
    current_obs_actor,
    current_obs_operation_id,
    get_observation_context,
)
from .observation_registry   import ObservationRegistry, get_observation_registry
from .observation_engine     import ObservationEngine, get_observation_engine, reset_observation_engine
