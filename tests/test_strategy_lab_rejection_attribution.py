"""
tests/test_strategy_lab_rejection_attribution.py
====================================================
Evidence-labeling audit follow-up: `strategy_lab/strategy_generator_ai.py`'s
`classify_rejection_reason()` gives 2 previously-generic "ASSIGN_REJECTED"
gates (bear-market equity BUY rejection, volatile-regime low-confidence
rejection) their own distinct labels, so the already-live
`analysis/rejection_tracker.py` / `analysis/rejection_attribution_monitor.py`
pipeline (real T+1/T+3/T+5 price follow-through, per-reason reliability)
can, for the first time, measure whether these 2 specific gates are
actually correct rejections or false negatives -- purely additive labeling,
zero change to which signals get dropped.

T01  Bear-market equity BUY -> BEAR_MARKET_BUY_REJECTED (checked first,
     matching _assign()'s own gate order)
T02  RR below min_rr -> RR_x.x_below_min_y.y (even in BEAR_MARKET, if the
     bear-market predicate doesn't match e.g. non-equity/non-BUY)
T03  Volatile regime + low confidence + volatile-eligible strategy ->
     VOLATILE_LOW_CONFIDENCE_REJECTED
T04  Strategy in the disabled set -> STRATEGY_DISABLED
T05  None of the above -> generic ASSIGN_REJECTED fallback preserved
T06  Bear-market SELL (not BUY) does not trigger BEAR_MARKET_BUY_REJECTED
T07  Volatile regime but confidence >= threshold does not trigger the
     volatile-low-confidence label
T08  Real str-mixin Enum members (SignalType/SignalDirection) compare
     correctly without needing str() -- regression guard for the exact
     bug class already documented in user memory (enum stringification)
"""
from __future__ import annotations

from strategy_lab.strategy_generator_ai import (
    classify_rejection_reason,
    VOLATILE_EQUITY_MIN_CONFIDENCE,
)
from models.trade_signal import SignalType, SignalDirection


def test_t01_bear_market_buy_rejected():
    reason = classify_rejection_reason(
        signal_type="equity", direction="BUY", confidence=8.0,
        strategy_name="Mean_Reversion", risk_reward_ratio=3.0, min_rr=2.0,
        cycle_regime="BEAR_MARKET", disabled_strategies=set(),
    )
    assert reason == "BEAR_MARKET_BUY_REJECTED"


def test_t02_rr_below_min():
    reason = classify_rejection_reason(
        signal_type="equity", direction="SELL", confidence=8.0,
        strategy_name="Mean_Reversion", risk_reward_ratio=1.2, min_rr=2.0,
        cycle_regime="BEAR_MARKET", disabled_strategies=set(),
    )
    assert reason == "RR_1.2_below_min_2.0"


def test_t03_volatile_low_confidence_rejected():
    reason = classify_rejection_reason(
        signal_type="equity", direction="BUY", confidence=5.0,
        strategy_name="Equity_Breakout", risk_reward_ratio=3.0, min_rr=2.5,
        cycle_regime="VOLATILE", disabled_strategies=set(),
    )
    assert reason == "VOLATILE_LOW_CONFIDENCE_REJECTED"


def test_t04_strategy_disabled():
    reason = classify_rejection_reason(
        signal_type="equity", direction="SELL", confidence=8.0,
        strategy_name="Mean_Reversion", risk_reward_ratio=3.0, min_rr=2.0,
        cycle_regime="RANGE_MARKET", disabled_strategies={"Mean_Reversion"},
    )
    assert reason == "STRATEGY_DISABLED"


def test_t05_generic_fallback():
    reason = classify_rejection_reason(
        signal_type="equity", direction="SELL", confidence=8.0,
        strategy_name="Mean_Reversion", risk_reward_ratio=3.0, min_rr=2.0,
        cycle_regime="RANGE_MARKET", disabled_strategies=set(),
    )
    assert reason == "ASSIGN_REJECTED"


def test_t06_bear_market_sell_not_flagged():
    reason = classify_rejection_reason(
        signal_type="equity", direction="SELL", confidence=8.0,
        strategy_name="Mean_Reversion", risk_reward_ratio=1.0, min_rr=2.0,
        cycle_regime="BEAR_MARKET", disabled_strategies=set(),
    )
    assert reason != "BEAR_MARKET_BUY_REJECTED"
    assert reason == "RR_1.0_below_min_2.0"


def test_t07_volatile_high_confidence_not_flagged():
    reason = classify_rejection_reason(
        signal_type="equity", direction="BUY",
        confidence=VOLATILE_EQUITY_MIN_CONFIDENCE + 1.0,
        strategy_name="Equity_Breakout", risk_reward_ratio=1.0, min_rr=2.5,
        cycle_regime="VOLATILE", disabled_strategies=set(),
    )
    assert reason != "VOLATILE_LOW_CONFIDENCE_REJECTED"


def test_t08_real_enum_members_compare_correctly_without_str():
    reason = classify_rejection_reason(
        signal_type=SignalType.EQUITY, direction=SignalDirection.BUY,
        confidence=8.0, strategy_name="Mean_Reversion",
        risk_reward_ratio=3.0, min_rr=2.0,
        cycle_regime="BEAR_MARKET", disabled_strategies=set(),
    )
    assert reason == "BEAR_MARKET_BUY_REJECTED"
