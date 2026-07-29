"""
model_registry.py -- iios.ai.model_management.registry
========================================================
:class:`AIModelRegistry` — the central store for all registered AI models.

Responsibilities:
  - Register / deregister models
  - Enable / disable models
  - Version management (add, activate, rollback)
  - Lookup: by id, by name, by capability / category / tier
  - Publishes domain events on every mutation

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import threading
import uuid
from typing import Dict, FrozenSet, List, Optional, Tuple, TYPE_CHECKING

from ..capabilities.capability_type import ModelCapabilityType
from ..core.ai_model                 import AIModel
from ..core.model_category           import ModelCategory
from ..core.model_metadata           import ModelMetadata
from ..core.model_tier               import ModelTier
from ..core.model_version            import AIModelVersion
from ..events.event_bus              import ModelEventBus
from ..events.model_events           import (
    ModelDisabledEvent,
    ModelEnabledEvent,
    ModelRegisteredEvent,
    ModelRemovedEvent,
    VersionActivatedEvent,
)
from ..exceptions import (
    AIModelAlreadyExistsError,
    AIModelNotFoundError,
    AIModelVersionError,
)

if TYPE_CHECKING:
    pass

SYSTEM_ID = "iios:ai:model_management:registry"


class AIModelRegistry:
    """Thread-safe registry for AI models."""

    def __init__(self, event_bus: Optional[ModelEventBus] = None) -> None:
        self._models:      Dict[str, AIModel] = {}   # model_id -> AIModel
        self._name_index:  Dict[str, str]     = {}   # name -> model_id
        self._lock:        threading.RLock    = threading.RLock()
        self._event_bus:   Optional[ModelEventBus] = event_bus

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        name:         str,
        category:     ModelCategory,
        capabilities: FrozenSet[ModelCapabilityType],
        *,
        tier:                ModelTier          = ModelTier.STANDARD,
        provider_id:         str                = "",
        description:         str                = "",
        tags:                Tuple[str, ...]    = (),
        owner:               str                = "",
        context_window:      int                = 4_096,
        max_output_tokens:   int                = 1_024,
        parameters_billions: float              = 0.0,
    ) -> AIModel:
        """
        Register a new model and its initial (active) version.

        Raises
        ------
        AIModelAlreadyExistsError
            If a model with the same ``name`` is already registered.
        """
        with self._lock:
            if name in self._name_index:
                raise AIModelAlreadyExistsError(name)

            metadata = ModelMetadata.create(
                name, category,
                tier=tier, provider_id=provider_id, description=description,
                tags=tuple(tags), owner=owner,
            )
            model = AIModel(metadata)

            v1 = AIModelVersion.create(
                metadata.model_id, 1, frozenset(capabilities),
                context_window=context_window,
                max_output_tokens=max_output_tokens,
                parameters_billions=parameters_billions,
            )
            model.add_version(v1, activate=True)

            self._models[metadata.model_id]  = model
            self._name_index[name]            = metadata.model_id

        self._publish(ModelRegisteredEvent.create(SYSTEM_ID, metadata.model_id, name))
        return model

    def deregister(self, model_id: str) -> None:
        """Permanently remove a model from the registry."""
        with self._lock:
            if model_id not in self._models:
                raise AIModelNotFoundError(model_id)
            model = self._models.pop(model_id)
            self._name_index.pop(model.metadata.name, None)

        self._publish(ModelRemovedEvent.create(SYSTEM_ID, model_id, model.metadata.name))

    # ── Enable / Disable ──────────────────────────────────────────────────────

    def enable(self, model_id: str) -> None:
        model = self._get_or_raise(model_id)
        model.enable()
        self._publish(ModelEnabledEvent.create(SYSTEM_ID, model_id))

    def disable(self, model_id: str) -> None:
        model = self._get_or_raise(model_id)
        model.disable()
        self._publish(ModelDisabledEvent.create(SYSTEM_ID, model_id))

    # ── Versioning ────────────────────────────────────────────────────────────

    def add_version(
        self,
        model_id:     str,
        capabilities: FrozenSet[ModelCapabilityType],
        *,
        context_window:      int   = 4_096,
        max_output_tokens:   int   = 1_024,
        parameters_billions: float = 0.0,
        activate:            bool  = True,
    ) -> AIModelVersion:
        """Add a new version to an existing model."""
        model = self._get_or_raise(model_id)
        with self._lock:
            next_number = len(model.history()) + 1

        version = AIModelVersion.create(
            model_id, next_number, frozenset(capabilities),
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            parameters_billions=parameters_billions,
        )
        result = model.add_version(version, activate=activate)
        if activate:
            self._publish(VersionActivatedEvent.create(
                SYSTEM_ID, model_id, result.version_id, result.version_number
            ))
        return result

    def activate_version(self, model_id: str, version_id: str) -> AIModelVersion:
        model = self._get_or_raise(model_id)
        result = model.activate_version(version_id)   # raises AIModelVersionError
        self._publish(VersionActivatedEvent.create(
            SYSTEM_ID, model_id, version_id, result.version_number
        ))
        return result

    def rollback(self, model_id: str, version_id: str) -> AIModelVersion:
        """Re-activate a prior version (semantically identical to activate_version)."""
        return self.activate_version(model_id, version_id)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, model_id: str) -> AIModel:
        """Fetch by model_id; raises :class:`AIModelNotFoundError` if missing."""
        return self._get_or_raise(model_id)

    def find_by_name(self, name: str) -> Optional[AIModel]:
        with self._lock:
            model_id = self._name_index.get(name)
            return self._models.get(model_id) if model_id else None

    def search(
        self,
        *,
        category:     Optional[ModelCategory]          = None,
        capability:   Optional[ModelCapabilityType]    = None,
        tier:         Optional[ModelTier]               = None,
        enabled_only: bool                             = False,
    ) -> List[AIModel]:
        with self._lock:
            models = list(self._models.values())

        results = []
        for model in models:
            if enabled_only and not model.enabled:
                continue
            if category and model.metadata.category != category:
                continue
            if tier and model.metadata.tier != tier:
                continue
            if capability:
                version = model.active_version
                if version is None:
                    continue
                if capability not in version.descriptor.capabilities:
                    continue
            results.append(model)
        return results

    def list_all(self) -> List[AIModel]:
        with self._lock:
            return list(self._models.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._models)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, model_id: str) -> AIModel:
        with self._lock:
            if model_id not in self._models:
                raise AIModelNotFoundError(model_id)
            return self._models[model_id]

    def _publish(self, event) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(event)
