"""iios/investment/decision/core/decision_registry.py
DecisionRegistry — maps type keys to concrete BaseDecision subclasses.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Type

from iios.investment.decision.core.decision_constants import DecisionType


class DuplicateDecisionTypeError(Exception): ...
class UnknownDecisionTypeError(Exception): ...


class DecisionRegistry:
    """
    Thread-safe map from a string key (decision_type.value or custom)
    to a concrete BaseDecision subclass.

    Supports:
    - Dynamic registration at runtime
    - Versioned entries (key + version)
    - Capability tags
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock                          = threading.RLock()
        self._registry: Dict[str, Type]                          = {}
        self._versions: Dict[str, str]                           = {}
        self._caps:     Dict[str, tuple]                         = {}

    def register(
        self,
        key:          str,
        klass:        Type,
        version:      str  = "1.0.0",
        capabilities: tuple = (),
        overwrite:    bool  = False,
    ) -> None:
        with self._lock:
            if key in self._registry and not overwrite:
                raise DuplicateDecisionTypeError(
                    f"Decision type {key!r} is already registered. "
                    f"Use overwrite=True to replace."
                )
            self._registry[key] = klass
            self._versions[key]  = version
            self._caps[key]      = capabilities

    def unregister(self, key: str) -> None:
        with self._lock:
            self._registry.pop(key, None)
            self._versions.pop(key, None)
            self._caps.pop(key, None)

    def get(self, key: str) -> Type:
        with self._lock:
            klass = self._registry.get(key)
            if klass is None:
                raise UnknownDecisionTypeError(f"Decision type {key!r} is not registered.")
            return klass

    def get_optional(self, key: str) -> Optional[Type]:
        with self._lock:
            return self._registry.get(key)

    def version(self, key: str) -> Optional[str]:
        with self._lock:
            return self._versions.get(key)

    def capabilities(self, key: str) -> tuple:
        with self._lock:
            return self._caps.get(key, ())

    def all_keys(self) -> List[str]:
        with self._lock:
            return list(self._registry.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._registry)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._registry
