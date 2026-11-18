"""
oios/engine/decision_logger.py

MAS_v1.2 Table 7 (decision_log): every decision per cycle per opportunity, so PASS
decisions exist as counterfactual data. The table and repository.log_decision() existed
but nothing wrote to them, so the table stayed empty and PHASE_C_ACCEPTANCE C5 could
never be met. Later prices and the counterfactual class are filled by the existing
counterfactual_engine.run_nightly_retroactive_job().

Pure observation: reads the opportunity after the ELE cycle and appends one row.
It never changes state, scores or transitions.
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from typing import Optional

from ..db import repository as R
from ..domain.models import DecisionLogEntry, InvalidationReason, OpportunityState

log = logging.getLogger(__name__)

_ACTION_BY_INVALIDATION = {
    InvalidationReason.TTL_EXHAUSTED:  "INVALID_TTL",
    InvalidationReason.EC_EXHAUSTED:   "INVALID_EC",
    InvalidationReason.THESIS_INVALID: "INVALID_VOLUME_BURST",
    InvalidationReason.ZOMBIE_CAP:     "INVALID_ZOMBIE",
    InvalidationReason.CONTRADICTED:   "INVALID_CONTRADICTED",
    InvalidationReason.NEVER_MATURED:  "INVALID_NEVER_MATURED",
}


def decision_for(state: str, invalidation_reason: Optional[str], re_score: Optional[float],
                 re_threshold: float) -> tuple[str, Optional[str]]:
    """Map an opportunity's post-cycle state to (action, suppression_reason)."""
    if state == OpportunityState.INVALID:
        reason = invalidation_reason or "UNKNOWN"
        return _ACTION_BY_INVALIDATION.get(reason, "INVALID_" + reason), reason
    if state == OpportunityState.ACTIVE:
        return "ENTER", None
    if state == OpportunityState.WATCHING:
        if re_score is not None and re_score < re_threshold:
            return "PASS_RE_LOW", f"RE {re_score:.2f} below {re_threshold:.2f}"
        return "PASS_WATCHING", "WATCHING"
    return "PASS_WATCHING", "DISCOVERED_AWAITING_ACTIVATION"


def _price_at(conn: sqlite3.Connection, symbol: str, today: str) -> Optional[float]:
    row = conn.execute(
        "SELECT close FROM ohlcv_daily WHERE symbol = ? AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT 1", (symbol, today)).fetchone()
    return float(row[0]) if row and row[0] else None


def log_cycle_decision(conn: sqlite3.Connection, opportunity_id: str, today: str,
                       regime: str, re_threshold: float) -> bool:
    """Append today's decision for one opportunity. Idempotent per (opportunity, day)."""
    opp = R.get_opportunity(conn, opportunity_id)
    if opp is None:
        return False
    decision_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"oios-decision|{opportunity_id}|{today}"))
    if conn.execute("SELECT 1 FROM decision_log WHERE decision_id = ?", (decision_id,)).fetchone():
        return False
    price = _price_at(conn, opp.symbol, today)
    if price is None:
        return False            # price_at_decision is mandatory (C5); no price, no row
    action, reason = decision_for(opp.current_state, opp.invalidation_reason, opp.re_score, re_threshold)
    R.log_decision(conn, DecisionLogEntry(
        decision_id=decision_id, opportunity_id=opportunity_id, symbol=opp.symbol,
        decided_at=f"{today}T16:45:00", action=action, price_at_decision=price,
        signal_id=opp.first_signal_id, conviction_score=opp.conviction_score, re_score=opp.re_score,
        re_threshold_applied=re_threshold, suppression_reason=reason,
        signal_age_trading_days=opp.age_trading_days, regime=regime,
        theme_phase=opp.theme_phase_at_birth, edge_consumed_pct=opp.edge_consumed_pct,
        maturity_combined=opp.maturity_combined,
        position_size_pct_at_decision=opp.position_size_pct,
    ))
    return True
