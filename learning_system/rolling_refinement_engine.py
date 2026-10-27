"""
learning_system/rolling_refinement_engine.py
================================================
DTA-UNIVERSAL-ROLLING-REFINEMENT-001

Shared, reusable primitives implementing the two self-improvement design
principles agreed with the user (2026-10-27):

  1. MATURITY-STAGED REQUIREMENTS -- a module's "how much evidence do I
     need before I trust a finding" bar should not be one fixed number
     forever. A young, low-volume system cannot honestly meet the same
     bar as a mature one on day 1 -- demanding it just means "never."
     Start lenient, get stricter as the system accumulates real
     operating history (not evidence volume -- *calendar time actually
     running live*, since that is what was found to compound slowly).
     get_staged_requirement() implements this: EARLY (lenient, today's
     already-recalibrated floor) -> MID (~2.5 months in) -> MATURE
     (~6 months in).

  2. ROLLING INCREMENTAL REFINEMENT -- instead of one single all-or-
     nothing checkpoint that can leave a module running on zero
     accumulated knowledge for months (confirmed real: RSL-001's one
     surviving shadow candidate has been unresolved 21+ days), use
     whatever evidence exists AT EVERY weekly checkpoint, and apply a
     SMALL, BOUNDED, CONFIDENCE-SCALED nudge every time -- never "blank
     mode." compute_confidence_scaled_delta() + is_checkpoint_due()
     implement this.

Every function here is a pure, stateless primitive (or operates on a
small state dict a caller persists itself) -- this module holds no
state of its own and makes no live-trading decisions. Each self-learning
module remains the one deciding WHAT evidence/effect to feed in and
WHAT to do with the returned nudge/requirement; this module only
supplies the shared, tested MATH so every module computes it the same,
safe way instead of each reinventing bespoke logic.

Anchor date for maturity staging: SYSTEM_LIVE_TRADING_START = 2026-09-14
(the deliberate operator decision to go live, per .github/copilot-
instructions.md). All "how mature is the system" calculations measure
real calendar days since this date, not evidence-volume counts -- this
was the user's explicit framing ("after 2-3 months... after 6 months").
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

SYSTEM_LIVE_TRADING_START = "2026-09-14"

# Maturity-stage boundaries, in real calendar days since go-live.
MID_STAGE_THRESHOLD_DAYS    = 75    # ~2.5 months
MATURE_STAGE_THRESHOLD_DAYS = 180   # ~6 months

# Default weekly refinement cadence.
DEFAULT_CHECKPOINT_PERIOD_DAYS = 7


def _today(now: Optional[date] = None) -> date:
    return now or date.today()


def days_since_live_start(now: Optional[date] = None,
                           system_start_date: str = SYSTEM_LIVE_TRADING_START) -> int:
    start = date.fromisoformat(system_start_date)
    return max(0, (_today(now) - start).days)


def get_maturity_stage(now: Optional[date] = None,
                        system_start_date: str = SYSTEM_LIVE_TRADING_START) -> str:
    """Returns "EARLY" | "MID" | "MATURE" based on real elapsed live-trading days."""
    elapsed = days_since_live_start(now, system_start_date)
    if elapsed >= MATURE_STAGE_THRESHOLD_DAYS:
        return "MATURE"
    if elapsed >= MID_STAGE_THRESHOLD_DAYS:
        return "MID"
    return "EARLY"


def get_staged_requirement(
    early: int,
    mid: int,
    mature: int,
    now: Optional[date] = None,
    system_start_date: str = SYSTEM_LIVE_TRADING_START,
) -> int:
    """
    Returns the EFFECTIVE requirement (sample count, days, whatever unit
    the caller uses) for today, given the module's own 3 stage values.
    `early` should be the already-recalibrated lenient floor a module
    uses today; `mid`/`mature` are the stricter values to grow into as
    the system accumulates real operating history. Monotonic by
    convention (early <= mid <= mature) but not enforced -- callers
    choose their own numbers.
    """
    stage = get_maturity_stage(now, system_start_date)
    if stage == "MATURE":
        return mature
    if stage == "MID":
        return mid
    return early


def compute_confidence_scaled_delta(
    n: int,
    effect: float,
    max_delta: float,
    full_confidence_n: int = 100,
    min_n_for_any_effect: int = 1,
) -> float:
    """
    Returns a bounded nudge in [-max_delta, +max_delta], scaled by how
    much real evidence exists. `effect` is expected pre-normalized to
    roughly [-1, 1] (e.g. a win-rate delta vs 0.5, or a signed z-score
    clipped to [-1, 1] by the caller) -- this function clips it
    defensively either way. With few samples the nudge is small no
    matter how large `effect` claims to be; it only reaches the full
    `max_delta` range once `n >= full_confidence_n`. Never raises for
    non-finite/garbage input -- returns 0.0 on any computation error.
    """
    try:
        if n < min_n_for_any_effect or full_confidence_n <= 0:
            return 0.0
        confidence = min(1.0, max(0.0, n / full_confidence_n))
        bounded_effect = max(-1.0, min(1.0, float(effect)))
        return round(bounded_effect * float(max_delta) * confidence, 6)
    except Exception:
        return 0.0


def is_checkpoint_due(
    last_checkpoint_at: Optional[str],
    now: Optional[datetime] = None,
    period_days: int = DEFAULT_CHECKPOINT_PERIOD_DAYS,
) -> bool:
    """
    True if a rolling refinement checkpoint is due: either none has ever
    run (`last_checkpoint_at` is None/empty -- always due immediately,
    so a brand-new module never starts in "blank mode"), or at least
    `period_days` have elapsed since the last one. Never raises --
    malformed `last_checkpoint_at` is treated as "due" (fail toward
    making progress, not toward silently never refining again).
    """
    if not last_checkpoint_at:
        return True
    try:
        last = datetime.fromisoformat(last_checkpoint_at)
        current = now if now is not None else datetime.now(last.tzinfo)
        # Guard against a naive/aware mismatch (different modules in this
        # repo use different clock conventions) -- compare naive either way.
        if (current.tzinfo is None) != (last.tzinfo is None):
            current = current.replace(tzinfo=None)
            last = last.replace(tzinfo=None)
        return (current - last).days >= period_days
    except Exception:
        return True
