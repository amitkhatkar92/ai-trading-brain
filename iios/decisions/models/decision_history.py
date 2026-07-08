"""
iios/decisions/models/decision_history.py
==========================================
DecisionHistory — ordered timeline of Decision records for a source.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .decision import Decision
from .decision_statistics import DecisionStatistics, build_statistics


@dataclass
class DecisionHistory:
    """
    Ordered, append-only history of decisions for a given source.

    Attributes
    ----------
    history_id    : Unique identifier.
    source_id     : Owning source (engine / module).
    decisions     : Chronological list of decisions.
    max_entries   : Cap on retained history length.
    created_at    : Unix creation timestamp.
    last_updated  : Unix last-append timestamp.
    """

    history_id:   str             = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:    str             = ""
    decisions:    list[Decision]  = field(default_factory=list)
    max_entries:  int             = 10_000
    created_at:   float           = field(default_factory=time.time)
    last_updated: float           = field(default_factory=time.time)

    def append(self, decision: Decision) -> None:
        if len(self.decisions) >= self.max_entries:
            self.decisions.pop(0)
        self.decisions.append(decision)
        self.last_updated = time.time()

    def latest(self, n: int = 10) -> list[Decision]:
        return list(self.decisions[-n:])

    def statistics(self) -> DecisionStatistics:
        return build_statistics(self.decisions, source_id=self.source_id)

    def to_dict(self, include_decisions: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "history_id":   self.history_id,
            "source_id":    self.source_id,
            "total":        len(self.decisions),
            "max_entries":  self.max_entries,
            "created_at":   self.created_at,
            "last_updated": self.last_updated,
            "statistics":   self.statistics().to_dict(),
        }
        if include_decisions:
            d["decisions"] = [dec.to_dict() for dec in self.decisions]
        return d
