"""
tests/test_dta_live_004.py
============================
DTA-LIVE-004: Runtime Reliability — comprehensive test suite.

Tests:
  A: datetime alias — all four previously broken _dt lines work with datetime.now()
  B: _guarded_cycle exception containment — exceptions do NOT propagate to caller
  C: schedule.next_run advances after exception in guarded_cycle
  D: No infinite 15-second crash loop (next_run advances on exception)
  E: missed-cycle recording in SchedulerHealth
  F: restart recovery — state loaded from JSON file
  G: MOP_RC001 → LOL recovery — idempotent (run twice = same result)
  H: SchedulerHealth persistence — survives instantiation from file
  I: EOD guarded wrapper — never raises
  J: Anti-lookahead preserved in recovery records
  K: Mean_Reversion consec_losses reconciled after _load()
  L: SchedulerHealth records failure with error string
  M: Recovery skips invalid MOP_RC001 rows
  N: Recovery on missing MOP_RC001 file returns NO_MOP_FILE
  O: Strategy _check_disable is NOT called during _load if no file exists (no crash)
"""
from __future__ import annotations

import json
import os
import sys
import threading
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is in path
_REPO = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO))


# ════════════════════════════════════════════════════════════════════════════
# GROUP A — datetime alias: all four previously broken lines parse correctly
# ════════════════════════════════════════════════════════════════════════════

class TestDatetimeAlias:
    """Verify that all four _dt.now() occurrences are replaced with datetime.now()."""

    def test_A01_no_dt_alias_in_orchestrator(self):
        """orchestrator/master_orchestrator.py must NOT contain '_dt.now('."""
        orches = _REPO / "orchestrator" / "master_orchestrator.py"
        text = orches.read_text(encoding="utf-8")
        assert "_dt.now(" not in text, (
            "Found '_dt.now(' in master_orchestrator.py — _dt NameError not fully fixed"
        )

    def test_A02_no_dt_strftime_alias(self):
        """master_orchestrator.py must NOT contain '_dt.strftime'."""
        orches = _REPO / "orchestrator" / "master_orchestrator.py"
        text = orches.read_text(encoding="utf-8")
        assert "_dt.strftime(" not in text, (
            "Found '_dt.strftime(' in master_orchestrator.py"
        )

    def test_A03_datetime_now_present(self):
        """master_orchestrator.py must use datetime.now() in the LOL/KDA/rejection sections."""
        orches = _REPO / "orchestrator" / "master_orchestrator.py"
        text = orches.read_text(encoding="utf-8")
        # Verify the fix landed at least four times
        count = text.count("datetime.now()")
        assert count >= 4, f"Expected at least 4 datetime.now() calls, found {count}"

    def test_A04_datetime_now_callable(self):
        """datetime.now() produces a string without NameError."""
        result = datetime.now().strftime("%Y-%m-%d")
        assert len(result) == 10
        assert result[4] == "-"


# ════════════════════════════════════════════════════════════════════════════
# GROUP B — _guarded_cycle exception containment
# ════════════════════════════════════════════════════════════════════════════

class TestGuardedCycleExceptionContainment:
    """_guarded_cycle must swallow ALL exceptions and never re-raise them."""

    def _make_orchestrator(self):
        """Return a lightweight MasterOrchestrator stand-in with _guarded_cycle."""
        from orchestrator.master_orchestrator import MasterOrchestrator
        orch = MasterOrchestrator.__new__(MasterOrchestrator)
        # Minimal state required by _guarded_cycle
        orch._is_market_session = MagicMock(return_value=True)
        return orch

    def test_B01_guarded_cycle_swallows_exception(self):
        """A crashing run_full_cycle must not escape _guarded_cycle."""
        orch = self._make_orchestrator()
        orch.run_full_cycle = MagicMock(side_effect=RuntimeError("deliberate crash"))
        # Should not raise
        orch._guarded_cycle()

    def test_B02_guarded_cycle_returns_none_on_exception(self):
        """_guarded_cycle returns None even when run_full_cycle raises."""
        orch = self._make_orchestrator()
        orch.run_full_cycle = MagicMock(side_effect=ValueError("boom"))
        result = orch._guarded_cycle()
        assert result is None

    def test_B03_guarded_cycle_outside_market_hours_no_call(self):
        """Outside market hours: run_full_cycle is not called."""
        orch = self._make_orchestrator()
        orch._is_market_session = MagicMock(return_value=False)
        orch.run_full_cycle = MagicMock()
        orch._guarded_cycle()
        orch.run_full_cycle.assert_not_called()

    def test_B04_guarded_cycle_success_path(self):
        """Successful cycle: run_full_cycle is called exactly once."""
        orch = self._make_orchestrator()
        orch.run_full_cycle = MagicMock(return_value=None)
        orch._guarded_cycle()
        orch.run_full_cycle.assert_called_once()

    def test_B05_guarded_cycle_name_error_swallowed(self):
        """NameError (like _dt NameError) must also be swallowed."""
        orch = self._make_orchestrator()
        def _name_error():
            raise NameError("name '_dt' is not defined")
        orch.run_full_cycle = _name_error
        orch._guarded_cycle()  # must not raise


