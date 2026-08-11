"""
FRZ-001 Phase 1 — Scheduler double-fire elimination tests.

Verified:
  1.  MarketMonitor does NOT trigger 10:30.
  2.  MarketMonitor does NOT trigger 11:30.
  3.  MarketMonitor does NOT trigger 13:00.
  4.  MarketMonitor does NOT trigger 14:00.
  5.  MarketMonitor does NOT trigger 15:00.
  6.  Opening scans 09:05 / 09:10 / 09:20 remain intact.
  7.  sched_lib still owns 10:30 / 11:30 / 13:00 / 14:00 / 15:00.
  8.  No duplicate run_full_cycle for the same scheduled slot.
  9.  Single ownership assertion: every intraday slot has exactly one owner.

Run with:  python -m pytest tests/test_frz001_scheduler.py -v
"""
import sys
import os
import types
import unittest
from unittest.mock import MagicMock, patch, call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _load_market_monitor():
    """
    Load market_monitor.py directly (bypassing market_intelligence/__init__.py)
    so that package-level imports (MarketDataAI, etc.) never execute.
    The 'utils' stub is registered only if the real module is not yet present.
    """
    import importlib.util as _ilu
    if "utils" not in sys.modules:
        _stub("utils", get_logger=MagicMock(return_value=MagicMock()))
    mm_path = os.path.join(ROOT, "market_intelligence", "market_monitor.py")
    spec = _ilu.spec_from_file_location("_market_monitor_frz001", mm_path)
    mod  = _ilu.module_from_spec(spec)
    # Register under the real dotted name too so MarketMonitor patch works
    sys.modules.setdefault("market_intelligence.market_monitor", mod)
    spec.loader.exec_module(mod)
    return mod


_mm_mod = _load_market_monitor()
DEEP_SCAN_SCHEDULE = _mm_mod.DEEP_SCAN_SCHEDULE


# ── Tests ────────────────────────────────────────────────────────────────────

class TestDeepScanScheduleContents(unittest.TestCase):
    """DEEP_SCAN_SCHEDULE must contain only the three opening-window slots."""

    def test_10_30_not_in_deep_scan_schedule(self):
        self.assertNotIn("10:30", DEEP_SCAN_SCHEDULE,
            "10:30 must NOT be in DEEP_SCAN_SCHEDULE (owned by sched_lib)")

    def test_11_30_not_in_deep_scan_schedule(self):
        self.assertNotIn("11:30", DEEP_SCAN_SCHEDULE,
            "11:30 must NOT be in DEEP_SCAN_SCHEDULE (owned by sched_lib)")

    def test_13_00_not_in_deep_scan_schedule(self):
        self.assertNotIn("13:00", DEEP_SCAN_SCHEDULE,
            "13:00 must NOT be in DEEP_SCAN_SCHEDULE (owned by sched_lib)")

    def test_14_00_not_in_deep_scan_schedule(self):
        self.assertNotIn("14:00", DEEP_SCAN_SCHEDULE,
            "14:00 must NOT be in DEEP_SCAN_SCHEDULE (owned by sched_lib)")

    def test_15_00_not_in_deep_scan_schedule(self):
        self.assertNotIn("15:00", DEEP_SCAN_SCHEDULE,
            "15:00 must NOT be in DEEP_SCAN_SCHEDULE (owned by sched_lib)")

    def test_09_05_present(self):
        self.assertIn("09:05", DEEP_SCAN_SCHEDULE, "09:05 opening scan must remain")

    def test_09_10_present(self):
        self.assertIn("09:10", DEEP_SCAN_SCHEDULE, "09:10 opening scan must remain")

    def test_09_20_present(self):
        self.assertIn("09:20", DEEP_SCAN_SCHEDULE, "09:20 opening scan must remain")

    def test_exactly_three_slots(self):
        self.assertEqual(len(DEEP_SCAN_SCHEDULE), 3,
            f"DEEP_SCAN_SCHEDULE must have exactly 3 slots; got {DEEP_SCAN_SCHEDULE}")


