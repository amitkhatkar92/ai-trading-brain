"""
Replay Learning Integrity Validator
=====================================
Read-only validation layer for Historical Experience Training.
No learning state is modified; all checks are observational only.

Verifies per replay day:
  1. Closed Trades           == Replay Learning Records
  2. Replay Learning Records == Feature Labels Updated
     (exempt when no unlabeled feature rows exist for traded symbols)
  3. Feature Labels Updated  <= Feature Rows Available
  4. Edge Discovery completed successfully
  5. Knowledge persistence files are present

Emits ReplayIntegritySummary at the end of a full replay run.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, List

from utils import get_logger

log = get_logger(__name__)

_EDGES_PATH   = os.path.join("data", "discovered_edges.json")
_FEAT_DB_PATH = os.path.join("data", "ede_feature_db.json")
_PATTERN_RE   = re.compile(r"Patterns mined:\s+(\d+)")


class ReplayIntegrityError(Exception):
    """Raised in strict mode when a replay day fails an integrity check."""


@dataclass
class DayIntegrityResult:
    day_num:                int
    trading_date:           Any
    trades_closed:          int
    learning_records_fed:   int
    feature_rows_available: int    # unlabeled DB rows for traded symbols before enrichment
    labels_updated:         int
    ede_completed:          bool
    ede_patterns_found:     int
    persistence_ok:         bool
    failures:               List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0


@dataclass
class ReplayIntegritySummary:
    total_days:                int
    days_passed:               int
    days_failed:               int
    total_trades_closed:       int
    total_labels_updated:      int
    total_patterns_discovered: int
    total_edges_promoted:      int
    integrity_failures:        List[str] = field(default_factory=list)
    overall_status:            str = "PASS"


class IntegrityValidator:
    """
    Validates that each replay day's learning pipeline is fully connected.
    Does not modify any learning state.
    """

    def __init__(self, strict: bool = False) -> None:
        self._strict       = strict
        self._day_results: List[DayIntegrityResult] = []
        self._edges_start: int = 0

    def snapshot_start(self) -> None:
        """Record baseline edge count before the first replay day."""
        self._edges_start = _count_edges()

    def check_day(
        self,
        *,
        day_num:                int,
        trading_date:           Any,
        n_closed:               int,
        n_fed:                  int,
        feature_rows_available: int,
        n_labels_updated:       int,
        ede_completed:          bool,
        ede_report:             str,
    ) -> DayIntegrityResult:
        failures: List[str] = []
        patterns = _parse_patterns(ede_report)

        # Check 1 — closed trades must equal learning records fed
        if n_closed != n_fed:
            failures.append(
                f"[ReplayIntegrityError] day={day_num} | stage=learning_records | "
                f"expected={n_closed} | actual={n_fed} | "
                f"reason=closed_trades_mismatch"
            )

        # Check 2 — every trade should have had a feature row to enrich
        # Exempt when feature_rows_available == 0 (Day 1 bootstrap or symbol-universe gap)
        if n_fed > 0 and feature_rows_available > 0 and n_labels_updated != n_fed:
            failures.append(
                f"[ReplayIntegrityError] day={day_num} | stage=label_enrichment | "
                f"expected={n_fed} | actual={n_labels_updated} | "
                f"reason=label_update_mismatch"
            )

        # Check 3 — labels updated cannot exceed rows available
        if n_labels_updated > feature_rows_available:
            failures.append(
                f"[ReplayIntegrityError] day={day_num} | stage=feature_db | "
                f"expected_max={feature_rows_available} | actual={n_labels_updated} | "
                f"reason=labels_exceed_feature_rows"
            )

        # Check 4 — EDE must complete when there were trades to learn from
        if n_fed > 0 and not ede_completed:
            failures.append(
                f"[ReplayIntegrityError] day={day_num} | stage=edge_discovery | "
                f"expected=completed | actual=skipped_or_failed | "
                f"reason=ede_did_not_complete"
            )

        # Check 5 — knowledge persistence files must exist after any learning
        persistence_ok = _check_persistence()
        if n_fed > 0 and not persistence_ok:
            failures.append(
                f"[ReplayIntegrityError] day={day_num} | stage=persistence | "
                f"expected=written | actual=missing | "
                f"reason=knowledge_files_absent"
            )

        for msg in failures:
            log.error(msg)

        result = DayIntegrityResult(
            day_num=day_num,
            trading_date=trading_date,
            trades_closed=n_closed,
            learning_records_fed=n_fed,
            feature_rows_available=feature_rows_available,
            labels_updated=n_labels_updated,
            ede_completed=ede_completed,
            ede_patterns_found=patterns,
            persistence_ok=persistence_ok,
            failures=failures,
        )
        self._day_results.append(result)

        status = "PASS" if result.passed else "FAIL"
        log.info(
            "[ReplayIntegrity] Day %d %s — closed=%d fed=%d rows_avail=%d "
            "labels=%d patterns=%d",
            day_num, status, n_closed, n_fed,
            feature_rows_available, n_labels_updated, patterns,
        )

        if failures and self._strict:
            raise ReplayIntegrityError(
                f"Day {day_num}: {len(failures)} integrity check(s) failed"
            )

        return result

    def generate_summary(self) -> ReplayIntegritySummary:
        total     = len(self._day_results)
        passed    = sum(1 for r in self._day_results if r.passed)
        failed    = total - passed
        closed    = sum(r.trades_closed        for r in self._day_results)
        labeled   = sum(r.labels_updated        for r in self._day_results)
        patterns  = sum(r.ede_patterns_found    for r in self._day_results)
        failures  = [f for r in self._day_results for f in r.failures]
        promoted  = max(0, _count_edges() - self._edges_start)
        overall   = "PASS" if failed == 0 else "FAIL"

        summary = ReplayIntegritySummary(
            total_days=total,
            days_passed=passed,
            days_failed=failed,
            total_trades_closed=closed,
            total_labels_updated=labeled,
            total_patterns_discovered=patterns,
            total_edges_promoted=promoted,
            integrity_failures=failures,
            overall_status=overall,
        )
        _log_summary(summary)
        return summary


# ── Module helpers ────────────────────────────────────────────────────────────

def _count_edges() -> int:
    try:
        if os.path.isfile(_EDGES_PATH):
            with open(_EDGES_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            return len(data)
    except Exception:
        pass
    return 0


def _check_persistence() -> bool:
    return os.path.isfile(_FEAT_DB_PATH) and os.path.isfile(_EDGES_PATH)


def _parse_patterns(report: str) -> int:
    if not report:
        return 0
    match = _PATTERN_RE.search(report)
    return int(match.group(1)) if match else 0


def _log_summary(s: ReplayIntegritySummary) -> None:
    sep = "=" * 62
    lines = [
        sep,
        "  REPLAY LEARNING INTEGRITY REPORT",
        sep,
        f"  Total replay days        : {s.total_days}",
        f"  Days passed              : {s.days_passed}",
        f"  Days failed              : {s.days_failed}",
        f"  Total trades closed      : {s.total_trades_closed}",
        f"  Total labels updated     : {s.total_labels_updated}",
        f"  Total patterns discovered: {s.total_patterns_discovered}",
        f"  Total edges promoted     : {s.total_edges_promoted}",
        f"  Integrity failures       : {len(s.integrity_failures)}",
        f"  Overall status           : {s.overall_status}",
        sep,
    ]
    if s.integrity_failures:
        lines.append("  FAILURES:")
        for msg in s.integrity_failures:
            lines.append(f"    {msg}")
        lines.append(sep)
    text = "\n".join(lines)
    if s.overall_status == "PASS":
        log.info("\n%s", text)
    else:
        log.error("\n%s", text)
