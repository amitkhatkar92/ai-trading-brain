"""
knowledge_component_factory.py — iios.knowledge.integration
------------------------------------------------------------
Factory that creates and initializes M1–M5 subsystem components,
then returns a populated KnowledgeComponentRegistry.

Components are instantiated via optional imports; any missing subsystem
is silently skipped and logged as unavailable.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import importlib
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

from .knowledge_component_registry import KnowledgeComponentRegistry

_log = get_logger(__name__)


def _try_import(module_path: str, class_name: str) -> Optional[Any]:
    """Import a class from a module; return None on ImportError."""
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name, None)
    except ImportError as exc:
        _log.debug(f"Optional import skipped: {module_path}.{class_name}: {exc!r}")
        return None


class KnowledgeComponentFactory:
    """
    Discovers and instantiates M1–M5 subsystem components.

    Each component is created if its package is importable; otherwise
    the slot in KnowledgeComponentRegistry remains None.
    """

    # ----------------------------------------------------------------
    # Individual creators
    # ----------------------------------------------------------------

    def create_lifecycle(self) -> Optional[Any]:
        """M1: KnowledgeLifecycle from iios.knowledge.lifecycle."""
        cls = _try_import("iios.knowledge.lifecycle", "KnowledgeLifecycle")
        if cls is None:
            return None
        try:
            instance = cls()
            instance.initialize()
            return instance
        except Exception as exc:
            _log.warning(f"M1 KnowledgeLifecycle init failed: {exc!r}")
            return None

    def create_engine(self) -> Optional[Any]:
        """M2: KnowledgeEngine from iios.knowledge.engine."""
        cls = _try_import("iios.knowledge.engine", "KnowledgeEngine")
        if cls is None:
            return None
        try:
            instance = cls()
            instance.initialize()
            return instance
        except Exception as exc:
            _log.warning(f"M2 KnowledgeEngine init failed: {exc!r}")
            return None

    def create_governance(self) -> Optional[Any]:
        """M3: PolicyManager from iios.knowledge.governance."""
        cls = _try_import("iios.knowledge.governance", "PolicyManager")
        if cls is None:
            return None
        try:
            return cls()
        except Exception as exc:
            _log.warning(f"M3 PolicyManager init failed: {exc!r}")
            return None

    def create_intelligence(self) -> Optional[Any]:
        """M4: KnowledgeIntelligenceEngine from iios.knowledge.intelligence."""
        cls = _try_import(
            "iios.knowledge.intelligence", "KnowledgeIntelligenceEngine"
        )
        if cls is None:
            return None
        try:
            instance = cls()
            instance.initialize()
            return instance
        except Exception as exc:
            _log.warning(f"M4 KnowledgeIntelligenceEngine init failed: {exc!r}")
            return None

    def create_snapshot_factory(self) -> Any:
        """M5: KnowledgeSnapshotFactory from iios.knowledge.snapshot (always available)."""
        from iios.knowledge.snapshot import KnowledgeSnapshotFactory
        return KnowledgeSnapshotFactory()

    # ----------------------------------------------------------------
    # Full registry creation
    # ----------------------------------------------------------------

    def create_registry(self) -> KnowledgeComponentRegistry:
        """
        Create and return a fully populated KnowledgeComponentRegistry.

        Any component that fails to initialise is silently omitted.
        """
        registry = KnowledgeComponentRegistry()

        lc = self.create_lifecycle()
        if lc is not None:
            registry.register_lifecycle(lc)

        eng = self.create_engine()
        if eng is not None:
            registry.register_engine(eng)

        gov = self.create_governance()
        if gov is not None:
            registry.register_governance(gov)

        intel = self.create_intelligence()
        if intel is not None:
            registry.register_intelligence(intel)

        snap = self.create_snapshot_factory()
        registry.register_snapshot(snap)

        available = registry.available_names()
        _log.info(f"Component registry created: available={available!r}")
        return registry
