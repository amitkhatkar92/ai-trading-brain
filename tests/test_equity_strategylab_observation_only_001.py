"""
tests/test_equity_strategylab_observation_only_001.py
========================================================
DTA-EQUITY-STRATEGYLAB-OBSERVATION-001

Verifies StrategyLab's SHM/PerfTracker health judgement is observation-only
for EQUITY too (previously only exempted for OPTIONS/SPREAD) -- KDA is the
sole authority on whether a trade proceeds. A disabled/inactive strategy no
longer causes StrategyGeneratorAI to drop the signal; it is recorded on
`TradeSignal.strategy_health_status` and still forwarded.

Untouched, still-enforced equity gates (regression checks):
  - Bear-market equity BUY rejection
  - RR-below-minimum rejection
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from strategy_lab.strategy_generator_ai import StrategyGeneratorAI, STRATEGY_PARAMS


def _snapshot(regime=RegimeLabel.RANGE_MARKET, volatility=VolatilityLevel.MEDIUM) -> MarketSnapshot:
    return MarketSnapshot(timestamp=datetime.now(), indices={}, regime=regime, volatility=volatility)


def _signal(strategy_name="Mean_Reversion", signal_type=SignalType.EQUITY,
            direction=SignalDirection.BUY, entry=100.0, stop=98.0, target=106.0) -> TradeSignal:
    return TradeSignal(
        symbol="TESTSTOCK", direction=direction, signal_type=signal_type,
        entry_price=entry, stop_loss=stop, target_price=target,
        quantity=10, strategy_name=strategy_name, confidence=7.0,
    )


def _sg() -> StrategyGeneratorAI:
    sg = object.__new__(StrategyGeneratorAI)
    sg._meta = None
    sg._evolved = {}
    return sg


@pytest.fixture(autouse=True)
def _ensure_mean_reversion_registered():
    if "Mean_Reversion" not in STRATEGY_PARAMS:
        STRATEGY_PARAMS["Mean_Reversion"] = {"min_rr": 1.5, "max_loss_pct": 0.01}
    yield


# ─────────────────────────────────────────────────────────────────────────────
# Core behaviour: equity is now observation-only, matching options/spread
# ─────────────────────────────────────────────────────────────────────────────

def test_t001_equity_signal_forwarded_despite_shm_exclusion():
    sg = _sg()
    signals = [_signal(signal_type=SignalType.EQUITY)]
    result = sg.assign_strategy(signals, _snapshot(), excluded_strategies={"Mean_Reversion"})
    assert len(result) == 1, "Equity signal must be forwarded, not dropped, when strategy is SHM-excluded"


def test_t002_equity_signal_gets_health_status_recorded():
    sg = _sg()
    signals = [_signal(signal_type=SignalType.EQUITY)]
    result = sg.assign_strategy(signals, _snapshot(), excluded_strategies={"Mean_Reversion"})
    assert result[0].strategy_health_status is not None


def test_t003_active_set_exclusion_inside_assign_does_not_drop_equity():
    sg = _sg()
    signal = _signal(signal_type=SignalType.EQUITY)
    result = sg._assign(signal, _snapshot(), active={"Some_Other_Strategy"})
    assert result is not None, "_assign must not return None for equity due to active-set exclusion"
    assert result.strategy_health_status == "META_INACTIVE"


def test_t004_options_signal_still_forwarded_and_recorded_consistently():
    sg = _sg()
    if "Bull_Call_Spread" not in STRATEGY_PARAMS:
        STRATEGY_PARAMS["Bull_Call_Spread"] = {"min_rr": 0.5, "max_loss_pct": 0.01}
    signal = _signal(strategy_name="Bull_Call_Spread", signal_type=SignalType.OPTIONS)
    result = sg._assign(signal, _snapshot(), active={"Some_Other_Strategy"})
    assert result is not None
    assert result.strategy_health_status == "META_INACTIVE"


# ─────────────────────────────────────────────────────────────────────────────
# Regression: untouched equity gates must still reject
# ─────────────────────────────────────────────────────────────────────────────

def test_t005_bear_market_equity_buy_still_rejected():
    sg = _sg()
    signal = _signal(signal_type=SignalType.EQUITY, direction=SignalDirection.BUY)
    result = sg._assign(signal, _snapshot(regime=RegimeLabel.BEAR_MARKET), active=None)
    assert result is None, "Bear-market equity BUY rejection must remain in effect"


def test_t006_rr_below_minimum_still_rejected_for_equity():
    sg = _sg()
    STRATEGY_PARAMS["Mean_Reversion"]["min_rr"] = 5.0
    try:
        # entry=100, stop=98 (risk=2), target=101 (reward=1) -> RR=0.5, well below 5.0
        signal = _signal(signal_type=SignalType.EQUITY, entry=100.0, stop=98.0, target=101.0)
        result = sg._assign(signal, _snapshot(), active=None)
        assert result is None, "RR-below-minimum rejection must remain in effect for equity"
    finally:
        STRATEGY_PARAMS["Mean_Reversion"]["min_rr"] = 1.5


def test_t007_final_hard_gate_no_longer_drops_equity():
    sg = _sg()
    signals = [_signal(signal_type=SignalType.EQUITY)]
    # Force assign_strategy's post-_assign hard gate to see strategy already excluded
    result = sg.assign_strategy(signals, _snapshot(), excluded_strategies={"Mean_Reversion"}, shm_ref=None)
    assert len(result) == 1


def test_t008_no_excluded_strategies_means_no_health_status_set():
    sg = _sg()
    signals = [_signal(signal_type=SignalType.EQUITY)]
    result = sg.assign_strategy(signals, _snapshot(), excluded_strategies=None)
    assert result[0].strategy_health_status is None


def test_t009_trade_signal_field_defaults_to_none():
    signal = _signal()
    assert signal.strategy_health_status is None
