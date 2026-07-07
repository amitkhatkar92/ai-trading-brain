"""
iios/knowledge/governance/quality_registry.py
=============================================
QualityRegistry — lazy auto-registering component registry for all
quality-side services.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

__all__ = ["QualityRegistry", "get_quality_registry", "reset_quality_registry"]

_LOG = logging.getLogger("iios.knowledge.governance.quality_registry")
_lock = threading.Lock()
_reg: Optional["QualityRegistry"] = None


class QualityRegistry:
    """Thread-safe registry for quality subsystem components."""

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._components: dict[str, Any] = {}
        self._registered  = False

    def _auto_register(self) -> None:
        if self._registered:
            return
        from .quality_engine   import get_quality_engine
        from .quality_validator import get_quality_validator
        from .quality_monitor  import get_quality_monitor
        from .quality_context  import get_quality_context

        self._components = {
            "quality_engine":    get_quality_engine(),
            "quality_validator": get_quality_validator(),
            "quality_monitor":   get_quality_monitor(),
            "quality_context":   get_quality_context(),
        }
        self._registered = True

    def register(self, name: str, component: Any) -> None:
        with self._lock:
            self._auto_register()
            self._components[name] = component

    def get(self, name: str) -> Any:
        with self._lock:
            self._auto_register()
            if name not in self._components:
                raise KeyError(f"QualityRegistry: component '{name}' not found.")
            return self._components[name]

    def has(self, name: str) -> bool:
        with self._lock:
            self._auto_register()
            return name in self._components

    def names(self) -> list[str]:
        with self._lock:
            self._auto_register()
            return list(self._components)

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._auto_register()
            return {name: type(c).__name__ for name, c in self._components.items()}


def get_quality_registry() -> QualityRegistry:
    global _reg
    if _reg is None:
        with _lock:
            if _reg is None:
                _reg = QualityRegistry()
    return _reg


def reset_quality_registry() -> None:
    global _reg
    with _lock:
        _reg = None
