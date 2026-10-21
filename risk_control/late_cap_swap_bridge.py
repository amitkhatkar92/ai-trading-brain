"""
risk_control/late_cap_swap_bridge.py
=======================================
DTA-LATE-CAP-SWAP-BRIDGE-001

Connects the existing, already-tested, already-live
execution_engine/order_manager.py::_smart_swap_check() swap mechanism to
master_orchestrator.py's LatePositionCap rejection path -- the ONE real
capacity gate that governs live trading today (config.MAX_POSITIONS, a
small capital-tier-scaled number) but was never wired to offer a swap.

Background (verified against real data before building this, not assumed)
---------------------------------------------------------------------------
_smart_swap_check() already has two live call sites inside
OrderManager.execute() -- duplicate-symbol re-entry (FIX1) and this
class's own internal MAX_OPEN_POSITIONS safety-net cap (FIX2, e.g. 15
slots). Neither fires often in practice, because the REAL, binding
capacity limit is DTA-CRE-LATE-CAP-001's _rank_and_split_by_position_cap()
in master_orchestrator.py (config.MAX_POSITIONS, e.g. 5 slots) -- a
Debate/KDA-approved signal capped THERE is simply dropped and never
reaches OrderManager.execute() at all, so it never gets a chance at a
swap. Confirmed live: 41 real MAX_POSITIONS_CAP_FINAL rejections recorded
in rejection_audit.db (all post-Debate/KDA, high-conviction candidates),
zero of which were ever offered a swap -- a real, previously-undiscovered
gap, not a hypothetical one.

Separately found and corrected in the same investigation: the PRE-EXISTING
self-learning module #28 (analysis/capital_reserve_readiness_engine.py)
had measured its "54% false-rejection" readiness evidence against the
WRONG rejection reason (plain "MAX_POSITIONS_CAP", CapitalRiskEngine's
early, pre-Debate/KDA, compute-cost eval-pool cutoff -- not a real
capital constraint at all) instead of the real "MAX_POSITIONS_CAP_FINAL"
population this module actually cares about. See DTA-CAPITAL-RESERVE-
READINESS-REASON-FIX-001 for that correction.

Design: reuses 100% of the existing swap safety logic
----------------------------------------------------------------------
This module does NOT reimplement weakest-position selection or any swap
safety gate -- it only calls OrderManager's own existing
_smart_swap_check() (read-only, decision-only) and, once ACTIVE,
OrderManager's new execute_late_cap_swap() (which internally reuses the
exact same daily rotation throttle and close_position() primitive FIX1/
FIX2 already rely on). This module's only job is the evidence-gated
decision of WHEN to flip this one, previously-unconnected trigger point
from observe-only to live.

Lifecycle (same automatic, no-human-gate pattern as every other
self-learning module in this ecosystem -- explicit user instruction):
  ACTIVE (default, from deploy) -> ROLLED_BACK (auto-paused on live
  degradation, keeps shadow-collecting) -> ACTIVE again (auto-reactivated
  once fresh post-rollback evidence clears the bar) / REJECTED (gave up
  -- failed to re-qualify within the observation window).

DTA-LATE-CAP-SWAP-GO-LIVE-001 (2026-10-21, user-directed reversal): the
original design gated the ENTIRE feature behind 30 resolved SHADOW
samples before any real swap ever happened -- at the real ~1 MAX_
POSITIONS_CAP_FINAL rejection/day observed in production, that would
have taken 3-4 months to even start. Reversed per explicit instruction:
the swap executes live from day one (every real swap evaluated and
confirmed by _smart_swap_check()'s existing, already-tested safety
gates -- nothing novel is risked), and every real swap's own outcome is
recorded and resolved (see is_real_swap on LateCapSwapShadowRecord) to
keep validating/refining the parameters and to drive the automatic
ROLLED_BACK safety net if live performance degrades. MIN_SAMPLES_FOR_
ACTIVATION was lowered from 30 to 10 (the repo-wide "normal" floor,
DTA-REALISTIC-THRESHOLDS-001 precedent) -- it now only governs how fast
a ROLLED_BACK pause can automatically re-qualify back to ACTIVE.

Safety contract: SHADOW mode never touches execution_engine/order_manager
beyond the existing, already-tested _smart_swap_check() (read-only
decision, no side effects) and real OHLCV data (read-only). It never
closes, modifies, or reads a live position until promoted to ACTIVE, and
even then only via execute_late_cap_swap()'s existing, shared safety path.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

ACTOR = "LATE-CAP-SWAP-BRIDGE-001"

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR   = os.path.join(_ROOT, "data", "risk_control", "late_cap_swap")
_RECORDS_PATH = os.path.join(_STORE_DIR, "shadow_records.json")
_STATE_PATH  = os.path.join(_STORE_DIR, "state.json")
_LEDGER_PATH = os.path.join(_STORE_DIR, "ledger.jsonl")

# ── Governance ───────────────────────────────────────────────────────────
# DTA-LATE-CAP-SWAP-GO-LIVE-001 (user-directed reversal, 2026-10-21):
# originally gated the ENTIRE feature behind 30 resolved samples before any
# real swap ever happened -- at ~1 real MAX_POSITIONS_CAP_FINAL rejection/day
# that would have taken 3-4 months to even start collecting usable evidence.
# Reversed per explicit instruction: the swap mechanism goes LIVE immediately
# (see _load_state()'s default == STATUS_ACTIVE below) since it only reuses
# the existing, already-safety-gated _smart_swap_check() logic -- nothing
# novel is being risked. Shadow-style evidence collection now runs ALONGSIDE
# live swapping (every real swap is itself recorded and resolved -- see
# is_real_swap below) purely to keep refining/validating the parameters and
# to drive the automatic ROLLED_BACK safety net if live performance sours.
MIN_SAMPLES_FOR_ACTIVATION  = 10     # lowered from 30 to the repo-wide "normal"
                                      # floor (DTA-REALISTIC-THRESHOLDS-001
                                      # precedent) -- now only governs
                                      # re-promotion after a ROLLED_BACK pause
MIN_HIT_RATE_FOR_ACTIVATION = 0.55   # must show a clear edge, not a coin flip
MAX_OBSERVATION_DAYS        = 30     # lowered from 60, matches RSL-001's own
                                      # provisional give-up window
RESOLUTION_HORIZON_DAYS     = 5      # T+5 follow-through window for the rejected candidate
MAX_RECORD_AGE_DAYS         = 60     # give up waiting for a weak position's real close
MIN_SAMPLES_FOR_ROLLBACK_CHECK = 15
ROLLBACK_HIT_RATE_FLOOR     = 0.45   # post-activation: revert if rolling hit-rate falls below this

STATUS_SHADOW_ACTIVE = "SHADOW_ACTIVE"
STATUS_ACTIVE         = "ACTIVE"
STATUS_REJECTED       = "REJECTED"
STATUS_ROLLED_BACK    = "ROLLED_BACK"


@dataclass
class LateCapSwapShadowRecord:
    swap_id:              str
    created_at:            str
    trade_date:            str
    rejected_symbol:       str
    rejected_strategy:     str
    rejected_direction:    str
    rejected_score:        float
    rejected_entry:        float
    rejected_stop:         float
    rejected_target:       float
    weak_order_id:         str
    weak_symbol:           str
    weak_score:            float
    weak_direction:        str
    weak_entry_price:      float
    weak_quantity:         int
    weak_pnl_if_closed_at_decision: float
    weak_stop_loss:        float = 0.0   # snapshot at swap time, for forward simulation
    weak_target:           float = 0.0
    rejected_hypothetical_pnl: Optional[float] = None
    weak_actual_pnl:       Optional[float] = None
    resolved_at:           str = ""
    classification:        Optional[str] = None   # CORRECT_SWAP | INCORRECT_SWAP
    net_benefit_rs:         Optional[float] = None
    status:                str = "PENDING"         # PENDING | RESOLVED | ABANDONED
    # DTA-LATE-CAP-SWAP-GO-LIVE-001: set True for a REAL executed swap (vs a
    # SHADOW-only hypothetical record). Real swaps resolve the other
    # direction -- weak_actual_pnl is known immediately (the weak leg really
    # closed); admitted_real_pnl / weak_hypothetical_pnl_if_held fill in once
    # the admitted position itself closes and enough days pass.
    is_real_swap:          bool = False
    admitted_symbol:       str = ""
    swap_executed_at:      str = ""    # naive local clock, matches OrderRecord.placed_at
    admitted_order_id:     Optional[str] = None
    admitted_real_pnl:     Optional[float] = None
    weak_hypothetical_pnl_if_held: Optional[float] = None


def _ensure_dir() -> None:
    os.makedirs(_STORE_DIR, exist_ok=True)


def _load_records() -> List[LateCapSwapShadowRecord]:
    _ensure_dir()
    if not os.path.exists(_RECORDS_PATH):
        return []
    try:
        with open(_RECORDS_PATH, encoding="utf-8") as fh:
            raw = json.load(fh)
        return [LateCapSwapShadowRecord(**r) for r in raw]
    except Exception as exc:
        log.warning("[LateCapSwapBridge] records load failed: %s", exc)
        return []


def _save_records(records: List[LateCapSwapShadowRecord]) -> None:
    _ensure_dir()
    try:
        with open(_RECORDS_PATH, "w", encoding="utf-8") as fh:
            json.dump([asdict(r) for r in records], fh, indent=2, default=str)
    except Exception as exc:
        log.warning("[LateCapSwapBridge] records save failed: %s", exc)


def _load_state() -> Dict[str, Any]:
    _ensure_dir()
    if not os.path.exists(_STATE_PATH):
        # DTA-LATE-CAP-SWAP-GO-LIVE-001: starts ACTIVE, not SHADOW_ACTIVE --
        # see module docstring / Governance block above for why.
        return {
            "status": STATUS_ACTIVE,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }
    try:
        with open(_STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        log.warning("[LateCapSwapBridge] state load failed: %s", exc)
        return {
            "status": STATUS_ACTIVE,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }


def _save_state(state: Dict[str, Any]) -> None:
    _ensure_dir()
    try:
        with open(_STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, default=str)
    except Exception as exc:
        log.warning("[LateCapSwapBridge] state save failed: %s", exc)


def _append_ledger(event: Dict[str, Any]) -> None:
    _ensure_dir()
    try:
        event = dict(event)
        event.setdefault("ts", datetime.now(timezone.utc).isoformat())
        event.setdefault("actor", ACTOR)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, default=str) + "\n")
    except Exception as exc:
        log.warning("[LateCapSwapBridge] ledger append failed: %s", exc)


def get_status() -> str:
    return _load_state().get("status", STATUS_ACTIVE)


def get_readiness_status() -> Dict[str, Any]:
    """Read-only accessor (Sandy-compatible)."""
    try:
        state = _load_state()
        records = _load_records()
        resolved = [r for r in records if r.status == "RESOLVED"]
        correct = sum(1 for r in resolved if r.classification == "CORRECT_SWAP")
        return {
            "status": state.get("status", STATUS_ACTIVE),
            "shadow_candidates_total": len(records),
            "resolved": len(resolved),
            "correct_swap_count": correct,
            "hit_rate": round(correct / len(resolved), 3) if resolved else None,
            "min_samples_for_activation": MIN_SAMPLES_FOR_ACTIVATION,
        }
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────
# Stage A — registration (called by the orchestrator at every real
# LatePositionCap rejection)
# ─────────────────────────────────────────────────────────────────────────

def register_late_cap_swap_opportunity(
    order_manager: Any,
    signal: Any,
    decision: Any,
    trade_date: Optional[str] = None,
) -> bool:
    """
    Called for every real LatePositionCap (MAX_POSITIONS_CAP_FINAL)
    rejection. Returns True only if a REAL swap was just executed (the
    caller should then proceed to place `signal`'s order instead of
    rejecting it); False otherwise (SHADOW mode, or ACTIVE but no
    swap candidate existed) -- the caller keeps the existing rejection.

    Never raises -- any internal error fails open to False (no behavior
    change, signal stays rejected).
    """
    try:
        return _register_impl(order_manager, signal, decision, trade_date)
    except Exception as exc:
        log.debug("[LateCapSwapBridge] registration error: %s", exc)
        return False


def _register_impl(order_manager, signal, decision, trade_date) -> bool:
    status = get_status()
    if status in (STATUS_REJECTED,):
        return False   # gave up -- do nothing further

    new_score = float(getattr(decision, "confidence_score", 0.0))
    new_entry = float(getattr(signal, "entry_price", 0.0) or 0.0)
    new_stop  = float(getattr(signal, "stop_loss", 0.0) or 0.0)
    new_target = float(getattr(signal, "target_price", 0.0) or 0.0)

    if status == STATUS_ACTIVE:
        # DTA-LATE-CAP-SWAP-GO-LIVE-001: peek (read-only, deterministic given
        # unchanged state) at the same decision execute_late_cap_swap() will
        # make, so a real-swap evidence record can be built -- the swap
        # mechanism itself still only ever runs through the one, already-
        # tested execute_late_cap_swap()/_smart_swap_check() path; this adds
        # no new swap logic, only post-hoc evidence capture for ongoing
        # refinement and the automatic ROLLED_BACK safety net below.
        swap = order_manager._smart_swap_check(
            signal.symbol, new_score, new_entry=new_entry, new_stop=new_stop, new_target=new_target,
        )
        if not swap:
            return False
        weak_oid, weak_sym, weak_score = swap
        weak_rec = order_manager._orders.get(weak_oid)
        if weak_rec is None:
            return False
        weak_entry_price, weak_direction = weak_rec.entry_price, weak_rec.direction
        weak_quantity, weak_stop_loss, weak_target = (
            weak_rec.quantity, weak_rec.stop_loss, weak_rec.target,
        )

        executed = bool(order_manager.execute_late_cap_swap(
            signal.symbol, new_score, new_entry, new_stop, new_target,
        ))
        if not executed:
            return False

        closed_rec = order_manager._orders.get(weak_oid)
        weak_actual = float(closed_rec.pnl) if closed_rec is not None else None

        record = LateCapSwapShadowRecord(
            swap_id=f"LCSB-{uuid.uuid4().hex[:12]}",
            created_at=datetime.now(timezone.utc).isoformat(),
            trade_date=trade_date or date.today().isoformat(),
            rejected_symbol=signal.symbol,
            rejected_strategy=str(getattr(signal, "strategy_name", "") or ""),
            rejected_direction=str(getattr(signal.direction, "value", signal.direction) or "BUY"),
            rejected_score=new_score, rejected_entry=new_entry,
            rejected_stop=new_stop, rejected_target=new_target,
            weak_order_id=weak_oid, weak_symbol=weak_sym, weak_score=weak_score,
            weak_direction=weak_direction, weak_entry_price=weak_entry_price,
            weak_quantity=weak_quantity, weak_stop_loss=weak_stop_loss, weak_target=weak_target,
            weak_pnl_if_closed_at_decision=round(weak_actual, 2) if weak_actual is not None else 0.0,
            weak_actual_pnl=weak_actual,
            is_real_swap=True,
            admitted_symbol=signal.symbol,
            swap_executed_at=datetime.now().isoformat(),
        )
        records = _load_records()
        records.append(record)
        _save_records(records)
        log.info(
            "[LateCapSwapBridge] REAL SWAP executed: closed %s(score=%.1f, pnl=%.2f) "
            "-> admitted %s(score=%.1f).",
            weak_sym, weak_score, weak_actual or 0.0, signal.symbol, new_score,
        )
        return True

    # SHADOW_ACTIVE / ROLLED_BACK (still observing) -- decision-only, no side effects
    swap = order_manager._smart_swap_check(
        signal.symbol, new_score, new_entry=new_entry, new_stop=new_stop, new_target=new_target,
    )
    if not swap:
        return False
    weak_oid, weak_sym, weak_score = swap

    weak_rec = order_manager._orders.get(weak_oid)
    if weak_rec is None:
        return False

    weak_pos = getattr(order_manager, "_portfolio", None)
    weak_pos = weak_pos.positions.get(weak_sym) if weak_pos else None
    exit_px = (
        weak_pos.ltp if weak_pos and getattr(weak_pos, "has_live_ltp", False) and weak_pos.ltp > 0
        else weak_rec.entry_price
    )
    if weak_rec.direction == "BUY":
        weak_pnl_if_closed = (exit_px - weak_rec.entry_price) * weak_rec.quantity
    else:
        weak_pnl_if_closed = (weak_rec.entry_price - exit_px) * weak_rec.quantity

    record = LateCapSwapShadowRecord(
        swap_id=f"LCSB-{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        trade_date=trade_date or date.today().isoformat(),
        rejected_symbol=signal.symbol,
        rejected_strategy=str(getattr(signal, "strategy_name", "") or ""),
        rejected_direction=str(getattr(signal.direction, "value", signal.direction) or "BUY"),
        rejected_score=new_score,
        rejected_entry=new_entry,
        rejected_stop=new_stop,
        rejected_target=new_target,
        weak_order_id=weak_oid,
        weak_symbol=weak_sym,
        weak_score=weak_score,
        weak_direction=weak_rec.direction,
        weak_entry_price=weak_rec.entry_price,
        weak_quantity=weak_rec.quantity,
        weak_stop_loss=weak_rec.stop_loss,
        weak_target=weak_rec.target,
        weak_pnl_if_closed_at_decision=round(weak_pnl_if_closed, 2),
    )
    records = _load_records()
    records.append(record)
    _save_records(records)
    log.info(
        "[LateCapSwapBridge] SHADOW recorded: would-swap %s(score=%.1f) -> %s(score=%.1f)",
        weak_sym, weak_score, signal.symbol, new_score,
    )
    return False


# ─────────────────────────────────────────────────────────────────────────
# Stage B — resolution (EOD-loop wired)
# ─────────────────────────────────────────────────────────────────────────

def _simulate_candidate_exit(
    symbol: str, trade_date: str, direction: str,
    entry: float, stop: float, target: float, quantity: int,
) -> Optional[float]:
    """Walk T+1..T+5 real closes in order; exit at stop/target if touched,
    else at the T+5 close. Returns hypothetical P&L in rupees, or None if
    no real OHLCV data is available yet."""
    from analysis.rejection_attribution_monitor import _fetch_ohlcv_closes
    closes = _fetch_ohlcv_closes(symbol, trade_date, horizon_days=RESOLUTION_HORIZON_DAYS)
    if not closes:
        return None
    exit_price = closes[-1]
    for px in closes:
        if direction == "BUY":
            if px <= stop:
                exit_price = stop
                break
            if target > 0 and px >= target:
                exit_price = target
                break
        else:
            if px >= stop:
                exit_price = stop
                break
            if target > 0 and px <= target:
                exit_price = target
                break
    if direction == "BUY":
        return (exit_price - entry) * quantity
    return (entry - exit_price) * quantity


def _swap_cost_estimate(symbol: str, quantity: int, price: float) -> float:
    """Conservative round-trip cost estimate for the extra re-entry a swap
    causes (weak position's early exit + the new candidate's own full
    round trip), reusing the existing, already-tested cost model."""
    try:
        from models.transaction_costs import get_cost_model, InstrumentType
        model = get_cost_model()
        breakdown = model.compute(
            symbol=symbol, quantity=quantity, entry_price=price, exit_price=price,
            instrument_type=InstrumentType.EQUITY_INTRADAY,
        )
        return float(breakdown.total_cost) * 2.0   # weak-exit leg + new-candidate round trip
    except Exception:
        return 0.0


def _find_order_by_symbol_after(order_manager: Any, symbol: str, since_iso: str) -> Optional[Any]:
    """Best-effort match: the earliest order for `symbol` placed at/after
    `since_iso` (naive local clock, matching OrderRecord.placed_at's own
    convention). Low-volume-per-symbol-per-day heuristic -- the admitted
    candidate's order is placed by the orchestrator immediately after this
    bridge returns True, so there is normally exactly one match."""
    try:
        since_dt = datetime.fromisoformat(since_iso)
    except Exception:
        return None
    candidates = [
        rec for rec in order_manager._orders.values()
        if rec.symbol == symbol and rec.placed_at is not None and rec.placed_at >= since_dt
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda r: r.placed_at)
    return candidates[0]


def resolve_matured_shadow_records(order_manager: Any, max_items: int = 50) -> Dict[str, Any]:
    """EOD-called. Never raises."""
    try:
        return _resolve_impl(order_manager, max_items)
    except Exception as exc:
        log.debug("[LateCapSwapBridge] resolution error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _resolve_impl(order_manager: Any, max_items: int) -> Dict[str, Any]:
    records = _load_records()
    resolved_now = 0
    abandoned_now = 0
    today = date.today()

    for rec in records:
        if rec.status != "PENDING":
            continue
        if resolved_now + abandoned_now >= max_items:
            break

        age_days = (today - date.fromisoformat(rec.trade_date)).days

        if rec.is_real_swap:
            # Real swap: weak_actual_pnl is already known (captured at swap
            # time). Resolve the admitted candidate's real close, and
            # simulate what the weak leg WOULD have done had it not been
            # swapped out -- the mirror image of the SHADOW resolution math.
            if rec.admitted_real_pnl is None:
                admitted_order = _find_order_by_symbol_after(
                    order_manager, rec.admitted_symbol, rec.swap_executed_at,
                )
                if admitted_order is not None and admitted_order.status == "closed":
                    rec.admitted_order_id = admitted_order.order_id
                    rec.admitted_real_pnl = float(admitted_order.pnl)

            if rec.weak_hypothetical_pnl_if_held is None and age_days >= RESOLUTION_HORIZON_DAYS:
                rec.weak_hypothetical_pnl_if_held = _simulate_candidate_exit(
                    rec.weak_symbol, rec.trade_date, rec.weak_direction,
                    rec.weak_entry_price, rec.weak_stop_loss, rec.weak_target,
                    rec.weak_quantity,
                )

            if rec.admitted_real_pnl is not None and rec.weak_hypothetical_pnl_if_held is not None:
                cost = _swap_cost_estimate(
                    rec.admitted_symbol, rec.weak_quantity, rec.rejected_entry,
                )
                scenario_swap_real = (rec.weak_actual_pnl or 0.0) + rec.admitted_real_pnl - cost
                scenario_no_swap_hypothetical = rec.weak_hypothetical_pnl_if_held
                net_benefit = scenario_swap_real - scenario_no_swap_hypothetical
                rec.net_benefit_rs = round(net_benefit, 2)
                rec.classification = "CORRECT_SWAP" if net_benefit > 0 else "INCORRECT_SWAP"
                rec.status = "RESOLVED"
                rec.resolved_at = datetime.now(timezone.utc).isoformat()
                resolved_now += 1
            elif age_days >= MAX_RECORD_AGE_DAYS:
                rec.status = "ABANDONED"
                abandoned_now += 1
            continue

        if rec.rejected_hypothetical_pnl is None and age_days >= RESOLUTION_HORIZON_DAYS:
            rec.rejected_hypothetical_pnl = _simulate_candidate_exit(
                rec.rejected_symbol, rec.trade_date, rec.rejected_direction,
                rec.rejected_entry, rec.rejected_stop, rec.rejected_target,
                rec.weak_quantity,
            )

        if rec.weak_actual_pnl is None:
            weak_rec = order_manager._orders.get(rec.weak_order_id)
            if weak_rec is not None and weak_rec.status == "closed":
                rec.weak_actual_pnl = float(weak_rec.pnl)

        if rec.rejected_hypothetical_pnl is not None and rec.weak_actual_pnl is not None:
            cost = _swap_cost_estimate(
                rec.rejected_symbol, rec.weak_quantity, rec.rejected_entry,
            )
            scenario_no_swap = rec.weak_actual_pnl
            scenario_swap = (
                rec.weak_pnl_if_closed_at_decision + rec.rejected_hypothetical_pnl - cost
            )
            net_benefit = scenario_swap - scenario_no_swap
            rec.net_benefit_rs = round(net_benefit, 2)
            rec.classification = "CORRECT_SWAP" if net_benefit > 0 else "INCORRECT_SWAP"
            rec.status = "RESOLVED"
            rec.resolved_at = datetime.now(timezone.utc).isoformat()
            resolved_now += 1
        elif age_days >= MAX_RECORD_AGE_DAYS:
            rec.status = "ABANDONED"
            abandoned_now += 1

    if resolved_now or abandoned_now:
        _save_records(records)

    return {
        "success": True,
        "resolved": resolved_now,
        "abandoned": abandoned_now,
        "still_pending": sum(1 for r in records if r.status == "PENDING"),
    }


# ─────────────────────────────────────────────────────────────────────────
# Stage C — lifecycle (EOD-loop wired, fully automatic, no human gate)
# ─────────────────────────────────────────────────────────────────────────

def advance_lifecycle() -> Dict[str, Any]:
    """Never raises."""
    try:
        return _advance_impl()
    except Exception as exc:
        log.debug("[LateCapSwapBridge] lifecycle error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _advance_impl() -> Dict[str, Any]:
    state = _load_state()
    status = state.get("status", STATUS_ACTIVE)
    records = _load_records()
    resolved = [r for r in records if r.status == "RESOLVED"]
    correct = sum(1 for r in resolved if r.classification == "CORRECT_SWAP")
    hit_rate = (correct / len(resolved)) if resolved else 0.0

    summary = {"status": status, "resolved": len(resolved), "hit_rate": round(hit_rate, 3)}

    if status == STATUS_SHADOW_ACTIVE:
        shadow_start = date.fromisoformat(state.get("shadow_start_date", date.today().isoformat()))
        age_days = (date.today() - shadow_start).days

        if len(resolved) >= MIN_SAMPLES_FOR_ACTIVATION and hit_rate >= MIN_HIT_RATE_FOR_ACTIVATION:
            state["status"] = STATUS_ACTIVE
            state["activated_at"] = datetime.now(timezone.utc).isoformat()
            _save_state(state)
            _append_ledger({
                "event": "PROMOTED_TO_ACTIVE", "resolved": len(resolved),
                "hit_rate": round(hit_rate, 3),
                "reason": f"hit_rate={hit_rate:.3f} on n={len(resolved)} >= "
                          f"{MIN_HIT_RATE_FOR_ACTIVATION} on n>={MIN_SAMPLES_FOR_ACTIVATION}",
            })
            log.info(
                "[LateCapSwapBridge] PROMOTED to ACTIVE: hit_rate=%.3f on n=%d. "
                "Future LatePositionCap rejections may now trigger a real swap.",
                hit_rate, len(resolved),
            )
            summary["status"] = STATUS_ACTIVE
        elif age_days >= MAX_OBSERVATION_DAYS:
            state["status"] = STATUS_REJECTED
            state["status_reason"] = (
                f"No usable signal within {MAX_OBSERVATION_DAYS} days "
                f"(n={len(resolved)}, hit_rate={hit_rate:.3f})."
            )
            _save_state(state)
            _append_ledger({"event": "REJECTED", "reason": state["status_reason"]})
            log.info("[LateCapSwapBridge] REJECTED: %s", state["status_reason"])
            summary["status"] = STATUS_REJECTED

    elif status == STATUS_ACTIVE:
        # Auto-rollback monitor: only consider records resolved AFTER activation.
        activated_at = state.get("activated_at", "")
        post_activation = [r for r in resolved if r.resolved_at >= activated_at] if activated_at else resolved
        if len(post_activation) >= MIN_SAMPLES_FOR_ROLLBACK_CHECK:
            post_hit = sum(1 for r in post_activation if r.classification == "CORRECT_SWAP") / len(post_activation)
            if post_hit < ROLLBACK_HIT_RATE_FLOOR:
                state["status"] = STATUS_ROLLED_BACK
                state["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
                _save_state(state)
                _append_ledger({
                    "event": "ROLLED_BACK",
                    "reason": f"post-activation hit_rate={post_hit:.3f} < floor {ROLLBACK_HIT_RATE_FLOOR}",
                })
                log.warning(
                    "[LateCapSwapBridge] ROLLED BACK to SHADOW_ACTIVE: post-activation "
                    "hit_rate=%.3f < floor %.2f on n=%d.",
                    post_hit, ROLLBACK_HIT_RATE_FLOOR, len(post_activation),
                )
                summary["status"] = STATUS_ROLLED_BACK

    elif status == STATUS_ROLLED_BACK:
        # DTA-LATE-CAP-SWAP-GO-LIVE-001: ROLLED_BACK is not terminal -- real
        # swapping is paused, but register_late_cap_swap_opportunity() keeps
        # shadow-recording in the meantime (same decision-only path as
        # SHADOW_ACTIVE). Once fresh evidence since the rollback clears the
        # same bar again, automatically re-promote; give up to REJECTED only
        # after MAX_OBSERVATION_DAYS of failing to re-qualify.
        rolled_back_at = state.get("rolled_back_at", "")
        post_rollback = [r for r in resolved if r.resolved_at >= rolled_back_at] if rolled_back_at else resolved
        post_hit = (
            sum(1 for r in post_rollback if r.classification == "CORRECT_SWAP") / len(post_rollback)
            if post_rollback else 0.0
        )
        if len(post_rollback) >= MIN_SAMPLES_FOR_ACTIVATION and post_hit >= MIN_HIT_RATE_FOR_ACTIVATION:
            state["status"] = STATUS_ACTIVE
            state["activated_at"] = datetime.now(timezone.utc).isoformat()
            _save_state(state)
            _append_ledger({
                "event": "REACTIVATED_AFTER_ROLLBACK", "resolved": len(post_rollback),
                "hit_rate": round(post_hit, 3),
            })
            log.info(
                "[LateCapSwapBridge] REACTIVATED to ACTIVE after rollback: "
                "post-rollback hit_rate=%.3f on n=%d.", post_hit, len(post_rollback),
            )
            summary["status"] = STATUS_ACTIVE
        else:
            try:
                rolled_back_dt = datetime.fromisoformat(rolled_back_at) if rolled_back_at else datetime.now(timezone.utc)
            except Exception:
                rolled_back_dt = datetime.now(timezone.utc)
            age_days_since_rollback = (datetime.now(timezone.utc) - rolled_back_dt).days
            if age_days_since_rollback >= MAX_OBSERVATION_DAYS:
                state["status"] = STATUS_REJECTED
                state["status_reason"] = (
                    f"Failed to re-qualify within {MAX_OBSERVATION_DAYS} days of rollback "
                    f"(n={len(post_rollback)}, hit_rate={post_hit:.3f})."
                )
                _save_state(state)
                _append_ledger({"event": "REJECTED_AFTER_ROLLBACK", "reason": state["status_reason"]})
                log.info("[LateCapSwapBridge] REJECTED after rollback: %s", state["status_reason"])
                summary["status"] = STATUS_REJECTED

    return summary
