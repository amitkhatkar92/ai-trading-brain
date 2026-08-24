"""
Options Opportunity Registry
=============================

Single source of truth for opportunity identity across the full lifecycle.

Every discovered options opportunity receives one `opportunity_id` at the
moment of discovery.  ALL subsequent observations — shortlisted, rejected,
executed, outcome, counterfactual — reference that same ID.

This solves the Phase 3 / audit finding where each lifecycle state generated
a new unrelated obs_id, making it impossible to reconstruct:

    What did the system know → what did it decide → why → what happened?

Persistence: data/options_opportunity_registry.jsonl (append-only)
Singleton: get_options_opportunity_registry()
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_REGISTRY_PATH = "data/options_opportunity_registry.jsonl"

# Lifecycle states (ordered)
OPP_DISCOVERED                = "DISCOVERED"
OPP_CONTEXT_ENRICHED          = "CONTEXT_ENRICHED"
OPP_SHORTLISTED               = "SHORTLISTED"
OPP_QUALITY_REJECTED          = "QUALITY_REJECTED"
OPP_RISK_APPROVED             = "RISK_APPROVED"
OPP_RISK_REJECTED             = "RISK_REJECTED"
OPP_EXECUTED                  = "EXECUTED"
OPP_NOT_EXECUTED              = "NOT_EXECUTED"
OPP_OPEN                      = "OPEN"
OPP_EXIT                      = "EXIT"
OPP_OUTCOME_OBSERVED          = "OUTCOME_OBSERVED"
OPP_COUNTERFACTUAL_MONITORING = "COUNTERFACTUAL_MONITORING"
OPP_COUNTERFACTUAL_OUTCOME    = "COUNTERFACTUAL_OUTCOME"
OPP_REJECTION_CORRECT         = "REJECTION_CORRECT"
OPP_REJECTION_INCORRECT       = "REJECTION_INCORRECT"
OPP_MISSED_OPPORTUNITY        = "MISSED_OPPORTUNITY"

_ALL_STATES = frozenset({
    OPP_DISCOVERED, OPP_CONTEXT_ENRICHED, OPP_SHORTLISTED,
    OPP_QUALITY_REJECTED, OPP_RISK_APPROVED, OPP_RISK_REJECTED,
    OPP_EXECUTED, OPP_NOT_EXECUTED, OPP_OPEN, OPP_EXIT,
    OPP_OUTCOME_OBSERVED, OPP_COUNTERFACTUAL_MONITORING,
    OPP_COUNTERFACTUAL_OUTCOME, OPP_REJECTION_CORRECT,
    OPP_REJECTION_INCORRECT, OPP_MISSED_OPPORTUNITY,
})


class OptionsOpportunityRegistry:
    """
    Generates and tracks `opportunity_id` across the complete lifecycle.

    Thread-safe.  All state transitions are appended to a JSONL log so that
    the full history of every opportunity survives restarts.
    """

    def __init__(self) -> None:
        self._lock   = threading.Lock()
        self._seq    = 0
        self._states: Dict[str, str] = {}  # opportunity_id → current state
        os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
        self._reload_from_disk()

    # ── Public API ─────────────────────────────────────────────────────────

    def new_opportunity_id(self, symbol: str) -> str:
        """
        Create a new opportunity_id for a freshly discovered opportunity.
        Must be called at the DISCOVERED state before any other observation.

        Format: OPT-{YYYYMMDD}-{HHMMSS}-{SEQ:06d}-{SYMBOL}
        """
        with self._lock:
            self._seq += 1
            seq = self._seq
        dt  = datetime.now()
        oid = (f"OPT-{dt.strftime('%Y%m%d')}-{dt.strftime('%H%M%S')}"
               f"-{seq:06d}-{symbol.upper()[:12]}")
        self._transition(oid, OPP_DISCOVERED)
        return oid

    def transition(self, opportunity_id: str, new_state: str,
                   metadata: Optional[dict] = None) -> None:
        """Record a state transition for an existing opportunity_id."""
        if new_state not in _ALL_STATES:
            log.warning(
                "[OpportunityRegistry] Unknown state '%s' for %s",
                new_state, opportunity_id,
            )
            return
        self._transition(opportunity_id, new_state, metadata)

    def current_state(self, opportunity_id: str) -> Optional[str]:
        """Return the most recent state for an opportunity_id."""
        with self._lock:
            return self._states.get(opportunity_id)

    def is_known(self, opportunity_id: str) -> bool:
        with self._lock:
            return opportunity_id in self._states

    def get_all_in_state(self, state: str) -> List[str]:
        """Return all opportunity_ids currently in the given state."""
        with self._lock:
            return [oid for oid, s in self._states.items() if s == state]

    # ── Private ────────────────────────────────────────────────────────────

    def _transition(self, opportunity_id: str, state: str,
                    metadata: Optional[dict] = None) -> None:
        with self._lock:
            self._states[opportunity_id] = state
        record = {
            "opportunity_id": opportunity_id,
            "state":          state,
            "ts":             datetime.now().isoformat(),
        }
        if metadata:
            record["metadata"] = metadata
        try:
            with open(_REGISTRY_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception as exc:
            log.debug("[OpportunityRegistry] Write failed: %s", exc)

    def _reload_from_disk(self) -> None:
        """Restore in-memory state from the persisted registry log."""
        if not os.path.exists(_REGISTRY_PATH):
            return
        try:
            with open(_REGISTRY_PATH, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        oid   = rec.get("opportunity_id", "")
                        state = rec.get("state", "")
                        if oid and state:
                            self._states[oid] = state
                    except Exception:
                        pass
            if self._states:
                log.info(
                    "[OpportunityRegistry] Restored %d opportunity records.",
                    len(self._states),
                )
        except Exception as exc:
            log.debug("[OpportunityRegistry] Reload failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────

_REGISTRY_INSTANCE: Optional[OptionsOpportunityRegistry] = None
_REGISTRY_LOCK      = threading.Lock()


def get_options_opportunity_registry() -> OptionsOpportunityRegistry:
    """Return the process-wide OptionsOpportunityRegistry singleton."""
    global _REGISTRY_INSTANCE
    with _REGISTRY_LOCK:
        if _REGISTRY_INSTANCE is None:
            _REGISTRY_INSTANCE = OptionsOpportunityRegistry()
    return _REGISTRY_INSTANCE
