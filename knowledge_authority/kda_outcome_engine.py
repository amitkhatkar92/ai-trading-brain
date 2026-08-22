"""
knowledge_authority/kda_outcome_engine.py
===========================================
KDA-002 — Evaluates KDA shadow decisions against subsequent market data.

Key design principles:
  - Takes pre-filtered OHLCV bars (bars[0] = first bar AFTER decision)
  - Never uses lookahead: bars must NOT include the decision bar itself
  - All metrics in percentage terms (not raw price)
  - MFE/MAE computed path-dependently bar-by-bar
  - Target/stop events detected per-bar using high/low (not only close)
  - Returns are at close price of bar N (T+1 = bars[0].close, etc.)

Safety contract:
  broker_calls = 0, orders = 0, no_lookahead = True, PAPER_TRADING unchanged
  No imports from execution_engine, OrderManager, broker APIs.
"""
from __future__ import annotations

import statistics
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .kda_models import KDADecisionRecord
from .kda_outcome_models import (
    MoveSpeed,
    OHLCVBar,
    OutcomeClass,
    OutcomeStatus,
    KDAOutcomeRecord,
    TargetComparison,
)


# Maximum evaluation window
_MAX_EVAL_BARS = 20

# Missed-opportunity threshold: move > this % qualifies (absolute)
_MISSED_MOVE_THRESHOLD = 2.0

# Minimum T bars to classify direction (otherwise UNRESOLVED)
_MIN_BARS_FOR_DIRECTION = 1


