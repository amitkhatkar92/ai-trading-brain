"""
Options Outcome Observer
=========================

Post-close outcome recorder for options positions.

Bridges OptionsOrderManager → OptionsObservationJournal + OptionsKnowledgeObserver:
  1. Called after a position closes (status == "closed")
  2. Writes an OUTCOME_OBSERVED entry to the observation journal
  3. Feeds actual P&L data to the knowledge observer (accumulates evidence)

Safety rules:
  1. ONLY called after status == "closed" — never before.
  2. Idempotent: recording the same order_id twice is a no-op.
  3. NEVER modifies OptionsOrderRecord, the trades journal, or any execution-path module.
  4. All failures are silently logged at DEBUG level — must never block execution.
  5. NEVER modifies production parameters (strategy_lab, risk thresholds, etc.).

Singleton: get_options_outcome_observer()
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional, Set

from utils import get_logger

log = get_logger(__name__)


class OptionsOutcomeObserver:
    """
    Post-close outcome recorder for options positions.

    Feeds both the observation journal (OUTCOME_OBSERVED state) and the
    knowledge observer (P&L evidence for win-rate tracking).
    """

    def __init__(self) -> None:
        self._lock           = threading.Lock()
        self._recorded: Set[str] = set()   # order_ids already observed (idempotency)

    # ── Public API ─────────────────────────────────────────────────────────

    def record_outcome(self, rec) -> None:
        """
        Record the outcome of a closed options position.

        Args:
            rec: OptionsOrderRecord — must have status == "closed".
                 Accepts any duck-typed object with the required attributes.
        """
        try:
            if getattr(rec, "status", "") != "closed":
                log.debug(
                    "[OptionsOutcomeObserver] Skipping %s — not closed (status=%s).",
                    getattr(rec, "order_id", "?"), getattr(rec, "status", "?"),
                )
                return

            order_id = getattr(rec, "order_id", None)
            if not order_id:
                return

            with self._lock:
                if order_id in self._recorded:
                    return   # idempotent
                self._recorded.add(order_id)

            self._do_record(rec)

        except Exception as exc:
            log.debug(
                "[OptionsOutcomeObserver] Outcome recording failed for %s: %s",
                getattr(rec, "order_id", "?"), exc,
            )

    # ── Internal ───────────────────────────────────────────────────────────

    def _do_record(self, rec) -> None:
        """Write OUTCOME_OBSERVED to journal and feed knowledge observer + research pipeline."""
        from execution_engine.options_observation_journal import (
            get_options_observation_journal,
            OptionsOpportunityObservation,
            OBS_OUTCOME_OBSERVED,
        )
        from knowledge_system.options_knowledge_observer import (
            get_options_knowledge_observer,
        )

        obs_journal = get_options_observation_journal()
        ko          = get_options_knowledge_observer()

        # Compute hold days
        hold_days: Optional[int] = None
        try:
            placed_at = getattr(rec, "placed_at", None)
            closed_at = getattr(rec, "closed_at", None)
            if placed_at and closed_at:
                hold_days = max((closed_at.date() - placed_at.date()).days, 0)
        except Exception:
            pass

        actual_pnl   = getattr(rec, "pnl_rs", None)
        expected_pnl = getattr(rec, "expected_pnl", None)

        # Extract opportunity_id from knowledge_provenance (attached at execution time)
        opportunity_id = None
        try:
            kprov = getattr(rec, "knowledge_provenance", None) or {}
            opportunity_id = kprov.get("opportunity_id")
        except Exception:
            pass

        # Write OUTCOME_OBSERVED entry to observation journal
        obs = OptionsOpportunityObservation(
            obs_id        = obs_journal.make_obs_id(
                getattr(rec, "symbol", ""),
                getattr(rec, "strategy", ""),
            ),
            symbol        = getattr(rec, "symbol", ""),
            strategy_name = getattr(rec, "strategy", ""),
            observed_at   = datetime.now().isoformat(),
            state         = OBS_OUTCOME_OBSERVED,

            # Lifecycle identity
            opportunity_id = opportunity_id,

            # Signal context preserved from execution record
            direction     = getattr(rec, "direction", ""),
            dte           = getattr(rec, "dte_at_entry", 0),
            iv_rank       = getattr(rec, "iv_rank_at_entry", 0.0),
            regime        = getattr(rec, "regime_at_entry", ""),

            # Execution linkage
            order_id      = getattr(rec, "order_id", None),

            # Outcome fields
            actual_pnl           = actual_pnl,
            expected_pnl         = expected_pnl,
            actual_exit_price    = getattr(rec, "actual_exit_fill_price", None),
            actual_entry_price   = getattr(rec, "actual_entry_fill_price", None),
            expected_entry_price = getattr(rec, "expected_entry_price", 0.0),
            hold_days            = hold_days,
            exit_reason          = getattr(rec, "exit_reason", None),
            outcome_correctness  = getattr(rec, "outcome_correctness", None),

            # Knowledge state at close time (before feeding this outcome)
            knowledge_state = ko.get_state(),
        )
        obs_journal.record(obs)

        # Feed knowledge observer with P&L evidence
        if actual_pnl is not None and expected_pnl is not None:
            ko.record_outcome(
                actual_pnl   = float(actual_pnl),
                expected_pnl = float(expected_pnl),
            )

        # Trigger the research pipeline to process this new outcome immediately
        try:
            from knowledge_system.options_research_pipeline import (
                get_options_research_pipeline,
            )
            get_options_research_pipeline().trigger_now()
        except Exception:
            pass

        # Update shadow scorer with outcome
        try:
            from learning_system.options_shadow_scorer import get_options_shadow_scorer
            if opportunity_id and actual_pnl is not None:
                get_options_shadow_scorer().record_outcome(opportunity_id, float(actual_pnl))
        except Exception:
            pass

        log.info(
            "[OptionsOutcomeObserver] Outcome recorded: %s  P&L=₹%.0f  "
            "hold_days=%s  knowledge_state=%s  opportunity_id=%s",
            getattr(rec, "order_id", "?"),
            float(actual_pnl) if actual_pnl is not None else 0.0,
            hold_days,
            ko.get_state(),
            opportunity_id or "None",
        )


# ── Module-level singleton ─────────────────────────────────────────────────

_OO_INSTANCE: Optional[OptionsOutcomeObserver] = None
_OO_LOCK      = threading.Lock()


def get_options_outcome_observer() -> OptionsOutcomeObserver:
    """Return the process-wide OptionsOutcomeObserver singleton."""
    global _OO_INSTANCE
    with _OO_LOCK:
        if _OO_INSTANCE is None:
            _OO_INSTANCE = OptionsOutcomeObserver()
    return _OO_INSTANCE
