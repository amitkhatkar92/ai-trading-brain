"""
knowledge_integration_snapshot.py — iios.knowledge.integration
---------------------------------------------------------------
KnowledgeIntegrationSnapshot — a point-in-time operational snapshot
of the integration engine itself (not the M5 KnowledgeSnapshot).

Captures: engine state, last statistics, last health summary, recent history.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from .constants import IntegrationState


@dataclass(frozen=True)
class KnowledgeIntegrationSnapshot:
    """
    Point-in-time snapshot of the integration engine's operational state.

    Distinct from iios.knowledge.snapshot.KnowledgeSnapshot, which represents
    published enterprise knowledge.  This object represents the integration
    engine's own operational state.
    """
    snapshot_id:        str
    integration_state:  IntegrationState
    statistics:         Dict[str, Any]
    health:             Dict[str, Any]
    recent_responses:   tuple   # Tuple[Dict[str, Any]]
    uptime_seconds:     float
    captured_at:        str

    @classmethod
    def capture(
        cls,
        integration_state: IntegrationState,
        statistics:        Dict[str, Any],
        health:            Dict[str, Any],
        recent_responses:  List[Dict[str, Any]],
        uptime_seconds:    float = 0.0,
    ) -> "KnowledgeIntegrationSnapshot":
        return cls(
            snapshot_id       = f"isnap-{uuid.uuid4().hex[:12]}",
            integration_state = integration_state,
            statistics        = dict(statistics),
            health            = dict(health),
            recent_responses  = tuple(recent_responses),
            uptime_seconds    = uptime_seconds,
            captured_at       = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "integration_state": self.integration_state.value,
            "statistics":        self.statistics,
            "health":            self.health,
            "recent_responses":  list(self.recent_responses),
            "uptime_seconds":    self.uptime_seconds,
            "captured_at":       self.captured_at,
        }
