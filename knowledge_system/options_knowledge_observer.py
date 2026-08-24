"""
Options Knowledge Observer
===========================

Options-specific knowledge accumulator — completely independent of the equity
KDA (Knowledge-Driven Approval) and KLP (Knowledge Learning Platform) systems.

Knowledge states:
  DEVELOPING  — fewer than MIN_OBS observations OR fewer than MIN_OUTCOMES outcomes.
                The system has not seen enough to form a reliable view.
                knowledge_score is None (explicitly withheld — not zero).
  LEARNING    — ≥ MIN_OBS observations AND ≥ MIN_OUTCOMES outcomes recorded.
                Evidence is accumulating; knowledge_score is computed from win_rate.
  VALIDATED   — ≥ MIN_VALIDATED_OUTCOMES outcomes AND win_rate ≥ MIN_WIN_RATE.
                Evidence is sufficiently consistent to be considered reliable.

Absolute invariants (never violated):
  1. This observer NEVER modifies strategy_lab, risk_control, DecisionEngine,
     OptionsRiskEngine, or any other production-trading module.
  2. A single trade CANNOT transition the system from DEVELOPING to VALIDATED.
     (MIN_OUTCOMES = 5 enforces a minimum evidence base before LEARNING;
      MIN_VALIDATED_OUTCOMES = 20 before VALIDATED.)
  3. knowledge_score is None when state == DEVELOPING.
     Callers must check for None rather than treating 0.0 as "low confidence".
  4. Evidence accumulates in memory. State is recomputed on each observation.
     There is no persistence — this is by design (prevents stale knowledge
     from prior sessions influencing current execution decisions).
  5. This is an observational accumulator, not a decision authority.
     It reports what the data shows — nothing more.

Singleton: get_options_knowledge_observer()
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── Transition thresholds ──────────────────────────────────────────────────
_MIN_OBS           = 10    # observations before leaving DEVELOPING
_MIN_OUTCOMES      = 5     # outcome records before leaving DEVELOPING
_MIN_VALIDATED_OUT = 20    # outcomes needed for VALIDATED
_MIN_WIN_RATE      = 0.50  # minimum win rate for VALIDATED

# ── State labels ───────────────────────────────────────────────────────────
KS_DEVELOPING = "DEVELOPING"
KS_LEARNING   = "LEARNING"
KS_VALIDATED  = "VALIDATED"


class OptionsKnowledgeObserver:
    """
    Accumulates evidence from options opportunity observations.

    Tracks observation counts and P&L outcomes to determine the system's
    current knowledge state. Returns (state, score) for each opportunity.
    Does NOT modify any production parameters — ever.
    """

    def __init__(self) -> None:
        self._lock         = threading.Lock()
        self._obs_count: int        = 0
        self._outcomes:  List[Dict] = []   # {"actual_pnl": float, "expected_pnl": float, "is_win": bool}

    # ── Public API ─────────────────────────────────────────────────────────

    def observe_opportunity(
        self,
        symbol:         str,
        strategy_name:  str,
        market_context: Optional[Dict] = None,
    ) -> Tuple[str, Optional[float]]:
        """
        Record an opportunity observation. Increments the observation counter.

        Args:
            symbol: underlying symbol, e.g. "NIFTY"
            strategy_name: strategy name, e.g. "Iron_Condor_Range"
            market_context: optional dict with vix, regime, iv_rank, etc. (not used
                            for state computation — reserved for future analytics)

        Returns:
            (knowledge_state, knowledge_score)
            knowledge_score is None when state is DEVELOPING.
        """
        with self._lock:
            self._obs_count += 1
            state = self._compute_state_locked()
            score = self._compute_score_locked() if state != KS_DEVELOPING else None

        log.debug(
            "[OptionsKnowledgeObserver] obs=%d  outcomes=%d  state=%s  score=%s",
            self._obs_count, len(self._outcomes), state, score,
        )
        return state, score

    def record_outcome(
        self,
        actual_pnl:   float,
        expected_pnl: float,
    ) -> None:
        """
        Record a realized P&L outcome against the expected P&L.
        Called after a position closes.
        Does NOT modify any production rule or threshold.

        Args:
            actual_pnl:   realized P&L in ₹ (positive = profit, negative = loss)
            expected_pnl: model-estimated P&L at entry time
        """
        with self._lock:
            self._outcomes.append({
                "actual_pnl":   actual_pnl,
                "expected_pnl": expected_pnl,
                "is_win":       actual_pnl > 0.0,
            })

    def get_state(self) -> str:
        """Return the current knowledge state."""
        with self._lock:
            return self._compute_state_locked()

    def get_summary(self) -> Dict:
        """
        Return a diagnostic summary dict.
        Safe for logging and test assertions.
        """
        with self._lock:
            state = self._compute_state_locked()
            score = self._compute_score_locked() if state != KS_DEVELOPING else None
            return {
                "state":           state,
                "obs_count":       self._obs_count,
                "outcome_count":   len(self._outcomes),
                "knowledge_score": score,
                "win_rate":        self._win_rate_locked(),
            }

    # ── Private helpers ────────────────────────────────────────────────────
    # All _locked helpers must be called with self._lock held.

    def _compute_state_locked(self) -> str:
        n_obs = self._obs_count
        n_out = len(self._outcomes)
        if n_obs < _MIN_OBS or n_out < _MIN_OUTCOMES:
            return KS_DEVELOPING
        if n_out >= _MIN_VALIDATED_OUT and self._win_rate_locked() >= _MIN_WIN_RATE:
            return KS_VALIDATED
        return KS_LEARNING

    def _compute_score_locked(self) -> Optional[float]:
        """0.0–1.0 score based on win_rate. Returns None if no outcomes."""
        if not self._outcomes:
            return None
        return round(min(max(self._win_rate_locked(), 0.0), 1.0), 4)

    def _win_rate_locked(self) -> float:
        if not self._outcomes:
            return 0.0
        wins = sum(1 for o in self._outcomes if o.get("is_win", False))
        return wins / len(self._outcomes)


# ── Module-level singleton ─────────────────────────────────────────────────

_KO_INSTANCE: Optional[OptionsKnowledgeObserver] = None
_KO_LOCK      = threading.Lock()


def get_options_knowledge_observer() -> OptionsKnowledgeObserver:
    """Return the process-wide OptionsKnowledgeObserver singleton."""
    global _KO_INSTANCE
    with _KO_LOCK:
        if _KO_INSTANCE is None:
            _KO_INSTANCE = OptionsKnowledgeObserver()
    return _KO_INSTANCE