class KDAOutcomeEngine:
    """
    Evaluates KDA decisions against actual OHLCV price bars.
    Stateless — all state is in the returned KDAOutcomeRecord.
    """

    def evaluate(
        self,
        decision:     KDADecisionRecord,
        bars:         List[OHLCVBar],    # post-decision bars, chronological
        entry_price:  Optional[float] = None,
        observation_id: Optional[str] = None,
        trading_date: Optional[str]   = None,
    ) -> KDAOutcomeRecord:
        """
        Evaluate one completed KDA decision.

        bars[0] must be the first trading day AFTER the decision timestamp.
        No lookahead: bars must NOT contain the bar on which the decision was made.

        entry_price: if None, uses bars[0].open (next-day open execution).
        """
        outcome_id = str(uuid.uuid4())
        td = trading_date or (bars[0].date if bars else datetime.now(timezone.utc).date().isoformat())

        if not bars:
            return self._no_data_record(outcome_id, decision, observation_id, td)

        entry = entry_price if (entry_price is not None and entry_price > 0) else bars[0].open
        if entry <= 0:
            return self._invalid_record(outcome_id, decision, observation_id, td, bars)

        # Use KDA decision (not scanner direction) to determine if this is a real trade
        kda_dec   = decision.decision.value.upper()
        is_buy    = "BUY"  in kda_dec
        is_sell   = "SELL" in kda_dec
        direction = decision.direction.upper()
        is_directional = is_buy or is_sell

        n_bars = min(len(bars), _MAX_EVAL_BARS)
        eval_bars = bars[:n_bars]

        target    = decision.target
        stop_loss = decision.stop_loss

        # ── bar-by-bar scan ──────────────────────────────────────────────────
        target_day: Optional[int] = None
        stop_day:   Optional[int] = None
        mfe_raw = 0.0
        mae_raw = 0.0

        for i, bar in enumerate(eval_bars, start=1):
            if is_buy:
                fav = bar.high - entry
                adv = entry - bar.low
                if target is not None and bar.high >= target and target_day is None:
                    target_day = i
                if stop_loss is not None and bar.low <= stop_loss and stop_day is None:
                    stop_day = i
            elif is_sell:
                fav = entry - bar.low
                adv = bar.high - entry
                if target is not None and bar.low <= target and target_day is None:
                    target_day = i
                if stop_loss is not None and bar.high >= stop_loss and stop_day is None:
                    stop_day = i
            else:
                fav = 0.0
                adv = 0.0
            mfe_raw = max(mfe_raw, fav)
            mae_raw = max(mae_raw, adv)

        mfe = (mfe_raw / entry * 100.0) if is_directional else None
        mae = (mae_raw / entry * 100.0) if is_directional else None

        # ── T+N returns ──────────────────────────────────────────────────────
        def _ret(n: int) -> Optional[float]:
            if n > len(eval_bars):
                return None
            c = eval_bars[n - 1].close
            if is_buy:
                return (c - entry) / entry * 100.0
            elif is_sell:
                return (entry - c) / entry * 100.0
            return None

        return_t1  = _ret(1)
        return_t3  = _ret(3)
        return_t5  = _ret(5)
        return_t10 = _ret(10)
        return_t20 = _ret(20)

        # ── events ───────────────────────────────────────────────────────────
        target_hit = target_day is not None
        stop_hit   = stop_day is not None

        if target_hit and stop_hit:
            if target_day <= stop_day:
                first_event = "TARGET_HIT"
                event_day   = target_day
            else:
                first_event = "STOP_HIT"
                event_day   = stop_day
        elif target_hit:
            first_event = "TARGET_HIT"
            event_day   = target_day
        elif stop_hit:
            first_event = "STOP_HIT"
            event_day   = stop_day
        else:
            first_event = None
            event_day   = None

        # ── direction correctness ─────────────────────────────────────────
        ref_return = return_t5 if return_t5 is not None else return_t1
        direction_correct: Optional[bool] = None
        if is_directional and ref_return is not None:
            direction_correct = ref_return > 0.0

        # ── horizon ───────────────────────────────────────────────────────
        horizon_error, horizon_accuracy, move_speed = self._eval_horizon(
            decision, event_day, n_bars
        )

        # ── target comparison ─────────────────────────────────────────────
        target_accuracy, target_comparison = self._eval_target(
            decision, entry, target, first_event, return_t5, is_buy
        )

        # ── classification ────────────────────────────────────────────────
        outcome_class = _classify_outcome(
            decision.decision.value,
            is_directional,
            target_hit,
            stop_hit,
            direction_correct,
            ref_return,
            n_bars,
        )

        decision_correct = _decision_correct(outcome_class)

        return KDAOutcomeRecord(
            outcome_id            = outcome_id,
            decision_id           = decision.decision_id,
            observation_id        = observation_id,
            trading_date          = td,
            symbol                = decision.symbol,
            direction             = direction,
            decision              = decision.decision.value,
            authority             = decision.authority.value,
            knowledge_authority   = decision.knowledge_authority,
            entry_price           = entry,

            target                = target,
            stop_loss             = stop_loss,
            expected_move_p25     = decision.expected_move_p25,
            expected_move_p50     = decision.expected_move_p50,
            expected_move_p75     = decision.expected_move_p75,
            expected_days_p25     = decision.expected_days_p25,
            expected_days_p50     = decision.expected_days_p50,
            expected_days_p75     = decision.expected_days_p75,
            target_source         = decision.target_source,
            stop_source           = decision.stop_source,
            horizon_source        = decision.horizon_source,

            return_t1             = return_t1,
            return_t3             = return_t3,
            return_t5             = return_t5,
            return_t10            = return_t10,
            return_t20            = return_t20,

            mfe                   = mfe,
            mae                   = mae,

            target_hit            = target_hit,
            stop_hit              = stop_hit,
            time_to_target        = target_day,
            time_to_stop          = stop_day,
            first_event           = first_event,
            event_day             = event_day,

            horizon_error         = horizon_error,
            horizon_accuracy      = horizon_accuracy,
            move_speed            = move_speed,

            target_accuracy       = target_accuracy,
            target_comparison     = target_comparison,

            direction_correct     = direction_correct,
            decision_correct      = decision_correct,
            outcome_class         = outcome_class,

            evidence_state        = decision.evidence_state.value,
            evidence_level        = decision.evidence_level.value,

            status                = OutcomeStatus.OUTCOME_COMPLETE.value,
            bars_available        = n_bars,
            evaluation_horizon    = _MAX_EVAL_BARS,

            strategy_status       = (
                decision.strategy_context.status
                if decision.strategy_context else None
            ),
            scanner_confidence    = decision.knowledge_score,

            no_lookahead          = True,
            broker_calls          = 0,
            orders                = 0,
        )

    # ── horizon helpers ───────────────────────────────────────────────────

    def _eval_horizon(
        self,
        decision: KDADecisionRecord,
        event_day: Optional[int],
        n_bars: int,
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        p50 = decision.expected_days_p50
        p25 = decision.expected_days_p25
        p75 = decision.expected_days_p75

        if p50 is None or p50 <= 0:
            return None, None, None

        actual_day = event_day or n_bars
        error = abs(actual_day - p50)
        accuracy = max(0.0, 1.0 - error / p50)

        # Move speed relative to predicted p25/p50/p75
        speed = MoveSpeed.UNRESOLVED.value
        if event_day is not None:
            if p25 is not None and event_day <= p25:
                speed = MoveSpeed.FAST_MOVE.value
            elif p75 is not None and event_day >= p75:
                speed = MoveSpeed.SLOW_MOVE.value
            else:
                speed = MoveSpeed.NORMAL_MOVE.value

        return error, accuracy, speed

    # ── target comparison helper ──────────────────────────────────────────

    def _eval_target(
        self,
        decision:    KDADecisionRecord,
        entry:       float,
        target:      Optional[float],
        first_event: Optional[str],
        return_t5:   Optional[float],
        is_buy:      bool,
    ) -> Tuple[Optional[float], Optional[str]]:
        if target is None or entry <= 0:
            return None, TargetComparison.INSUFFICIENT_DATA.value

        knowledge_pct = abs(target - entry) / entry * 100.0

        if knowledge_pct < 0.01:
            return None, TargetComparison.INSUFFICIENT_DATA.value

        if first_event == "TARGET_HIT":
            accuracy = 1.0
            comp = TargetComparison.REASONABLE.value
        elif return_t5 is not None:
            actual_pct = abs(return_t5)
            ratio = actual_pct / knowledge_pct
            accuracy = min(ratio, 1.0)
            if ratio < 0.5:
                comp = TargetComparison.TOO_AGGRESSIVE.value
            elif ratio > 1.5:
                comp = TargetComparison.TOO_CONSERVATIVE.value
            else:
                comp = TargetComparison.REASONABLE.value
        else:
            return None, TargetComparison.INSUFFICIENT_DATA.value

        return accuracy, comp

    # ── fallback records ──────────────────────────────────────────────────

    def _no_data_record(
        self,
        outcome_id:     str,
        decision:       KDADecisionRecord,
        observation_id: Optional[str],
        trading_date:   str,
    ) -> KDAOutcomeRecord:
        return self._status_record(
            outcome_id, decision, observation_id, trading_date,
            OutcomeStatus.OUTCOME_NO_DATA, 0
        )

    def _invalid_record(
        self,
        outcome_id:     str,
        decision:       KDADecisionRecord,
        observation_id: Optional[str],
        trading_date:   str,
        bars:           List[OHLCVBar],
    ) -> KDAOutcomeRecord:
        return self._status_record(
            outcome_id, decision, observation_id, trading_date,
            OutcomeStatus.OUTCOME_INVALID, len(bars)
        )

    @staticmethod
    def _status_record(
        outcome_id:     str,
        decision:       KDADecisionRecord,
        observation_id: Optional[str],
        trading_date:   str,
        status:         OutcomeStatus,
        bars_available: int,
    ) -> KDAOutcomeRecord:
        return KDAOutcomeRecord(
            outcome_id            = outcome_id,
            decision_id           = decision.decision_id,
            observation_id        = observation_id,
            trading_date          = trading_date,
            symbol                = decision.symbol,
            direction             = decision.direction,
            decision              = decision.decision.value,
            authority             = decision.authority.value,
            knowledge_authority   = decision.knowledge_authority,
            entry_price           = 0.0,
            target                = decision.target,
            stop_loss             = decision.stop_loss,
            expected_move_p25     = decision.expected_move_p25,
            expected_move_p50     = decision.expected_move_p50,
            expected_move_p75     = decision.expected_move_p75,
            expected_days_p25     = decision.expected_days_p25,
            expected_days_p50     = decision.expected_days_p50,
            expected_days_p75     = decision.expected_days_p75,
            target_source         = decision.target_source,
            stop_source           = decision.stop_source,
            horizon_source        = decision.horizon_source,
            return_t1=None, return_t3=None, return_t5=None,
            return_t10=None, return_t20=None,
            mfe=None, mae=None,
            target_hit=None, stop_hit=None,
            time_to_target=None, time_to_stop=None,
            first_event=None, event_day=None,
            horizon_error=None, horizon_accuracy=None, move_speed=None,
            target_accuracy=None, target_comparison=None,
            direction_correct=None, decision_correct=None,
            outcome_class=OutcomeClass.UNRESOLVED.value,
            evidence_state        = decision.evidence_state.value,
            evidence_level        = decision.evidence_level.value,
            status                = status.value,
            bars_available        = bars_available,
            evaluation_horizon    = _MAX_EVAL_BARS,
            strategy_status       = (
                decision.strategy_context.status
                if decision.strategy_context else None
            ),
            scanner_confidence    = decision.knowledge_score,
            no_lookahead          = True,
            broker_calls          = 0,
            orders                = 0,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Classification helpers (module-level, pure functions)
# ─────────────────────────────────────────────────────────────────────────────

def _classify_outcome(
    decision_value:   str,
    is_directional:   bool,
    target_hit:       bool,
    stop_hit:         bool,
    direction_correct: Optional[bool],
    ref_return:       Optional[float],
    n_bars:           int,
) -> str:
    d = decision_value.upper()

    # Directional decisions (BUY / SELL)
    if "BUY" in d or "SELL" in d:
        suffix = "BUY" if "BUY" in d else "SELL"
        if target_hit and not stop_hit:
            return OutcomeClass(f"CORRECT_{suffix}").value
        if stop_hit and not target_hit:
            return OutcomeClass(f"INCORRECT_{suffix}").value
        if target_hit and stop_hit:
            return OutcomeClass(f"CORRECT_{suffix}").value  # target first wins per earlier logic
        # No event — use direction at T+5 or last available
        if direction_correct is True:
            return OutcomeClass(f"CORRECT_{suffix}").value
        if direction_correct is False:
            return OutcomeClass(f"INCORRECT_{suffix}").value
        return OutcomeClass.UNRESOLVED.value

    # HOLD
    if "HOLD" in d:
        if ref_return is None:
            return OutcomeClass.UNRESOLVED.value
        if direction_correct is True:
            return OutcomeClass.CORRECT_HOLD.value
        if direction_correct is False:
            return OutcomeClass.INCORRECT_HOLD.value
        return OutcomeClass.UNRESOLVED.value

    # WAIT — check for missed opportunity
    if "WAIT" in d:
        if ref_return is not None and abs(ref_return) >= _MISSED_MOVE_THRESHOLD:
            return OutcomeClass.MISSED_OPPORTUNITY.value
        if n_bars >= _MIN_BARS_FOR_DIRECTION:
            return OutcomeClass.CORRECT_WAIT.value
        return OutcomeClass.UNRESOLVED.value

    # EXIT
    if "EXIT" in d:
        if direction_correct is True:
            return OutcomeClass.CORRECT_EXIT.value
        return OutcomeClass.INCORRECT_EXIT.value

    return OutcomeClass.UNRESOLVED.value


def _decision_correct(outcome_class: Optional[str]) -> Optional[bool]:
    if outcome_class is None:
        return None
    correct_classes = {
        "CORRECT_BUY", "CORRECT_SELL", "CORRECT_WAIT",
        "CORRECT_HOLD", "CORRECT_EXIT",
    }
    if outcome_class in correct_classes:
        return True
    if outcome_class == "UNRESOLVED":
        return None
    return False
