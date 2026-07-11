"""test_rolling_correlation.py — RollingCorrelationCalculator tests."""
from __future__ import annotations

import numpy as np
import pytest

from iios.investment.market.correlation.rolling_correlation import RollingCorrelationCalculator
from iios.investment.market.correlation.pearson_estimator import PearsonEstimator
from iios.investment.market.correlation.models import CorrelationMethod

from tests.unit.investment.market.correlation.conftest import (
    make_correlated_snapshots,
    make_anti_correlated_snapshots,
)


def _returns_from_snaps(snaps):
    return [s.returns() for s in snaps]


class TestRollingCorrelationCalculator:
    def _make(self, window=30, min_obs=5):
        return RollingCorrelationCalculator(
            window=window,
            estimator=PearsonEstimator(),
            min_observations=min_obs,
        )

    def test_none_before_min_observations(self):
        calc = self._make(window=30, min_obs=10)
        for i in range(5):
            result = calc.update({"A": 0.01, "B": -0.01}, i, float(i))
        assert result is None

    def test_returns_matrix_after_min_obs(self):
        calc = self._make(window=30, min_obs=5)
        matrix = None
        for i in range(10):
            matrix = calc.update({"A": 0.01 * i, "B": -0.005 * i}, i, float(i))
        assert matrix is not None

    def test_window_respects_maxlen(self):
        calc = self._make(window=5, min_obs=3)
        for i in range(20):
            calc.update({"A": float(i), "B": -float(i)}, i, float(i))
        arr = calc.get_returns("A")
        assert len(arr) == 5  # capped at window

    def test_new_symbol_auto_added(self):
        calc = self._make()
        calc.update({"A": 0.01}, 0, 0.0)
        calc.update({"A": 0.01, "B": -0.01}, 1, 1.0)
        assert "B" in calc.all_symbols()

    def test_history_length(self):
        calc = self._make()
        for i in range(8):
            calc.update({"A": 0.01, "B": -0.01}, i, float(i))
        assert calc.history_length("A") == 8

    def test_correlated_positive(self):
        calc = self._make(window=60, min_obs=5)
        snaps = make_correlated_snapshots(80, ["P", "Q"], target_corr=0.90)
        matrix = None
        for s in snaps:
            matrix = calc.update(s.returns(), s.bar_index, s.timestamp)
        assert matrix is not None
        r = matrix.get("P", "Q")
        assert r is not None
        assert r > 0.40

    def test_anti_correlated_negative(self):
        calc = self._make(window=60, min_obs=5)
        snaps = make_anti_correlated_snapshots(80, "X", "Y")
        matrix = None
        for s in snaps:
            matrix = calc.update(s.returns(), s.bar_index, s.timestamp)
        assert matrix is not None
        r = matrix.get("X", "Y")
        assert r is not None
        assert r < 0.0

    def test_matrix_confidence_grows(self):
        calc = self._make(window=30, min_obs=5)
        matrix = None
        for i in range(10):
            matrix = calc.update({"A": 0.01, "B": -0.01}, i, float(i))
        early_conf = matrix.confidence if matrix else 0.0
        for i in range(10, 35):
            matrix = calc.update({"A": 0.01, "B": -0.01}, i, float(i))
        assert matrix is not None
        assert matrix.confidence >= early_conf

    def test_window_property(self):
        calc = self._make(window=45)
        assert calc.window == 45

    def test_nan_return_skipped(self):
        calc = self._make(min_obs=3)
        for i in range(10):
            calc.update({"A": float("nan"), "B": 0.01}, i, float(i))
        # Should not crash; history for A should be empty
        assert calc.history_length("A") == 0