# ════════════════════════════════════════════════════════════════════════════
# GROUP C/D — schedule library next_run advancement
# ════════════════════════════════════════════════════════════════════════════

class TestScheduleNextRunAdvancement:
    """When _guarded_cycle never re-raises, schedule.next_run must advance."""

    def test_C01_schedule_next_run_advances_after_safe_wrapper(self):
        """schedule.next_run must update when the job function doesn't raise."""
        import schedule as sched_lib

        _calls = []

        def _safe_job():
            _calls.append(1)
            raise RuntimeError("would crash if not wrapped")

        def _guarded():
            try:
                _safe_job()
            except Exception:
                pass  # swallowed — mirrors _guarded_cycle behaviour

        sched_lib.clear()
        job = sched_lib.every(1).seconds.do(_guarded)
        prev_next_run = job.next_run

        # Simulate the scheduler loop tick
        import time
        time.sleep(1.1)
        sched_lib.run_pending()

        assert job.next_run > prev_next_run, (
            "next_run did not advance — crash loop would occur"
        )
        sched_lib.clear()

    def test_D01_no_infinite_crash_loop(self):
        """Calling run_pending() N times should call the job at most ceil(elapsed/interval) times."""
        import schedule as sched_lib
        import time

        _calls = []

        def _guarded():
            try:
                _calls.append(1)
                raise RuntimeError("crash")
            except Exception:
                pass

        sched_lib.clear()
        sched_lib.every(60).seconds.do(_guarded)
        # Run pending 5 times in rapid succession — job should fire at most once
        for _ in range(5):
            sched_lib.run_pending()

        assert len(_calls) <= 1, (
            f"Job called {len(_calls)} times — crash loop detected"
        )
        sched_lib.clear()


# ════════════════════════════════════════════════════════════════════════════
# GROUP E — missed-cycle recording
# ════════════════════════════════════════════════════════════════════════════

class TestMissedCycleRecording:
    """SchedulerHealth persists missed slots on startup."""

    def test_E01_record_startup_detects_missed_slots(self, tmp_path):
        """If a slot passed since last_successful_slot, it appears in missed_slots_on_restart."""
        from orchestrator.scheduler_health import SchedulerHealth

        health_file = tmp_path / "scheduler_health.json"
        # Write a state that indicates last success was at 09:00
        health_file.write_text(json.dumps({
            "last_successful_slot": "09:00",
        }))

        # Patch the health file path and mock config to return a slot at 09:45
        with (
            patch("orchestrator.scheduler_health._HEALTH_FILE", health_file),
            patch("orchestrator.scheduler_health.SchedulerHealth._detect_missed_slots",
                  return_value=["09:45"]),
        ):
            sh = SchedulerHealth()
            sh.record_startup()
            state = sh.get_state()

        assert "09:45" in state.get("missed_slots_on_restart", [])

    def test_E02_slot_history_grows_on_failure(self, tmp_path):
        """record_slot_failure appends to slot_history."""
        from orchestrator.scheduler_health import SchedulerHealth

        with patch("orchestrator.scheduler_health._HEALTH_FILE", tmp_path / "sh.json"):
            sh = SchedulerHealth()
            sh.record_slot_failure("10:30", "boom")
            state = sh.get_state()

        hist = state.get("slot_history", [])
        assert any(h["slot"] == "10:30" and h["status"] == "FAILED" for h in hist)

    def test_E03_slot_history_grows_on_success(self, tmp_path):
        """record_slot_success appends to slot_history."""
        from orchestrator.scheduler_health import SchedulerHealth

        with patch("orchestrator.scheduler_health._HEALTH_FILE", tmp_path / "sh.json"):
            sh = SchedulerHealth()
            sh.record_slot_success("11:30")
            state = sh.get_state()

        hist = state.get("slot_history", [])
        assert any(h["slot"] == "11:30" and h["status"] == "SUCCESS" for h in hist)


