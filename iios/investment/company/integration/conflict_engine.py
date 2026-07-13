"""iios/investment/company/integration/conflict_engine.py
Orchestrates conflict detection, classification, resolution, and history.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.integration.conflict_classifier import (
    conflict_summary, reclassify_all, sort_by_priority,
)
from iios.investment.company.integration.conflict_detector import ConflictRecord, detect_conflicts
from iios.investment.company.integration.conflict_history import ConflictHistory
from iios.investment.company.integration.conflict_resolution import ConflictResolver
from iios.investment.company.integration.company_state import ConflictSeverity


class ConflictEngine:
    """
    Single entry point for conflict management.

    Per evaluation:
    1. Detect conflicts in aggregated intelligence.
    2. Reclassify severity (post-detection tuning).
    3. Sort by priority.
    4. Attempt resolution for each conflict.
    5. Persist to history.
    6. Return structured results.
    """

    def __init__(self) -> None:
        self._resolver = ConflictResolver()
        self._history  = ConflictHistory()

    def process(
        self,
        ticker:       str,
        intel:        Any,
        engine_ages:  Optional[Dict[str, float]] = None,
    ) -> List[ConflictRecord]:
        """
        Run the full conflict pipeline for one ticker evaluation.
        Returns the list of (possibly resolved) ConflictRecord objects.
        """
        # 1. Detect
        conflicts = detect_conflicts(ticker, intel)

        # 2. Reclassify severity
        conflicts = reclassify_all(conflicts)

        # 3. Sort by priority (critical first)
        conflicts = sort_by_priority(conflicts)

        # 4. Resolve
        self._resolver.resolve_all(conflicts, intel=intel, engine_ages=engine_ages)

        # 5. Persist
        self._history.record_all(ticker, conflicts)

        return conflicts

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_history(
        self,
        ticker:   str,
        n:        int = 20,
        severity: Optional[ConflictSeverity] = None,
    ) -> List[ConflictRecord]:
        return self._history.get_history(ticker, n=n, severity=severity)

    def unresolved(self, ticker: str) -> List[ConflictRecord]:
        return self._history.unresolved(ticker)

    def critical_unresolved(self, ticker: str) -> List[ConflictRecord]:
        return self._history.critical_unresolved(ticker)

    def summary(self, conflicts: List[ConflictRecord]) -> str:
        return conflict_summary(conflicts)

    def critical_count(self, conflicts: List[ConflictRecord]) -> int:
        return sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL)

    def known_tickers(self) -> List[str]:
        return self._history.known_tickers()
