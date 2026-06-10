"""
PREPARED_UNIVERSE_V2.5 — Priority 5: LifecycleTransitionAudit
==============================================================

Tracks candidate lifecycle state transitions between consecutive scan cycles.

Emits:
  [LifecycleTransitionAudit]  — per scan cycle (observational, never blocks execution)
  [LifecycleTransitionReport] — EOD summary

What it measures:
  transitions       — dict of (from_state→to_state) pair counts this cycle
  unchanged         — candidates whose lifecycle state did not change
  stuck_invalidated — symbols in INVALIDATED state for 3+ consecutive cycles
  stuck_expired     — symbols in EXPIRED state for 3+ consecutive cycles
  new_invalidated   — symbols that freshly entered INVALIDATED this cycle
  new_expired       — symbols that freshly entered EXPIRED this cycle

Valid states: FRESH, ACTIVE, WEAKENING, REACTIVATED, INVALIDATED, EXPIRED, UNKNOWN
Priority order in compute_lifecycle_state():
  EXPIRED → INVALIDATED → REACTIVATED → WEAKENING → FRESH/ACTIVE

Thread-safe; auto-resets at midnight UTC.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Set

log = logging.getLogger(__name__)

# ── Module-level singleton ────────────────────────────────────────────────────
_AUDIT_LOCK     = threading.Lock()
_AUDIT_INSTANCE: "LifecycleTransitionAudit | None" = None


def get_lifecycle_audit() -> "LifecycleTransitionAudit":
    """Return the session-scoped singleton (thread-safe, lazily created)."""
    global _AUDIT_INSTANCE
    if _AUDIT_INSTANCE is None:
        with _AUDIT_LOCK:
            if _AUDIT_INSTANCE is None:
                _AUDIT_INSTANCE = LifecycleTransitionAudit()
    return _AUDIT_INSTANCE


# ── Stuck threshold (consecutive cycles before flagging) ────────────────────
_STUCK_THRESHOLD = 3    # 3+ cycles in terminal state → flagged


class LifecycleTransitionAudit:
    """
    Session-scoped lifecycle transition tracker.

    Usage:
        audit = get_lifecycle_audit()
        audit.record_cycle(before_states, after_states)
        audit.emit_cycle_audit()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_day = datetime.now(timezone.utc).date()

        # Previous cycle's lifecycle state per symbol (for diff)
        self._prev_states: Dict[str, str] = {}

        # Consecutive-cycle counters for terminal states (INVALIDATED, EXPIRED)
        self._stuck_cycles: Dict[str, int] = defaultdict(int)

        # Session-wide transition accumulator
        self._session_transitions: Dict[str, int] = defaultdict(int)
        self._session_cycles       = 0
        self._session_total_changes = 0
        self._session_new_invalidated = 0
        self._session_new_expired     = 0

        # Last cycle data (for emit)
        self._last: Dict = {}

    # ── Midnight reset ───────────────────────────────────────────────────────
    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._reset_day:
            self._prev_states.clear()
            self._stuck_cycles.clear()
            self._session_transitions.clear()
            self._session_cycles            = 0
            self._session_total_changes     = 0
            self._session_new_invalidated   = 0
            self._session_new_expired       = 0
            self._last                      = {}
            self._reset_day                 = today

    # ── Core API ─────────────────────────────────────────────────────────────
    def record_cycle(
        self,
        before_states: Dict[str, str],
        after_states:  Dict[str, str],
    ) -> None:
        """
        Record one scan-cycle of lifecycle state changes.

        Args:
            before_states:  {symbol: lifecycle_state} as read FROM the store at
                            scan start (Step 1 baseline).
            after_states:   {symbol: lifecycle_state} as computed during scan
                            (after Step 2 scan override + Step 3 invalidation).
        """
        with self._lock:
            self._maybe_reset()

            transitions: Dict[str, int] = defaultdict(int)
            unchanged     = 0
            new_invalid: Set[str] = set()
            new_expired:  Set[str] = set()

            all_symbols = set(before_states) | set(after_states)

            for sym in all_symbols:
                state_before = before_states.get(sym, "UNKNOWN")
                state_after  = after_states.get(sym, "UNKNOWN")

                if state_before == state_after:
                    unchanged += 1
                else:
                    key = f"{state_before}→{state_after}"
                    transitions[key] += 1
                    self._session_transitions[key] += 1
                    self._session_total_changes += 1

                    if state_after == "INVALIDATED" and state_before != "INVALIDATED":
                        new_invalid.add(sym)
                        self._session_new_invalidated += 1
                    if state_after == "EXPIRED" and state_before != "EXPIRED":
                        new_expired.add(sym)
                        self._session_new_expired += 1

                # Update stuck counters
                if state_after in ("INVALIDATED", "EXPIRED"):
                    self._stuck_cycles[sym] += 1
                else:
                    self._stuck_cycles[sym] = 0

            # Count stuck symbols
            stuck_invalid = [
                s for s, n in self._stuck_cycles.items()
                if n >= _STUCK_THRESHOLD
                and after_states.get(s) == "INVALIDATED"
            ]
            stuck_expired = [
                s for s, n in self._stuck_cycles.items()
                if n >= _STUCK_THRESHOLD
                and after_states.get(s) == "EXPIRED"
            ]

            self._session_cycles += 1
            self._prev_states = dict(after_states)

            self._last = {
                "total":            len(all_symbols),
                "unchanged":        unchanged,
                "transitions":      dict(transitions),
                "new_invalidated":  sorted(new_invalid),
                "new_expired":      sorted(new_expired),
                "stuck_invalidated": sorted(stuck_invalid),
                "stuck_expired":    sorted(stuck_expired),
            }

    def emit_cycle_audit(self) -> None:
        """Emit [LifecycleTransitionAudit] for the most recent cycle."""
        with self._lock:
            d = self._last
            if not d:
                return

            trans_str = "none"
            if d["transitions"]:
                # Sort by count descending for readability
                parts = sorted(d["transitions"].items(), key=lambda x: -x[1])
                trans_str = "  ".join(f"{k}:{v}" for k, v in parts)

            stuck_inv_str = (
                ",".join(d["stuck_invalidated"])
                if d["stuck_invalidated"] else "none"
            )
            stuck_exp_str = (
                ",".join(d["stuck_expired"])
                if d["stuck_expired"] else "none"
            )

            log.info(
                "[LifecycleTransitionAudit] total=%d unchanged=%d transitions=%d | %s"
                " | new_invalidated=%d new_expired=%d"
                " | stuck_invalidated=%d(%s) stuck_expired=%d(%s)",
                d["total"],
                d["unchanged"],
                sum(d["transitions"].values()),
                trans_str,
                len(d["new_invalidated"]),
                len(d["new_expired"]),
                len(d["stuck_invalidated"]),
                stuck_inv_str,
                len(d["stuck_expired"]),
                stuck_exp_str,
            )

    def emit_eod_report(self) -> None:
        """Emit [LifecycleTransitionReport] EOD summary."""
        with self._lock:
            if self._session_cycles == 0:
                return

            top_trans = sorted(
                self._session_transitions.items(), key=lambda x: -x[1]
            )[:5]
            top_str = "  ".join(f"{k}:{v}" for k, v in top_trans) or "none"

            log.info(
                "[LifecycleTransitionReport] session_cycles=%d"
                " total_changes=%d new_invalidated=%d new_expired=%d"
                " | top_transitions: %s"
                " | stuck_invalidated_now=%d stuck_expired_now=%d",
                self._session_cycles,
                self._session_total_changes,
                self._session_new_invalidated,
                self._session_new_expired,
                top_str,
                len([s for s, n in self._stuck_cycles.items()
                     if n >= _STUCK_THRESHOLD
                     and self._prev_states.get(s) == "INVALIDATED"]),
                len([s for s, n in self._stuck_cycles.items()
                     if n >= _STUCK_THRESHOLD
                     and self._prev_states.get(s) == "EXPIRED"]),
            )

    def get_stats(self) -> dict:
        """Return a snapshot dict (for unit tests and smoke checks)."""
        with self._lock:
            return {
                "last_cycle":       dict(self._last),
                "session_cycles":   self._session_cycles,
                "session_changes":  self._session_total_changes,
            }
