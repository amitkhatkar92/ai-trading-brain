"""
risk_model_registry.py — iios.risk.assessment
===============================================
Thread-safe versioned model registry for the Risk Assessment Framework.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .constants import DEFAULT_MAX_MODELS, ModelType, VERSION
from .exceptions import (
    RiskAssessmentRegistryError,
    RiskModelNotFoundError,
)


# ---------------------------------------------------------------------------
# Model descriptor
# ---------------------------------------------------------------------------

@dataclass
class RiskModel:
    """
    Descriptor for a registered quantitative risk model.

    Fields
    ------
    model_id :      Unique model identifier.
    name :          Human-readable model name.
    model_type :    Classification of the model.
    version :       Model version string.
    description :   Model description.
    fn :            Callable that executes the model.
    enabled :       Whether the model is active.
    registered_at : Wall-clock registration time.
    metadata :      Supplementary metadata.
    """
    model_id:      str
    name:          str
    model_type:    ModelType
    version:       str
    description:   str
    fn:            Callable[..., Any]
    enabled:       bool = True
    registered_at: float = field(default_factory=time.time)
    metadata:      Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id":      self.model_id,
            "name":          self.name,
            "model_type":    self.model_type.value,
            "version":       self.version,
            "description":   self.description,
            "enabled":       self.enabled,
            "registered_at": self.registered_at,
        }


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

class RiskModelRegistry:
    """
    Thread-safe registry of versioned quantitative risk models.

    Parameters
    ----------
    max_models :
        Maximum number of models that can be registered.
        Defaults to :data:`~.constants.DEFAULT_MAX_MODELS`.
    """

    def __init__(self, max_models: int = DEFAULT_MAX_MODELS) -> None:
        self._max    = max_models
        self._lock   = threading.RLock()
        self._models: Dict[str, RiskModel] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, model: RiskModel) -> None:
        """
        Register or update a model.

        Raises
        ------
        RiskAssessmentRegistryError
            When ``model`` is ``None``.
        RiskAssessmentCapacityError
            When capacity is exhausted for a new (non-update) registration.
        """
        if model is None:
            raise RiskAssessmentRegistryError("Cannot register None model")
        with self._lock:
            is_update = model.model_id in self._models
            if not is_update and len(self._models) >= self._max:
                from .exceptions import RiskAssessmentCapacityError
                raise RiskAssessmentCapacityError(self._max)
            self._models[model.model_id] = model

    def unregister(self, model_id: str) -> None:
        """Remove a model. Raises :class:`~.exceptions.RiskModelNotFoundError` if absent."""
        with self._lock:
            if model_id not in self._models:
                raise RiskModelNotFoundError(model_id)
            del self._models[model_id]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> RiskModel:
        """Return model or raise :class:`~.exceptions.RiskModelNotFoundError`."""
        with self._lock:
            model = self._models.get(model_id)
        if model is None:
            raise RiskModelNotFoundError(model_id)
        return model

    def get_optional(self, model_id: str) -> Optional[RiskModel]:
        with self._lock:
            return self._models.get(model_id)

    def list_by_type(self, model_type: ModelType) -> List[RiskModel]:
        with self._lock:
            return [m for m in self._models.values() if m.model_type == model_type]

    def list_enabled(self) -> List[RiskModel]:
        with self._lock:
            return [m for m in self._models.values() if m.enabled]

    def list_all(self) -> List[RiskModel]:
        with self._lock:
            return list(self._models.values())

    def count(self) -> int:
        with self._lock:
            return len(self._models)

    def enable(self, model_id: str) -> None:
        """Enable a registered model."""
        with self._lock:
            m = self._models.get(model_id)
            if m is None:
                raise RiskModelNotFoundError(model_id)
            m.enabled = True

    def disable(self, model_id: str) -> None:
        """Disable a registered model (without removing it)."""
        with self._lock:
            m = self._models.get(model_id)
            if m is None:
                raise RiskModelNotFoundError(model_id)
            m.enabled = False
