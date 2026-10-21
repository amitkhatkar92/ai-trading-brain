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
  SHADOW_ACTIVE -> ACTIVE (auto-promoted once real evidence confirms a
  net benefit) -> ROLLED_BACK (auto-reverted on live degradation) /
  REJECTED (gave up -- no usable signal within the max observation
  window).

Evidence requirement is deliberately HIGHER than most other modules in
this session (MIN_SAMPLES_FOR_ACTIVATION=30, MIN_HIT_RATE=0.55) because,
unlike a ranking-weight or sizing-bound nudge, going ACTIVE here means
this module will itself close a real, currently-open position the next
time it fires -- the one module in this set with that property.

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
MIN_SAMPLES_FOR_ACTIVATION  = 30     # resolved shadow records before any promotion
MIN_HIT_RATE_FOR_ACTIVATION = 0.55   # must show a clear edge, not a coin flip
MAX_OBSERVATION_DAYS        = 60     # give up (REJECTED) if never conclusive by then
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
    rejected_hypothetical_pnl: Optional[float] = None
    weak_actual_pnl:       Optional[float] = None
    resolved_at:           str = ""
    classification:        Optional[str] = None   # CORRECT_SWAP | INCORRECT_SWAP
    net_benefit_rs:         Optional[float] = None
    status:                str = "PENDING"         # PENDING | RESOLVED | ABANDONED


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
        return {"status": STATUS_SHADOW_ACTIVE, "shadow_start_date": date.today().isoformat()}
    try:
        with open(_STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        log.warning("[LateCapSwapBridge] state load failed: %s", exc)
        return {"status": STATUS_SHADOW_ACTIVE, "shadow_start_date": date.today().isoformat()}


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
    return _load_state().get("status", STATUS_SHADOW_ACTIVE)


def get_readiness_status() -> Dict[str, Any]:
    """Read-only accessor (Sandy-compatible)."""
    try:
        state = _load_state()
        records = _load_records()
        resolved = [r for r in records if r.status == "RESOLVED"]
        correct = sum(1 for r in resolved if r.classification == "CORRECT_SWAP")
        return {
            "status": state.get("status", STATUS_SHADOW_ACTIVE),
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
        return bool(order_manager.execute_late_cap_swap(
            signal.symbol, new_score, new_entry, new_stop, new_target,
        ))

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
    status = state.get("status", STATUS_SHADOW_ACTIVE)
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

    return summary
