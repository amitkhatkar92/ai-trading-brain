"""
FORENSIC REFINEMENT — Priority 6: SimulationCalibrationAudit
=============================================================

Tracks the simulation engine's acceptance behaviour across cycles to detect
threshold calibration drift — when thresholds are so loose that 100% always
pass (no filtering value) or so tight that 0% always pass (over-blocking).

Emits:
  [SimulationCalibrationAudit]  — per cycle (after simulation_engine.run())
  [SimulationCalibrationReport] — EOD summary

What it measures per cycle:
  submitted          — signals entering simulation
  approved           — signals that passed all thresholds
  rejected           — signals blocked
  approval_rate      — approved / submitted  (0.0 when submitted=0)
  rejection_reasons  — dict of reason-prefix → count
  avg_survival_rate  — mean survival_rate across all ResilienceScores
  avg_stability      — mean stability_score
  avg_mc_profit_prob — mean monte_carlo_profit_prob
  avg_overall_score  — mean overall_score() (0–10 composite)

Calibration drift flags:
  consecutive_100pct — cycles where submitted>0 and approval_rate=1.0 (too loose)
  consecutive_0pct   — cycles where submitted>0 and approval_rate=0.0 (too tight)

Thread-safe; auto-resets at midnight UTC.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# ── Module-level singleton ────────────────────────────────────────────────────
_AUDIT_LOCK:     threading.Lock                       = threading.Lock()
_AUDIT_INSTANCE: "Optional[SimulationCalibrationAudit]" = None


def get_simulation_audit() -> "SimulationCalibrationAudit":
    """Return the session-scoped singleton (thread-safe, lazily created)."""
    global _AUDIT_INSTANCE
    if _AUDIT_INSTANCE is None:
        with _AUDIT_LOCK:
            if _AUDIT_INSTANCE is None:
                _AUDIT_INSTANCE = SimulationCalibrationAudit()
    return _AUDIT_INSTANCE


# ── Drift thresholds ─────────────────────────────────────────────────────────
_CONSEC_FULL_PASS_WARN  = 5   # emit WARNING after 5 consecutive 100%-pass cycles
_CONSEC_ZERO_PASS_WARN  = 3   # emit WARNING after 3 consecutive 0%-pass cycles


class SimulationCalibrationAudit:
    """
    Session-scoped simulation calibration tracker.

    Usage:
        from market_simulation.simulation_calibration_audit import get_simulation_audit
        audit = get_simulation_audit()
        audit.record_cycle(sim_result)
        audit.emit_cycle_audit()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_day = datetime.now(timezone.utc).date()

        # Session accumulators
        self._session_cycles            = 0
        self._session_submitted         = 0
        self._session_approved          = 0
        self._session_rejection_reasons: Dict[str, int] = defaultdict(int)

        # Calibration drift counters
        self._consec_full_pass = 0   # cycles where all submitted signals passed
        self._consec_zero_pass = 0   # cycles where no submitted signals passed

        # Last cycle snapshot (for emit)
        self._last: Dict = {}

    # ── Midnight reset ────────────────────────────────────────────────────────
    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._reset_day:
            self._session_cycles            = 0
            self._session_submitted         = 0
            self._session_approved          = 0
            self._session_rejection_reasons = defaultdict(int)
            self._consec_full_pass          = 0
            self._consec_zero_pass          = 0
            self._last                      = {}
            self._reset_day                 = today

    # ── Core API ──────────────────────────────────────────────────────────────
    def record_cycle(self, sim_result: object) -> None:
        """
        Record one simulation cycle.

        Args:
            sim_result: SimulationResult instance from SimulationEngine.run().
                        Accesses: .approved_trades, .rejected_trades, .scores,
                        .total_evaluated, .approval_rate.
        """
        with self._lock:
            self._maybe_reset()

            # Safely extract attributes (avoids hard import dependency)
            submitted: int  = getattr(sim_result, "total_evaluated",   0) or 0
            approved_list   = getattr(sim_result, "approved_trades",    []) or []
            rejected_list   = getattr(sim_result, "rejected_trades",    []) or []
            scores_list     = getattr(sim_result, "scores",             []) or []

            approved  = len(approved_list)
            rejected  = len(rejected_list)
            rate      = approved / submitted if submitted > 0 else 0.0

            # Aggregate rejection reasons (use first ~30 chars as key)
            reason_counts: Dict[str, int] = defaultdict(int)
            for score in scores_list:
                if not getattr(score, "approved", True):
                    reason = str(getattr(score, "rejection_reason", "") or "unknown")
                    # Truncate to the first meaningful clause for grouping
                    key = reason[:50].split(" <")[0].split(" —")[0].strip() or "unknown"
                    reason_counts[key] += 1
                    self._session_rejection_reasons[key] += 1

            # Score distribution averages
            def _mean(vals: List[float]) -> float:
                return round(sum(vals) / len(vals), 4) if vals else 0.0

            survival_rates = [
                getattr(s, "survival_rate", 0.0) for s in scores_list
            ]
            stability_scores = [
                getattr(s, "stability_score", 0.0) for s in scores_list
            ]
            mc_profit_probs = [
                getattr(s, "monte_carlo_profit_prob", 0.0) for s in scores_list
            ]
            # overall_score() is a method on ResilienceScore
            overall_scores = []
            for s in scores_list:
                try:
                    overall_scores.append(s.overall_score())
                except Exception:
                    pass

            # Update calibration drift counters (only when signals were submitted)
            if submitted > 0:
                if rate >= 1.0:
                    self._consec_full_pass += 1
                    self._consec_zero_pass  = 0
                elif rate <= 0.0:
                    self._consec_zero_pass += 1
                    self._consec_full_pass  = 0
                else:
                    self._consec_full_pass  = 0
                    self._consec_zero_pass  = 0

            # Session totals
            self._session_cycles    += 1
            self._session_submitted += submitted
            self._session_approved  += approved

            self._last = {
                "submitted":          submitted,
                "approved":           approved,
                "rejected":           rejected,
                "approval_rate":      round(rate, 4),
                "rejection_reasons":  dict(reason_counts),
                "avg_survival_rate":  _mean(survival_rates),
                "avg_stability":      _mean(stability_scores),
                "avg_mc_profit_prob": _mean(mc_profit_probs),
                "avg_overall_score":  _mean(overall_scores),
                "consec_full_pass":   self._consec_full_pass,
                "consec_zero_pass":   self._consec_zero_pass,
            }

    def emit_cycle_audit(self) -> None:
        """Emit [SimulationCalibrationAudit] for the most recent cycle."""
        with self._lock:
            d = self._last
            if not d:
                return

            reason_str = "none"
            if d["rejection_reasons"]:
                parts = sorted(d["rejection_reasons"].items(), key=lambda x: -x[1])
                reason_str = "  ".join(f"{k}:{v}" for k, v in parts)

            log.info(
                "[SimulationCalibrationAudit] submitted=%d approved=%d rejected=%d"
                " approval_rate=%.0f%%"
                " | avg_survival=%.2f avg_stability=%.2f avg_mc_prob=%.2f"
                " avg_score=%.1f"
                " | rejections: %s"
                " | drift: consec_full=%d consec_zero=%d",
                d["submitted"],
                d["approved"],
                d["rejected"],
                d["approval_rate"] * 100,
                d["avg_survival_rate"],
                d["avg_stability"],
                d["avg_mc_profit_prob"],
                d["avg_overall_score"],
                reason_str,
                d["consec_full_pass"],
                d["consec_zero_pass"],
            )

            # Emit calibration drift warnings
            if d["consec_full_pass"] >= _CONSEC_FULL_PASS_WARN:
                log.warning(
                    "[SimulationCalibrationDrift] 100%% pass rate for %d consecutive"
                    " cycles — thresholds may be too permissive (survival≥%.2f"
                    " stability≥%.2f mc_prob≥%.2f).",
                    d["consec_full_pass"],
                    d["avg_survival_rate"],
                    d["avg_stability"],
                    d["avg_mc_profit_prob"],
                )
            if d["consec_zero_pass"] >= _CONSEC_ZERO_PASS_WARN:
                log.warning(
                    "[SimulationCalibrationDrift] 0%% pass rate for %d consecutive"
                    " cycles — thresholds may be over-blocking"
                    " (avg_survival=%.2f avg_stability=%.2f avg_mc_prob=%.2f).",
                    d["consec_zero_pass"],
                    d["avg_survival_rate"],
                    d["avg_stability"],
                    d["avg_mc_profit_prob"],
                )

    def emit_eod_report(self) -> None:
        """Emit [SimulationCalibrationReport] EOD summary."""
        with self._lock:
            if self._session_cycles == 0:
                return

            session_rate = (
                self._session_approved / self._session_submitted
                if self._session_submitted > 0 else 0.0
            )
            top_reasons = sorted(
                self._session_rejection_reasons.items(), key=lambda x: -x[1]
            )[:5]
            reason_str = "  ".join(f"{k}:{v}" for k, v in top_reasons) or "none"

            log.info(
                "[SimulationCalibrationReport] session_cycles=%d"
                " total_submitted=%d total_approved=%d session_rate=%.0f%%"
                " | top_rejection_reasons: %s",
                self._session_cycles,
                self._session_submitted,
                self._session_approved,
                session_rate * 100,
                reason_str,
            )

    def get_stats(self) -> dict:
        """Return snapshot dict (for unit tests and smoke checks)."""
        with self._lock:
            return {
                "last_cycle":        dict(self._last),
                "session_cycles":    self._session_cycles,
                "session_submitted": self._session_submitted,
                "session_approved":  self._session_approved,
            }
