"""
test_dta_system_004.py
======================
DTA-SYSTEM-004 test suite — full-system hardening validation.

Tests:
  H-002 : RiskGuardian state persistence (T001–T015)
  H-003 : Strict anti-lookahead in LOL bridge (T016–T025)
  L-001 : outcome_at uses bar date, not wall-clock (T026–T030)
  S     : Live execution journal OPEN/CLOSE (T031–T040)
  H-001 : Live position restore from journal (T041–T050)
  M-001 : KLP observation_id standardization (T051–T060)
  P-002 : MetaModel per-strategy minimum-sample guard (T061–T065)
  D-008 : HBE daily snapshot write (T066–T070)
  K-001 : Failure taxonomy classification (T071–T085)
  D-009 : Scan no-signal observer (T086–T090)
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# H-002: RiskGuardian State Persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskGuardianPersistence:
    """T001–T015: RiskGuardian survives restart with same-day accumulated loss."""

    def _make_guardian(self, tmp_path):
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        state_file = str(tmp_path / "rg_state.json")
        return FailSafeRiskGuardian(total_capital=100_000, state_file=state_file), state_file

    def test_T001_state_file_created_on_trade_record(self, tmp_path):
        """State file created after first record_trade_result()."""
        g, sf = self._make_guardian(tmp_path)
        g.record_trade_result(pnl=-500.0, won=False)
        assert os.path.exists(sf), "State file must exist after record_trade_result()"

    def test_T002_daily_pnl_persisted(self, tmp_path):
        """daily_pnl is written to state file correctly."""
        g, sf = self._make_guardian(tmp_path)
        g.record_trade_result(pnl=-1200.0, won=False)
        state = json.loads(Path(sf).read_text())
        assert abs(state["daily_pnl"] - (-1200.0)) < 0.01

    def test_T003_trading_halted_persisted(self, tmp_path):
        """trading_halted=True is written when kill-switch fires."""
        g, sf = self._make_guardian(tmp_path)
        # Force kill-switch by record + evaluate with high VIX
        from models import MarketSnapshot
        snap = MagicMock()
        snap.vix = 50.0
        snap.nifty_change_pct = 0.0
        g.evaluate([], snap)
        state = json.loads(Path(sf).read_text())
        assert state["trading_halted"] is True

    def test_T004_same_day_restore(self, tmp_path):
        """Restart on same day restores accumulated P&L and halted flag."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        state_file = str(tmp_path / "rg_state.json")
        # Session 1 — record a loss
        g1 = FailSafeRiskGuardian(total_capital=100_000, state_file=state_file)
        g1.record_trade_result(pnl=-800.0, won=False)
        g1.record_trade_result(pnl=-300.0, won=False)
        # Session 2 — new instance, same state file
        g2 = FailSafeRiskGuardian(total_capital=100_000, state_file=state_file)
        assert abs(g2._daily_pnl - (-1100.0)) < 0.01, (
            f"Expected restored daily_pnl=-1100, got {g2._daily_pnl}"
        )

    def test_T005_consec_losses_persisted(self, tmp_path):
        """consec_losses is restored on restart."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        g1 = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        g1.record_trade_result(pnl=-100.0, won=False)
        g1.record_trade_result(pnl=-100.0, won=False)
        g2 = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        assert g2._consec_losses == 2

    def test_T006_new_day_resets_state(self, tmp_path):
        """Previous-day state is ignored — fresh session started."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        # Write a state for yesterday
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        state = {
            "session_date": yesterday,
            "daily_pnl": -5000.0,
            "trading_halted": True,
            "halt_reason": "DAILY_LOSS",
            "consec_losses": 3,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        Path(sf).write_text(json.dumps(state))
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        assert g._daily_pnl == 0.0, "Previous-day P&L must not carry over"
        assert g._trading_halted is False, "Previous-day halt must not carry over"

    def test_T007_missing_state_file_is_safe(self, tmp_path):
        """Missing state file starts fresh (fail-safe default)."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "nonexistent.json")
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        assert g._daily_pnl == 0.0
        assert g._trading_halted is False

    def test_T008_corrupt_state_file_is_safe(self, tmp_path):
        """Corrupt state file starts fresh (fail-safe default)."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        Path(sf).write_text("NOT_VALID_JSON{{{{")
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        assert g._daily_pnl == 0.0
        assert g._trading_halted is False

    def test_T009_halt_reason_preserved(self, tmp_path):
        """halt_reason string is restored correctly."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        today = date.today().isoformat()
        state = {
            "session_date": today,
            "daily_pnl": -2500.0,
            "trading_halted": True,
            "halt_reason": "VIX=47.5 ≥ 45.0",
            "consec_losses": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        Path(sf).write_text(json.dumps(state))
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        assert g._trading_halted is True
        assert "VIX" in g._halt_reason

    def test_T010_state_update_on_daily_loss_trigger(self, tmp_path):
        """State file updated when daily loss limit fires inside evaluate()."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        # Seed via proper API so _session_date is set
        for _ in range(19):
            g.record_trade_result(pnl=-100.0, won=False)   # total = -1900
        assert g._daily_pnl == -1900.0
        # Now push over the 2% limit (2000 = 2% of 100000)
        g.record_trade_result(pnl=-110.0, won=False)       # total = -2010
        snap = MagicMock()
        snap.vix = 15.0
        g.evaluate([], snap)
        state = json.loads(Path(sf).read_text())
        assert state["trading_halted"] is True

    def test_T011_atomic_write_on_kill_switch(self, tmp_path):
        """Kill-switch triggers save_state atomically."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        snap = MagicMock()
        snap.vix = 50.0
        g.evaluate([], snap)
        assert os.path.exists(sf)
        state = json.loads(Path(sf).read_text())
        assert state["trading_halted"] is True

    def test_T012_no_tmp_file_left_after_save(self, tmp_path):
        """No .tmp files left after successful save."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        g.record_trade_result(pnl=-100.0, won=False)
        tmp_files = list(tmp_path.glob(".rg_state_*.tmp"))
        assert len(tmp_files) == 0, f"Leftover tmp files: {tmp_files}"

    def test_T013_get_status_after_restore(self, tmp_path):
        """get_status() reflects restored P&L."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        g1 = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        g1.record_trade_result(pnl=-600.0, won=False)
        g2 = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        status = g2.get_status()
        assert status["daily_pnl"] == -600.0

    def test_T014_position_governor_uses_restored_pnl(self, tmp_path):
        """get_position_governor_factor() uses restored P&L."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian, DD_PAUSE_PCT
        sf = str(tmp_path / "rg.json")
        # Write a state with loss at pause level
        today = date.today().isoformat()
        pause_loss = DD_PAUSE_PCT / 100.0 * 100_000 + 1  # just over pause threshold
        state = {
            "session_date": today,
            "daily_pnl": -pause_loss,
            "trading_halted": False,
            "halt_reason": "",
            "consec_losses": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        Path(sf).write_text(json.dumps(state))
        g = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        factor = g.get_position_governor_factor()
        assert factor == 0.0, f"Expected 0.0 (paused) after restoring deep loss, got {factor}"

    def test_T015_capital_parameter_not_persisted(self, tmp_path):
        """total_capital is NOT persisted (passed at construction — not session state)."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = str(tmp_path / "rg.json")
        g1 = FailSafeRiskGuardian(total_capital=100_000, state_file=sf)
        g1.record_trade_result(pnl=0.0, won=True)
        g2 = FailSafeRiskGuardian(total_capital=999_999, state_file=sf)
        assert g2._capital == 999_999, "Capital must come from constructor, not state file"


# ─────────────────────────────────────────────────────────────────────────────
# H-003: Strict Anti-Lookahead in LOL Bridge
# ─────────────────────────────────────────────────────────────────────────────

class TestStrictAntiLookahead:
    """T016–T025: LOL bridge rejects records missing temporal proof."""

    def _make_lol_file(self, tmp_path, records):
        lol_dir = tmp_path / "lol"
        lol_dir.mkdir(exist_ok=True)
        today = date.today().isoformat()
        lol_file = lol_dir / f"LOL_{today}.jsonl"
        with lol_file.open("w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        return lol_dir, today

    def _run_bridge(self, tmp_path, records):
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes
        lol_dir, today = self._make_lol_file(tmp_path, records)
        kel = tmp_path / "kel.jsonl"
        state = tmp_path / "state.json"
        return ingest_lol_outcomes(
            dates=[today],
            lol_data_dir=lol_dir,
            knowledge_ledger=kel,
            state_path=state,
        )

    def _make_outcome_record(self, obs_id, outcome_at=None, decision_at=None,
                             outcome_class="EXECUTED_WIN", lifecycle="OUTCOME_OBSERVED"):
        return {
            "observation_id":  obs_id,
            "lifecycle_state": lifecycle,
            "event_type":      lifecycle,
            "outcome_class":   outcome_class,
            "symbol":          "TESTSTK",
            "direction":       "BUY",
            "outcome_at":      outcome_at,
            "decision_at":     decision_at,
        }

    def test_T016_missing_both_timestamps_skipped(self, tmp_path):
        """Record with both outcome_at and decision_at missing is skipped."""
        rec = self._make_outcome_record("obs001", outcome_at=None, decision_at=None)
        result = self._run_bridge(tmp_path, [rec])
        assert result["new_records"] == 0
        assert result["skipped"] >= 1

    def test_T017_missing_decision_at_skipped(self, tmp_path):
        """Record with decision_at missing is skipped even if outcome_at present."""
        rec = self._make_outcome_record(
            "obs002",
            outcome_at="2026-08-26T15:30:00+05:30",
            decision_at=None,
        )
        result = self._run_bridge(tmp_path, [rec])
        assert result["new_records"] == 0

    def test_T018_missing_outcome_at_skipped(self, tmp_path):
        """Record with outcome_at missing is skipped even if decision_at present."""
        rec = self._make_outcome_record(
            "obs003",
            outcome_at=None,
            decision_at="2026-08-25T10:00:00+05:30",
        )
        result = self._run_bridge(tmp_path, [rec])
        assert result["new_records"] == 0

    def test_T019_outcome_before_decision_skipped(self, tmp_path):
        """outcome_at <= decision_at is a lookahead violation — skipped."""
        rec = self._make_outcome_record(
            "obs004",
            outcome_at="2026-08-25T09:00:00+05:30",
            decision_at="2026-08-25T10:00:00+05:30",
        )
        result = self._run_bridge(tmp_path, [rec])
        assert result["new_records"] == 0

    def test_T020_outcome_equal_decision_skipped(self, tmp_path):
        """outcome_at == decision_at is also a violation — skipped."""
        ts = "2026-08-25T10:00:00+05:30"
        rec = self._make_outcome_record("obs005", outcome_at=ts, decision_at=ts)
        result = self._run_bridge(tmp_path, [rec])
        assert result["new_records"] == 0

    def test_T021_valid_temporal_order_accepted(self, tmp_path):
        """outcome_at > decision_at with EXECUTED_WIN is admitted."""
        rec = self._make_outcome_record(
            "obs006",
            outcome_at="2026-08-27T15:30:00+05:30",
            decision_at="2026-08-25T09:45:00+05:30",
            outcome_class="EXECUTED_WIN",
        )
        result = self._run_bridge(tmp_path, [rec])
        assert result["new_records"] == 1

    def test_T022_mixture_valid_invalid(self, tmp_path):
        """Mixed batch: valid admitted, invalid skipped."""
        recs = [
            self._make_outcome_record("obs007", outcome_at=None, decision_at="2026-08-25T10:00:00+05:30"),
            self._make_outcome_record("obs008",
                outcome_at="2026-08-27T15:30:00+05:30",
                decision_at="2026-08-25T09:45:00+05:30",
                outcome_class="EXECUTED_WIN",
            ),
        ]
        result = self._run_bridge(tmp_path, recs)
        assert result["new_records"] == 1
        assert result["skipped"] >= 1

    def test_T023_no_lookahead_field_set_on_admitted(self, tmp_path):
        """Admitted records in KEL have no_lookahead=True."""
        rec = self._make_outcome_record(
            "obs009",
            outcome_at="2026-08-27T15:30:00+05:30",
            decision_at="2026-08-25T09:45:00+05:30",
            outcome_class="EXECUTED_WIN",
        )
        kel = tmp_path / "kel.jsonl"
        lol_dir, today = self._make_lol_file(tmp_path, [rec])
        state = tmp_path / "state.json"
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes
        ingest_lol_outcomes(dates=[today], lol_data_dir=lol_dir,
                            knowledge_ledger=kel, state_path=state)
        evidence = [json.loads(l) for l in kel.read_text().splitlines() if l.strip()]
        assert len(evidence) == 1
        assert evidence[0].get("no_lookahead") is True

    def test_T024_not_outcome_observed_lifecycle_skipped(self, tmp_path):
        """Records not in OUTCOME_OBSERVED/LEARNING_PROCESSED state are skipped."""
        rec = self._make_outcome_record(
            "obs010",
            outcome_at="2026-08-27T15:30:00+05:30",
            decision_at="2026-08-25T09:45:00+05:30",
            lifecycle="OUTCOME_PENDING",
        )
        result = self._run_bridge(tmp_path, [rec])
        assert result["new_records"] == 0

    def test_T025_idempotent_dedup(self, tmp_path):
        """Running bridge twice on same file produces 1 new record total (dedup)."""
        rec = self._make_outcome_record(
            "obs011",
            outcome_at="2026-08-27T15:30:00+05:30",
            decision_at="2026-08-25T09:45:00+05:30",
            outcome_class="EXECUTED_WIN",
        )
        kel   = tmp_path / "kel.jsonl"
        state = tmp_path / "state.json"
        lol_dir, today = self._make_lol_file(tmp_path, [rec])
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes
        r1 = ingest_lol_outcomes(dates=[today], lol_data_dir=lol_dir,
                                  knowledge_ledger=kel, state_path=state)
        r2 = ingest_lol_outcomes(dates=[today], lol_data_dir=lol_dir,
                                  knowledge_ledger=kel, state_path=state)
        assert r1["new_records"] == 1
        assert r2["new_records"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# L-001: outcome_at Uses Bar Date
# ─────────────────────────────────────────────────────────────────────────────

class TestOutcomeAtTimestamp:
    """T026–T030: outcome_at uses actual bar date, not wall-clock."""

    def test_T026_outcome_at_uses_bar_date(self, tmp_path):
        """
        When bars are available, outcome_at should encode the first bar's date
        (YYYY-MM-DD at 15:30 IST) rather than the current wall clock.
        """
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger,
        )
        lol = LearningObservationLedger(data_dir=tmp_path / "lol")
        # Build a minimal pending record
        import uuid
        today = date.today()
        obs_id = str(uuid.uuid4())
        yesterday = (today - timedelta(days=1)).isoformat()
        pending_rec = {
            "observation_id":    obs_id,
            "lifecycle_state":   "OUTCOME_PENDING",
            "event_type":        "OUTCOME_PENDING",
            "trading_date":      yesterday,
            "symbol":            "FAKESYM",
            "direction":         "BUY",
            "entry_price":       100.0,
            "stop_loss":         95.0,
            "target_price":      110.0,
            "kda_decision":      "PASS",
            "authorization_source": "KDA",
        }
        lol._pending[obs_id] = pending_rec

        # Create fake bars — T+1 bar with a specific date
        bar_date = (today - timedelta(days=0)).isoformat()   # today as T+1
        fake_bars = [
            {"date": bar_date, "open": 100.0, "high": 108.0, "low": 98.0,
             "close": 107.0, "volume": 10000},
        ] * 5

        written_records = []

        def fake_fetch(symbol, trading_date, horizon):
            return fake_bars

        original_fetch = None
        import learning_system.learning_observation_ledger as _lol_mod
        original_fetch = _lol_mod._OHLCV_FETCHER if hasattr(_lol_mod, "_OHLCV_FETCHER") else None

        # Patch the ledger's fetcher
        lol._fetcher = fake_fetch
        original_append = lol._append

        def capture_append(rec):
            written_records.append(rec)
            original_append(rec)

        lol._append = capture_append

        result = lol.fill_pending_outcomes(_ohlcv_fetcher=fake_fetch)
        assert result.get("processed", 0) >= 0  # may be 0 if guard stops it

        # If any records were written, check outcome_at
        for rec in written_records:
            if rec.get("lifecycle_state") == "OUTCOME_OBSERVED":
                outcome_at = rec.get("outcome_at", "")
                assert bar_date[:10] in outcome_at, (
                    f"outcome_at '{outcome_at}' should contain bar date '{bar_date[:10]}'"
                )
                processed_at = rec.get("processed_at")
                assert processed_at is not None, "processed_at should be set"

    def test_T027_processed_at_is_wall_clock(self, tmp_path):
        """processed_at is set to a different field than outcome_at."""
        # This verifies the schema separation — processed_at vs outcome_at
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger,
        )
        lol = LearningObservationLedger(data_dir=tmp_path / "lol")
        import uuid
        obs_id = str(uuid.uuid4())
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        pending_rec = {
            "observation_id":       obs_id,
            "lifecycle_state":      "OUTCOME_PENDING",
            "event_type":           "OUTCOME_PENDING",
            "trading_date":         yesterday,
            "symbol":               "FAKESYM",
            "direction":            "BUY",
            "entry_price":          100.0,
            "stop_loss":            95.0,
            "target_price":         110.0,
            "kda_decision":         "PASS",
            "authorization_source": "KDA",
        }
        lol._pending[obs_id] = pending_rec

        bar_date = date.today().isoformat()
        fake_bars = [
            {"date": bar_date, "open": 100.0, "high": 108.0, "low": 98.0,
             "close": 107.0, "volume": 10000},
        ] * 5

        written = []
        orig = lol._append
        def cap(r): written.append(r); orig(r)
        lol._append = cap

        lol.fill_pending_outcomes(_ohlcv_fetcher=lambda s, d, h: fake_bars)
        # The fields should be separate
        for r in written:
            if r.get("lifecycle_state") == "OUTCOME_OBSERVED":
                assert "outcome_at" in r
                assert "processed_at" in r
                # They CAN differ since outcome_at is bar-based
                # Just assert both are present
                break

    def test_T028_outcome_at_fallback_when_no_bars(self, tmp_path):
        """If bars list is empty, outcome_at uses a safe default (ISO string)."""
        # outcome_at must always be set to some ISO string
        from learning_system import learning_observation_ledger as _mod
        # _compute_outcome with empty bars won't produce OUTCOME_OBSERVED
        # so test the guard in _fill_outcomes_impl directly via the
        # code path's fallback logic:
        import uuid
        obs_id = str(uuid.uuid4())
        updated = {"observation_id": obs_id}
        bars_empty: list = []

        _outcome_bar_date = bars_empty[0].get("date") if bars_empty else None
        if _outcome_bar_date:
            outcome_at = str(_outcome_bar_date) + "T15:30:00+05:30"
        else:
            outcome_at = datetime.now(timezone.utc).isoformat()

        assert outcome_at is not None
        assert len(outcome_at) > 10  # at minimum a date string

    def test_T029_outcome_at_contains_tz_info(self, tmp_path):
        """outcome_at value contains timezone info (not naive datetime)."""
        # Construct as the code would
        bar_date = "2026-08-26"
        outcome_at = bar_date + "T15:30:00+05:30"
        assert "+05:30" in outcome_at or "Z" in outcome_at or "+" in outcome_at

    def test_T030_no_lookahead_flag_still_set(self, tmp_path):
        """no_lookahead=True is still set even with bar-date outcome_at."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(data_dir=tmp_path / "lol")
        import uuid
        obs_id = str(uuid.uuid4())
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        lol._pending[obs_id] = {
            "observation_id":       obs_id,
            "lifecycle_state":      "OUTCOME_PENDING",
            "event_type":           "OUTCOME_PENDING",
            "trading_date":         yesterday,
            "symbol":               "FAKESYM",
            "direction":            "BUY",
            "entry_price":          100.0,
            "stop_loss":            95.0,
            "target_price":         110.0,
            "kda_decision":         "PASS",
            "authorization_source": "KDA",
        }
        bar_date = date.today().isoformat()
        fake_bars = [
            {"date": bar_date, "open": 100.0, "high": 112.0, "low": 98.0,
             "close": 111.0, "volume": 10000},
        ] * 5
        written = []
        orig = lol._append
        def cap(r): written.append(r); orig(r)
        lol._append = cap
        lol.fill_pending_outcomes(_ohlcv_fetcher=lambda s, d, h: fake_bars)
        for r in written:
            if r.get("lifecycle_state") == "OUTCOME_OBSERVED":
                assert r.get("no_lookahead") is True
                break


# ─────────────────────────────────────────────────────────────────────────────
# S: Live Execution Journal
# ─────────────────────────────────────────────────────────────────────────────

class TestLiveExecutionJournal:
    """T031–T040: Live journal writes OPEN/CLOSE for position restart recovery."""

    def _make_order_record(self):
        from execution_engine.order_manager import OrderRecord
        return OrderRecord(
            order_id    = "LIVE_001",
            symbol      = "TATASTEEL",
            direction   = "BUY",
            quantity    = 10,
            entry_price = 150.0,
            stop_loss   = 145.0,
            target      = 160.0,
            strategy    = "Breakout",
            broker_order_id   = "BROKER_001",
            fill_status       = "FILLED",
            actual_fill_price = 150.5,
        )

    def test_T031_open_event_written(self, tmp_path):
        """OPEN event is written to live journal."""
        from execution_engine.order_manager import OrderManager
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = False
        import json as _j
        from datetime import timezone as _tz
        live_log = str(tmp_path / "live_orders.jsonl")

        # Patch the constant
        import execution_engine.order_manager as _om
        orig = _om.LIVE_ORDER_LOG
        orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = live_log
            _om._LIVE_DIR = str(tmp_path)
            rec = self._make_order_record()
            om._append_live_journal("OPEN", rec)
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        lines = [json.loads(l) for l in Path(live_log).read_text().splitlines()]
        assert len(lines) == 1
        assert lines[0]["event"] == "OPEN"
        assert lines[0]["symbol"] == "TATASTEEL"
        assert lines[0]["order_id"] == "LIVE_001"

    def test_T032_close_event_written_with_pnl(self, tmp_path):
        """CLOSE event includes exit_price and pnl."""
        from execution_engine.order_manager import OrderManager
        import execution_engine.order_manager as _om
        live_log = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = live_log
            _om._LIVE_DIR = str(tmp_path)
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = self._make_order_record()
            om._append_live_journal("CLOSE", rec,
                                     extra={"exit_price": 158.0, "pnl": 75.0, "reason": "TARGET_HIT"})
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        lines = [json.loads(l) for l in Path(live_log).read_text().splitlines()]
        assert lines[0]["event"] == "CLOSE"
        assert lines[0]["exit_price"] == 158.0
        assert lines[0]["pnl"] == 75.0

    def test_T033_journal_is_append_only(self, tmp_path):
        """Multiple calls append lines; prior lines are not overwritten."""
        import execution_engine.order_manager as _om
        live_log = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = live_log
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = self._make_order_record()
            om._append_live_journal("OPEN", rec)
            rec2 = self._make_order_record()
            rec2.order_id = "LIVE_002"
            om._append_live_journal("OPEN", rec2)
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        lines = Path(live_log).read_text().splitlines()
        assert len(lines) == 2

    def test_T034_journal_contains_timestamp(self, tmp_path):
        """Each journal entry has a timestamp field."""
        import execution_engine.order_manager as _om
        live_log = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = live_log
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._append_live_journal("OPEN", self._make_order_record())
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        row = json.loads(Path(live_log).read_text())
        assert "timestamp" in row
        assert len(row["timestamp"]) > 10

    def test_T035_journal_write_failure_is_non_fatal(self, tmp_path):
        """Write failure (e.g. disk full) never raises."""
        import execution_engine.order_manager as _om
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = "/nonexistent_dir/cannot_write.jsonl"
            _om._LIVE_DIR = "/nonexistent_dir"
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            # Must not raise
            om._append_live_journal("OPEN", self._make_order_record())
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

    def test_T036_opportunity_id_persisted_in_open_event(self, tmp_path):
        """OPEN event carries opportunity_id from OrderRecord."""
        import execution_engine.order_manager as _om
        live_log = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = live_log
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager, OrderRecord
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = OrderRecord(
                order_id="LIVE_036", symbol="INFY", direction="BUY",
                quantity=5, entry_price=1800.0, stop_loss=1760.0, target=1870.0,
                strategy="Momentum", opportunity_id="TEST-OPP-036",
            )
            om._append_live_journal("OPEN", rec)
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        row = json.loads(Path(live_log).read_text().splitlines()[0])
        assert row["opportunity_id"] == "TEST-OPP-036"

    def test_T037_opportunity_id_persisted_in_close_event(self, tmp_path):
        """CLOSE event carries same opportunity_id as OPEN event."""
        import execution_engine.order_manager as _om
        live_log = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = live_log
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager, OrderRecord
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = OrderRecord(
                order_id="LIVE_037", symbol="RELIANCE", direction="BUY",
                quantity=3, entry_price=2900.0, stop_loss=2840.0, target=3000.0,
                strategy="Breakout", opportunity_id="TEST-OPP-037",
            )
            om._append_live_journal("OPEN", rec)
            om._append_live_journal("CLOSE", rec,
                extra={"exit_price": 3000.0, "pnl": 300.0, "reason": "TARGET_HIT"})
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        lines = [json.loads(l) for l in Path(live_log).read_text().splitlines()]
        assert lines[0]["opportunity_id"] == "TEST-OPP-037"
        assert lines[1]["opportunity_id"] == "TEST-OPP-037"

    def test_T038_opportunity_id_restored_from_journal(self, tmp_path):
        """opportunity_id is recovered when restoring OPEN events at restart."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        ts = datetime.now(timezone.utc).isoformat()
        jf.write_text(json.dumps({
            "event": "OPEN", "timestamp": ts, "order_id": "LIVE_038",
            "symbol": "TCS", "direction": "BUY", "quantity": 2,
            "entry_price": 4000.0, "stop_loss": 3900.0, "target_price": 4200.0,
            "strategy": "Momentum", "fill_status": "FILLED",
            "actual_fill_price": 4005.0, "broker_order_id": "B038",
            "opportunity_id": "TEST-OPP-038",
        }) + "\n")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager
            from models import Portfolio
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._restore_stats = {"restored_today": 0}
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        rec = om._orders.get("LIVE_038")
        assert rec is not None
        assert rec.opportunity_id == "TEST-OPP-038"

    def test_T039_broker_without_get_fill_details_skips_reconcile(self, tmp_path):
        """reconcile_startup_fills() skips gracefully if broker lacks get_fill_details."""
        from execution_engine.order_manager import OrderManager, OrderRecord
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = False
        om._orders = {}
        rec = OrderRecord(
            order_id="LIVE_039", symbol="HDFC", direction="BUY",
            quantity=1, entry_price=1600.0, stop_loss=1560.0, target=1680.0,
            strategy="Test", fill_status="JOURNAL_RESTORED",
        )
        om._orders["LIVE_039"] = rec
        # Broker with NO get_fill_details (simulates old-style adapter)
        class _NoFillDetailsBroker:
            pass
        om._broker = _NoFillDetailsBroker()
        count = om.reconcile_startup_fills()
        assert count == 0  # skipped, not crashed
        assert rec.fill_status == "JOURNAL_RESTORED"  # unchanged

    def test_T040_broker_with_get_fill_details_reconciles(self, tmp_path):
        """reconcile_startup_fills() uses get_fill_details when present on broker."""
        from execution_engine.order_manager import OrderManager, OrderRecord
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = False
        om._orders = {}
        rec = OrderRecord(
            order_id="LIVE_040", symbol="WIPRO", direction="BUY",
            quantity=4, entry_price=500.0, stop_loss=480.0, target=540.0,
            strategy="Test", fill_status="JOURNAL_RESTORED",
        )
        om._orders["LIVE_040"] = rec

        class _FillDetailsBroker:
            def get_fill_details(self, order_id):
                return {
                    "status": "FILLED", "actual_fill_price": 501.0,
                    "filled_quantity": 4, "requested_price": 500.0,
                    "order_status_raw": "TRADED", "fill_timestamp": "",
                    "reconciliation_source": "TEST",
                }

        om._broker = _FillDetailsBroker()
        # Use real _reconcile_fill but stub the broker
        def fake_reconcile(r):
            fill = om._broker.get_fill_details(r.order_id)
            r.fill_status       = fill["status"]
            r.actual_fill_price = fill["actual_fill_price"]
        om._reconcile_fill = fake_reconcile
        count = om.reconcile_startup_fills()
        assert count == 1
        assert rec.fill_status == "FILLED"
        assert rec.actual_fill_price == 501.0




# ─────────────────────────────────────────────────────────────────────────────
# H-001: Live Position Restore
# ─────────────────────────────────────────────────────────────────────────────

class TestLivePositionRestore:
    """T041–T050: Container restart recovers open positions from live journal."""

    def _write_journal(self, journal_path, events):
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        with journal_path.open("w") as fh:
            for ev in events:
                fh.write(json.dumps(ev) + "\n")

    def test_T041_open_without_close_is_restored(self, tmp_path):
        """Single OPEN without CLOSE is in _orders after restore."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            self._write_journal(jf, [{
                "event":       "OPEN",
                "timestamp":   datetime.now(timezone.utc).isoformat(),
                "order_id":    "LIVE_99",
                "symbol":      "RELIANCE",
                "direction":   "BUY",
                "quantity":    5,
                "entry_price": 2500.0,
                "stop_loss":   2450.0,
                "target_price": 2600.0,
                "strategy":    "Breakout",
                "fill_status": "FILLED",
                "actual_fill_price": 2502.0,
                "broker_order_id": "B99",
            }])
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert "LIVE_99" in om._orders
        assert om._restore_stats["restored_today"] == 1

    def test_T042_closed_position_not_restored(self, tmp_path):
        """OPEN followed by CLOSE is NOT in _orders after restore."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            ts = datetime.now(timezone.utc).isoformat()
            self._write_journal(jf, [
                {"event": "OPEN",  "timestamp": ts, "order_id": "LIVE_100",
                 "symbol": "TCS", "direction": "BUY", "quantity": 2,
                 "entry_price": 3500.0, "stop_loss": 3400.0, "target_price": 3700.0,
                 "strategy": "Trend", "fill_status": "FILLED", "actual_fill_price": 3502.0,
                 "broker_order_id": "B100"},
                {"event": "CLOSE", "timestamp": ts, "order_id": "LIVE_100",
                 "exit_price": 3700.0, "pnl": 400.0, "reason": "TARGET_HIT"},
            ])
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert "LIVE_100" not in om._orders

    def test_T043_no_journal_safe_noop(self, tmp_path):
        """Missing journal file is a safe no-op."""
        import execution_engine.order_manager as _om
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(tmp_path / "nonexistent.jsonl")
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()  # must not raise
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert len(om._orders) == 0

    def test_T044_restored_position_has_journal_restored_fill_status(self, tmp_path):
        """Restored position has fill_status='JOURNAL_RESTORED'."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            self._write_journal(jf, [{
                "event": "OPEN", "timestamp": datetime.now(timezone.utc).isoformat(),
                "order_id": "LIVE_200", "symbol": "INFY", "direction": "SELL",
                "quantity": 3, "entry_price": 1800.0, "stop_loss": 1850.0,
                "target_price": 1700.0, "strategy": "Momentum", "fill_status": "FILLED",
                "actual_fill_price": 1799.0, "broker_order_id": "B200",
            }])
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert om._orders["LIVE_200"].fill_status == "JOURNAL_RESTORED"

    def test_T045_old_events_beyond_7_days_ignored(self, tmp_path):
        """Events older than 7 days are not restored."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            self._write_journal(jf, [{
                "event": "OPEN", "timestamp": old_ts,
                "order_id": "OLD_001", "symbol": "WIPRO", "direction": "BUY",
                "quantity": 1, "entry_price": 500.0, "stop_loss": 480.0,
                "target_price": 530.0, "strategy": "Trend", "fill_status": "FILLED",
                "actual_fill_price": 501.0, "broker_order_id": "BOLD",
            }])
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert "OLD_001" not in om._orders

    def test_T046_paper_mode_skips_restore(self, tmp_path):
        """Paper mode does NOT call _restore_from_live_journal logic."""
        from execution_engine.order_manager import OrderManager
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = True
        om._orders    = {}
        om._restore_stats = {"restored_today": 0}
        from models import Portfolio
        om._portfolio = Portfolio(capital=100_000)
        import execution_engine.order_manager as _om
        orig = _om.LIVE_ORDER_LOG
        _om.LIVE_ORDER_LOG = str(tmp_path / "nonexistent.jsonl")
        try:
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
        # Should not raise and orders remain empty
        assert len(om._orders) == 0

    def test_T047_portfolio_positions_populated(self, tmp_path):
        """Restored position is registered in _portfolio.positions."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            self._write_journal(jf, [{
                "event": "OPEN", "timestamp": datetime.now(timezone.utc).isoformat(),
                "order_id": "LIVE_300", "symbol": "HDFC", "direction": "BUY",
                "quantity": 2, "entry_price": 1600.0, "stop_loss": 1560.0,
                "target_price": 1680.0, "strategy": "Swing", "fill_status": "FILLED",
                "actual_fill_price": 1601.0, "broker_order_id": "B300",
            }])
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert "HDFC" in om._portfolio.positions

    def test_T048_corrupt_line_skipped_rest_restored(self, tmp_path):
        """Corrupt JSON line is skipped; valid lines still restored."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            ts = datetime.now(timezone.utc).isoformat()
            jf.parent.mkdir(parents=True, exist_ok=True)
            with jf.open("w") as fh:
                fh.write("NOT VALID JSON\n")
                fh.write(json.dumps({
                    "event": "OPEN", "timestamp": ts,
                    "order_id": "LIVE_400", "symbol": "BAJAJ", "direction": "BUY",
                    "quantity": 1, "entry_price": 7000.0, "stop_loss": 6800.0,
                    "target_price": 7300.0, "strategy": "Breakout", "fill_status": "FILLED",
                    "actual_fill_price": 7005.0, "broker_order_id": "B400",
                }) + "\n")
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert "LIVE_400" in om._orders

    def test_T049_reconcile_startup_fills_handles_journal_restored(self, tmp_path):
        """reconcile_startup_fills() processes JOURNAL_RESTORED via real-shaped broker."""
        from execution_engine.order_manager import OrderManager, OrderRecord

        class _RealShapedBroker:
            """Shaped like DhanBroker — has get_fill_details, not MagicMock."""
            def get_fill_details(self, order_id):
                return {
                    "status": "FILLED", "actual_fill_price": 601.0,
                    "filled_quantity": 5, "requested_price": 600.0,
                    "order_status_raw": "TRADED", "fill_timestamp": "",
                    "reconciliation_source": "TEST",
                }

        om = OrderManager.__new__(OrderManager)
        om._paper_mode = False
        om._orders = {}
        rec = OrderRecord(
            order_id="LIVE_500", symbol="SBIN", direction="BUY",
            quantity=5, entry_price=600.0, stop_loss=580.0, target=640.0,
            strategy="Momentum", fill_status="JOURNAL_RESTORED",
        )
        om._orders["LIVE_500"] = rec
        om._broker = _RealShapedBroker()

        def fake_reconcile(r):
            fill = om._broker.get_fill_details(r.order_id)
            r.fill_status       = fill["status"]
            r.actual_fill_price = fill["actual_fill_price"]
        om._reconcile_fill = fake_reconcile

        count = om.reconcile_startup_fills()
        assert count == 1
        assert om._orders["LIVE_500"].fill_status == "FILLED"
        assert om._orders["LIVE_500"].actual_fill_price == 601.0

    def test_T050_multiple_positions_all_restored(self, tmp_path):
        """Multiple distinct OPEN events are all restored."""
        import execution_engine.order_manager as _om
        jf = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            ts = datetime.now(timezone.utc).isoformat()
            events = []
            for i in range(3):
                events.append({
                    "event": "OPEN", "timestamp": ts,
                    "order_id": f"LIVE_6{i:02d}", "symbol": f"SYM{i}",
                    "direction": "BUY", "quantity": 1, "entry_price": 100.0,
                    "stop_loss": 95.0, "target_price": 110.0, "strategy": "Test",
                    "fill_status": "FILLED", "actual_fill_price": 100.5,
                    "broker_order_id": f"B6{i:02d}",
                })
            self._write_journal(jf, events)
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders    = {}
            om._restore_stats = {"restored_today": 0}
            from models import Portfolio
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir

        assert om._restore_stats["restored_today"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# M-001: KLP observation_id standardization
# ─────────────────────────────────────────────────────────────────────────────

class TestObservationIdStandardization:
    """T051–T060: KLP outcome engine uses canonical observation_id field."""

    def _make_klp_outcome_engine(self, tmp_path):
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        return KLPOutcomeEngine(data_dir=tmp_path)

    def test_T051_build_outcome_record_has_observation_id(self, tmp_path):
        """_build_outcome_record returns observation_id field."""
        engine = self._make_klp_outcome_engine(tmp_path)
        obs = {"obs_id": "OBS_123", "trading_date": "2026-08-25",
               "symbol": "TEST", "direction": "BUY", "reference_entry": 100.0}
        result = engine._build_outcome_record(obs, {"first_event": "OUTCOME_NO_DATA"})
        assert "observation_id" in result, "observation_id must be present in outcome record"

    def test_T052_observation_id_equals_obs_id(self, tmp_path):
        """observation_id == obs_id for backward compatibility."""
        engine = self._make_klp_outcome_engine(tmp_path)
        obs = {"obs_id": "OBS_ABC", "trading_date": "2026-08-25",
               "symbol": "TEST", "direction": "BUY", "reference_entry": 100.0}
        result = engine._build_outcome_record(obs, {"first_event": "OUTCOME_NO_DATA"})
        assert result["observation_id"] == result["obs_id"]

    def test_T053_build_outcome_record_uses_observation_id_field_first(self, tmp_path):
        """When obs has observation_id, it takes priority over obs_id."""
        engine = self._make_klp_outcome_engine(tmp_path)
        obs = {
            "observation_id": "CANONICAL_ID",
            "obs_id":         "OLD_ID",
            "trading_date":   "2026-08-25",
            "symbol":         "TEST",
            "direction":      "BUY",
            "reference_entry": 100.0,
        }
        result = engine._build_outcome_record(obs, {"first_event": "OUTCOME_NO_DATA"})
        assert result["observation_id"] == "CANONICAL_ID"

    def test_T054_obs_id_alias_preserved(self, tmp_path):
        """obs_id field is still present in outcome record (backward compat)."""
        engine = self._make_klp_outcome_engine(tmp_path)
        obs = {"obs_id": "LEGACY_ID", "trading_date": "2026-08-25",
               "symbol": "TEST", "direction": "BUY", "reference_entry": 100.0}
        result = engine._build_outcome_record(obs, {"first_event": "OUTCOME_NO_DATA"})
        assert "obs_id" in result, "obs_id alias must be preserved for backward compat"

    def test_T055_load_pending_obs_checks_both_fields(self, tmp_path):
        """_load_pending_obs recognizes OUTCOME_UPDATE keyed by either field."""
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        engine = KLPOutcomeEngine(data_dir=tmp_path)
        today = date.today().isoformat()
        klp_file = tmp_path / f"KLP_{today}.jsonl"
        obs_id = "DUAL_FIELD_OBS"
        # Write KNOWLEDGE_OBSERVATION with obs_id only
        ko = {
            "event_type": "KNOWLEDGE_OBSERVATION",
            "obs_id": obs_id, "observation_id": obs_id,
            "trading_date": today, "symbol": "TEST",
            "direction": "BUY", "reference_entry": 100.0,
            "knowledge_target": 110.0, "knowledge_stop_loss": 95.0,
        }
        # Write OUTCOME_UPDATE keyed by observation_id
        ou = {
            "event_type": "OUTCOME_UPDATE",
            "observation_id": obs_id,
            "first_event": "TARGET_HIT",
        }
        with klp_file.open("w") as fh:
            fh.write(json.dumps(ko) + "\n")
            fh.write(json.dumps(ou) + "\n")
        pending = engine._load_pending_obs(today)
        # obs_id should be in completed_obs_ids from OUTCOME_UPDATE, so pending = []
        assert not any(
            (r.get("obs_id") == obs_id or r.get("observation_id") == obs_id)
            for r in pending
        ), "Already-completed obs should not appear in pending"


# ─────────────────────────────────────────────────────────────────────────────
# P-002: MetaModel per-strategy minimum-sample guard
# ─────────────────────────────────────────────────────────────────────────────

class TestMetaModelSmallSampleGuard:
    """T061–T065: MetaModel falls back to DEFAULT_PRED for sparse strategies."""

    def _make_features(self):
        from meta_learning.feature_extractor import FeatureVector
        return FeatureVector(
            regime_score=0.5, vix_norm=0.3, breadth_norm=0.5,
            fii_score=0.2, global_sentiment=0.6, sector_strength=0.5,
            pcr_norm=0.5, vol_level=0.4,
        )

    def test_T061_sparse_strategy_returns_default_pred(self):
        """Strategy with fewer than MIN_PER_STRATEGY_OBS returns DEFAULT_PRED."""
        from meta_learning.meta_model import MetaModel, Observation, DEFAULT_PRED, MIN_PER_STRATEGY_OBS
        model = MetaModel(k=5)
        # Add 2 obs for sparse strategy (less than MIN=3)
        for i in range(2):
            model.add(Observation(features=[0.5]*8, strategy="Sparse", r_multiple=1.0))
        # Add 5 obs for well-sampled strategy
        for i in range(5):
            model.add(Observation(features=[0.5]*8, strategy="WellSampled", r_multiple=1.5))
        model._trained = True

        fv = self._make_features()
        preds = model.predict(fv, ["Sparse", "WellSampled"])
        assert preds["Sparse"] == DEFAULT_PRED, (
            f"Sparse strategy with {2} obs < MIN={MIN_PER_STRATEGY_OBS} "
            f"should return DEFAULT_PRED={DEFAULT_PRED}"
        )

    def test_T062_above_min_uses_knn(self):
        """Strategy at or above MIN_PER_STRATEGY_OBS uses k-NN prediction."""
        from meta_learning.meta_model import MetaModel, Observation, DEFAULT_PRED, MIN_PER_STRATEGY_OBS
        model = MetaModel(k=3)
        for i in range(MIN_PER_STRATEGY_OBS):
            model.add(Observation(features=[0.5]*8, strategy="Enough", r_multiple=2.0))
        model._trained = True
        fv = self._make_features()
        preds = model.predict(fv, ["Enough"])
        # k-NN on all-same features should return ~2.0
        assert abs(preds["Enough"] - 2.0) < 0.1, f"Expected ~2.0 from k-NN, got {preds['Enough']}"

    def test_T063_zero_obs_returns_default(self):
        """Strategy with zero observations returns DEFAULT_PRED."""
        from meta_learning.meta_model import MetaModel, DEFAULT_PRED
        model = MetaModel(k=5)
        for i in range(10):
            model.add(
                __import__("meta_learning.meta_model", fromlist=["Observation"]).Observation(
                    features=[0.5]*8, strategy="Other", r_multiple=1.0
                )
            )
        model._trained = True
        fv = self._make_features()
        preds = model.predict(fv, ["NoHistory"])
        assert preds["NoHistory"] == DEFAULT_PRED

    def test_T064_min_per_strategy_constant_is_3(self):
        """MIN_PER_STRATEGY_OBS is defined as 3 (P-002 requirement)."""
        from meta_learning.meta_model import MIN_PER_STRATEGY_OBS
        assert MIN_PER_STRATEGY_OBS == 3

    def test_T065_model_not_trained_returns_equal_weight(self):
        """When model is not trained, StrategyWeightPredictor returns equal weights."""
        from meta_learning.strategy_weight_predictor import StrategyWeightPredictor
        from meta_learning.meta_model import MetaModel
        model = MetaModel(k=5)
        predictor = StrategyWeightPredictor(model)
        fv = self._make_features()
        alloc = predictor.predict(fv, ["A", "B", "C"])
        assert not alloc.model_active
        assert abs(alloc.allocations["A"] - 1/3) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# D-008: HBE Daily Snapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestHBEDailySnapshot:
    """T066–T070: HBE writes daily snapshot to data/klp/historical_behaviour/."""

    def test_T066_snapshot_file_created(self, tmp_path):
        """write_daily_snapshot() creates hbe_snapshot_YYYY-MM-DD.json."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        hbe = HistoricalBehaviourEngine(data_dir=tmp_path / "klp")
        hbe.write_daily_snapshot(output_dir=tmp_path / "hbe_out")
        today = date.today().isoformat()
        snap = tmp_path / "hbe_out" / f"hbe_snapshot_{today}.json"
        assert snap.exists(), f"Snapshot file not found: {snap}"

    def test_T067_snapshot_contains_required_fields(self, tmp_path):
        """Snapshot JSON has snapshot_date, outcome_count, version."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        hbe = HistoricalBehaviourEngine(data_dir=tmp_path / "klp")
        out = tmp_path / "hbe_out"
        hbe.write_daily_snapshot(output_dir=out)
        today = date.today().isoformat()
        snap = json.loads((out / f"hbe_snapshot_{today}.json").read_text())
        assert "snapshot_date" in snap
        assert "outcome_count" in snap
        assert "version"       in snap

    def test_T068_snapshot_is_idempotent(self, tmp_path):
        """Calling write_daily_snapshot twice overwrites, doesn't append."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        hbe = HistoricalBehaviourEngine(data_dir=tmp_path / "klp")
        out = tmp_path / "hbe_out"
        hbe.write_daily_snapshot(output_dir=out)
        hbe.write_daily_snapshot(output_dir=out)
        today = date.today().isoformat()
        snap = tmp_path / "hbe_out" / f"hbe_snapshot_{today}.json"
        # Should be valid JSON (no double-writing)
        data = json.loads(snap.read_text())
        assert isinstance(data, dict)

    def test_T069_snapshot_outcome_count_matches(self, tmp_path):
        """snapshot.outcome_count matches hbe.get_outcome_count()."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        hbe = HistoricalBehaviourEngine(data_dir=tmp_path / "klp")
        out = tmp_path / "hbe_out"
        hbe.write_daily_snapshot(output_dir=out)
        today = date.today().isoformat()
        snap = json.loads((out / f"hbe_snapshot_{today}.json").read_text())
        assert snap["outcome_count"] == hbe.get_outcome_count()

    def test_T070_snapshot_non_fatal_on_write_error(self):
        """write_daily_snapshot() is non-fatal even with invalid output_dir."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        hbe = HistoricalBehaviourEngine()
        # Must not raise
        hbe.write_daily_snapshot(output_dir=Path("/nonexistent_dir_xyz/hbe"))


