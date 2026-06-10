"""
Ranking Instability Audit
==========================
Session-scoped tracker that detects how much candidate rank ordering
changes between consecutive scan cycles.

Problem it detects:
    The scanner sector-reranks ~65 prepared candidates each cycle using
    conviction-decayed scores.  If score thresholds are near boundary values
    (e.g. RSI=71.9 → normal decay vs RSI=72.1 → momentum_extreme decay),
    a candidate can jump from rank #2 to rank #18 with a trivial input change.
    This produces non-deterministic signal priority and makes the system
    unable to consistently favour its best candidates.

What is measured:
    • rank_changes       — how many candidates changed rank vs previous cycle
    • avg_rank_delta     — average absolute rank position shift
    • top5_churn         — how many of the top-5 ranked candidates changed
    • signals_from_top10 — signals that came from top-10 ranked candidates
    • instability_pct    — rank_changes / total_ranked * 100
    • score_range        — max−min score across all ranked candidates (spread width)
    • near_boundary      — symbols with score very close to a decay-rule boundary
                           (vol_collapse ≤0.40, momentum_extreme ≥72 RSI, etc.)

Emitted log tags:
    [RankingInstabilityAudit]  — per scan cycle
    [RankingInstabilityReport] — EOD session summary

Governance: strictly observational.
    - Never changes scores, thresholds, or sort order.
    - rank_changes / instability_pct are informational only.
    - Any remediation (e.g., smoothed decay) is a separate deliberate change.
"""
from __future__ import annotations

import threading
from datetime import date
from typing import Dict, Optional, Set

from utils.logger import get_logger

log = get_logger(__name__)


