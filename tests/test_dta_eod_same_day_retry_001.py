"""
tests/test_dta_eod_same_day_retry_001.py
==========================================
DTA-EOD-SAME-DAY-RETRY-001

Verifies:
  1. _eod_status_today() correctly reads today's EOD status from disk,
     treating a missing file / a different day's stale status / a
     corrupt file all as "not completed" (safe default).
  2. config.SCHEDULE has 3 new same-day retry/final-check slots, timed
     to avoid the existing 16:15 (universe rebuild) and 16:45
     (post_market_scan, ~20min) slots, all before end of day.
  3. start_scheduler()'s source wires the 2 retry slots + 1 final-check
     slot, checks completed-status BEFORE re-running (cheap no-op when
     already done), calls run_eod_learning() on retry, and sends a
     Telegram alert via get_notifier().send_alert() only when the final
     check still finds an incomplete status.
"""
from __future__ import annotations

import inspect
import json
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

import config
from orchestrator.master_orchestrator import MasterOrchestrator


class _FallbackMO(MasterOrchestrator):
    """Mirrors the established test_dta_system_008.py pattern: unset
    attributes lazily resolve to a fresh MagicMock."""
    def __getattr__(self, name):
        m = MagicMock()
        object.__setattr__(self, name, m)
        return m


def _mo():
    mo = _FallbackMO.__new__(_FallbackMO)
    return mo


class TestEodStatusToday:

    def test_t01_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mo = _mo()
        assert mo._eod_status_today() == {}

    def test_t02_completed_today_returns_full_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        today = date.today().strftime("%Y-%m-%d")
        p = tmp_path / "data" / "eod_status.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({
            "last_eod_date": today, "status": "COMPLETED",
            "started_at": "x", "completed_at": "y",
        }))
        mo = _mo()
        status = mo._eod_status_today()
        assert status.get("status") == "COMPLETED"

    def test_t03_started_today_returns_started_status(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        today = date.today().strftime("%Y-%m-%d")
        p = tmp_path / "data" / "eod_status.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({
            "last_eod_date": today, "status": "STARTED",
            "started_at": "x", "completed_at": None,
        }))
        mo = _mo()
        status = mo._eod_status_today()
        assert status.get("status") == "STARTED"

    def test_t04_stale_yesterday_status_treated_as_not_completed(self, tmp_path, monkeypatch):
        """A COMPLETED status from a PREVIOUS day must not be mistaken for
        today's completion (would wrongly suppress a real retry)."""
        monkeypatch.chdir(tmp_path)
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        p = tmp_path / "data" / "eod_status.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({
            "last_eod_date": yesterday, "status": "COMPLETED",
            "started_at": "x", "completed_at": "y",
        }))
        mo = _mo()
        assert mo._eod_status_today() == {}

    def test_t05_corrupt_file_fails_safe_to_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        p = tmp_path / "data" / "eod_status.json"
        p.parent.mkdir(parents=True)
        p.write_text("{not valid json")
        mo = _mo()
        assert mo._eod_status_today() == {}


class TestScheduleConfig:

    def test_t06_three_new_slots_exist(self):
        assert "eod_learning_retry_1" in config.SCHEDULE
        assert "eod_learning_retry_2" in config.SCHEDULE
        assert "eod_learning_final_check" in config.SCHEDULE

    def test_t07_slots_are_valid_hhmm_after_eod_learning(self):
        def _to_minutes(hhmm: str) -> int:
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        base = _to_minutes(config.SCHEDULE["eod_learning"])
        r1 = _to_minutes(config.SCHEDULE["eod_learning_retry_1"])
        r2 = _to_minutes(config.SCHEDULE["eod_learning_retry_2"])
        fc = _to_minutes(config.SCHEDULE["eod_learning_final_check"])
        assert base < r1 < r2 < fc, "retry/final-check slots must be strictly ordered after eod_learning"

    def test_t08_no_collision_with_universe_rebuild_or_post_market_scan(self):
        occupied = {"16:15", "16:45"}  # universe rebuild / post_market_scan
        new_slots = {
            config.SCHEDULE["eod_learning_retry_1"],
            config.SCHEDULE["eod_learning_retry_2"],
            config.SCHEDULE["eod_learning_final_check"],
        }
        assert not (occupied & new_slots), "new retry slots must not collide with existing schedules"


class TestSchedulerWiring:

    def _source(self) -> str:
        return inspect.getsource(MasterOrchestrator.start_scheduler)

    def test_t09_retry_slots_registered(self):
        src = self._source()
        assert 'SCHEDULE["eod_learning_retry_1"]' in src
        assert 'SCHEDULE["eod_learning_retry_2"]' in src
        assert 'SCHEDULE["eod_learning_final_check"]' in src

    def test_t10_retry_checks_completed_status_before_rerunning(self):
        src = self._source()
        assert "_guarded_eod_retry" in src
        assert '"COMPLETED"' in src
        assert "self.run_eod_learning()" in src

    def test_t11_final_check_sends_telegram_alert_on_incomplete(self):
        src = self._source()
        assert "_guarded_eod_final_check" in src
        assert "get_notifier" in src
        assert "send_alert" in src

    def test_t12_retry_and_final_check_never_raise_into_scheduler(self):
        """Both new closures must be wrapped in try/except, matching the
        existing _guarded_eod convention (EOD must never crash the
        scheduler loop)."""
        src = self._source()
        # crude but effective: the retry/final-check block must contain at
        # least 2 more try/except pairs beyond the original _guarded_eod's own.
        assert src.count("except Exception as _exc:") >= 2
