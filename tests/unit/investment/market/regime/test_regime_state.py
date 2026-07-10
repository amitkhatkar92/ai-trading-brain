"""tests/unit/investment/market/regime/test_regime_state.py"""
from __future__ import annotations

import threading
import pytest

from iios.investment.market.regime.models import RegimeType
from iios.investment.market.regime.regime_state import RegimeState


@pytest.fixture
def state() -> RegimeState:
    return RegimeState(market_id="M1", symbol="SYM")


class TestRegimeStateInitial:
    def test_initial_regime_is_unknown(self, state):
        assert state.current_regime() == RegimeType.UNKNOWN

    def test_initial_bars_is_zero(self, state):
        assert state.bars_in_current() == 0


class TestSetCurrent:
    def test_set_current_returns_true_on_change(self, state):
        assert state.set_current(RegimeType.BULL) is True

    def test_set_current_returns_false_on_same(self, state):
        state.set_current(RegimeType.BULL)
        assert state.set_current(RegimeType.BULL) is False

    def test_current_regime_updates(self, state):
        state.set_current(RegimeType.BEAR)
        assert state.current_regime() == RegimeType.BEAR


class TestBarsInCurrent:
    def test_bars_increments_on_same_regime(self, state):
        state.set_current(RegimeType.BULL)
        state.set_current(RegimeType.BULL)
        state.set_current(RegimeType.BULL)
        assert state.bars_in_current() == 3

    def test_bars_resets_to_1_on_regime_change(self, state):
        state.set_current(RegimeType.BULL)
        state.set_current(RegimeType.BULL)
        assert state.bars_in_current() == 2
        state.set_current(RegimeType.BEAR)
        assert state.bars_in_current() == 1

    def test_bars_is_1_after_first_set(self, state):
        state.set_current(RegimeType.BULL)
        assert state.bars_in_current() == 1


class TestReset:
    def test_reset_returns_to_unknown(self, state):
        state.set_current(RegimeType.BULL)
        state.reset()
        assert state.current_regime() == RegimeType.UNKNOWN

    def test_reset_clears_bars(self, state):
        state.set_current(RegimeType.BULL)
        state.set_current(RegimeType.BULL)
        state.reset()
        assert state.bars_in_current() == 0


class TestThreadSafety:
    def test_concurrent_set_current(self):
        state = RegimeState("M1", "SYM")
        errors = []

        def worker(regime: RegimeType):
            try:
                for _ in range(100):
                    state.set_current(regime)
                    state.current_regime()
                    state.bars_in_current()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(RegimeType.BULL,)),
            threading.Thread(target=worker, args=(RegimeType.BEAR,)),
            threading.Thread(target=worker, args=(RegimeType.SIDEWAYS,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        # After all threads, state must be in a valid regime
        assert state.current_regime() in RegimeType
        assert state.bars_in_current() >= 0


class TestToDict:
    def test_to_dict_has_expected_keys(self, state):
        state.set_current(RegimeType.BULL)
        d = state.to_dict()
        assert "market_id" in d
        assert "symbol" in d
        assert "current" in d
        assert "bars" in d

    def test_to_dict_current_is_string(self, state):
        state.set_current(RegimeType.BULL)
        d = state.to_dict()
        assert d["current"] == "bull"
