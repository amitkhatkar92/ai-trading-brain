"""
knowledge_graph_registry.py — iios.knowledge.intelligence
----------------------------------------------------------
Thread-safe registry of active KnowledgeGraph instances keyed by graph_id.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .knowledge_graph_engine import KnowledgeGraph

_log = get_logger(__name__)


class KnowledgeGraphRegistry:
    """Thread-safe registry of named KnowledgeGraph instances."""

    def __init__(self) -> None:
        self._graphs: Dict[str, KnowledgeGraph] = {}
        self._lock   = threading.Lock()

    def register(self, graph: KnowledgeGraph) -> None:
        with self._lock:
            self._graphs[graph.graph_id] = graph
            _log.debug(f"Graph registered: id={graph.graph_id!r}")

    def get(self, graph_id: str) -> Optional[KnowledgeGraph]:
        with self._lock:
            return self._graphs.get(graph_id)

    def remove(self, graph_id: str) -> bool:
        with self._lock:
            if graph_id in self._graphs:
                del self._graphs[graph_id]
                return True
            return False

    def all_graph_ids(self) -> List[str]:
        with self._lock:
            return list(self._graphs.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._graphs)

    def clear(self) -> None:
        with self._lock:
            self._graphs.clear()