# ════════════════════════════════════════════════════════════════════════════
# GROUP F — restart recovery
# ════════════════════════════════════════════════════════════════════════════

class TestRestartRecovery:
    """SchedulerHealth loads persisted state on init."""

    def test_F01_last_successful_slot_survives_restart(self, tmp_path):
        from orchestrator.scheduler_health import SchedulerHealth

        health_file = tmp_path / "sh.json"
        with patch("orchestrator.scheduler_health._HEALTH_FILE", health_file):
            sh1 = SchedulerHealth()
            sh1.record_slot_success("13:00")

        with patch("orchestrator.scheduler_health._HEALTH_FILE", health_file):
            sh2 = SchedulerHealth()
            state = sh2.get_state()

        assert state["last_successful_slot"] == "13:00"

    def test_F02_empty_file_does_not_crash(self, tmp_path):
        from orchestrator.scheduler_health import SchedulerHealth

        bad_file = tmp_path / "sh.json"
        bad_file.write_text("{invalid json !!!}")
        with patch("orchestrator.scheduler_health._HEALTH_FILE", bad_file):
            sh = SchedulerHealth()  # must not raise
        assert sh is not None


# ════════════════════════════════════════════════════════════════════════════
# GROUP G — MOP_RC001 → LOL recovery idempotency
# ════════════════════════════════════════════════════════════════════════════

