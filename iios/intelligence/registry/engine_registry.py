"""
iios/intelligence/registry/engine_registry.py
=============================================
AI Engine Registry — registers and discovers AI engine implementations.

This module provides registration infrastructure for all current and future
AI engines within IIOS.  Engines are registered by EngineType; multiple
implementations can be registered for the same type (versioned, fallback).

Supported engine types (registration only — not yet implemented):
  Reasoning, Debate, Hypothesis, Forecast, Decision, Strategy, Risk,
  Portfolio, Learning, Execution, Agent, Plugin, Ontology, Observation, Knowledge

Singleton: get_engine_registry() / reset_engine_registry()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from ..intelligence_constants import EngineType, EngineStatus, Priority, SYSTEM_ACTOR
from ..intelligence_exceptions import (
    EngineNotFoundError,
    EngineAlreadyRegisteredError,
    EngineNotInitializedError,
    EngineUnavailableError,
)

__all__ = [
    "EngineDescriptor",
    "AIEngine",
    "EngineRegistry",
    "get_engine_registry",
    "reset_engine_registry",
]


@runtime_checkable
class AIEngine(Protocol):
    """Minimal protocol every AI engine implementation must satisfy."""
    engine_id:   str
    engine_type: EngineType

    def initialize(self) -> None: ...
    def execute(self, request: Any) -> Any: ...
    def health(self) -> dict: ...


@dataclass
class EngineDescriptor:
    """
    Metadata and reference for a registered AI engine.

    The descriptor decouples registration from instantiation:
    ``factory`` is called lazily when the engine is first needed.
    """
    engine_id:    str
    engine_type:  EngineType
    name:         str
    version:      str                   = "1.0.0"
    description:  str                   = ""
    status:        EngineStatus          = EngineStatus.REGISTERED
    priority:     Priority              = Priority.NORMAL
    factory:      Optional[Callable]    = field(default=None, repr=False)
    instance:     Optional[Any]         = field(default=None, repr=False)
    tags:         list[str]             = field(default_factory=list)
    metadata:     dict[str, Any]        = field(default_factory=dict)
    registered_at: float                = field(default_factory=time.time)
    actor:        str                   = SYSTEM_ACTOR

    # ── Lazy instantiation ────────────────────────────────────────────────────

    def get_instance(self) -> Any:
        """Return or create the engine instance via its factory."""
        if self.instance is None:
            if self.factory is None:
                raise EngineNotInitializedError(self.engine_id)
            self.instance = self.factory()
        return self.instance

    def is_ready(self) -> bool:
        return self.status == EngineStatus.READY

    def to_dict(self) -> dict:
        return {
            "engine_id":    self.engine_id,
            "engine_type":  self.engine_type.value,
            "name":         self.name,
            "version":      self.version,
            "description":  self.description,
            "status":        self.status.value,
            "priority":     self.priority.value,
            "tags":         self.tags,
            "registered_at": self.registered_at,
            "has_instance": self.instance is not None,
        }


class EngineRegistry:
    """
    Thread-safe registry of AI engine descriptors.

    Registration
    ------------
    register(descriptor)           — register a pre-built descriptor
    register_factory(...)          — shortcut: build descriptor + register

    Lookup
    ------
    get(engine_id)                 — by exact ID
    get_by_type(engine_type)       — all engines of a given type
    best(engine_type)              — highest-priority ready engine of type
    has(engine_id)                 — existence check
    """

    def __init__(self) -> None:
        self._engines: dict[str, EngineDescriptor]          = {}
        self._by_type: dict[EngineType, list[str]]          = {}
        self._lock    = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        descriptor: EngineDescriptor,
        overwrite:  bool = False,
    ) -> None:
        with self._lock:
            if descriptor.engine_id in self._engines and not overwrite:
                raise EngineAlreadyRegisteredError(descriptor.engine_id)
            self._engines[descriptor.engine_id] = descriptor
            bucket = self._by_type.setdefault(descriptor.engine_type, [])
            if descriptor.engine_id not in bucket:
                bucket.append(descriptor.engine_id)

    def register_factory(
        self,
        engine_id:   str,
        engine_type: EngineType,
        name:        str,
        factory:     Callable,
        version:     str         = "1.0.0",
        description: str         = "",
        priority:    Priority    = Priority.NORMAL,
        tags:        list[str] | None = None,
        overwrite:   bool        = False,
    ) -> EngineDescriptor:
        """Create a descriptor with a factory callable and register it."""
        desc = EngineDescriptor(
            engine_id   = engine_id,
            engine_type = engine_type,
            name        = name,
            version     = version,
            description = description,
            factory     = factory,
            priority    = priority,
            tags        = tags or [],
        )
        self.register(desc, overwrite=overwrite)
        return desc

    def register_instance(
        self,
        engine_id:   str,
        engine_type: EngineType,
        name:        str,
        instance:    Any,
        version:     str      = "1.0.0",
        priority:    Priority = Priority.NORMAL,
        overwrite:   bool     = False,
    ) -> EngineDescriptor:
        """Register a pre-created engine instance."""
        desc = EngineDescriptor(
            engine_id   = engine_id,
            engine_type = engine_type,
            name        = name,
            version     = version,
            instance    = instance,
            status       = EngineStatus.READY,
            priority    = priority,
        )
        self.register(desc, overwrite=overwrite)
        return desc

    def unregister(self, engine_id: str) -> bool:
        with self._lock:
            desc = self._engines.pop(engine_id, None)
            if desc is None:
                return False
            bucket = self._by_type.get(desc.engine_type, [])
            if engine_id in bucket:
                bucket.remove(engine_id)
            return True

    # ── Status updates ────────────────────────────────────────────────────────

    def set_status(self, engine_id: str, status: EngineStatus) -> None:
        with self._lock:
            d = self._engines.get(engine_id)
            if d is None:
                raise EngineNotFoundError(engine_id)
            d.status = status

    def mark_ready(self, engine_id: str) -> None:
        self.set_status(engine_id, EngineStatus.READY)

    def mark_disabled(self, engine_id: str) -> None:
        self.set_status(engine_id, EngineStatus.DISABLED)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, engine_id: str) -> EngineDescriptor:
        with self._lock:
            d = self._engines.get(engine_id)
            if d is None:
                raise EngineNotFoundError(engine_id)
            return d

    def has(self, engine_id: str) -> bool:
        with self._lock:
            return engine_id in self._engines

    def get_by_type(self, engine_type: EngineType) -> list[EngineDescriptor]:
        with self._lock:
            ids = self._by_type.get(engine_type, [])
            return [self._engines[i] for i in ids if i in self._engines]

    def best(self, engine_type: EngineType) -> Optional[EngineDescriptor]:
        """Return the highest-priority READY engine of the given type."""
        with self._lock:
            candidates = [
                self._engines[i]
                for i in self._by_type.get(engine_type, [])
                if i in self._engines
                and self._engines[i].status == EngineStatus.READY
            ]
            if not candidates:
                return None
            return max(candidates, key=lambda d: d.priority.value)

    def all_descriptors(self) -> list[EngineDescriptor]:
        with self._lock:
            return list(self._engines.values())

    def registered_types(self) -> list[EngineType]:
        with self._lock:
            return list(self._by_type.keys())

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            by_status: dict[str, int] = {}
            for d in self._engines.values():
                by_status[d.status.value] = by_status.get(d.status.value, 0) + 1
            return {
                "total":     len(self._engines),
                "by_status": by_status,
                "types":     len(self._by_type),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_reg_lock = threading.Lock()
_reg_inst: Optional[EngineRegistry] = None


def get_engine_registry() -> EngineRegistry:
    global _reg_inst
    if _reg_inst is None:
        with _reg_lock:
            if _reg_inst is None:
                _reg_inst = EngineRegistry()
    return _reg_inst


def reset_engine_registry() -> None:
    global _reg_inst
    with _reg_lock:
        _reg_inst = None
