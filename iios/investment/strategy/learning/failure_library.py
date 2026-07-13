"""iios/investment/strategy/learning/failure_library.py
FailureLibrary — catalogs failure patterns with remedies.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.failure_pattern import FailurePattern
from iios.investment.strategy.learning.lesson_registry import Lesson, LessonCategory


@dataclass(frozen=True)
class FailureEntry:
    """A catalogued failure pattern with structured remediation guidance."""
    entry_id:      str
    strategy_id:   str
    pattern_name:  str
    description:   str
    root_cause:    str
    remedy:        str
    severity:      str
    evidence:      List[str]
    confidence:    float
    created_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved:      bool = False

    def to_lesson(self) -> Lesson:
        return Lesson(
            lesson_id=str(uuid.uuid4()),
            strategy_id=self.strategy_id,
            category=LessonCategory.FAILURE,
            title=f"Failure: {self.pattern_name}",
            description=f"{self.description}\n\nRemedy: {self.remedy}",
            evidence=self.evidence,
            confidence=self.confidence,
            support_count=len(self.evidence),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":     self.entry_id,
            "strategy_id":  self.strategy_id,
            "pattern_name": self.pattern_name,
            "description":  self.description,
            "root_cause":   self.root_cause,
            "remedy":       self.remedy,
            "severity":     self.severity,
            "confidence":   round(self.confidence, 3),
            "resolved":     self.resolved,
            "created_at":   self.created_at.isoformat(),
        }


class FailureLibrary:
    """
    Persistent (in-process) catalog of failure patterns across strategies.
    Thread-safe. Entries are never deleted — only marked as resolved.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, List[FailureEntry]] = {}
        self._lock = threading.RLock()

    def catalog(self, patterns: List[FailurePattern]) -> List[FailureEntry]:
        """Convert FailurePattern objects to FailureEntry objects and store them."""
        entries: List[FailureEntry] = []
        for p in patterns:
            entry = FailureEntry(
                entry_id=str(uuid.uuid4()),
                strategy_id=p.strategy_id,
                pattern_name=p.name,
                description=p.description,
                root_cause=self._infer_root_cause(p.name),
                remedy=p.suggested_remedy,
                severity=p.severity,
                evidence=[
                    f"Failure rate: {p.failure_rate:.0%}",
                    f"Support: {p.observation_count} observations",
                    f"Regimes: {', '.join(p.characteristic_regimes) or 'various'}",
                ],
                confidence=p.confidence,
            )
            entries.append(entry)
            with self._lock:
                self._entries.setdefault(p.strategy_id, []).append(entry)
        return entries

    def get(self, strategy_id: str, include_resolved: bool = False) -> List[FailureEntry]:
        with self._lock:
            all_e = self._entries.get(strategy_id, [])
            if include_resolved:
                return list(all_e)
            return [e for e in all_e if not e.resolved]

    def resolve(self, entry_id: str) -> bool:
        with self._lock:
            for entries in self._entries.values():
                for i, e in enumerate(entries):
                    if e.entry_id == entry_id:
                        entries[i] = FailureEntry(
                            entry_id=e.entry_id,
                            strategy_id=e.strategy_id,
                            pattern_name=e.pattern_name,
                            description=e.description,
                            root_cause=e.root_cause,
                            remedy=e.remedy,
                            severity=e.severity,
                            evidence=e.evidence,
                            confidence=e.confidence,
                            created_at=e.created_at,
                            resolved=True,
                        )
                        return True
        return False

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._entries.get(strategy_id, []))

    @staticmethod
    def _infer_root_cause(pattern_name: str) -> str:
        causes = {
            "regime_mismatch_failure": "Strategy deployed outside its effective market regime",
            "excessive_drawdown":      "Insufficient position-sizing or stop-loss discipline",
            "low_win_rate":            "Entry signal quality below viable threshold",
            "high_volatility_failure": "Strategy not adapted for elevated volatility environments",
        }
        return causes.get(pattern_name, "Root cause requires further investigation")
