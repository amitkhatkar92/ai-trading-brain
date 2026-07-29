"""
validation_report.py -- iios.ai.learning_evaluation.quality
=============================================================
:class:`ValidationReport` — immutable per-assessment validation summary.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class ValidationReport:
    """
    Immutable summary of which quality rules passed or failed.

    ``blocking_failures`` — rule names that are blocking (assessment failed).
    ``overall_passed``    — True only if no blocking rules failed.
    """

    report_id:        str
    session_id:       str
    target_id:        str
    rules_evaluated:  int
    rules_passed:     int
    rules_failed:     int
    blocking_failures: FrozenSet[str]
    overall_passed:   bool
    created_at:       float
    notes:            str

    @classmethod
    def build(
        cls,
        session_id:       str,
        target_id:        str,
        rules_passed:     int,
        rules_failed:     int,
        blocking_failures: FrozenSet[str],
        notes:            str = "",
    ) -> "ValidationReport":
        return cls(
            report_id         = str(uuid.uuid4()),
            session_id        = session_id,
            target_id         = target_id,
            rules_evaluated   = rules_passed + rules_failed,
            rules_passed      = rules_passed,
            rules_failed      = rules_failed,
            blocking_failures = frozenset(blocking_failures),
            overall_passed    = len(blocking_failures) == 0,
            created_at        = time.time(),
            notes             = notes,
        )

    def failure_rate(self) -> float:
        return (self.rules_failed / self.rules_evaluated) if self.rules_evaluated else 0.0