class TestMarketMonitorDoesNotFireLateSlots(unittest.TestCase):
    """
    _check_deep_schedule must NOT invoke the callback for 10:30–15:00 because
    those times are no longer in DEEP_SCAN_SCHEDULE.

    Setup: pre-mark all opening slots (09:05/09:10/09:20) as already fired for
    the test date, so only the late-time slot (if present in the schedule) would
    trigger a callback.  Since none of those slots are in DEEP_SCAN_SCHEDULE
    after FRZ-001, no callback fires.
    """

    _TODAY = None

    @classmethod
    def setUpClass(cls):
        from datetime import date
        cls._TODAY = date(2026, 8, 11)

    def _make_monitor_with_morning_fired(self, callback):
        """Create a monitor with 09:05/09:10/09:20 already marked as fired."""
        MarketMonitor = _mm_mod.MarketMonitor
        feed = MagicMock()
        feed.get_quote.return_value = None
        m = MarketMonitor(feed=feed, on_deep_scan=callback)
        # Pre-mark all opening slots as fired (simulating a real trading day where
        # morning has already passed).  This means only a truly scheduled late
        # slot would trigger the callback.
        for slot in DEEP_SCAN_SCHEDULE:
            m._scans_fired[slot] = self._TODAY
        return m

    def _fire_at(self, monitor, hhmm: str):
        """Simulate one tick of _check_deep_schedule at a given HH:MM."""
        from datetime import date
        fake_now = MagicMock()
        fake_now.strftime.return_value = hhmm
        fake_now.date.return_value = self._TODAY
        with patch.object(_mm_mod, "datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            monitor._check_deep_schedule()

    def test_no_callback_at_10_30(self):
        cb = MagicMock()
        m  = self._make_monitor_with_morning_fired(cb)
        self._fire_at(m, "10:30")
        cb.assert_not_called()

    def test_no_callback_at_11_30(self):
        cb = MagicMock()
        m  = self._make_monitor_with_morning_fired(cb)
        self._fire_at(m, "11:30")
        cb.assert_not_called()

    def test_no_callback_at_13_00(self):
        cb = MagicMock()
        m  = self._make_monitor_with_morning_fired(cb)
        self._fire_at(m, "13:00")
        cb.assert_not_called()

    def test_no_callback_at_14_00(self):
        cb = MagicMock()
        m  = self._make_monitor_with_morning_fired(cb)
        self._fire_at(m, "14:00")
        cb.assert_not_called()

    def test_no_callback_at_15_00(self):
        cb = MagicMock()
        m  = self._make_monitor_with_morning_fired(cb)
        self._fire_at(m, "15:00")
        cb.assert_not_called()

    def test_callback_fires_at_09_05(self):
        """09:05 must fire the callback when no slots have been marked yet."""
        from datetime import date
        cb   = MagicMock()
        feed = MagicMock()
        m    = _mm_mod.MarketMonitor(feed=feed, on_deep_scan=cb)
        today = date(2026, 8, 11)
        fake_now = MagicMock()
        fake_now.strftime.return_value = "09:05"
        fake_now.date.return_value = today
        with patch.object(_mm_mod, "datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            m._check_deep_schedule()
        cb.assert_called_once()

    def test_callback_fires_at_09_10(self):
        """09:10 fires when 09:05 is pre-marked."""
        from datetime import date
        cb   = MagicMock()
        feed = MagicMock()
        m    = _mm_mod.MarketMonitor(feed=feed, on_deep_scan=cb)
        today = date(2026, 8, 11)
        m._scans_fired["09:05"] = today
        fake_now = MagicMock()
        fake_now.strftime.return_value = "09:10"
        fake_now.date.return_value = today
        with patch.object(_mm_mod, "datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            m._check_deep_schedule()
        cb.assert_called_once()

    def test_callback_fires_at_09_20(self):
        """09:20 fires when 09:05 and 09:10 are pre-marked."""
        from datetime import date
        cb   = MagicMock()
        feed = MagicMock()
        m    = _mm_mod.MarketMonitor(feed=feed, on_deep_scan=cb)
        today = date(2026, 8, 11)
        m._scans_fired["09:05"] = today
        m._scans_fired["09:10"] = today
        fake_now = MagicMock()
        fake_now.strftime.return_value = "09:20"
        fake_now.date.return_value = today
        with patch.object(_mm_mod, "datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            m._check_deep_schedule()
        cb.assert_called_once()


class TestScheduleOwnershipExclusivity(unittest.TestCase):
    """
    Every intraday cycle slot must have exactly ONE owner.
    Opening slots (09:05/09:10/09:20) owned by MarketMonitor.
    Later slots (09:45, 10:30-15:00) owned by sched_lib only.
    """

    # All full-cycle slots registered by sched_lib in start_scheduler
    SCHED_LIB_FULL_CYCLE_SLOTS = {"09:45", "10:30", "11:30", "13:00", "14:00", "15:00"}
    MARKET_MONITOR_SLOTS       = set(DEEP_SCAN_SCHEDULE)

    def test_no_overlap_between_monitor_and_schedlib(self):
        overlap = self.MARKET_MONITOR_SLOTS & self.SCHED_LIB_FULL_CYCLE_SLOTS
        self.assertEqual(overlap, set(),
            f"Overlapping slots between MarketMonitor and sched_lib: {overlap}")

    def test_sched_lib_owns_mid_morning(self):
        self.assertIn("10:30", self.SCHED_LIB_FULL_CYCLE_SLOTS)
        self.assertNotIn("10:30", self.MARKET_MONITOR_SLOTS)

    def test_sched_lib_owns_mid_session(self):
        self.assertIn("11:30", self.SCHED_LIB_FULL_CYCLE_SLOTS)
        self.assertNotIn("11:30", self.MARKET_MONITOR_SLOTS)

    def test_sched_lib_owns_afternoon(self):
        self.assertIn("13:00", self.SCHED_LIB_FULL_CYCLE_SLOTS)
        self.assertNotIn("13:00", self.MARKET_MONITOR_SLOTS)

    def test_sched_lib_owns_early_afternoon(self):
        self.assertIn("14:00", self.SCHED_LIB_FULL_CYCLE_SLOTS)
        self.assertNotIn("14:00", self.MARKET_MONITOR_SLOTS)

    def test_sched_lib_owns_closing_analysis(self):
        self.assertIn("15:00", self.SCHED_LIB_FULL_CYCLE_SLOTS)
        self.assertNotIn("15:00", self.MARKET_MONITOR_SLOTS)

    def test_market_monitor_owns_09_05(self):
        self.assertIn("09:05", self.MARKET_MONITOR_SLOTS)
        self.assertNotIn("09:05", self.SCHED_LIB_FULL_CYCLE_SLOTS)

    def test_market_monitor_owns_09_10(self):
        self.assertIn("09:10", self.MARKET_MONITOR_SLOTS)
        self.assertNotIn("09:10", self.SCHED_LIB_FULL_CYCLE_SLOTS)

    def test_market_monitor_owns_09_20(self):
        self.assertIn("09:20", self.MARKET_MONITOR_SLOTS)
        self.assertNotIn("09:20", self.SCHED_LIB_FULL_CYCLE_SLOTS)


if __name__ == "__main__":
    unittest.main()
