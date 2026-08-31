"""
Regression test — DTA-FIX-024
Guards against reintroduction of the undefined _pd_MultiIndex NameError
in validate_and_refresh_sr_levels().

Run:  python -m pytest test_sr_validator_multiindex.py -v
"""
import inspect
import types
import unittest
from unittest.mock import patch

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Helper: build minimal watchlist stubs
# ---------------------------------------------------------------------------
_STUB_WATCHLIST = [
    {"symbol": "RELIANCE    ", "base_ltp": 2900.0, "resistance": 2950.0, "support": 2850.0, "volume_ratio": 1.0, "rsi": 50.0, "adv_crore": 1000},
    {"symbol": "INFY        ", "base_ltp": 1500.0, "resistance": 1550.0, "support": 1450.0, "volume_ratio": 1.0, "rsi": 50.0, "adv_crore": 800},
]


def _make_multiindex_df(symbols_ns: list[str]) -> pd.DataFrame:
    """Simulate yfinance multi-symbol download: MultiIndex columns (metric, symbol)."""
    closes = {sym: np.array([2900.0, 2910.0]) for sym in symbols_ns}
    arrays = [
        ["Close"] * len(symbols_ns),
        symbols_ns,
    ]
    mi = pd.MultiIndex.from_arrays(arrays, names=["Price", "Ticker"])
    data = np.column_stack([closes[s] for s in symbols_ns])
    return pd.DataFrame(data, columns=mi)


def _make_single_index_df(symbol_ns: str) -> pd.DataFrame:
    """Simulate yfinance single-symbol download: single-level columns."""
    return pd.DataFrame({"Close": [2900.0, 2910.0], "Open": [2890.0, 2900.0]})


# ---------------------------------------------------------------------------
# T001 — _pd_MultiIndex must NOT appear in the source of the function
# ---------------------------------------------------------------------------
class TestNoPdMultiIndexSymbol(unittest.TestCase):
    def test_t001_undefined_alias_absent_from_source(self):
        """
        REGRESSION GUARD: _pd_MultiIndex must never appear in
        validate_and_refresh_sr_levels source again.
        """
        import opportunity_engine.equity_scanner_ai as esa
        src = inspect.getsource(esa.validate_and_refresh_sr_levels)
        self.assertNotIn(
            "_pd_MultiIndex",
            src,
            "_pd_MultiIndex alias has been reintroduced — DTA-FIX-024 regression",
        )


# ---------------------------------------------------------------------------
# T002 — MultiIndex path: runs without NameError, parses LTPs
# ---------------------------------------------------------------------------
class TestSRValidatorMultiIndex(unittest.TestCase):
    def _run_with_mock(self, mock_df: pd.DataFrame):
        import opportunity_engine.equity_scanner_ai as esa
        symbols_ns = [e["symbol"].strip() + ".NS" for e in _STUB_WATCHLIST]

        with (
            patch.object(esa, "_BASE_WATCHLIST", _STUB_WATCHLIST),
            patch.object(esa, "_EXTENDED_WATCHLIST", []),
            patch.object(esa, "_sr_last_refresh_date", ""),
            patch("yfinance.download", return_value=mock_df),
        ):
            # Reset the module-level guard so the function actually runs
            esa._sr_last_refresh_date = ""
            result = esa.validate_and_refresh_sr_levels()
        return result

    def test_t002_multiindex_columns_no_nameerror(self):
        """MultiIndex DataFrame must not raise NameError."""
        symbols_ns = [e["symbol"].strip() + ".NS" for e in _STUB_WATCHLIST]
        df = _make_multiindex_df(symbols_ns)
        # Must complete without exception
        result = self._run_with_mock(df)
        self.assertIn("error", result)
        self.assertIn("repaired", result)

    def test_t003_single_index_columns_no_nameerror(self):
        """Single-level column DataFrame must not raise NameError."""
        df = _make_single_index_df("RELIANCE.NS")
        result = self._run_with_mock(df)
        self.assertIn("error", result)
        self.assertIn("repaired", result)

    def test_t004_empty_dataframe_returns_error(self):
        """Empty yfinance response must return error, not crash."""
        import opportunity_engine.equity_scanner_ai as esa
        empty_df = pd.DataFrame()
        with (
            patch.object(esa, "_BASE_WATCHLIST", _STUB_WATCHLIST),
            patch.object(esa, "_EXTENDED_WATCHLIST", []),
            patch.object(esa, "_sr_last_refresh_date", ""),
            patch("yfinance.download", return_value=empty_df),
        ):
            esa._sr_last_refresh_date = ""
            result = esa.validate_and_refresh_sr_levels()
        self.assertEqual(result["repaired"], 0)
        self.assertIsNotNone(result["error"])

    def test_t005_same_day_guard_skips(self):
        """Same-day guard must return skipped=True immediately."""
        import opportunity_engine.equity_scanner_ai as esa
        from datetime import date
        today = date.today().isoformat()
        original = esa._sr_last_refresh_date
        try:
            esa._sr_last_refresh_date = today
            result = esa.validate_and_refresh_sr_levels()
            self.assertTrue(result.get("skipped"), "Expected skipped=True when already refreshed today")
        finally:
            esa._sr_last_refresh_date = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