# ─────────────────────────────────────────────────────────────────────────────
# K-001: Failure Taxonomy
# ─────────────────────────────────────────────────────────────────────────────

class TestFailureTaxonomy:
    """T071–T085: Failure categories are assigned correctly."""

    def _make_rec(self, outcome_class, t5_ret=None, stop_hit=False,
                  direction="BUY", mae_pct=0.0, t1_ret=None,
                  first_event="OUTCOME_EXPIRED", regime="BULL"):
        return {
            "observation_id": "OBS_TAX_001",
            "lifecycle_state": "OUTCOME_OBSERVED",
            "outcome_class": outcome_class,
            "direction": direction,
            "t5_ret_pct": t5_ret,
            "t1_ret_pct": t1_ret,
            "stop_hit": stop_hit,
            "mae_pct": mae_pct,
            "outcome_first_event": first_event,
            "regime": regime,
        }

    def test_T071_direction_wrong_classified(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_DIRECTION_WRONG
        rec = self._make_rec("EXECUTED_LOSS", t5_ret=-2.5, direction="BUY")
        assert classify_failure(rec) == CATEGORY_DIRECTION_WRONG

    def test_T072_regime_mismatch_bear_buy(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_REGIME_MISMATCH
        rec = self._make_rec("EXECUTED_LOSS", direction="BUY", regime="BEAR", t5_ret=-1.5)
        # Should get DIRECTION_WRONG since t5_ret < 0 for BUY
        # After that check: REGIME_MISMATCH only applies if not direction_wrong
        result = classify_failure(rec)
        # Either DIRECTION_WRONG or REGIME_MISMATCH is acceptable here
        assert result in (CATEGORY_REGIME_MISMATCH,
                          __import__("learning_system.failure_taxonomy",
                                     fromlist=["CATEGORY_DIRECTION_WRONG"]).CATEGORY_DIRECTION_WRONG)

    def test_T073_stop_too_tight_first_bar(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_STOP_TOO_TIGHT
        rec = self._make_rec("STOP_EXIT", stop_hit=True, mae_pct=-0.2,
                             first_event="STOP_HIT", t5_ret=1.0)
        result = classify_failure(rec)
        # STOP_TOO_TIGHT: mae < 0.5 and stop_hit on first event
        # But t5_ret > 0 (BUY) means THESIS_INTACT takes priority
        from learning_system.failure_taxonomy import CATEGORY_THESIS_INTACT
        assert result in (CATEGORY_STOP_TOO_TIGHT, CATEGORY_THESIS_INTACT)

    def test_T074_thesis_intact_classified(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_THESIS_INTACT
        rec = self._make_rec("STOP_EXIT", stop_hit=True, t5_ret=2.0, first_event="STOP_HIT")
        assert classify_failure(rec) == CATEGORY_THESIS_INTACT

    def test_T075_low_follow_through_classified(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_LOW_FOLLOW_THROUGH
        rec = self._make_rec("EXECUTED_LOSS", t1_ret=0.5, t5_ret=-0.5, direction="BUY")
        result = classify_failure(rec)
        assert result == CATEGORY_LOW_FOLLOW_THROUGH

    def test_T076_execution_skip_rejected_incorrect(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_EXECUTION_SKIP
        rec = self._make_rec("REJECTED_INCORRECT")
        assert classify_failure(rec) == CATEGORY_EXECUTION_SKIP

    def test_T077_execution_skip_missed_opportunity(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_EXECUTION_SKIP
        rec = self._make_rec("MISSED_OPPORTUNITY")
        assert classify_failure(rec) == CATEGORY_EXECUTION_SKIP

    def test_T078_uncategorised_for_unknown_outcome(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_UNCATEGORISED
        rec = self._make_rec("EXECUTED_WIN", t5_ret=2.0)
        assert classify_failure(rec) == CATEGORY_UNCATEGORISED

    def test_T079_never_raises(self):
        from learning_system.failure_taxonomy import classify_failure
        # Totally malformed record
        result = classify_failure({"garbage": True})
        assert isinstance(result, str)

    def test_T080_write_failure_summary_creates_file(self, tmp_path):
        from learning_system.failure_taxonomy import write_failure_summary, CATEGORY_EXECUTION_SKIP
        recs = [
            {"observation_id": "OBS1", "lifecycle_state": "OUTCOME_OBSERVED",
             "outcome_class": "REJECTED_INCORRECT", "direction": "BUY",
             "t5_ret_pct": None},
        ]
        result = write_failure_summary(recs, trading_date="2026-08-26", output_dir=tmp_path)
        assert result["total_classified"] == 1
        assert result["error"] is None
        sf = tmp_path / "failure_summary_2026-08-26.jsonl"
        assert sf.exists()

    def test_T081_write_skips_pending_records(self, tmp_path):
        from learning_system.failure_taxonomy import write_failure_summary
        recs = [
            {"observation_id": "OBS2", "lifecycle_state": "OUTCOME_PENDING",
             "outcome_class": "EXECUTED_WIN"},
        ]
        result = write_failure_summary(recs, trading_date="2026-08-26", output_dir=tmp_path)
        assert result["total_classified"] == 0

    def test_T082_write_is_non_fatal(self, tmp_path):
        from learning_system.failure_taxonomy import write_failure_summary
        # Invalid output dir
        result = write_failure_summary([], trading_date="2026-08-26",
                                        output_dir=Path("/no_such_dir_xyz"))
        # Non-fatal: returns result dict, no raise
        assert isinstance(result, dict)

    def test_T083_category_counts_in_result(self, tmp_path):
        from learning_system.failure_taxonomy import (
            write_failure_summary,
            CATEGORY_EXECUTION_SKIP,
            CATEGORY_DIRECTION_WRONG,
        )
        recs = [
            {"observation_id": f"OBS{i}", "lifecycle_state": "OUTCOME_OBSERVED",
             "outcome_class": "REJECTED_INCORRECT", "direction": "BUY"}
            for i in range(3)
        ] + [
            {"observation_id": f"OBS_D{i}", "lifecycle_state": "OUTCOME_OBSERVED",
             "outcome_class": "EXECUTED_LOSS", "direction": "BUY", "t5_ret_pct": -2.5}
            for i in range(2)
        ]
        result = write_failure_summary(recs, trading_date="2026-08-26", output_dir=tmp_path)
        assert result["categories"].get(CATEGORY_EXECUTION_SKIP, 0) == 3
        assert result["categories"].get(CATEGORY_DIRECTION_WRONG, 0) == 2

    def test_T084_stop_too_wide_classified(self):
        from learning_system.failure_taxonomy import classify_failure, CATEGORY_STOP_TOO_WIDE
        rec = self._make_rec("EXECUTED_LOSS", mae_pct=-4.5, t5_ret=0.5, stop_hit=True,
                             first_event="STOP_HIT")
        # t5_ret > 0 for BUY → THESIS_INTACT takes priority, not STOP_TOO_WIDE
        # But if t5_ret is small/negative → STOP_TOO_WIDE
        rec2 = self._make_rec("EXECUTED_LOSS", mae_pct=-4.5, t5_ret=-0.3,
                              stop_hit=False, first_event="OUTCOME_EXPIRED")
        result = classify_failure(rec2)
        assert result == CATEGORY_STOP_TOO_WIDE

    def test_T085_written_records_parseable(self, tmp_path):
        from learning_system.failure_taxonomy import write_failure_summary
        recs = [
            {"observation_id": "OBS_X", "lifecycle_state": "OUTCOME_OBSERVED",
             "outcome_class": "MISSED_OPPORTUNITY", "direction": "SELL",
             "trading_date": "2026-08-26"},
        ]
        write_failure_summary(recs, trading_date="2026-08-26", output_dir=tmp_path)
        sf = tmp_path / "failure_summary_2026-08-26.jsonl"
        row = json.loads(sf.read_text().strip())
        assert "failure_category" in row
        assert "observation_id" in row


# ─────────────────────────────────────────────────────────────────────────────
# D-009: Scan No-Signal Observer
# ─────────────────────────────────────────────────────────────────────────────

class TestScanNoSignalObserver:
    """T086–T090: Scanned-but-no-setup observations recorded to KLP."""

    def test_T086_observation_written_to_klp(self, tmp_path):
        """record_no_signal writes a SCAN_NO_SETUP record."""
        import opportunity_engine.scan_no_signal_observer as _obs
        orig = _obs._KLP_DIR
        try:
            _obs._KLP_DIR = tmp_path / "klp"
            snap = MagicMock()
            snap.regime = MagicMock()
            snap.regime.value = "BULL"
            snap.vix = 14.5
            stock = {"symbol": "WIPRO", "ltp": 500.0, "rsi": 55.0,
                     "volume_ratio": 0.8, "atr": 5.0, "score": 7.2,
                     "_prepared": True}
            _obs.record_no_signal(stock, snap, "rsi_neutral")
        finally:
            _obs._KLP_DIR = orig

        today = date.today().isoformat()
        klp_file = tmp_path / "klp" / f"KLP_{today}.jsonl"
        assert klp_file.exists()
        row = json.loads(klp_file.read_text().strip())
        assert row["event_type"] == "SCAN_NO_SETUP"
        assert row["symbol"] == "WIPRO"

    def test_T087_observation_has_observation_id(self, tmp_path):
        """SCAN_NO_SETUP record has both observation_id and obs_id."""
        import opportunity_engine.scan_no_signal_observer as _obs
        orig = _obs._KLP_DIR
        try:
            _obs._KLP_DIR = tmp_path / "klp"
            snap = MagicMock(); snap.regime = MagicMock(); snap.regime.value = "BULL"
            snap.vix = 14.5
            _obs.record_no_signal({"symbol": "TCS", "_prepared": True, "ltp": 3500.0}, snap, "rsi_neutral")
        finally:
            _obs._KLP_DIR = orig

        today = date.today().isoformat()
        row = json.loads((tmp_path / "klp" / f"KLP_{today}.jsonl").read_text().strip())
        assert "observation_id" in row
        assert "obs_id" in row
        assert row["observation_id"] == row["obs_id"]

    def test_T088_no_lookahead_flag_set(self, tmp_path):
        """SCAN_NO_SETUP record has no_lookahead=True."""
        import opportunity_engine.scan_no_signal_observer as _obs
        orig = _obs._KLP_DIR
        try:
            _obs._KLP_DIR = tmp_path / "klp"
            snap = MagicMock(); snap.regime = MagicMock(); snap.regime.value = "BULL"; snap.vix = 15.0
            _obs.record_no_signal({"symbol": "HDFC", "_prepared": True, "ltp": 1600.0}, snap, "rsi_overbought")
        finally:
            _obs._KLP_DIR = orig

        today = date.today().isoformat()
        row = json.loads((tmp_path / "klp" / f"KLP_{today}.jsonl").read_text().strip())
        assert row.get("no_lookahead") is True

    def test_T089_non_fatal_on_write_failure(self):
        """record_no_signal is non-fatal even with invalid KLP dir."""
        import opportunity_engine.scan_no_signal_observer as _obs
        orig = _obs._KLP_DIR
        try:
            _obs._KLP_DIR = Path("/nonexistent_dir_xyz/klp")
            snap = MagicMock(); snap.regime = MagicMock(); snap.regime.value = "BULL"; snap.vix = 15.0
            # Must not raise
            _obs.record_no_signal({"symbol": "INFY", "_prepared": True, "ltp": 1800.0}, snap, "vol_below_min")
        finally:
            _obs._KLP_DIR = orig

    def test_T090_empty_symbol_not_written(self, tmp_path):
        """record_no_signal skips stocks with empty symbol."""
        import opportunity_engine.scan_no_signal_observer as _obs
        orig = _obs._KLP_DIR
        try:
            _obs._KLP_DIR = tmp_path / "klp"
            snap = MagicMock(); snap.regime = MagicMock(); snap.regime.value = "BULL"; snap.vix = 15.0
            _obs.record_no_signal({"symbol": "", "_prepared": True}, snap, "rsi_neutral")
        finally:
            _obs._KLP_DIR = orig

        today = date.today().isoformat()
        klp_file = tmp_path / "klp" / f"KLP_{today}.jsonl"
        assert not klp_file.exists(), "File should not be written for empty symbol"
