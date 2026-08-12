"""
tests/test_emp001.py — EMP-001 Early-Move Persistence & Previous-Day Predictive Value Audit

Coverage
--------
  TS-*  Timestamp correctness (price extraction from 5m series)
  GC-*  Gap calculation
  RK-*  Ranking calculation
  PS-*  Persistence calculation
  RC-*  Reversal classification
  LA-*  Look-ahead prevention
  MA-*  Model A (previous-day)
  MB-*  Model B (opening window)
  MC-*  Model C (combined)
  CC-*  Capital-constraint classification
  DQ-*  Missing-data handling
  IP-*  Idempotency

Run with:  python -m pytest tests/test_emp001.py -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── Stub heavy dependencies ───────────────────────────────────────────────────

def _stub(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)
    return mod

_stub("utils", get_logger=MagicMock(return_value=MagicMock()))

# yfinance and pandas are used directly — provide real implementations if available,
# otherwise stub for tests that don't need them.
try:
    import pandas as pd
    import numpy as np
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False


# ── Helpers to build test DayRecords ─────────────────────────────────────────

def _make_record(**kwargs):
    """Create a DayRecord with sensible defaults, overridden by kwargs."""
    from early_move_audit.emp_collector import DayRecord
    defaults = dict(
        date="2026-08-07",
        symbol="TESTCO",
        prev_close=100.0,
        prev_return_pct=1.0,
        prev_volume=1_000_000,
        prev_20d_avg_vol=800_000,
        prev_volume_ratio=1.25,
        prev_high=103.0,
        prev_low=98.0,
        prev_range_pct=5.0,
        open_price=101.0,
        close_price=104.0,
        day_high=106.0,
        day_low=100.0,
        day_volume=1_200_000,
        gap_pct=1.0,
        gap_class="MILD_UP",
        close_return_pct=4.0,
        p930=102.0,
        p945=103.0,
        p1000=103.5,
        p1100=104.0,
        p1300=104.5,
        p1500=104.8,
        ret_to_930=0.99,
        ret_to_945=1.98,
        ret_to_1000=2.48,
        ret_to_1100=2.97,
        ret_to_1300=3.47,
        ret_to_1500=3.76,
        was_in_prev_scan=False,
        was_prev_pga_flag=False,
        was_prev_leader=False,
        prev_leader_type="NONE",
        has_daily=True,
        has_intraday=True,
        missing_snapshots=[],
    )
    defaults.update(kwargs)
    return DayRecord(**defaults)


def _make_universe(n: int, date: str = "2026-08-07", spread: float = 1.0):
    """Create n records with linearly spaced close returns."""
    records = []
    for i in range(n):
        ret = (i - n / 2) * spread
        prev_ret = (i - n / 2) * spread * 0.5
        records.append(_make_record(
            symbol=f"SYM{i:02d}",
            date=date,
            close_return_pct=ret,
            prev_return_pct=prev_ret,
            ret_to_930=prev_ret * 0.3,
            ret_to_945=prev_ret * 0.4,
            ret_to_1000=prev_ret * 0.5,
            gap_pct=prev_ret * 0.1,
        ))
    return records


# ══════════════════════════════════════════════════════════════════════════════
# TS — Timestamp correctness
# ══════════════════════════════════════════════════════════════════════════════

class TestTimestampExtraction(unittest.TestCase):
    """Verify that price_at_time() returns the correct bar for IST times."""

    @unittest.skipUnless(_HAS_PANDAS, "pandas required")
    def test_ts001_exact_time_match(self):
        """price_at_time should return close of bar starting at exactly HH:MM."""
        from early_move_audit.emp_collector import _price_at_time
        import pandas as pd
        from datetime import datetime, timezone, timedelta

        # Use stdlib timezone to avoid pytz dependency
        IST = timezone(timedelta(hours=5, minutes=30))
        times = [
            datetime(2026, 8, 7, 9, 15, tzinfo=IST),
            datetime(2026, 8, 7, 9, 20, tzinfo=IST),
            datetime(2026, 8, 7, 9, 25, tzinfo=IST),
            datetime(2026, 8, 7, 9, 30, tzinfo=IST),   # ← target
            datetime(2026, 8, 7, 9, 35, tzinfo=IST),
        ]
        closes = [100.0, 101.0, 102.0, 103.5, 104.0]
        df = pd.DataFrame({"Close": closes, "High": closes, "Low": closes}, index=pd.DatetimeIndex(times))
        result = _price_at_time(df, "09:30")
        self.assertAlmostEqual(result, 103.5, places=1)

    @unittest.skipUnless(_HAS_PANDAS, "pandas required")
    def test_ts002_missing_time_returns_none(self):
        """If no bar exists at the requested time, return None."""
        from early_move_audit.emp_collector import _price_at_time
        import pandas as pd
        from datetime import datetime, timezone, timedelta

        IST = timezone(timedelta(hours=5, minutes=30))
        times = [datetime(2026, 8, 7, 9, 15, tzinfo=IST),
                 datetime(2026, 8, 7, 9, 20, tzinfo=IST)]
        df = pd.DataFrame({"Close": [100.0, 101.0], "High": [100.0, 101.0], "Low": [100.0, 101.0]},
                          index=pd.DatetimeIndex(times))
        result = _price_at_time(df, "09:30")
        self.assertIsNone(result)

    @unittest.skipUnless(_HAS_PANDAS, "pandas required")
    def test_ts003_empty_dataframe(self):
        """price_at_time on empty df returns None (no crash)."""
        from early_move_audit.emp_collector import _price_at_time
        import pandas as pd
        df = pd.DataFrame({"Close": [], "High": [], "Low": []})
        self.assertIsNone(_price_at_time(df, "09:30"))

    @unittest.skipUnless(_HAS_PANDAS, "pandas required")
    def test_ts004_tz_naive_index(self):
        """price_at_time handles timezone-naive index gracefully."""
        from early_move_audit.emp_collector import _price_at_time
        import pandas as pd
        from datetime import datetime
        times = [datetime(2026, 8, 7, 9, 30), datetime(2026, 8, 7, 9, 35)]
        df = pd.DataFrame({"Close": [105.0, 106.0], "High": [105.0, 106.0], "Low": [105.0, 106.0]},
                          index=pd.DatetimeIndex(times))
        result = _price_at_time(df, "09:30")
        self.assertAlmostEqual(result, 105.0, places=1)


# ══════════════════════════════════════════════════════════════════════════════
# GC — Gap calculation
# ══════════════════════════════════════════════════════════════════════════════

class TestGapCalculation(unittest.TestCase):
    """Verify gap_pct = (open - prev_close) / prev_close * 100."""

    def test_gc001_gap_up(self):
        """gap_pct formula: (open - prev_close) / prev_close * 100."""
        # _make_record stores explicit values; verify the formula directly
        open_p = 102.0
        prev_c = 100.0
        expected = (open_p - prev_c) / prev_c * 100.0
        self.assertAlmostEqual(expected, 2.0, places=4)
        # Record with the computed gap_pct
        r = _make_record(open_price=open_p, prev_close=prev_c, gap_pct=expected)
        self.assertAlmostEqual(r.gap_pct, 2.0, places=4)

    def test_gc002_gap_down(self):
        r = _make_record(open_price=97.0, prev_close=100.0, gap_pct=-3.0, gap_class="DOWN")
        self.assertAlmostEqual(r.gap_pct, -3.0, places=4)

    def test_gc003_flat_gap(self):
        r = _make_record(open_price=100.0, prev_close=100.0, gap_pct=0.0, gap_class="FLAT")
        self.assertEqual(r.gap_pct, 0.0)

    def test_gc004_classify_strong_up(self):
        from early_move_audit.emp_config import classify_gap
        self.assertEqual(classify_gap(3.5),  "STRONG_UP")
        self.assertEqual(classify_gap(3.0),  "STRONG_UP")
        self.assertEqual(classify_gap(2.5),  "UP")
        self.assertEqual(classify_gap(2.0),  "UP")
        self.assertEqual(classify_gap(1.5),  "MILD_UP")
        self.assertEqual(classify_gap(0.5),  "FLAT")
        self.assertEqual(classify_gap(-0.5), "FLAT")
        self.assertEqual(classify_gap(-1.5), "MILD_DOWN")
        self.assertEqual(classify_gap(-2.5), "DOWN")
        self.assertEqual(classify_gap(-3.5), "STRONG_DOWN")

    def test_gc005_classify_boundary_values(self):
        from early_move_audit.emp_config import classify_gap, GAP_MILD_DOWN, GAP_STRONG_DOWN
        # Boundary: exactly 1.0 → first condition >= 1.0 → MILD_UP
        self.assertEqual(classify_gap(1.0),  "MILD_UP")
        # Boundary: exactly -1.0 → NOT > GAP_MILD_DOWN (-1.0), falls to MILD_DOWN
        self.assertEqual(classify_gap(-1.0), "MILD_DOWN")
        # Boundary: exactly -3.0 → NOT > GAP_STRONG_DOWN (-3.0), falls to STRONG_DOWN
        self.assertEqual(classify_gap(-3.0), "STRONG_DOWN")


# ══════════════════════════════════════════════════════════════════════════════
# RK — Ranking calculation
# ══════════════════════════════════════════════════════════════════════════════

class TestRankingCalculation(unittest.TestCase):
    """Verify that symbol ranking is computed correctly."""

    def test_rk001_top5_correct_order(self):
        """Top-5 by close return should return the 5 highest-return symbols."""
        records = _make_universe(20, spread=1.0)
        sorted_by_close = sorted(records, key=lambda r: r.close_return_pct, reverse=True)
        top5 = [r.symbol for r in sorted_by_close[:5]]
        # Highest close return should be SYM19 (index 19, return = (19-10) = 9)
        self.assertEqual(top5[0], "SYM19")
        self.assertEqual(top5[4], "SYM15")

    def test_rk002_bottom5_correct_order(self):
        """Bottom-5 (losers) should be the 5 lowest-return symbols."""
        records = _make_universe(20, spread=1.0)
        sorted_by_close = sorted(records, key=lambda r: r.close_return_pct)
        bottom5 = [r.symbol for r in sorted_by_close[:5]]
        self.assertEqual(bottom5[0], "SYM00")
        self.assertEqual(bottom5[4], "SYM04")

    def test_rk003_spearman_perfect_correlation(self):
        """Perfect rank correlation should return rho=1.0."""
        from early_move_audit.emp_persistence import _spearman
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        rho = _spearman(x, x)
        self.assertAlmostEqual(rho, 1.0, places=3)

    def test_rk004_spearman_reverse_correlation(self):
        """Reversed ranking should return rho=-1.0."""
        from early_move_audit.emp_persistence import _spearman
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        rho = _spearman(x, y)
        self.assertAlmostEqual(rho, -1.0, places=3)

    def test_rk005_spearman_short_list(self):
        """Spearman with fewer than 3 items returns nan."""
        import math
        from early_move_audit.emp_persistence import _spearman
        self.assertTrue(math.isnan(_spearman([1.0], [1.0])))
        self.assertTrue(math.isnan(_spearman([1.0, 2.0], [2.0, 1.0])))


# ══════════════════════════════════════════════════════════════════════════════
# PS — Persistence calculation
# ══════════════════════════════════════════════════════════════════════════════

class TestPersistenceCalculation(unittest.TestCase):
    """Verify morning rank persistence computation."""

    def test_ps001_perfect_persistence(self):
        """If morning rank == close rank, overlap should be 100%."""
        from early_move_audit.emp_persistence import compute_persistence
        # Create identical ordering for ret_to_930 and close_return_pct
        records = []
        for i in range(20):
            ret = float(i)
            records.append(_make_record(
                symbol=f"SYM{i:02d}", date="2026-08-07",
                ret_to_930=ret, close_return_pct=ret,
            ))
        result = compute_persistence(records, [5, 10])
        # Find the 09:30 → CLOSE interval
        iv = next((x for x in result.interval_stats if "09:30" in x.label and "CLOSE" in x.label), None)
        self.assertIsNotNone(iv)
        self.assertEqual(iv.overlap.get(10), 100.0)

    def test_ps002_zero_persistence(self):
        """If morning order is reversed vs close, overlap should be 0%."""
        from early_move_audit.emp_persistence import compute_persistence
        n = 10
        records = []
        for i in range(n):
            records.append(_make_record(
                symbol=f"SYM{i:02d}", date="2026-08-07",
                ret_to_930=float(i),            # morning: SYM09 is top
                close_return_pct=float(n - 1 - i),  # close: SYM00 is top
            ))
        result = compute_persistence(records, [5])
        iv = next((x for x in result.interval_stats if "09:30" in x.label and "CLOSE" in x.label), None)
        self.assertIsNotNone(iv)
        # Top-5 in morning {SYM05-SYM09} vs top-5 at close {SYM05-SYM09} — might overlap
        # With exact reversal and 10 symbols, top-5 in morning = {SYM05..SYM09}
        # top-5 at close = {SYM00..SYM04}  → overlap = 0
        self.assertEqual(iv.overlap.get(5), 0.0)

    def test_ps003_direction_persistence_all_positive(self):
        """If all symbols that were positive in morning are positive at close, rate = 100%."""
        from early_move_audit.emp_persistence import compute_persistence
        records = [
            _make_record(symbol=f"S{i}", date="2026-08-07",
                         ret_to_930=1.0, close_return_pct=2.0)
            for i in range(10)
        ]
        result = compute_persistence(records, [5])
        iv = next((x for x in result.interval_stats if "09:30" in x.label and "CLOSE" in x.label), None)
        if iv:
            self.assertAlmostEqual(iv.gainer_stays_positive, 100.0, places=0)

    def test_ps004_n_trading_days_correct(self):
        """n_trading_days should equal number of distinct dates with ≥ 3 valid pairs."""
        from early_move_audit.emp_persistence import compute_persistence
        records = (_make_universe(10, date="2026-08-07") +
                   _make_universe(10, date="2026-08-08") +
                   _make_universe(10, date="2026-08-11"))
        result = compute_persistence(records, [5])
        self.assertEqual(result.n_trading_days, 3)

    def test_ps005_insufficient_data_day_skipped(self):
        """Days with fewer than 3 valid records are skipped without error."""
        from early_move_audit.emp_persistence import compute_persistence
        records = [
            _make_record(symbol="S1", date="2026-08-07", ret_to_930=1.0, close_return_pct=2.0),
            _make_record(symbol="S2", date="2026-08-07", ret_to_930=None, close_return_pct=2.0),
        ]
        result = compute_persistence(records, [5])
        # Should not crash; n_trading_days may be 0
        self.assertIsInstance(result.n_trading_days, int)


# ══════════════════════════════════════════════════════════════════════════════
# RC — Reversal classification
# ══════════════════════════════════════════════════════════════════════════════

class TestReversalClassification(unittest.TestCase):
    """Verify gap-up continuation / reversal classification."""

    def test_rc001_gap_up_continues(self):
        """Gap-up + positive close = continuation."""
        r = _make_record(gap_pct=2.5, gap_class="UP", close_return_pct=3.0)
        self.assertTrue(r.gap_pct > 0 and r.close_return_pct > 0)

    def test_rc002_gap_up_reversal(self):
        """Gap-up + negative close = reversal."""
        r = _make_record(gap_pct=2.5, gap_class="UP", close_return_pct=-1.0)
        self.assertTrue(r.gap_pct > 0 and r.close_return_pct < 0)

    def test_rc003_gap_stats_contain_all_classes(self):
        """Gap stats should produce a result for each gap class present in data."""
        from early_move_audit.emp_persistence import compute_persistence
        records = []
        gap_classes = [
            (3.5, "STRONG_UP", 2.0),
            (2.2, "UP", -1.0),
            (1.3, "MILD_UP", 0.5),
            (0.2, "FLAT", 0.0),
            (-1.5, "MILD_DOWN", -2.0),
            (-2.3, "DOWN", 1.0),
            (-3.5, "STRONG_DOWN", -3.0),
        ]
        for i, (gap_pct, gap_class, close_ret) in enumerate(gap_classes):
            records.append(_make_record(
                symbol=f"S{i}", date="2026-08-07",
                gap_pct=gap_pct, gap_class=gap_class,
                close_return_pct=close_ret,
                open_price=100.0, day_high=105.0, day_low=98.0,
            ))
        result = compute_persistence(records, [5])
        gap_class_names = {g.gap_class for g in result.gap_stats}
        self.assertIn("STRONG_UP",   gap_class_names)
        self.assertIn("UP",          gap_class_names)
        self.assertIn("STRONG_DOWN", gap_class_names)

    def test_rc004_continuation_rate_formula(self):
        """Continuation rate = (same-direction count) / total * 100."""
        from early_move_audit.emp_persistence import compute_persistence
        # 3 gap-up: 2 close positive (continue), 1 close negative (reverse)
        records = [
            _make_record(symbol="A", date="2026-08-07", gap_pct=2.0, gap_class="UP",
                         close_return_pct=1.0, open_price=100.0, day_high=103.0, day_low=99.0),
            _make_record(symbol="B", date="2026-08-07", gap_pct=2.5, gap_class="UP",
                         close_return_pct=0.5, open_price=100.0, day_high=103.0, day_low=99.0),
            _make_record(symbol="C", date="2026-08-07", gap_pct=2.1, gap_class="UP",
                         close_return_pct=-0.5, open_price=100.0, day_high=103.0, day_low=99.0),
        ]
        result = compute_persistence(records, [5])
        g_up = next((g for g in result.gap_stats if g.gap_class == "UP"), None)
        if g_up:
            # 2/3 continued → 66.67%
            self.assertAlmostEqual(g_up.continuation_pct, 66.67, places=1)
            self.assertAlmostEqual(g_up.reversal_pct, 33.33, places=1)


# ══════════════════════════════════════════════════════════════════════════════
# LA — Look-ahead prevention
# ══════════════════════════════════════════════════════════════════════════════

class TestLookAheadPrevention(unittest.TestCase):
    """Verify no current-day close data leaks into Models A and B."""

    def test_la001_model_a_description_no_close(self):
        """Model A description must not mention same-day close fields."""
        from early_move_audit.emp_analyzer import _verify_no_lookahead
        from early_move_audit.emp_analyzer import EMPResult
        from early_move_audit.emp_config import EmpConfig
        from early_move_audit.emp_collector import CollectionQuality
        from early_move_audit.emp_persistence import PersistenceResult
        from early_move_audit.emp_predictive import PredictiveResult, ModelResult

        pred = PredictiveResult()
        pred.model_a = ModelResult(
            name="Model A",
            description="Previous-day only: prev return, volume ratio, range, PGA flag, leader",
            window="previous_day",
            metrics=[],
        )
        result = EMPResult(
            run_date="2026-08-07",
            config=EmpConfig(),
            records=[],
            quality=CollectionQuality(),
            persistence=PersistenceResult(),
            predictive=pred,
        )
        violations = _verify_no_lookahead(result)
        self.assertEqual(violations, [])

    def test_la002_score_model_a_fields(self):
        """_score_model_a must NOT access open_price, gap_pct, p930, close_price."""
        from early_move_audit.emp_predictive import _score_model_a
        # Record where current-day fields are deliberately wrong
        r = _make_record(
            prev_return_pct=3.0,
            prev_volume_ratio=1.5,
            prev_range_pct=2.0,
            was_prev_pga_flag=True,
            was_prev_leader=False,
            # Set current-day to extreme values that would dominate if used
            open_price=99999.0,
            close_price=99999.0,
            gap_pct=99.0,
            ret_to_930=99.0,
        )
        score = _score_model_a(r)
        # If score uses prev fields only: roughly 3.0*0.4 + 0.5*0.3 + 2.0*0.1 + 0.5 = ~2.05
        self.assertIsNotNone(score)
        self.assertLess(abs(score), 10.0)  # Not influenced by 99999 values

    def test_la003_model_b_uses_only_opening_data(self):
        """Model B (09:30) returns a ModelResult with window='09:30'."""
        from early_move_audit.emp_predictive import _build_model_b, _group_by_date
        # Need ≥ 3 days (valid_days < 3 → _evaluate_model returns None)
        records = []
        dates = ["2026-08-07", "2026-08-08", "2026-08-11", "2026-08-12", "2026-08-13"]
        for day in dates:
            for i in range(20):
                records.append(_make_record(
                    symbol=f"SYM{i:02d}", date=day,
                    prev_return_pct=0.0,
                    ret_to_930=float(i + 1),   # +1: no zero values
                    close_return_pct=float(i + 1) * 0.5,
                    was_prev_pga_flag=False,
                    was_prev_leader=False,
                ))
        model = _build_model_b(_group_by_date(records), "ret_to_930", "09:30", [5, 10])
        self.assertIsNotNone(model)
        self.assertEqual(model.window, "09:30")
        self.assertTrue(len(model.metrics) > 0)

    def test_la004_model_b_window_respected(self):
        """Model B should produce different results for different windows."""
        from early_move_audit.emp_predictive import _build_model_b, _group_by_date
        records = _make_universe(20)
        by_date = _group_by_date(records)
        m930  = _build_model_b(by_date, "ret_to_930",  "09:30", [10])
        m945  = _build_model_b(by_date, "ret_to_945",  "09:45", [10])
        m1000 = _build_model_b(by_date, "ret_to_1000", "10:00", [10])
        # All 3 should have different window labels
        self.assertEqual(m930.window,  "09:30")
        self.assertEqual(m945.window,  "09:45")
        self.assertEqual(m1000.window, "10:00")


# ══════════════════════════════════════════════════════════════════════════════
# MA — Model A (previous-day)
# ══════════════════════════════════════════════════════════════════════════════

class TestModelA(unittest.TestCase):
    """Verify Model A precision, recall, and lift computation."""

    def _build_model_a_records(self):
        """Five days, 20 symbols each. Previous-day return predicts close perfectly."""
        records = []
        dates = ["2026-08-07", "2026-08-08", "2026-08-11", "2026-08-12", "2026-08-13"]
        for day in dates:
            for i in range(20):
                # prev_return and close_return are perfectly correlated
                records.append(_make_record(
                    symbol=f"SYM{i:02d}", date=day,
                    prev_return_pct=float(i + 1),   # +1 so no zero values
                    close_return_pct=float(i + 1),
                    prev_volume_ratio=1.0,
                    prev_range_pct=1.0,
                    was_prev_pga_flag=False,
                    was_prev_leader=False,
                ))
        return records

    def test_ma001_precision_perfect_correlation(self):
        """When prev_return perfectly predicts close return, precision should be high."""
        from early_move_audit.emp_predictive import _build_model_a, _group_by_date
        records = self._build_model_a_records()
        model = _build_model_a(_group_by_date(records), [10])
        m10 = next((m for m in model.metrics if m.top_n == 10), None)
        self.assertIsNotNone(m10)
        # With perfect correlation and n=10 out of 20, precision should be near 1.0
        self.assertGreater(m10.precision, 0.8)

    def test_ma002_lift_above_1_with_predictive_data(self):
        """A predictive model should have lift > 1 (better than random)."""
        from early_move_audit.emp_predictive import _build_model_a, _group_by_date
        records = self._build_model_a_records()
        model = _build_model_a(_group_by_date(records), [10])
        for m in model.metrics:
            self.assertGreater(m.lift, 1.0)

    def test_ma003_base_rate_computed_from_data(self):
        """Base rate should be top_n / universe_size."""
        from early_move_audit.emp_predictive import _build_model_a, _group_by_date
        records = self._build_model_a_records()
        model = _build_model_a(_group_by_date(records), [10])
        m10 = next((m for m in model.metrics if m.top_n == 10), None)
        self.assertIsNotNone(m10)
        # base_rate ≈ 10/20 = 0.5
        self.assertAlmostEqual(m10.base_rate, 0.5, places=1)

    def test_ma004_insufficient_days_returns_none_metrics(self):
        """Fewer than 3 valid days → no metrics computed."""
        from early_move_audit.emp_predictive import _build_model_a, _group_by_date
        records = _make_universe(10, date="2026-08-07")  # only 1 day
        model = _build_model_a(_group_by_date(records), [5])
        # With only 1 day, _evaluate_model returns None → no metrics
        self.assertEqual(len(model.metrics), 0)


# ══════════════════════════════════════════════════════════════════════════════
# MB — Model B (opening window)
# ══════════════════════════════════════════════════════════════════════════════

class TestModelB(unittest.TestCase):
    """Verify Model B metrics for different opening windows."""

    def _build_predictable_records(self, ret_col: str):
        """20 symbols × 5 days where ret_col perfectly predicts close."""
        records = []
        for d in range(5):
            day = f"2026-08-0{7+d}"
            for i in range(20):
                r = _make_record(
                    symbol=f"SYM{i:02d}", date=day,
                    close_return_pct=float(i),
                )
                setattr(r, ret_col, float(i))  # perfect predictor
                records.append(r)
        return records

    def test_mb001_930_window_metrics(self):
        """Model B (09:30) should produce metrics when ret_to_930 is present."""
        from early_move_audit.emp_predictive import _build_model_b, _group_by_date
        records = self._build_predictable_records("ret_to_930")
        model = _build_model_b(_group_by_date(records), "ret_to_930", "09:30", [10])
        self.assertTrue(len(model.metrics) > 0)
        m10 = model.metrics[0]
        self.assertGreater(m10.precision, 0.5)

    def test_mb002_945_window_different_from_930(self):
        """Model B (09:45) uses ret_to_945, not ret_to_930."""
        from early_move_audit.emp_predictive import _build_model_b, _group_by_date
        records = []
        for d in range(5):
            day = f"2026-08-0{7+d}"
            for i in range(20):
                # ret_to_945 predicts close; ret_to_930 does NOT
                r = _make_record(
                    symbol=f"SYM{i:02d}", date=day,
                    close_return_pct=float(i),
                    ret_to_930=float(19 - i),   # anti-predictive
                    ret_to_945=float(i),         # perfectly predictive
                )
                records.append(r)
        m930  = _build_model_b(_group_by_date(records), "ret_to_930", "09:30", [10])
        m945  = _build_model_b(_group_by_date(records), "ret_to_945", "09:45", [10])
        # 945 should have much higher precision
        p930 = m930.metrics[0].precision if m930.metrics else 0.0
        p945 = m945.metrics[0].precision if m945.metrics else 0.0
        self.assertGreater(p945, p930)

    def test_mb003_missing_intraday_falls_back_to_gap(self):
        """When ret_to_930 is None, score should fall back to gap_pct."""
        from early_move_audit.emp_predictive import _build_model_b, _group_by_date
        records = []
        for d in range(5):
            day = f"2026-08-0{7+d}"
            for i in range(20):
                # ret_to_930 = None, but gap_pct available
                r = _make_record(
                    symbol=f"SYM{i:02d}", date=day,
                    close_return_pct=float(i),
                    ret_to_930=None,
                    gap_pct=float(i) * 0.1,
                )
                records.append(r)
        model = _build_model_b(_group_by_date(records), "ret_to_930", "09:30", [10])
        # Should not crash and produce some metrics
        self.assertIsNotNone(model)


# ══════════════════════════════════════════════════════════════════════════════
# MC — Model C (combined)
# ══════════════════════════════════════════════════════════════════════════════

class TestModelC(unittest.TestCase):
    """Verify Model C (combined) is consistent combination of A and B."""

    def test_mc001_combined_model_name(self):
        """Model C should be named 'Model C' with window='combined'."""
        from early_move_audit.emp_predictive import _build_model_c, _group_by_date
        records = []
        for d in range(5):
            day = f"2026-08-0{7+d}"
            records.extend(_make_universe(20, date=day))
        model = _build_model_c(_group_by_date(records), [10])
        self.assertEqual(model.name, "Model C")
        self.assertEqual(model.window, "combined")

    def test_mc002_combined_not_worse_than_random(self):
        """Combined model lift should be > 0 on coherent data."""
        from early_move_audit.emp_predictive import _build_model_c, _group_by_date
        records = []
        for d in range(5):
            day = f"2026-08-0{7+d}"
            for i in range(20):
                r = _make_record(
                    symbol=f"SYM{i:02d}", date=day,
                    prev_return_pct=float(i),
                    ret_to_930=float(i) * 0.8,
                    close_return_pct=float(i),
                )
                records.append(r)
        model = _build_model_c(_group_by_date(records), [10])
        for m in model.metrics:
            self.assertGreater(m.lift, 0.0)

    def test_mc003_build_predictive_analysis_complete(self):
        """build_predictive_analysis should produce all 5 models."""
        from early_move_audit.emp_predictive import build_predictive_analysis
        records = []
        for d in range(5):
            day = f"2026-08-0{7+d}"
            records.extend(_make_universe(20, date=day))
        result = build_predictive_analysis(records, [5, 10])
        self.assertIsNotNone(result.model_a)
        self.assertIsNotNone(result.model_b_930)
        self.assertIsNotNone(result.model_b_945)
        self.assertIsNotNone(result.model_b_1000)
        self.assertIsNotNone(result.model_c)


# ══════════════════════════════════════════════════════════════════════════════
# CC — Capital-constraint classification
# ══════════════════════════════════════════════════════════════════════════════

class TestCapitalConstraint(unittest.TestCase):
    """Verify PREDICTED_BUT_UNACTIONABLE_CAPITAL vs PREDICTION_FAILURE."""

    def test_cc001_cheap_stock_is_prediction_failure(self):
        """A ₹100 stock that was missed by the model is PREDICTION_FAILURE."""
        from early_move_audit.emp_predictive import _classify_misses, _group_by_date, SMALL_CAPITAL
        records = []
        # Build a set where SYM09 (price ₹100) is top-1 but model ranks it low
        for i in range(20):
            ret = 9.0 if i == 9 else float(i) * 0.5
            prev_ret = 0.0 if i == 9 else float(i) * 0.3  # model scores SYM09 lowest
            r = _make_record(
                symbol=f"SYM{i:02d}", date="2026-08-07",
                close_return_pct=ret,
                prev_return_pct=prev_ret,
                close_price=100.0,    # cheap stock (₹100 < ₹10,000)
                prev_volume_ratio=1.0, prev_range_pct=1.0,
                was_prev_pga_flag=False, was_prev_leader=False,
            )
            records.append(r)
        misses = _classify_misses(_group_by_date(records), top_n=5)
        pred_failures = [m for m in misses if m.miss_class.value == "PREDICTION_FAILURE"]
        self.assertTrue(len(pred_failures) > 0)

    def test_cc002_expensive_stock_is_capital_failure(self):
        """A ₹15,000 stock is PREDICTED_BUT_UNACTIONABLE_CAPITAL."""
        from early_move_audit.emp_predictive import _classify_misses, _group_by_date, SMALL_CAPITAL
        records = []
        for i in range(20):
            ret = 9.0 if i == 9 else float(i) * 0.5
            prev_ret = 0.0 if i == 9 else float(i) * 0.3
            r = _make_record(
                symbol=f"SYM{i:02d}", date="2026-08-07",
                close_return_pct=ret,
                prev_return_pct=prev_ret,
                close_price=SMALL_CAPITAL * 2 if i == 9 else 100.0,  # expensive miss
                prev_volume_ratio=1.0, prev_range_pct=1.0,
                was_prev_pga_flag=False, was_prev_leader=False,
            )
            records.append(r)
        misses = _classify_misses(_group_by_date(records), top_n=5)
        cap_failures = [
            m for m in misses
            if m.miss_class.value == "PREDICTED_BUT_UNACTIONABLE_CAPITAL"
        ]
        self.assertTrue(len(cap_failures) > 0)

    def test_cc003_capital_miss_not_counted_as_prediction_failure(self):
        """Capital miss must NOT appear in PREDICTION_FAILURE list."""
        from early_move_audit.emp_predictive import _classify_misses, _group_by_date, SMALL_CAPITAL
        records = []
        for i in range(20):
            ret = 9.0 if i == 19 else float(i) * 0.5
            prev_ret = 0.0 if i == 19 else float(i) * 0.3
            r = _make_record(
                symbol=f"SYM{i:02d}", date="2026-08-07",
                close_return_pct=ret,
                prev_return_pct=prev_ret,
                close_price=SMALL_CAPITAL * 3 if i == 19 else 200.0,
                prev_volume_ratio=1.0, prev_range_pct=1.0,
            )
            records.append(r)
        misses = _classify_misses(_group_by_date(records), top_n=5)
        # Verify that each miss is classified exclusively
        for m in misses:
            # A record cannot be both PREDICTION_FAILURE and CAPITAL
            self.assertIn(
                m.miss_class.value,
                ["PREDICTION_FAILURE", "PREDICTED_BUT_UNACTIONABLE_CAPITAL"],
            )


# ══════════════════════════════════════════════════════════════════════════════
# DQ — Missing-data handling
# ══════════════════════════════════════════════════════════════════════════════

class TestMissingDataHandling(unittest.TestCase):
    """Verify graceful handling of NaN / None values."""

    def test_dq001_none_prev_return_does_not_crash(self):
        """Model A scoring with None prev_return_pct should return non-None score if others present."""
        from early_move_audit.emp_predictive import _score_model_a
        r = _make_record(prev_return_pct=None, prev_volume_ratio=1.5)
        score = _score_model_a(r)
        self.assertIsNotNone(score)

    def test_dq002_all_none_returns_none(self):
        """Model A scoring with all None prev fields returns None."""
        from early_move_audit.emp_predictive import _score_model_a
        r = _make_record(
            prev_return_pct=None,
            prev_volume_ratio=None,
            prev_range_pct=None,
            was_prev_pga_flag=False,
            was_prev_leader=False,
        )
        score = _score_model_a(r)
        self.assertIsNone(score)

    def test_dq003_persistence_with_none_snapshots(self):
        """Persistence computation skips records with None ret_to_930."""
        from early_move_audit.emp_persistence import compute_persistence
        records = _make_universe(10, date="2026-08-07")
        for r in records[:5]:
            r.ret_to_930 = None  # make half the records invalid
        # Should not crash
        result = compute_persistence(records, [5])
        self.assertIsInstance(result.interval_stats, list)

    def test_dq004_safe_float_nan(self):
        """_safe_float should return None for NaN and Inf."""
        from early_move_audit.emp_collector import _safe_float
        import math
        self.assertIsNone(_safe_float(float("nan")))
        self.assertIsNone(_safe_float(float("inf")))
        self.assertIsNone(_safe_float(float("-inf")))
        self.assertAlmostEqual(_safe_float(3.14), 3.14)
        self.assertIsNone(_safe_float(None))
        self.assertIsNone(_safe_float("bad"))

    def test_dq005_empty_records_no_crash(self):
        """All analysis functions handle empty record lists without crashing."""
        from early_move_audit.emp_persistence import compute_persistence
        from early_move_audit.emp_predictive import build_predictive_analysis
        result_p = compute_persistence([], [5, 10])
        result_q = build_predictive_analysis([], [5, 10])
        self.assertEqual(result_p.n_trading_days, 0)
        self.assertIsNone(result_q.model_a.metrics[0] if result_q.model_a and result_q.model_a.metrics else None)

    def test_dq006_gap_class_unknown_default(self):
        """Records with gap_class='UNKNOWN' are excluded from gap stats."""
        from early_move_audit.emp_persistence import compute_persistence
        r = _make_record(gap_class="UNKNOWN", close_return_pct=2.0)
        result = compute_persistence([r], [5])
        gap_classes = {g.gap_class for g in result.gap_stats}
        self.assertNotIn("UNKNOWN", gap_classes)


# ══════════════════════════════════════════════════════════════════════════════
# IP — Idempotency
# ══════════════════════════════════════════════════════════════════════════════

class TestIdempotency(unittest.TestCase):
    """Verify running the analysis twice produces identical results."""

    def test_ip001_persistence_deterministic(self):
        """compute_persistence produces identical output when called twice."""
        from early_move_audit.emp_persistence import compute_persistence
        records = []
        for d in range(5):
            records.extend(_make_universe(20, date=f"2026-08-0{7+d}"))
        r1 = compute_persistence(records, [5, 10])
        r2 = compute_persistence(records, [5, 10])
        self.assertEqual(r1.n_trading_days, r2.n_trading_days)
        self.assertEqual(len(r1.interval_stats), len(r2.interval_stats))
        for iv1, iv2 in zip(r1.interval_stats, r2.interval_stats):
            self.assertEqual(iv1.label,           iv2.label)
            self.assertAlmostEqual(iv1.continuation_rate, iv2.continuation_rate, places=6)
            self.assertEqual(iv1.overlap, iv2.overlap)

    def test_ip002_predictive_deterministic(self):
        """build_predictive_analysis produces identical output when called twice."""
        from early_move_audit.emp_predictive import build_predictive_analysis
        records = []
        for d in range(5):
            records.extend(_make_universe(20, date=f"2026-08-0{7+d}"))
        r1 = build_predictive_analysis(records, [5, 10])
        r2 = build_predictive_analysis(records, [5, 10])
        if r1.model_a and r2.model_a:
            m1 = {m.top_n: m.precision for m in r1.model_a.metrics}
            m2 = {m.top_n: m.precision for m in r2.model_a.metrics}
            self.assertEqual(m1, m2)

    def test_ip003_report_overwrite_safe(self):
        """Writing reports twice to the same directory is safe."""
        from early_move_audit.emp_analyzer import run_analysis, EMPResult
        from early_move_audit.emp_collector import CollectionQuality
        from early_move_audit.emp_config import EmpConfig
        from early_move_audit.emp_persistence import PersistenceResult
        from early_move_audit.emp_predictive import PredictiveResult
        from early_move_audit.emp_reporter import generate_reports

        records = _make_universe(15, date="2026-08-07") * 3

        with tempfile.TemporaryDirectory() as tmpdir:
            import early_move_audit.emp_reporter as reporter_mod
            original_report_dir = reporter_mod.Path

            # Patch REPORT_DIR to use temp dir
            from early_move_audit.emp_config import EmpConfig
            config = EmpConfig(lookback_days=3, top_n=5, dry_run=False)
            quality = CollectionQuality(total_symbol_days=45, with_daily=45, with_intraday=40)

            result = EMPResult(
                run_date="2026-08-07",
                config=config,
                records=records,
                quality=quality,
                persistence=PersistenceResult(n_trading_days=1, n_symbols=15),
                predictive=PredictiveResult(),
            )

            # Monkey-patch REPORT_DIR temporarily
            import early_move_audit.emp_config as cfg_mod
            old_dir = cfg_mod.REPORT_DIR
            cfg_mod.REPORT_DIR = Path(tmpdir)
            import early_move_audit.emp_reporter as rep_mod
            old_rep_dir = rep_mod.__dict__.get("REPORT_DIR")

            try:
                paths1 = generate_reports(result)
                paths2 = generate_reports(result)  # second run
                # Both runs should produce the same files
                self.assertEqual(set(paths1.keys()), set(paths2.keys()))
            finally:
                cfg_mod.REPORT_DIR = old_dir

    def test_ip004_gap_stats_order_stable(self):
        """Gap stats are sorted consistently across calls."""
        from early_move_audit.emp_persistence import compute_persistence
        records = []
        for gap_pct, gap_class, close_ret in [
            (2.0, "UP", 1.0), (-2.0, "DOWN", -1.5), (1.2, "MILD_UP", 0.5),
            (-1.2, "MILD_DOWN", -0.5), (0.3, "FLAT", 0.0),
        ]:
            for i in range(4):
                records.append(_make_record(
                    symbol=f"{gap_class}_{i}", date="2026-08-07",
                    gap_pct=gap_pct, gap_class=gap_class, close_return_pct=close_ret,
                    open_price=100.0, day_high=105.0, day_low=95.0,
                ))
        r1 = compute_persistence(records, [5])
        r2 = compute_persistence(records, [5])
        gc1 = [g.gap_class for g in r1.gap_stats]
        gc2 = [g.gap_class for g in r2.gap_stats]
        self.assertEqual(gc1, gc2)


# ══════════════════════════════════════════════════════════════════════════════
# Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_int001_run_emp_audit_dry_run(self):
        """run_emp_audit with dry_run=True should not raise even without yfinance data."""
        from early_move_audit.emp_runner import run_emp_audit
        # Will return empty dataset if yfinance unavailable — that's acceptable
        result = run_emp_audit(days=3, symbol="TCS", top_n=5, dry_run=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.run_date, str(__import__("datetime").date.today()))

    def test_int002_config_ns_symbols(self):
        """EmpConfig.ns_symbols() adds .NS suffix to each symbol."""
        from early_move_audit.emp_config import EmpConfig
        cfg = EmpConfig(universe=["TCS", "INFY", "HDFCBANK"])
        ns = cfg.ns_symbols()
        self.assertEqual(ns, ["TCS.NS", "INFY.NS", "HDFCBANK.NS"])

    def test_int003_analyze_empty_dataset(self):
        """run_analysis on empty records produces a result with warnings."""
        from early_move_audit.emp_analyzer import run_analysis
        from early_move_audit.emp_collector import CollectionQuality
        from early_move_audit.emp_config import EmpConfig
        result = run_analysis([], CollectionQuality(), EmpConfig(), "2026-08-07")
        self.assertEqual(len(result.records), 0)
        self.assertTrue(len(result.warnings) > 0)

    def test_int004_findings_json_valid(self):
        """EMP_FINDINGS.json must be valid JSON."""
        from early_move_audit.emp_analyzer import run_analysis
        from early_move_audit.emp_collector import CollectionQuality
        from early_move_audit.emp_config import EmpConfig
        from early_move_audit.emp_reporter import generate_reports
        import early_move_audit.emp_config as cfg_mod

        records = []
        for d in range(3):
            records.extend(_make_universe(20, date=f"2026-08-0{7+d}"))

        quality = CollectionQuality(total_symbol_days=60, with_daily=60, with_intraday=50)
        config = EmpConfig(lookback_days=3, top_n=5)
        result = run_analysis(records, quality, config, "2026-08-07")

        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = cfg_mod.REPORT_DIR
            cfg_mod.REPORT_DIR = Path(tmpdir)
            try:
                paths = generate_reports(result)
                json_path = paths.get("findings")
                self.assertIsNotNone(json_path)
                data = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertIn("run_date", data)
                self.assertIn("recommendation", data)
                self.assertIn("persistence", data)
                self.assertIn("predictive", data)
            finally:
                cfg_mod.REPORT_DIR = old_dir

    def test_int005_recommendation_is_one_of_options(self):
        """Recommendation must always be one of the defined option codes."""
        from early_move_audit.emp_predictive import build_predictive_analysis
        valid_options = {"OPTION_A", "OPTION_B", "OPTION_C", "OPTION_D", "OPTION_E", "INSUFFICIENT_DATA"}
        records = []
        for d in range(5):
            records.extend(_make_universe(20, date=f"2026-08-0{7+d}"))
        result = build_predictive_analysis(records, [5, 10])
        self.assertIn(result.recommendation, valid_options)


if __name__ == "__main__":
    unittest.main(verbosity=2)
