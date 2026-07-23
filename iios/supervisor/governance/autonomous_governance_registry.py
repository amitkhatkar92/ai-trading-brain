"""
autonomous_governance_registry.py — iios.supervisor.governance
---------------------------------------------------------------
Thread-safe registry of completed governance summaries.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SESSIONS
from .autonomous_governance_response import AutonomousGovernanceSummary
from .exceptions import (
    AutonomousGovernanceCapacityError,
    AutonomousGovernanceRegistryError,
)


class AutonomousGovernanceRegistry:
    """
    Thread-safe registry of completed governance summaries.

    Allows retrieval by summary_id and supervision_id.
    """

    def __init__(self, max_summaries: int = DEFAULT_MAX_SESSIONS) -> None:
        self._lock:         threading.RLock              = threading.RLock()
        self._max:          int                           = max_summaries
        self._by_id:        Dict[str, AutonomousGovernanceSummary] = {}
        self._by_sup:       Dict[str, List[str]]          = {}  # supervision_id → [summary_id, ...]

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, summary: AutonomousGovernanceSummary) -> None:
        """Register a completed governance summary."""
        if summary is None:
            raise AutonomousGovernanceRegistryError("Cannot register None summary")
        with self._lock:
            if summary.summary_id not in self._by_id and len(self._by_id) >= self._max:
                raise AutonomousGovernanceCapacityError(self._max)
            self._by_id[summary.summary_id] = summary
            self._by_sup.setdefault(summary.supervision_id, []).append(summary.summary_id)

    def unregister(self, summary_id: str) -> None:
        """Remove a summary by its ID."""
        with self._lock:
            if summary_id not in self._by_id:
                from .exceptions import AutonomousGovernanceRegistryError
                raise AutonomousGovernanceRegistryError(f"summary_id not found: {summary_id!r}")
            summary = self._by_id.pop(summary_id)
            ids = self._by_sup.get(summary.supervision_id, [])
            if summary_id in ids:
                ids.remove(summary_id)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, summary_id: str) -> AutonomousGovernanceSummary:
        with self._lock:
            if summary_id not in self._by_id:
                raise AutonomousGovernanceRegistryError(f"summary_id not found: {summary_id!r}")
            return self._by_id[summary_id]

    def get_optional(self, summary_id: str) -> Optional[AutonomousGovernanceSummary]:
        with self._lock:
            return self._by_id.get(summary_id)

    def get_for_supervision(self, supervision_id: str) -> List[AutonomousGovernanceSummary]:
        with self._lock:
            ids = self._by_sup.get(supervision_id, [])
            return [self._by_id[sid] for sid in ids if sid in self._by_id]

    def all_summaries(self) -> List[AutonomousGovernanceSummary]:
        with self._lock:
            return list(self._by_id.values())

    def successful_summaries(self) -> List[AutonomousGovernanceSummary]:
        with self._lock:
            return [s for s in self._by_id.values() if s.is_success]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    @property
    def success_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._by_id.values() if s.is_success)

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_sup.clear()
