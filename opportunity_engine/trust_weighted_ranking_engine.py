"""
opportunity_engine/trust_weighted_ranking_engine.py
=======================================================
Self-learning module #26 (part 2 of 2): SYNTHESIS + GOVERNANCE for
trust-weighted candidate ranking.

Consumes the persisted multi-day history built by
data_feeds/trust_score_history.py (ACQUISITION) to answer
postponed_improvements.md item #12's proposed composite:

    trust_adjusted_score = score * (TRUST_WEIGHT * data_trust_score
                                     + (1 - TRUST_WEIGHT))

DIFFERENT NATURE THAN THE OTHER SELF-LEARNING MODULES IN THIS SESSION
----------------------------------------------------------------------
#24/#25/#27 validate a P&L OUTCOME hypothesis (does this signal actually
predict better trade results?) via a bootstrap-CI train/OOS scorecard.
Trust score is not a P&L signal -- it is a DATA-QUALITY engineering
integrity signal (was this symbol's feed corrupted today?). The correct
gate here, per postponed_improvements.md's own explicit prerequisites,
is a DATA-READINESS gate (enough persisted multi-day history exists, and
no symbol is a degenerate restart artifact), not a statistical
significance test against a null hypothesis. Applying the identical
bootstrap-CI template here would be a category error -- there is no
"null" for a symbol's own feed corruption count to be tested against.

GATING (fully automatic, zero human step)
-------------------------------------------
  1. MIN_HISTORY_DAYS (5) days of persisted history must exist globally
     before this module ever adjusts any score -- below that, every
     score is returned byte-identical to the raw input.
  2. Per-symbol: a symbol newly seen (fewer than MIN_HISTORY_DAYS of its
     OWN persisted history) is also returned unadjusted -- fairness, a
     symbol first observed yesterday is not penalised for lacking
     history yet.
  3. Degenerate-symbol guard: if a symbol's persisted trust scores over
     the window show ZERO variance and sit below 0.9, this is far more
     likely a restart/measurement artifact (identical value every day)
     than a genuinely, consistently corrupted feed -- treated as neutral
     (1.0) rather than penalised, per postponed_improvements.md's own
     explicit caution ("Confirm no symbols are permanently penalised by
     restart artifacts").

TRUST_WEIGHT is a fixed, conservative constant (0.15, postponed_
improvements.md's own stated starting value) -- not itself evidence
-tuned in this version; the evidence gate here is data-readiness
(gate #1/#2/#3 above), which is the categorically correct gate for a
data-quality signal.

SAFETY CONTRACT
-----------------
  Zero imports of execution_engine, order_manager, broker APIs, or
  risk_control. Never raises -- get_effective_score() falls back to the
  raw, unadjusted score on any error. opportunity_engine/equity_scanner_
  ai.py's only change is wrapping its existing sort key through this
  accessor -- the ranking FORMULA and all other logic is untouched.
"""
from __future__ import annotations

from typing import Any, Dict

from utils import get_logger

log = get_logger(__name__)

MIN_HISTORY_DAYS = 5
TRUST_WEIGHT     = 0.15
DEGENERATE_TRUST_CEILING = 0.9   # flat scores below this over the whole window are suspect


def get_effective_score(symbol: str, raw_score: float, today_trust_score: float = 1.0) -> float:
    """
    Return a trust-weighted score for ranking. Falls back to raw_score
    unchanged whenever the data-readiness gate is not met, or on any
    error. Never raises.
    """
    try:
        from data_feeds.trust_score_history import get_history_days_count, get_records

        if get_history_days_count() < MIN_HISTORY_DAYS:
            return raw_score

        recs = get_records(symbol=symbol)
        by_date: Dict[str, float] = {}
        for r in recs:
            d = r.get("date")
            if d:
                by_date[d] = r.get("trust_score", 1.0)
        if len(by_date) < MIN_HISTORY_DAYS:
            return raw_score

        recent_dates = sorted(by_date.keys())[-MIN_HISTORY_DAYS:]
        scores = [by_date[d] for d in recent_dates]
        multi_day = sum(scores) / len(scores)

        # Degenerate-symbol guard: zero variance + low score looks like a
        # restart/measurement artifact, not a real recurring corruption.
        if len(set(scores)) == 1 and multi_day < DEGENERATE_TRUST_CEILING:
            multi_day = 1.0

        return raw_score * (TRUST_WEIGHT * multi_day + (1 - TRUST_WEIGHT))
    except Exception as exc:
        log.debug("[TrustWeightedRanking] get_effective_score fallback to raw_score: %s", exc)
        return raw_score


def run_daily_snapshot_and_check() -> Dict[str, Any]:
    """
    Self-scheduled, fully automated daily driver: persists today's trust
    snapshot, then returns a status summary. Never raises.
    """
    try:
        from data_feeds.trust_score_history import record_daily_trust_snapshot, get_history_days_count
        snapshot = record_daily_trust_snapshot()
        days = get_history_days_count()
        return {
            "status": "OK",
            "snapshot": snapshot,
            "history_days_count": days,
            "gate_met": days >= MIN_HISTORY_DAYS,
        }
    except Exception as exc:
        log.debug("[TrustWeightedRanking] daily check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def get_status() -> Dict[str, Any]:
    """Read-only accessor (Sandy-style)."""
    try:
        from data_feeds.trust_score_history import get_history_days_count
        days = get_history_days_count()
        return {
            "history_days_count": days,
            "min_history_days": MIN_HISTORY_DAYS,
            "gate_met": days >= MIN_HISTORY_DAYS,
            "trust_weight": TRUST_WEIGHT,
        }
    except Exception as exc:
        log.debug("[TrustWeightedRanking] get_status error: %s", exc)
        return {"history_days_count": 0, "min_history_days": MIN_HISTORY_DAYS, "gate_met": False, "trust_weight": TRUST_WEIGHT}
