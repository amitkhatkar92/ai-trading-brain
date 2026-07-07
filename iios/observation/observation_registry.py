"""
iios/observation/observation_registry.py
=========================================
ObservationRegistry — tracks and manages all registered observation
components (collectors, enrichers, validators, classifiers).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

__all__ = [
    "ObservationRegistry",
    "get_observation_registry",
    "reset_observation_registry",
]

_LOG  = logging.getLogger("iios.observation.registry")
_lock = threading.Lock()
_reg: Optional["ObservationRegistry"] = None


class ObservationRegistry:
    """Thread-safe lazy auto-registering component registry."""

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._components: dict[str, Any] = {}
        self._registered  = False

    def _auto_register(self) -> None:
        if self._registered:
            return
        from .repositories.observation_storage    import get_observation_storage
        from .repositories.observation_cache      import get_observation_cache
        from .repositories.observation_repository import get_observation_repository
        from .validators.observation_validator    import get_observation_validator
        from .classifiers.observation_classifier  import get_observation_classifier
        from .enrichment.observation_enricher     import get_observation_enricher
        from .pipeline.observation_pipeline       import get_observation_pipeline
        from .quality.observation_quality         import get_quality_assessor
        from .storage.observation_store           import get_observation_store
        from .observation_factory                 import get_observation_factory
        from .observation_context                 import get_observation_context

        self._components = {
            "storage":           get_observation_storage(),
            "cache":             get_observation_cache(),
            "repository":        get_observation_repository(),
            "validator":         get_observation_validator(),
            "classifier":        get_observation_classifier(),
            "enricher":          get_observation_enricher(),
            "pipeline":          get_observation_pipeline(),
            "quality_assessor":  get_quality_assessor(),
            "store":             get_observation_store(),
            "factory":           get_observation_factory(),
            "context":           get_observation_context(),
        }
        self._registered = True

    def register(self, name: str, component: Any) -> None:
        with self._lock:
            self._auto_register()
            self._components[name] = component
            _LOG.debug("Registered component: %s", name)

    def get(self, name: str) -> Any:
        with self._lock:
            self._auto_register()
            if name not in self._components:
                raise KeyError(f"ObservationRegistry: component '{name}' not found.")
            return self._components[name]

    def has(self, name: str) -> bool:
        with self._lock:
            self._auto_register()
            return name in self._components

    def names(self) -> list[str]:
        with self._lock:
            self._auto_register()
            return list(self._components)

    def status(self) -> dict[str, str]:
        with self._lock:
            self._auto_register()
            return {name: type(c).__name__ for name, c in self._components.items()}


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_registry() -> ObservationRegistry:
    global _reg
    if _reg is None:
        with _lock:
            if _reg is None:
                _reg = ObservationRegistry()
    return _reg


def reset_observation_registry() -> None:
    global _reg
    with _lock:
        _reg = None
