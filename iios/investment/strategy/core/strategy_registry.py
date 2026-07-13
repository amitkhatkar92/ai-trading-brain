"""iios/investment/strategy/core/strategy_registry.py
Thread-safe registry for institutional strategy classes and descriptors.

This lives in core/ and manages InstitutionalBaseStrategy subclasses.
It is distinct from the parent-level strategy_registry.py which manages
StrategyDefinition objects for the strategy intelligence subsystem.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Type

from .institutional_base_strategy import InstitutionalBaseStrategy
from .strategy_descriptor import StrategyDescriptor

logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """Raised when a strategy cannot be registered."""


class InstitutionalStrategyRegistry:
    """
    Global registry mapping strategy_id → (class, descriptor).
    Supports versioning, dependency tracking, and enable/disable.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._classes: Dict[str, Type[InstitutionalBaseStrategy]] = {}
        self._descriptors: Dict[str, StrategyDescriptor] = {}
        self._enabled: Dict[str, bool] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        strategy_class: Type[InstitutionalBaseStrategy],
        descriptor: StrategyDescriptor,
        replace: bool = False,
    ) -> None:
        sid = descriptor.strategy_id
        with self._lock:
            if sid in self._classes and not replace:
                raise RegistrationError(
                    f"Strategy '{sid}' already registered. Use replace=True to overwrite."
                )
            for dep in descriptor.dependencies:
                if dep not in self._classes:
                    raise RegistrationError(
                        f"Strategy '{sid}' depends on '{dep}' which is not registered."
                    )
            self._classes[sid] = strategy_class
            self._descriptors[sid] = descriptor
            self._enabled[sid] = not descriptor.is_deprecated
            logger.info(
                "Registered institutional strategy '%s' v%s",
                sid, descriptor.version,
            )

    def unregister(self, strategy_id: str) -> None:
        with self._lock:
            self._classes.pop(strategy_id, None)
            self._descriptors.pop(strategy_id, None)
            self._enabled.pop(strategy_id, None)
            logger.info("Unregistered strategy '%s'", strategy_id)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_class(
        self, strategy_id: str
    ) -> Optional[Type[InstitutionalBaseStrategy]]:
        with self._lock:
            return self._classes.get(strategy_id)

    def get_descriptor(self, strategy_id: str) -> Optional[StrategyDescriptor]:
        with self._lock:
            return self._descriptors.get(strategy_id)

    def is_registered(self, strategy_id: str) -> bool:
        with self._lock:
            return strategy_id in self._classes

    def is_enabled(self, strategy_id: str) -> bool:
        with self._lock:
            return self._enabled.get(strategy_id, False)

    # ── Control ───────────────────────────────────────────────────────────────

    def enable(self, strategy_id: str) -> None:
        with self._lock:
            if strategy_id not in self._classes:
                raise RegistrationError(f"Strategy '{strategy_id}' not registered.")
            self._enabled[strategy_id] = True

    def disable(self, strategy_id: str) -> None:
        with self._lock:
            self._enabled[strategy_id] = False

    # ── Enumeration ───────────────────────────────────────────────────────────

    def all_ids(self) -> List[str]:
        with self._lock:
            return list(self._classes.keys())

    def enabled_ids(self) -> List[str]:
        with self._lock:
            return [sid for sid, en in self._enabled.items() if en]

    def all_descriptors(self) -> List[StrategyDescriptor]:
        with self._lock:
            return list(self._descriptors.values())

    def count(self) -> int:
        with self._lock:
            return len(self._classes)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                sid: {
                    "enabled": self._enabled.get(sid, False),
                    "version": str(self._descriptors[sid].version),
                    "is_deprecated": self._descriptors[sid].is_deprecated,
                    "is_experimental": self._descriptors[sid].is_experimental,
                }
                for sid in self._classes
            }
