"""iios/observation/classifiers/__init__.py"""
from __future__ import annotations

# ── Baseline (keep — imported by observation_engine.py) ───────────────────────
from .observation_classifier import (
    ClassificationResult,
    ObservationClassifier,
    get_observation_classifier,
    reset_observation_classifier,
)

# ── Classification & Enrichment Engine ───────────────────────────────────────
from .classification_constants import (
    AssetClass, ClassificationStatus, EntityType, EventType, Geography,
    Importance, OntologyCategory, RiskLevel, Sector, TimeHorizon,
    CLASSIFICATION_ATTR_KEY, CLASSIFICATION_NAMESPACE,
    MIN_CLASSIFICATION_CONFIDENCE, SYSTEM_CLASSIFIER,
)
from .classification_exceptions import (
    ClassificationError, ClassifierNotFoundError,
    ClassifierAlreadyRegisteredError, ClassificationTimeoutError,
    ClassificationPipelineError, OntologyLinkError,
    ClassificationNotInitializedError,
)
from .classification_context import (
    ClassificationContext, get_classification_context,
    reset_classification_context, classification_operation,
    current_obs_id, current_classifier,
)
from .classification_registry import (
    ClassificationLabel, BaseClassifier, ClassifierRegistry,
    get_classifier_registry, reset_classifier_registry,
)
from .classification_engine import (
    ClassificationOutput, ClassificationEngine,
    DEFAULT_CLASSIFIERS,
    get_classification_engine, reset_classification_engine,
)
from .classification_manager import (
    ClassificationManagerResult, ClassificationManager,
    get_classification_manager, reset_classification_manager,
)

__all__ = [
    # Baseline
    "ClassificationResult", "ObservationClassifier",
    "get_observation_classifier", "reset_observation_classifier",
    # Constants
    "AssetClass", "ClassificationStatus", "EntityType", "EventType",
    "Geography", "Importance", "OntologyCategory", "RiskLevel",
    "Sector", "TimeHorizon",
    "CLASSIFICATION_ATTR_KEY", "CLASSIFICATION_NAMESPACE",
    "MIN_CLASSIFICATION_CONFIDENCE", "SYSTEM_CLASSIFIER",
    # Exceptions
    "ClassificationError", "ClassifierNotFoundError",
    "ClassifierAlreadyRegisteredError", "ClassificationTimeoutError",
    "ClassificationPipelineError", "OntologyLinkError",
    "ClassificationNotInitializedError",
    # Context
    "ClassificationContext", "get_classification_context",
    "reset_classification_context", "classification_operation",
    "current_obs_id", "current_classifier",
    # Registry
    "ClassificationLabel", "BaseClassifier", "ClassifierRegistry",
    "get_classifier_registry", "reset_classifier_registry",
    # Engine
    "ClassificationOutput", "ClassificationEngine", "DEFAULT_CLASSIFIERS",
    "get_classification_engine", "reset_classification_engine",
    # Manager
    "ClassificationManagerResult", "ClassificationManager",
    "get_classification_manager", "reset_classification_manager",
]