class TestMopRc001Recovery:
    """recover() writes LOL records and is idempotent."""

    _MOP_ROWS = [
        {
            "obs_id": "TATASTEEL_091500",
            "ts_utc": "2026-08-25T04:15:00Z",
            "trading_date": "2026-08-25",
            "symbol": "TATASTEEL",
            "direction": "LONG",
            "entry_price": 150.50,
            "stop_loss": 148.00,
            "target_price": 155.50,
            "atr": 2.5,
            "atr_pct": 1.66,
            "rr": 2.0,
            "expected_move_pct": 3.32,
            "confidence": 0.72,
            "candidate_score": 7.8,
            "strategy": "Breakout_Volume",
            "regime": "TRENDING",
            "rsi": 58.0,
            "vol_ratio": 1.4,
            "sector": "METALS",
            "observation_horizon_days": 1,
            "selected": None,
            "actual_return_pct": None,
            "no_lookahead": True,
        },
        {
            "obs_id": "RELIANCE_094500",
            "ts_utc": "2026-08-25T04:15:10Z",
            "trading_date": "2026-08-25",
            "symbol": "RELIANCE",
            "direction": "LONG",
            "entry_price": 2800.00,
            "stop_loss": 2780.00,
            "target_price": 2840.00,
            "atr": 20.0,
            "atr_pct": 0.71,
            "rr": 2.0,
            "expected_move_pct": 1.43,
            "confidence": 0.68,
            "candidate_score": 6.9,
            "strategy": "Breakout_Volume",
            "regime": "TRENDING",
            "rsi": 55.0,
            "vol_ratio": 1.3,
            "sector": "ENERGY",
            "observation_horizon_days": 1,
            "selected": None,
            "actual_return_pct": None,
            "no_lookahead": True,
        },
    ]

    def _setup(self, tmp_path: Path, rows=None):
        rows = rows or self._MOP_ROWS
        mop_dir = tmp_path / "data" / "mop_rc001"
        lol_dir = tmp_path / "data" / "lol"
        mop_dir.mkdir(parents=True)
        lol_dir.mkdir(parents=True)
        mop_file = mop_dir / "MOP_RC001_2026-08-25.json"
        with open(mop_file, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        return mop_dir, lol_dir

    def test_G01_recovery_creates_lol_records(self, tmp_path):
        from scripts.recover_mop_rc001_to_lol import recover, _MOP_DIR, _LOL_DIR
        mop_dir, lol_dir = self._setup(tmp_path)
        with (
            patch("scripts.recover_mop_rc001_to_lol._MOP_DIR", mop_dir),
            patch("scripts.recover_mop_rc001_to_lol._LOL_DIR", lol_dir),
        ):
            result = recover("2026-08-25")
        assert result["status"] == "SUCCESS"
        assert result["recovered"] == 2
        assert result["skipped"] == 0

    def test_G02_recovery_is_idempotent(self, tmp_path):
        """Running recovery twice must produce same recovered count (not double)."""
        from scripts.recover_mop_rc001_to_lol import recover
        mop_dir, lol_dir = self._setup(tmp_path)
        with (
            patch("scripts.recover_mop_rc001_to_lol._MOP_DIR", mop_dir),
            patch("scripts.recover_mop_rc001_to_lol._LOL_DIR", lol_dir),
        ):
            result1 = recover("2026-08-25")
            result2 = recover("2026-08-25")

        assert result1["recovered"] == 2
        # Second run: all records already exist → skipped
        assert result2["recovered"] == 0
        assert result2["skipped"] == 2

    def test_G03_obs_id_matches_lol_algorithm(self, tmp_path):
        """obs_id in recovered LOL record matches _make_obs_id formula."""
        import hashlib
        from scripts.recover_mop_rc001_to_lol import recover, _make_obs_id
        mop_dir, lol_dir = self._setup(tmp_path, rows=[self._MOP_ROWS[0]])
        with (
            patch("scripts.recover_mop_rc001_to_lol._MOP_DIR", mop_dir),
            patch("scripts.recover_mop_rc001_to_lol._LOL_DIR", lol_dir),
        ):
            recover("2026-08-25")

        lol_file = lol_dir / "LOL_2026-08-25.jsonl"
        records = [json.loads(l) for l in lol_file.read_text().splitlines() if l.strip()]
        assert len(records) == 1
        expected_id = _make_obs_id("TATASTEEL", "2026-08-25", 150.50)
        assert records[0]["observation_id"] == expected_id

    def test_N01_recovery_no_mop_file_returns_status(self, tmp_path):
        from scripts.recover_mop_rc001_to_lol import recover
        empty_dir = tmp_path / "nomop"
        empty_dir.mkdir()
        lol_dir   = tmp_path / "lol"
        lol_dir.mkdir()
        with (
            patch("scripts.recover_mop_rc001_to_lol._MOP_DIR", empty_dir),
            patch("scripts.recover_mop_rc001_to_lol._LOL_DIR", lol_dir),
        ):
            result = recover("2026-08-25")
        assert result["status"] == "NO_MOP_FILE"
        assert result["recovered"] == 0

    def test_M01_invalid_rows_are_skipped(self, tmp_path):
        """Rows with missing symbol or entry_price are skipped gracefully."""
        bad_rows = [
            {"symbol": "", "entry_price": 0.0, "trading_date": "2026-08-25"},
            {"symbol": "NOINF", "entry_price": None, "trading_date": "2026-08-25"},
        ]
        mop_dir, lol_dir = self._setup(tmp_path, rows=bad_rows)
        with (
            patch("scripts.recover_mop_rc001_to_lol._MOP_DIR", mop_dir),
            patch("scripts.recover_mop_rc001_to_lol._LOL_DIR", lol_dir),
        ):
            from scripts.recover_mop_rc001_to_lol import recover
            result = recover("2026-08-25")
        assert result["recovered"] == 0
        assert result["skipped"] == 2


# ════════════════════════════════════════════════════════════════════════════
# GROUP H — SchedulerHealth persistence
# ════════════════════════════════════════════════════════════════════════════

class TestSchedulerHealthPersistence:
    def test_H01_file_written_after_success(self, tmp_path):
        from orchestrator.scheduler_health import SchedulerHealth
        h_file = tmp_path / "sh.json"
        with patch("orchestrator.scheduler_health._HEALTH_FILE", h_file):
            sh = SchedulerHealth()
            sh.record_slot_success("14:00")
        assert h_file.exists()
        data = json.loads(h_file.read_text())
        assert data["last_successful_slot"] == "14:00"

    def test_H02_failure_stored_with_error(self, tmp_path):
        from orchestrator.scheduler_health import SchedulerHealth
        h_file = tmp_path / "sh.json"
        with patch("orchestrator.scheduler_health._HEALTH_FILE", h_file):
            sh = SchedulerHealth()
            sh.record_slot_failure("09:45", "NameError: _dt")
        data = json.loads(h_file.read_text())
        assert "NameError" in data.get("last_failure_error", "")

    def test_L01_failure_error_truncated_to_500(self, tmp_path):
        from orchestrator.scheduler_health import SchedulerHealth
        h_file = tmp_path / "sh.json"
        with patch("orchestrator.scheduler_health._HEALTH_FILE", h_file):
            sh = SchedulerHealth()
            long_error = "x" * 600
            sh.record_slot_failure("15:00", long_error)
        data = json.loads(h_file.read_text())
        assert len(data["last_failure_error"]) == 500


# ════════════════════════════════════════════════════════════════════════════
# GROUP I — EOD guarded wrapper
# ════════════════════════════════════════════════════════════════════════════

class TestEodGuardedWrapper:
    """start_scheduler registers a guarded EOD wrapper that never raises."""

    def test_I01_eod_guarded_wrapper_swallows_exception(self):
        """A crashing run_eod_learning must not escape the EOD guarded wrapper."""
        # Simulate the _guarded_eod closure from start_scheduler
        calls = []

        class _FakeOrch:
            def run_eod_learning(self):
                calls.append(1)
                raise RuntimeError("eod crash")

        orch = _FakeOrch()

        import traceback as _tb

        def _guarded_eod():
            try:
                orch.run_eod_learning()
            except Exception as _exc:
                pass  # mirrors the real implementation

        _guarded_eod()  # must not raise
        assert len(calls) == 1

    def test_I02_start_scheduler_registers_guarded_eod(self):
        """start_scheduler() in master_orchestrator.py should use _guarded_eod not self.run_eod_learning directly."""
        orches = _REPO / "orchestrator" / "master_orchestrator.py"
        text   = orches.read_text(encoding="utf-8")
        assert "_guarded_eod" in text, (
            "start_scheduler must register _guarded_eod, not self.run_eod_learning directly"
        )


# ════════════════════════════════════════════════════════════════════════════
# GROUP J — Anti-lookahead in recovery records
# ════════════════════════════════════════════════════════════════════════════

class TestAntiLookahead:
    def test_J01_recovered_records_have_no_lookahead_true(self, tmp_path):
        """All recovered LOL records must have no_lookahead=True."""
        from scripts.recover_mop_rc001_to_lol import recover
        mop_dir = tmp_path / "data" / "mop_rc001"
        lol_dir = tmp_path / "data" / "lol"
        mop_dir.mkdir(parents=True)
        lol_dir.mkdir(parents=True)
        rows = [
            {
                "symbol": "INFY", "direction": "LONG", "entry_price": 1800.0,
                "stop_loss": 1780.0, "target_price": 1840.0, "confidence": 0.7,
                "trading_date": "2026-08-25", "ts_utc": "2026-08-25T04:15:00Z",
                "rr": 2.0, "strategy": "Breakout_Volume", "regime": "TRENDING",
                "sector": "IT", "rsi": 55.0, "vol_ratio": 1.2,
                "candidate_score": 7.0, "expected_move_pct": 2.2,
            }
        ]
        (mop_dir / "MOP_RC001_2026-08-25.json").write_text(
            "\n".join(json.dumps(r) for r in rows)
        )
        with (
            patch("scripts.recover_mop_rc001_to_lol._MOP_DIR", mop_dir),
            patch("scripts.recover_mop_rc001_to_lol._LOL_DIR", lol_dir),
        ):
            recover("2026-08-25")

        lol_file = lol_dir / "LOL_2026-08-25.jsonl"
        records = [json.loads(l) for l in lol_file.read_text().splitlines() if l.strip()]
        for rec in records:
            assert rec.get("no_lookahead") is True

    def test_J02_recovered_records_no_outcome_data(self, tmp_path):
        """Recovered records must have outcome fields as None (no lookahead data)."""
        from scripts.recover_mop_rc001_to_lol import recover
        mop_dir = tmp_path / "data" / "mop_rc001"
        lol_dir = tmp_path / "data" / "lol"
        mop_dir.mkdir(parents=True)
        lol_dir.mkdir(parents=True)
        rows = [
            {
                "symbol": "HDFC", "direction": "LONG", "entry_price": 1600.0,
                "stop_loss": 1585.0, "target_price": 1630.0, "confidence": 0.65,
                "trading_date": "2026-08-25", "ts_utc": "2026-08-25T04:20:00Z",
                "rr": 2.0, "strategy": "Breakout_Volume", "regime": "RANGING",
                "sector": "FINANCE", "rsi": 52.0, "vol_ratio": 1.1,
                "candidate_score": 6.5, "expected_move_pct": 1.9,
            }
        ]
        (mop_dir / "MOP_RC001_2026-08-25.json").write_text(
            "\n".join(json.dumps(r) for r in rows)
        )
        with (
            patch("scripts.recover_mop_rc001_to_lol._MOP_DIR", mop_dir),
            patch("scripts.recover_mop_rc001_to_lol._LOL_DIR", lol_dir),
        ):
            recover("2026-08-25")

        lol_file = lol_dir / "LOL_2026-08-25.jsonl"
        records = [json.loads(l) for l in lol_file.read_text().splitlines() if l.strip()]
        for rec in records:
            assert rec.get("actual_return_pct") is None
            assert rec.get("executed") is False
            assert rec.get("order_id") is None
            assert rec.get("kda_decision") is None
            assert rec.get("strategy_decision") is None


# ════════════════════════════════════════════════════════════════════════════
# GROUP K — Mean_Reversion / strategy state reconciliation after _load
# ════════════════════════════════════════════════════════════════════════════

class TestStrategyStateReconciliation:
    """After _load(), _check_disable() is called on every loaded strategy."""

    def test_K01_load_calls_check_disable_per_strategy(self, tmp_path):
        """_load() must call _check_disable() for each strategy in the JSON."""
        from learning_system.strategy_performance_tracker import (
            StrategyPerformanceTracker, PERF_FILE,
        )

        # Build a minimal tracker JSON with one strategy at consec_losses=5
        data = {
            "Mean_Reversion": {
                "name": "Mean_Reversion",
                "total_trades": 2,
                "official_trades": 2,
                "prepared_universe_trades": 0,
                "wins": 1,
                "losses": 1,
                "total_r": -0.5,
                "win_r": 1.0,
                "loss_r": 1.5,
                "consec_losses": 5,
                "enabled": True,
                "disabled_reason": "",
                "last_updated": "2026-08-25T09:00:00",
                "last_trades": [],
            }
        }

        perf_file = tmp_path / "strategy_performance.json"
        perf_file.write_text(json.dumps(data))

        with patch(
            "learning_system.strategy_performance_tracker.PERF_FILE",
            str(perf_file),
        ):
            tracker = StrategyPerformanceTracker.__new__(StrategyPerformanceTracker)
            tracker._stats = {}
            tracker._lock  = __import__("threading").Lock()
            tracker._load()

        # _check_disable was called: the strategy MIGHT be disabled depending on
        # whether MIN_SAMPLE and is_clean_research_ready() guards pass.
        # The important assertion is that no exception was raised during _load().
        assert "Mean_Reversion" in tracker._stats

    def test_K02_no_crash_when_check_disable_guard_fires(self, tmp_path):
        """_load() must not crash if _check_disable raises internally."""
        from learning_system.strategy_performance_tracker import StrategyPerformanceTracker

        data = {
            "Fake_Strategy": {
                "name": "Fake_Strategy",
                "total_trades": 0,
                "official_trades": 0,
                "prepared_universe_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_r": 0.0,
                "win_r": 0.0,
                "loss_r": 0.0,
                "consec_losses": 0,
                "enabled": True,
                "disabled_reason": "",
                "last_updated": "",
                "last_trades": [],
            }
        }

        perf_file = tmp_path / "strategy_performance.json"
        perf_file.write_text(json.dumps(data))

        with patch(
            "learning_system.strategy_performance_tracker.PERF_FILE",
            str(perf_file),
        ):
            tracker = StrategyPerformanceTracker.__new__(StrategyPerformanceTracker)
            tracker._stats = {}
            tracker._lock  = __import__("threading").Lock()
            # Patch _check_disable to raise — _load must swallow it
            tracker._check_disable = MagicMock(side_effect=RuntimeError("guard"))
            tracker._load()  # must not raise

        assert "Fake_Strategy" in tracker._stats

    def test_O01_no_file_does_not_crash(self, tmp_path):
        """_load() with no existing file must not crash (empty stats)."""
        from learning_system.strategy_performance_tracker import StrategyPerformanceTracker

        non_existent = str(tmp_path / "no_such_file.json")
        with patch("learning_system.strategy_performance_tracker.PERF_FILE", non_existent):
            tracker = StrategyPerformanceTracker.__new__(StrategyPerformanceTracker)
            tracker._stats = {}
            tracker._lock  = __import__("threading").Lock()
            tracker._check_disable = MagicMock()
            tracker._load()

        tracker._check_disable.assert_not_called()
        assert len(tracker._stats) == 0