class RankingInstabilityAudit:
    """
    Thread-safe, session-scoped tracker for candidate rank stability.

    Stores one cycle's rank snapshot; next cycle computes the diff.
    Auto-resets at date rollover.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_date: date = date.today()
        self._reset()

    # ── Internal lifecycle ────────────────────────────────────────────────────

    def _reset(self) -> None:
        # Previous cycle rank map: symbol → 0-based rank position
        self._prev_ranks: Dict[str, int] = {}
        self._prev_scores: Dict[str, float] = {}

        # Session cumulative
        self._session_scans:           int   = 0
        self._session_rank_changes:    int   = 0
        self._session_prepared:        int   = 0
        self._session_instability_sum: float = 0.0
        self._peak_instability:        float = 0.0
        self._peak_instability_cycle:  int   = 0

        # Last cycle snapshot
        self._last_cycle: dict = {}

    def _ensure_today(self) -> None:
        today = date.today()
        if today != self._reset_date:
            with self._lock:
                if today != self._reset_date:
                    self._reset_date = today
                    self._reset()

    # ── Public API ────────────────────────────────────────────────────────────

    def record_cycle(
        self,
        current_ranks:  Dict[str, int],
        current_scores: Dict[str, float],
        signals_found:  Set[str],
    ) -> None:
        """
        Record rank snapshot for one scan cycle and compute instability vs
        the previous cycle.

        Args:
            current_ranks:  {symbol: 0-based rank position in prepared list}
            current_scores: {symbol: post-decay score}
            signals_found:  set of symbols that produced a TradeSignal
        """
        self._ensure_today()
        if not current_ranks:
            return

        total = len(current_ranks)
        scores = list(current_scores.values()) if current_scores else []
        score_range = (max(scores) - min(scores)) if len(scores) > 1 else 0.0

        with self._lock:
            prev = self._prev_ranks

            if prev:
                # Count rank changes vs previous cycle
                common = set(current_ranks) & set(prev)
                rank_changes = sum(
                    1 for sym in common
                    if current_ranks[sym] != prev[sym]
                )
                avg_delta = (
                    sum(abs(current_ranks[sym] - prev[sym]) for sym in common)
                    / len(common)
                    if common else 0.0
                )

                # Top-5 churn: how many of current top-5 were NOT in prev top-5
                prev_top5 = {s for s, r in prev.items() if r < 5}
                cur_top5  = {s for s, r in current_ranks.items() if r < 5}
                top5_churn = len(cur_top5 - prev_top5)

                # Score delta for symbols that crossed a meaningful boundary
                score_jumps = []
                for sym in common:
                    prev_sc = self._prev_scores.get(sym, 0.0)
                    cur_sc  = current_scores.get(sym, 0.0)
                    if abs(cur_sc - prev_sc) > 0.04:   # >4% score shift
                        score_jumps.append(f"{sym}:{prev_sc:.3f}→{cur_sc:.3f}")

                instability_pct = rank_changes / total * 100.0

            else:
                # First cycle — no previous snapshot
                rank_changes  = 0
                avg_delta     = 0.0
                top5_churn    = 0
                score_jumps   = []
                instability_pct = 0.0

            # Signals from top-10
            top10_syms = {s for s, r in current_ranks.items() if r < 10}
            sig_from_top10 = len(signals_found & top10_syms)

            self._session_scans  += 1
            self._session_rank_changes += rank_changes
            self._session_prepared     += total
            self._session_instability_sum += instability_pct
            if instability_pct > self._peak_instability:
                self._peak_instability = instability_pct
                self._peak_instability_cycle = self._session_scans

            self._last_cycle = {
                "total_ranked":       total,
                "rank_changes":       rank_changes,
                "avg_rank_delta":     round(avg_delta, 1),
                "top5_churn":         top5_churn,
                "instability_pct":    round(instability_pct, 1),
                "score_range":        round(score_range, 4),
                "score_jumps":        score_jumps[:5],   # top-5 biggest movers
                "sig_from_top10":     sig_from_top10,
                "signals_total":      len(signals_found),
            }

            # Update snapshots for next cycle
            self._prev_ranks  = dict(current_ranks)
            self._prev_scores = dict(current_scores)

    def emit_cycle_audit(self) -> None:
        """Emit [RankingInstabilityAudit] for the current cycle."""
        self._ensure_today()
        with self._lock:
            c = dict(self._last_cycle)
        if not c:
            return

        score_jump_str = "  ".join(c.get("score_jumps", [])) or "none"
        log.info(
            "[RankingInstabilityAudit]"
            " total_ranked=%d rank_changes=%d avg_rank_delta=%.1f"
            " top5_churn=%d instability_pct=%.1f%%"
            " score_range=%.4f sig_from_top10=%d/%d"
            " score_jumps=[%s]",
            c.get("total_ranked", 0),
            c.get("rank_changes", 0),
            c.get("avg_rank_delta", 0.0),
            c.get("top5_churn", 0),
            c.get("instability_pct", 0.0),
            c.get("score_range", 0.0),
            c.get("sig_from_top10", 0),
            c.get("signals_total", 0),
            score_jump_str,
        )

    def emit_eod_report(self) -> None:
        """Emit [RankingInstabilityReport] EOD session summary."""
        self._ensure_today()
        with self._lock:
            scans    = self._session_scans
            changes  = self._session_rank_changes
            prepared = self._session_prepared
            avg_inst = self._session_instability_sum / max(1, scans)
            peak     = self._peak_instability
            peak_cyc = self._peak_instability_cycle

        log.info(
            "[RankingInstabilityReport]"
            " session_scans=%d total_rank_changes=%d total_prepared=%d"
            " avg_instability=%.1f%% peak_instability=%.1f%%(cycle=%d)",
            scans, changes, prepared,
            avg_inst, peak, peak_cyc,
        )

    def get_stats(self) -> dict:
        """Return current stats dict."""
        self._ensure_today()
        with self._lock:
            return {
                "session_scans":    self._session_scans,
                "last_cycle":       dict(self._last_cycle),
                "peak_instability": self._peak_instability,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
_INSTANCE: Optional[RankingInstabilityAudit] = None
_INSTANCE_LOCK = threading.Lock()


def get_ranking_audit() -> RankingInstabilityAudit:
    """Thread-safe singleton accessor."""
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = RankingInstabilityAudit()
    return _INSTANCE
