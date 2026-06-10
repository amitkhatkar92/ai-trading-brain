"""
FORENSIC REFINEMENT — Priority 8: IntegrityPersistenceAudit
=============================================================

Tracks enrichment persistence outcomes across scan cycles.
Answers three questions forensically:

  1. How often is update_enrichment() being throttled vs actually writing?
     (A high throttle rate means scans run much faster than the 5-min gate —
      enrichment data is several cycles stale at any given moment.)

  2. When a write DOES happen, what is the metadata coverage quality?
     (Low strategy/lifecycle/trust coverage means the enrichment map is sparse —
      candidates are persisted without usable metadata.)

  3. Are there repeated write errors?
     (Consecutive errors = store file corruption, disk issue, or concurrent writer.)

Emits:
  [IntegrityPersistenceAudit]  — per successful write: outcome + coverage snapshot
  [IntegrityPersistenceDrift]  — WARNING when any coverage dimension < 50% on a write
  [IntegrityPersistenceReport] — EOD: session totals, throttle rate, avg coverage

Registered in TelemetryCoverageAudit (Priority 7) as module 7.

Thread-safe; auto-resets at midnight UTC.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

# ── Module-level singleton ────────────────────────────────────────────────────
_AUDIT_LOCK:     threading.Lock                         = threading.Lock()
_AUDIT_INSTANCE: "Optional[IntegrityPersistenceAudit]" = None


def get_integrity_audit() -> "IntegrityPersistenceAudit":
    """Return the session-scoped singleton (thread-safe, lazily created)."""
    global _AUDIT_INSTANCE
    if _AUDIT_INSTANCE is None:
        with _AUDIT_LOCK:
            if _AUDIT_INSTANCE is None:
                _AUDIT_INSTANCE = IntegrityPersistenceAudit()
    return _AUDIT_INSTANCE


# ── Low-coverage threshold ────────────────────────────────────────────────────
_LOW_COVERAGE_THRESHOLD = 50.0  # % — below this → emit [IntegrityPersistenceDrift]
_CONSEC_ERROR_WARN_THRESHOLD = 3  # consecutive write errors → escalate to WARNING


class IntegrityPersistenceAudit:
    """
    Singleton that tracks enrichment write outcomes in candidate_store.update_enrichment().

    Wiring points (all wrapped in try/except):
      record_attempt()   — every call to update_enrichment() (before throttle check)
      record_throttled() — called when throttle gate fires
      record_write(...)  — called after successful atomic write
      record_error(...)  — called when the except block fires

    Usage:
        from opportunity_engine.integrity_persistence_audit import get_integrity_audit
        a = get_integrity_audit()
        a.record_attempt()
        # ... throttle check ...
        a.record_throttled(); return False
        # ... after write ...
        a.record_write(total=50, enriched=42, drift=3, invalid_fields=0,
                       strategy_pct=84.0, lifecycle_pct=100.0, trust_pct=100.0)
        a.emit_cycle_audit()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_day = datetime.now(timezone.utc).date()

        # Session counters
        self._session_attempted: int = 0
        self._session_throttled: int = 0
        self._session_written:   int = 0
        self._session_errors:    int = 0
        self._consec_errors:     int = 0

        # Per-write accumulators (for avg over session)
        self._sum_enriched:      float = 0.0
        self._sum_drift:         float = 0.0
        self._sum_invalid:       float = 0.0
        self._sum_strategy_pct:  float = 0.0
        self._sum_lifecycle_pct: float = 0.0
        self._sum_trust_pct:     float = 0.0
        self._low_coverage_writes: int = 0

        # Last write snapshot (for emit_cycle_audit reference)
        self._last: Dict[str, Any] = {}

    # ── Auto-reset ────────────────────────────────────────────────────────────
    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._reset_day:
            self._reset_day = today
            self._session_attempted  = 0
            self._session_throttled  = 0
            self._session_written    = 0
            self._session_errors     = 0
            self._consec_errors      = 0
            self._sum_enriched       = 0.0
            self._sum_drift          = 0.0
            self._sum_invalid        = 0.0
            self._sum_strategy_pct   = 0.0
            self._sum_lifecycle_pct  = 0.0
            self._sum_trust_pct      = 0.0
            self._low_coverage_writes = 0
            self._last               = {}

    # ── Record methods ────────────────────────────────────────────────────────

    def record_attempt(self) -> None:
        """Call at the start of update_enrichment(), before the throttle gate."""
        with self._lock:
            self._maybe_reset()
            self._session_attempted += 1

    def record_throttled(self) -> None:
        """Call when the 5-min throttle gate fires (update_enrichment returns False)."""
        with self._lock:
            self._maybe_reset()
            self._session_throttled += 1

    def record_write(
        self,
        total:         int,
        enriched:      int,
        drift:         int,
        invalid_fields: int,
        strategy_pct:  float,
        lifecycle_pct: float,
        trust_pct:     float,
    ) -> None:
        """
        Call after the atomic write succeeds in update_enrichment().

        Args:
            total:          total candidates in store
            enriched:       candidates that received enrichment overlay
            drift:          candidates whose strategy or lifecycle changed
            invalid_fields: enrichment map entries missing required fields
            strategy_pct:   strategy coverage % post-write
            lifecycle_pct:  lifecycle_state coverage % post-write
            trust_pct:      data_trust_score coverage % post-write
        """
        with self._lock:
            self._maybe_reset()
            self._session_written += 1
            self._consec_errors    = 0  # reset consecutive error counter on success

            self._sum_enriched      += enriched
            self._sum_drift         += drift
            self._sum_invalid       += invalid_fields
            self._sum_strategy_pct  += strategy_pct
            self._sum_lifecycle_pct += lifecycle_pct
            self._sum_trust_pct     += trust_pct

            low_coverage = (
                strategy_pct  < _LOW_COVERAGE_THRESHOLD or
                lifecycle_pct < _LOW_COVERAGE_THRESHOLD or
                trust_pct     < _LOW_COVERAGE_THRESHOLD
            )
            if low_coverage:
                self._low_coverage_writes += 1

            self._last = {
                "total":          total,
                "enriched":       enriched,
                "drift":          drift,
                "invalid_fields": invalid_fields,
                "strategy_pct":   round(strategy_pct,  1),
                "lifecycle_pct":  round(lifecycle_pct, 1),
                "trust_pct":      round(trust_pct,     1),
                "low_coverage":   low_coverage,
            }

    def record_error(self, exc_str: str = "") -> None:
        """Call when the except block fires in update_enrichment()."""
        with self._lock:
            self._maybe_reset()
            self._session_errors += 1
            self._consec_errors  += 1

            if self._consec_errors >= _CONSEC_ERROR_WARN_THRESHOLD:
                log.warning(
                    "[IntegrityPersistenceError] %d consecutive write failures — "
                    "store may be corrupt or locked. last_exc=%s",
                    self._consec_errors, exc_str[:120],
                )

    # ── Emit methods ──────────────────────────────────────────────────────────

    def emit_cycle_audit(self) -> None:
        """
        Emit per-write audit line (call immediately after record_write()).

        [IntegrityPersistenceAudit] attempted=3 throttled=2 written=1 errors=0
          | enriched=42/50 drift=3 invalid_fields=0
          | strategy_cov=84.0% lifecycle_cov=100.0% trust_cov=100.0%
        """
        with self._lock:
            self._maybe_reset()
            last = self._last
            if not last:
                return

            low_tag = " LOW_COVERAGE" if last.get("low_coverage") else ""

            log.info(
                "[IntegrityPersistenceAudit] attempted=%d throttled=%d written=%d errors=%d"
                " | enriched=%d/%d drift=%d invalid_fields=%d"
                " | strategy_cov=%.1f%% lifecycle_cov=%.1f%% trust_cov=%.1f%%%s",
                self._session_attempted,
                self._session_throttled,
                self._session_written,
                self._session_errors,
                last["enriched"],
                last["total"],
                last["drift"],
                last["invalid_fields"],
                last["strategy_pct"],
                last["lifecycle_pct"],
                last["trust_pct"],
                low_tag,
            )

        # Separate WARNING for low coverage (outside lock to avoid nesting)
        if last.get("low_coverage"):
            log.warning(
                "[IntegrityPersistenceDrift] low metadata coverage on write — "
                "strategy=%.1f%% lifecycle=%.1f%% trust=%.1f%% "
                "(threshold=%.0f%%) — enrichment map may be sparse",
                last["strategy_pct"],
                last["lifecycle_pct"],
                last["trust_pct"],
                _LOW_COVERAGE_THRESHOLD,
            )

    def emit_eod_report(self) -> None:
        """
        EOD summary.

        [IntegrityPersistenceReport] session_attempted=15 throttled=12 written=3
          errors=0 throttle_rate=80.0% | avg_enriched=41.3 avg_drift=2.1
          avg_strategy_cov=84.0% avg_lifecycle_cov=100.0% avg_trust_cov=100.0%
          low_coverage_writes=0/3
        """
        with self._lock:
            self._maybe_reset()
            attempted  = self._session_attempted
            throttled  = self._session_throttled
            written    = self._session_written
            errors     = self._session_errors
            low_cov    = self._low_coverage_writes

        if attempted == 0:
            log.info(
                "[IntegrityPersistenceReport] session_attempted=0 — "
                "update_enrichment() was never called this session"
            )
            return

        throttle_rate = throttled / max(1, attempted) * 100.0
        n = max(1, written)
        avg_enriched  = self._sum_enriched      / n
        avg_drift     = self._sum_drift         / n
        avg_strat     = self._sum_strategy_pct  / n
        avg_lc        = self._sum_lifecycle_pct / n
        avg_trust     = self._sum_trust_pct     / n

        log.info(
            "[IntegrityPersistenceReport] session_attempted=%d throttled=%d written=%d"
            " errors=%d throttle_rate=%.1f%%"
            " | avg_enriched=%.1f avg_drift=%.1f"
            " avg_strategy_cov=%.1f%% avg_lifecycle_cov=%.1f%% avg_trust_cov=%.1f%%"
            " low_coverage_writes=%d/%d",
            attempted, throttled, written, errors, throttle_rate,
            avg_enriched, avg_drift,
            avg_strat, avg_lc, avg_trust,
            low_cov, written,
        )

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns session metrics dict.

        Used by TelemetryCoverageAudit to determine whether this module is active
        (session_attempted > 0).
        """
        with self._lock:
            self._maybe_reset()
            return {
                "session_attempted":   self._session_attempted,
                "session_throttled":   self._session_throttled,
                "session_written":     self._session_written,
                "session_errors":      self._session_errors,
                "low_coverage_writes": self._low_coverage_writes,
                "last_write":          dict(self._last),
            }
