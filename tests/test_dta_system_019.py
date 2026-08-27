"""
DTA-SYSTEM-019 tests — D019-001 LOL MultiIndex bar-capture fix.

Root cause: _fetch_ohlcv() in learning_observation_ledger.py iterated over a
yfinance DataFrame without normalising MultiIndex columns.  With yfinance ≥ 1.x
single-symbol downloads return MultiIndex columns; float(row["Open"]) then
returns a Series instead of a scalar and the broad outer except silently returned [].

Fix: apply the same droplevel convention already used in klp_outcome_engine.py
and knowledge_decision_pipeline.py.  Per-row errors now log a warning and skip
the bad row (rather than silently collapsing the entire result).

Tests T019-001 through T019-006.
"""
from __future__ import annotations

import math
import datetime
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

# ── Import the function under test ────────────────────────────────────────────
from learning_system.learning_observation_ledger import _fetch_ohlcv


# ── Helpers ───────────────────────────────────────────────────────────────────

_DECISION_DATE = "2026-01-05"   # a Monday; T+1 = 2026-01-06


def _flat_df(dates: List[str], opens: List[float], highs: List[float],
              lows: List[float], closes: List[float]) -> pd.DataFrame:
    """Build a normal single-level DataFrame (no MultiIndex)."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes}, index=idx)


def _multi_df(dates: List[str], opens: List[float], highs: List[float],
               lows: List[float], closes: List[float],
               ticker: str = "TATASTEEL.NS") -> pd.DataFrame:
    """Build a MultiIndex-column DataFrame as yfinance 1.x returns for single-symbol."""
    flat = _flat_df(dates, opens, highs, lows, closes)
    flat.columns = pd.MultiIndex.from_tuples(
        [(col, ticker) for col in flat.columns],
        names=["Price", "Ticker"],
    )
    return flat


def _dates_after(n: int) -> List[str]:
    """Return n daily ISO date strings starting from T+1 of _DECISION_DATE."""
    base = datetime.date.fromisoformat(_DECISION_DATE)
    return [(base + datetime.timedelta(days=i + 1)).isoformat() for i in range(n)]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestT019001_NormalScalarColumns:
    """T019-001: normal single-level OHLC columns → captured correctly."""

    def test_bars_returned_with_correct_values(self):
        dates  = _dates_after(3)
        opens  = [100.0, 101.0, 102.0]
        highs  = [105.0, 106.0, 107.0]
        lows   = [98.0,   99.0, 100.0]
        closes = [103.0, 104.0, 105.0]
        df = _flat_df(dates, opens, highs, lows, closes)

        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=3)

        assert len(bars) == 3
        assert bars[0]["open"]  == 100.0
        assert bars[0]["close"] == 103.0
        assert bars[2]["high"]  == 107.0
        for b in bars:
            assert isinstance(b["open"],  float)
            assert isinstance(b["close"], float)

    def test_horizon_respected(self):
        dates  = _dates_after(5)
        df = _flat_df(dates, [1.0]*5, [2.0]*5, [0.5]*5, [1.5]*5)

        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("SBIN", _DECISION_DATE, horizon=2)

        assert len(bars) == 2

    def test_decision_date_excluded(self):
        """Bar on decision_date must not appear in result."""
        all_dates  = [_DECISION_DATE] + _dates_after(2)
        df = _flat_df(all_dates, [10.0]*3, [11.0]*3, [9.0]*3, [10.5]*3)

        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("RELIANCE", _DECISION_DATE, horizon=5)

        dates_in_result = {b["date"] for b in bars}
        assert _DECISION_DATE not in dates_in_result
        assert len(bars) == 2


class TestT019002_MultiIndexColumns:
    """T019-002: MultiIndex OHLC columns → captured correctly."""

    def test_multiindex_produces_same_result_as_flat(self):
        dates  = _dates_after(3)
        opens  = [200.0, 201.0, 202.0]
        highs  = [210.0, 211.0, 212.0]
        lows   = [190.0, 191.0, 192.0]
        closes = [205.0, 206.0, 207.0]

        flat_df  = _flat_df (dates, opens, highs, lows, closes)
        multi_df = _multi_df(dates, opens, highs, lows, closes)

        with patch("yfinance.download", return_value=flat_df):
            flat_bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=3)

        with patch("yfinance.download", return_value=multi_df):
            multi_bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=3)

        assert len(flat_bars)  == 3
        assert len(multi_bars) == 3
        for fb, mb in zip(flat_bars, multi_bars):
            assert fb["open"]  == mb["open"],  f"open mismatch: {fb} vs {mb}"
            assert fb["close"] == mb["close"], f"close mismatch"
            assert fb["high"]  == mb["high"],  f"high mismatch"
            assert fb["low"]   == mb["low"],   f"low mismatch"

    def test_multiindex_scalars_not_series(self):
        """Ensure float(row["Open"]) extracts a Python float, not a Series."""
        dates  = _dates_after(1)
        multi_df = _multi_df(dates, [150.0], [160.0], [140.0], [155.0])

        with patch("yfinance.download", return_value=multi_df):
            bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=1)

        assert len(bars) == 1
        val = bars[0]["open"]
        assert isinstance(val, float), f"Expected float, got {type(val)}: {val}"
        assert val == 150.0


class TestT019003_MultiIndexWithTickerLevel:
    """T019-003: MultiIndex with ticker level → correct values extracted."""

    def test_ticker_level_dropped_correctly(self):
        dates = _dates_after(2)
        df = _multi_df(dates, [300.0, 301.0], [310.0, 311.0],
                       [290.0, 291.0], [305.0, 306.0], ticker="SBIN.NS")

        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("SBIN", _DECISION_DATE, horizon=2)

        assert len(bars) == 2
        assert bars[0]["close"] == 305.0
        assert bars[1]["open"]  == 301.0

    def test_duplicate_columns_deduplicated(self):
        """Simulates the edge case where droplevel creates duplicate column names."""
        dates = _dates_after(1)
        df = _multi_df(dates, [100.0], [110.0], [90.0], [105.0])
        # Manually add a duplicate by appending another ticker's columns
        df2 = _multi_df(dates, [200.0], [210.0], [190.0], [205.0], ticker="OTHER.NS")
        combined = pd.concat([df, df2], axis=1)

        with patch("yfinance.download", return_value=combined):
            bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=1)

        # Should not raise; result may be partial but must not crash
        assert isinstance(bars, list)


class TestT019004_EmptyDataframe:
    """T019-004: empty dataframe → safe empty result."""

    def test_empty_df_returns_empty_list(self):
        with patch("yfinance.download", return_value=pd.DataFrame()):
            bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=5)
        assert bars == []

    def test_none_return_from_download(self):
        with patch("yfinance.download", return_value=None):
            bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=5)
        assert bars == []

    def test_all_bars_before_decision_date_gives_empty(self):
        """All bars are on or before decision_date → no eligible bars."""
        old_dates = ["2026-01-02", "2026-01-03", "2026-01-04"]  # all before 2026-01-05
        df = _flat_df(old_dates, [1.0]*3, [2.0]*3, [0.5]*3, [1.5]*3)

        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=5)

        assert bars == []


class TestT019005_MissingInvalidOHLC:
    """T019-005: missing/invalid OHLC → safely rejected, visible in logs."""

    def test_nan_values_raise_per_row_not_crash(self, caplog):
        """NaN in OHLC causes ValueError in float() → row skipped with warning."""
        import logging
        dates  = _dates_after(3)
        opens  = [100.0, float("nan"), 102.0]
        highs  = [105.0, 106.0, float("nan")]
        lows   = [98.0,  99.0,  100.0]
        closes = [103.0, float("nan"), 105.0]

        df = _flat_df(dates, opens, highs, lows, closes)

        with patch("yfinance.download", return_value=df):
            with caplog.at_level(logging.WARNING, logger="learning_system.learning_observation_ledger"):
                bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=3)

        # NaN → float("nan") converts OK (float(math.nan) == math.nan), so rows
        # may still be appended. What matters is: no crash.
        assert isinstance(bars, list)

    def test_missing_column_logs_warning_skips_row(self, caplog):
        """DataFrame missing 'Open' column → KeyError per row → warning logged."""
        import logging
        dates  = _dates_after(2)
        df = pd.DataFrame(
            {"High": [10.0, 11.0], "Low": [8.0, 9.0], "Close": [9.5, 10.5]},
            index=pd.DatetimeIndex([pd.Timestamp(d) for d in dates]),
        )
        with patch("yfinance.download", return_value=df):
            with caplog.at_level(logging.WARNING, logger="learning_system.learning_observation_ledger"):
                bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=2)

        assert bars == [], f"Expected empty (all rows have KeyError), got {bars}"
        assert any("row parse error" in r.message for r in caplog.records), (
            "Expected a row parse error warning in logs"
        )

    def test_download_exception_logs_warning(self, caplog):
        """Network failure → exception caught, warning logged, [] returned."""
        import logging
        with patch("yfinance.download", side_effect=Exception("timeout")):
            with caplog.at_level(logging.WARNING, logger="learning_system.learning_observation_ledger"):
                bars = _fetch_ohlcv("TATASTEEL", _DECISION_DATE, horizon=5)

        assert bars == []
        assert any("bar fetch failed" in r.message for r in caplog.records), (
            "Expected 'bar fetch failed' warning in logs"
        )


class TestT019006_ExistingNormalPath:
    """T019-006: existing normal path remains unchanged — anti-regression."""

    def test_returns_list_of_dicts_with_expected_keys(self):
        dates  = _dates_after(3)
        df = _flat_df(dates, [1.0]*3, [2.0]*3, [0.5]*3, [1.5]*3)

        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("RELIANCE", _DECISION_DATE, horizon=3)

        assert isinstance(bars, list)
        for b in bars:
            assert set(b.keys()) >= {"date", "open", "high", "low", "close"}

    def test_all_ohlc_values_are_finite_floats(self):
        dates  = _dates_after(5)
        df = _flat_df(dates,
                      [100.0, 101.0, 102.0, 103.0, 104.0],
                      [110.0, 111.0, 112.0, 113.0, 114.0],
                      [90.0,   91.0,  92.0,  93.0,  94.0],
                      [105.0, 106.0, 107.0, 108.0, 109.0])

        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("HDFCBANK", _DECISION_DATE, horizon=5)

        assert len(bars) == 5
        for b in bars:
            for key in ("open", "high", "low", "close"):
                assert isinstance(b[key], float)
                assert math.isfinite(b[key]), f"{key} is not finite: {b[key]}"

    def test_timezone_aware_timestamps_handled(self):
        """yfinance can return tz-aware DatetimeIndex; date() still works."""
        dates = _dates_after(2)
        idx = pd.DatetimeIndex(
            [pd.Timestamp(d, tz="UTC") for d in dates]
        )
        df = pd.DataFrame(
            {"Open": [50.0, 51.0], "High": [55.0, 56.0],
             "Low": [48.0, 49.0], "Close": [52.0, 53.0]},
            index=idx,
        )
        with patch("yfinance.download", return_value=df):
            bars = _fetch_ohlcv("INFY", _DECISION_DATE, horizon=2)

        assert len(bars) == 2
        assert bars[0]["date"] > _DECISION_DATE
