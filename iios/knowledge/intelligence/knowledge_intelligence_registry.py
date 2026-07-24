"""
knowledge_intelligence_registry.py — iios.knowledge.intelligence
-----------------------------------------------------------------
Thread-safe registry of active KnowledgeIntelligenceEngine instances,
indexed by knowledge_id and subsystem_id.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)

# Forward reference only — avoids circular import
# The actual KnowledgeIntelligenceEngine is registered as Any
_EngineType = object


class KnowledgeIntelligenceRegistry:
    """Thread-safe registry mapping (knowledge_id, subsystem_id) → engine."""

    def __init__(self) -> None:
        self._engines: Dict[Tuple[str, str], _EngineType] = {}
        self._lock    = threading.Lock()

    def register(
        self,
        knowledge_id: str,
        subsystem_id: str,
        engine:       _EngineType,
    ) -> None:
        with self._lock:
            key = (knowledge_id, subsystem_id)
            self._engines[key] = engine
            _log.debug(
                f"Intelligence engine registered: "
                f"knowledge_id={knowledge_id!r} subsystem={subsystem_id!r}"
            )

    def get(
        self,
        knowledge_id: str,
        subsystem_id: str,
    ) -> Optional[_EngineType]:
        with self._lock:
            return self._engines.get((knowledge_id, subsystem_id))

    def remove(
        self,
        knowledge_id: str,
        subsystem_id: str,
    ) -> bool:
        with self._lock:
            key = (knowledge_id, subsystem_id)
            if key in self._engines:
                del self._engines[key]
                return True
            return False

    def all_keys(self) -> List[Tuple[str, str]]:
        with self._lock:
            return list(self._engines.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._engines)

    def clear(self) -> None:
        with self._lock:
            self._engines.clear()
