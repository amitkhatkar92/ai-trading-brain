"""
knowledge_component_registry.py — iios.knowledge.integration
------------------------------------------------------------
Registry of live M1–M5 subsystem component instances.

Each component is optional — the integration degrades gracefully when
a component is unavailable.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    COMPONENT_ENGINE,
    COMPONENT_GOVERNANCE,
    COMPONENT_INTELLIGENCE,
    COMPONENT_LIFECYCLE,
    COMPONENT_SNAPSHOT,
    ComponentStatus,
)
from .knowledge_integration_health import ComponentHealth

_log = get_logger(__name__)


class KnowledgeComponentRegistry:
    """
    Holds optional live references to M1–M5 subsystem components.

    Components:
      lifecycle    — iios.knowledge.lifecycle.KnowledgeLifecycle   (M1)
      engine       — iios.knowledge.engine.KnowledgeEngine          (M2)
      governance   — iios.knowledge.governance.PolicyManager        (M3)
      intelligence — iios.knowledge.intelligence.KnowledgeIntelligenceEngine (M4)
      snapshot     — iios.knowledge.snapshot.KnowledgeSnapshotFactory  (M5)
    """

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._lifecycle:    Optional[Any] = None   # M1
        self._engine:       Optional[Any] = None   # M2
        self._governance:   Optional[Any] = None   # M3
        self._intelligence: Optional[Any] = None   # M4
        self._snapshot:     Optional[Any] = None   # M5 factory

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register_lifecycle(self, component: Any) -> None:
        with self._lock:
            self._lifecycle = component
        _log.debug(f"Component registered: {COMPONENT_LIFECYCLE!r}")

    def register_engine(self, component: Any) -> None:
        with self._lock:
            self._engine = component
        _log.debug(f"Component registered: {COMPONENT_ENGINE!r}")

    def register_governance(self, component: Any) -> None:
        with self._lock:
            self._governance = component
        _log.debug(f"Component registered: {COMPONENT_GOVERNANCE!r}")

    def register_intelligence(self, component: Any) -> None:
        with self._lock:
            self._intelligence = component
        _log.debug(f"Component registered: {COMPONENT_INTELLIGENCE!r}")

    def register_snapshot(self, component: Any) -> None:
        with self._lock:
            self._snapshot = component
        _log.debug(f"Component registered: {COMPONENT_SNAPSHOT!r}")

    # ----------------------------------------------------------------
    # Access
    # ----------------------------------------------------------------

    @property
    def lifecycle(self) -> Optional[Any]:
        with self._lock:
            return self._lifecycle

    @property
    def engine(self) -> Optional[Any]:
        with self._lock:
            return self._engine

    @property
    def governance(self) -> Optional[Any]:
        with self._lock:
            return self._governance

    @property
    def intelligence(self) -> Optional[Any]:
        with self._lock:
            return self._intelligence

    @property
    def snapshot_factory(self) -> Optional[Any]:
        with self._lock:
            return self._snapshot

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def available_names(self) -> List[str]:
        """Return names of components that are currently registered."""
        names = []
        with self._lock:
            if self._lifecycle    is not None: names.append(COMPONENT_LIFECYCLE)
            if self._engine       is not None: names.append(COMPONENT_ENGINE)
            if self._governance   is not None: names.append(COMPONENT_GOVERNANCE)
            if self._intelligence is not None: names.append(COMPONENT_INTELLIGENCE)
            if self._snapshot     is not None: names.append(COMPONENT_SNAPSHOT)
        return names

    def health_checks(self) -> List[ComponentHealth]:
        """Return a ComponentHealth for each M1–M5 component."""
        checks: List[ComponentHealth] = []
        with self._lock:
            lc  = self._lifecycle
            eng = self._engine
            gov = self._governance
            intel = self._intelligence
            snap  = self._snapshot
        for name, obj in [
            (COMPONENT_LIFECYCLE,    lc),
            (COMPONENT_ENGINE,       eng),
            (COMPONENT_GOVERNANCE,   gov),
            (COMPONENT_INTELLIGENCE, intel),
            (COMPONENT_SNAPSHOT,     snap),
        ]:
            if obj is None:
                checks.append(ComponentHealth.unavailable(name))
                continue
            # Try calling .health() if the component exposes it
            try:
                h = obj.health() if callable(getattr(obj, "health", None)) else None
                if isinstance(h, dict) and h.get("healthy") is False:
                    checks.append(ComponentHealth.degraded(name, str(h)))
                else:
                    checks.append(ComponentHealth.available(name))
            except Exception as exc:
                _log.warning(f"Health check failed for {name!r}: {exc!r}")
                checks.append(ComponentHealth.degraded(name, str(exc)))
        return checks

    def clear(self) -> None:
        with self._lock:
            self._lifecycle    = None
            self._engine       = None
            self._governance   = None
            self._intelligence = None
            self._snapshot     = None
