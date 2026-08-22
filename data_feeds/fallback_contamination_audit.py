"""
Fallback Contamination Audit
=============================
Session-scoped (in-memory) tracker for feed-source provenance of live price
enrichment data.

Problem it detects:
    A candidate enriched using Yahoo fallback data during a Dhan outage is
    stored with ``fallback_contaminated=False`` and ``data_trust_score=1.0``
    — making it look identical to a candidate served from live Dhan data.
    This silently inflates the quality signal of all enriched candidates
    during any Dhan API degradation period.

Source classification:
    DHAN   — live Dhan broker feed (highest quality, real-time)
    YAHOO  — Yahoo Finance fallback (real data, slight delay/spread)
    CACHE  — stale cached quote served when both feeds missed
    SIM    — synthetic / simulated price (no live feed)
    UNKNOWN — feed source not recorded

Trust multipliers applied to ``data_trust_score``:
    DHAN    → ×1.00  (no reduction)
    YAHOO   → ×0.85  (real data, slight quality reduction)
    CACHE   → ×0.80  (stale: aged by at most 60 s before CACHE flag fires)
    SIM     → ×0.60  (synthetic: no live price basis)
    UNKNOWN → ×0.90  (conservative)

Emitted log tags:
    [FallbackContaminationAudit]  — per scan, with live/fallback breakdown
    [FallbackContaminationEvent]  — per symbol when fallback detected (INFO)
    [FallbackSourceReport]        — EOD or on-demand session summary

Governance: strictly observational.
    - Never blocks execution.
    - Never modifies thresholds or strategy logic.
    - ``data_trust_score`` is a telemetry field — not an execution gate.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date
from typing import Dict, Optional

from utils.logger import get_logger

log = get_logger(__name__)

# ── Trust multipliers per feed source ────────────────────────────────────────
FEED_TRUST_MULTIPLIER: Dict[str, float] = {
    "DHAN":    1.00,
    "YAHOO":   0.85,
    "CACHE":   0.80,
    "SIM":     0.60,
    "UNKNOWN": 0.90,
}

# Feed sources considered contaminated (non-live-grade)
CONTAMINATED_SOURCES = frozenset({"YAHOO", "CACHE", "SIM"})


def get_trust_multiplier(feed_source: str) -> float:
    """Return trust multiplier for a given feed source string."""
    return FEED_TRUST_MULTIPLIER.get((feed_source or "UNKNOWN").upper(), 0.90)


def is_contaminated(feed_source: str) -> bool:
    """True when feed_source is not live-grade Dhan data."""
    return (feed_source or "").upper() in CONTAMINATED_SOURCES


class FallbackContaminationAudit:
    """
    Thread-safe, session-scoped tracker for feed provenance events.

    Auto-resets at date rollover (midnight).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_date: date = date.today()
        self._reset()

    # ── Internal lifecycle ────────────────────────────────────────────────────

    def _reset(self) -> None:
        self._by_source: Dict[str, int] = defaultdict(int)  # source → count
        self._contaminated_symbols: Dict[str, str] = {}     # symbol → source
        self._live_symbols: Dict[str, str] = {}             # symbol → source (DHAN)
        self._total_events: int = 0
        self._scan_count: int = 0

    def _ensure_today(self) -> None:
        today = date.today()
        if today != self._reset_date:
            with self._lock:
                if today != self._reset_date:
                    self._reset_date = today
                    self._reset()

    # ── Public API ────────────────────────────────────────────────────────────

    def record_enrichment(self, symbol: str, feed_source: str) -> None:
        """
        Record the feed source for one enrichment event.

        Args:
            symbol:      e.g. 'RELIANCE'
            feed_source: 'DHAN' | 'YAHOO' | 'CACHE' | 'SIM' | ''
        """
        self._ensure_today()
        src = (feed_source or "UNKNOWN").upper()
        with self._lock:
            self._by_source[src] += 1
            self._total_events += 1
            if src in CONTAMINATED_SOURCES:
                self._contaminated_symbols[symbol] = src
            else:
                self._live_symbols[symbol] = src

        if src in CONTAMINATED_SOURCES:
            log.info(
                "[FallbackContaminationEvent] symbol=%s source=%s"
                " trust_multiplier=%.2f contaminated=True",
                symbol, src, get_trust_multiplier(src),
            )

    def emit_scan_audit(self, scan_prepared_count: int = 0) -> None:
        """
        Emit [FallbackContaminationAudit] at end of each scan.

        Args:
            scan_prepared_count: how many candidates went through this scan
        """
        self._ensure_today()
        with self._lock:
            self._scan_count += 1
            total = self._total_events
            by_src = dict(self._by_source)
            contaminated_count = sum(
                v for k, v in by_src.items() if k in CONTAMINATED_SOURCES
            )
            live_count = by_src.get("DHAN", 0)
            contamination_rate = (contaminated_count / total * 100.0) if total > 0 else 0.0

        log.info(
            "[FallbackContaminationAudit]"
            " scan_candidates=%d total_enriched=%d"
            " live_dhan=%d yahoo_fallback=%d cache_fallback=%d sim=%d unknown=%d"
            " contaminated=%d contamination_rate=%.1f%%",
            scan_prepared_count,
            total,
            live_count,
            by_src.get("YAHOO", 0),
            by_src.get("CACHE", 0),
            by_src.get("SIM", 0),
            by_src.get("UNKNOWN", 0),
            contaminated_count,
            contamination_rate,
        )

    def emit_eod_report(self) -> None:
        """Emit [FallbackSourceReport] EOD summary."""
        self._ensure_today()
        with self._lock:
            total = self._total_events
            by_src = dict(self._by_source)
            contaminated = sum(v for k, v in by_src.items() if k in CONTAMINATED_SOURCES)
            top_contaminated = sorted(self._contaminated_symbols.items())[:10]

        log.info(
            "[FallbackSourceReport] total_enrichment_events=%d"
            " live=%d contaminated=%d contamination_rate=%.1f%%"
            " by_source=%s top_contaminated_symbols=%r",
            total,
            by_src.get("DHAN", 0),
            contaminated,
            (contaminated / total * 100.0) if total > 0 else 0.0,
            dict(by_src),
            top_contaminated,
        )

    def get_stats(self) -> dict:
        """Return current stats dict (for programmatic access)."""
        self._ensure_today()
        with self._lock:
            total = self._total_events
            by_src = dict(self._by_source)
            contaminated = sum(v for k, v in by_src.items() if k in CONTAMINATED_SOURCES)
            return {
                "total_events":         total,
                "by_source":            by_src,
                "contaminated":         contaminated,
                "contamination_rate":   (contaminated / total * 100.0) if total > 0 else 0.0,
                "live_symbols":         len(self._live_symbols),
                "contaminated_symbols": len(self._contaminated_symbols),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
_INSTANCE: Optional[FallbackContaminationAudit] = None
_INSTANCE_LOCK = threading.Lock()


def get_fallback_audit() -> FallbackContaminationAudit:
    """Thread-safe singleton accessor."""
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = FallbackContaminationAudit()
    return _INSTANCE
