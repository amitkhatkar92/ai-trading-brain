"""
iios/ontology/reasoning/reasoning_statistics.py
================================================
Runtime statistics for the IIOS Reasoning Engine.

Singleton: get_reasoning_statistics() / reset_reasoning_statistics()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .reasoning_constants import ReasoningType

__all__ = [
    "ReasoningStats",
    "get_reasoning_statistics",
    "reset_reasoning_statistics",
]


@dataclass
class _TypeStats:
    count:           int   = 0
    total_facts:     int   = 0
    total_issues:    int   = 0
    total_ms:        float = 0.0
    total_iter:      int   = 0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0

    @property
    def avg_facts(self) -> float:
        return self.total_facts / self.count if self.count else 0.0

    def to_dict(self) -> dict:
        return {
            "count":        self.count,
            "total_facts":  self.total_facts,
            "total_issues": self.total_issues,
            "avg_ms":       round(self.avg_ms, 3),
            "avg_facts":    round(self.avg_facts, 2),
            "total_iter":   self.total_iter,
        }


class ReasoningStats:
    """Tracks aggregate performance metrics across all reasoning sessions."""

    def __init__(self) -> None:
        self._started_at            = time.time()
        self._session_count         = 0
        self._total_facts_inferred  = 0
        self._total_issues_found    = 0
        self._total_rules_fired     = 0
        self._total_ms              = 0.0
        self._by_type: dict[ReasoningType, _TypeStats] = {}
        self._lock                  = threading.Lock()

    def record(
        self,
        reasoning_type: ReasoningType,
        fact_count:     int,
        issue_count:    int,
        rule_fires:     int,
        duration_ms:    float,
        iterations:     int,
    ) -> None:
        with self._lock:
            self._session_count        += 1
            self._total_facts_inferred += fact_count
            self._total_issues_found   += issue_count
            self._total_rules_fired    += rule_fires
            self._total_ms             += duration_ms
            ts = self._by_type.setdefault(reasoning_type, _TypeStats())
            ts.count        += 1
            ts.total_facts  += fact_count
            ts.total_issues += issue_count
            ts.total_ms     += duration_ms
            ts.total_iter   += iterations

    @property
    def avg_ms(self) -> float:
        return self._total_ms / self._session_count if self._session_count else 0.0

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._started_at

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "session_count":        self._session_count,
                "total_facts_inferred": self._total_facts_inferred,
                "total_issues_found":   self._total_issues_found,
                "total_rules_fired":    self._total_rules_fired,
                "total_ms":             round(self._total_ms, 3),
                "avg_ms":               round(self.avg_ms, 3),
                "uptime_seconds":       round(self.uptime_seconds, 1),
                "by_type": {
                    rt.value: ts.to_dict()
                    for rt, ts in self._by_type.items()
                },
            }


_stats_lock = threading.Lock()
_stats_inst: Optional[ReasoningStats] = None


def get_reasoning_statistics() -> ReasoningStats:
    global _stats_inst
    if _stats_inst is None:
        with _stats_lock:
            if _stats_inst is None:
                _stats_inst = ReasoningStats()
    return _stats_inst


def reset_reasoning_statistics() -> None:
    global _stats_inst
    with _stats_lock:
        _stats_inst = None
