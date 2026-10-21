"""
tests/test_dta_late_cap_swap_bridge_001.py
=============================================
DTA-LATE-CAP-SWAP-BRIDGE-001

Verifies:
  1. OrderManager.execute_late_cap_swap() correctly reuses _smart_swap_check()
     + the shared daily rotation throttle + close_position(), returning
     True only on a real, successful swap.
  2. risk_control/late_cap_swap_bridge.py's SHADOW registration records a
     shadow candidate without ever calling execute_late_cap_swap(), and
     returns False (no behavior change) in SHADOW mode.
  3. ACTIVE mode calls execute_late_cap_swap() and returns its result.
  4. resolve_matured_shadow_records() correctly classifies CORRECT_SWAP /
     INCORRECT_SWAP once both legs of evidence exist, and leaves records
     PENDING otherwise.
  5. advance_lifecycle() promotes SHADOW_ACTIVE -> ACTIVE on sufficient
     evidence, REJECTED after the max observation window, and ACTIVE ->
     ROLLED_BACK on post-activation degradation.
  6. The real correctness fix: capital_reserve_readiness_engine.py now
     reads MAX_POSITIONS_CAP_FINAL, not MAX_POSITIONS_CAP.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import risk_control.late_cap_swap_bridge as lcsb


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_store(tmp_path, monkeypatch):
    monkeypatch.setattr(lcsb, "_STORE_DIR", str(tmp_path))
    monkeypatch.setattr(lcsb, "_RECORDS_PATH", str(tmp_path / "shadow_records.json"))
    monkeypatch.setattr(lcsb, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(lcsb, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    yield


def _make_order_manager():
    from execution_engine.order_manager import OrderManager
    mgr = OrderManager.__new__(OrderManager)
    mgr._paper_mode = True
    mgr._broker = None
    mgr._orders = {}
    mgr._lock = threading.Lock()
    mgr._portfolio = SimpleNamespace(positions={})
    mgr._swap_rotation_date = None
    return mgr


def _make_open_rec(order_id, symbol, direction="BUY", entry_price=100.0,
                    stop_loss=98.0, quantity=10, confidence_score=5.0):
    from execution_engine.order_manager import OrderRecord
    return OrderRecord(
        order_id=order_id, symbol=symbol, direction=direction, quantity=quantity,
        entry_price=entry_price, stop_loss=stop_loss, target=entry_price + 5.0,
        strategy="s", status="open", placed_at=datetime.now() - timedelta(minutes=60),
        confidence_score=confidence_score,
    )


def _signal(symbol="NEWSTK", entry=100.0, stop=98.0, target=106.0, strategy="Breakout"):
    return SimpleNamespace(
        symbol=symbol, entry_price=entry, stop_loss=stop, target_price=target,
        strategy_name=strategy, direction=SimpleNamespace(value="BUY"),
        price_is_live=True,
    )


def _decision(score=7.5):
    return SimpleNamespace(confidence_score=score)


# ---------------------------------------------------------------------------
# A — OrderManager.execute_late_cap_swap()
# ---------------------------------------------------------------------------

class TestA_ExecuteLateCapSwap:
    def test_a01_no_candidate_returns_false(self):
        mgr = _make_order_manager()
        with patch.object(mgr, "_smart_swap_check", return_value=None):
            assert mgr.execute_late_cap_swap("NEW", 8.0, 100.0, 98.0, 106.0) is False

    def test_a02_successful_swap_closes_weak_and_returns_true(self):
        mgr = _make_order_manager()
        weak = _make_open_rec("OID1", "WEAK")
        mgr._orders["OID1"] = weak
        with patch.object(mgr, "_smart_swap_check", return_value=("OID1", "WEAK", 3.0)), \
             patch.object(mgr, "close_position", return_value=True) as mock_close:
            result = mgr.execute_late_cap_swap("NEW", 8.0, 100.0, 98.0, 106.0)
        assert result is True
        mock_close.assert_called_once()
        assert mock_close.call_args.kwargs.get("reason") == "LATE_CAP_SWAP" or \
            mock_close.call_args[0][-1] == "LATE_CAP_SWAP" or "LATE_CAP_SWAP" in mock_close.call_args.args
        assert mgr._swap_rotation_date == datetime.now().strftime("%Y-%m-%d")

    def test_a03_daily_throttle_blocks_second_swap_same_day(self):
        mgr = _make_order_manager()
        mgr._swap_rotation_date = datetime.now().strftime("%Y-%m-%d")
        weak = _make_open_rec("OID1", "WEAK")
        mgr._orders["OID1"] = weak
        with patch.object(mgr, "_smart_swap_check", return_value=("OID1", "WEAK", 3.0)), \
             patch.object(mgr, "close_position") as mock_close:
            result = mgr.execute_late_cap_swap("NEW", 8.0, 100.0, 98.0, 106.0)
        assert result is False
        mock_close.assert_not_called()

    def test_a04_close_failure_returns_false_no_rotation_consumed(self):
        mgr = _make_order_manager()
        weak = _make_open_rec("OID1", "WEAK")
        mgr._orders["OID1"] = weak
        with patch.object(mgr, "_smart_swap_check", return_value=("OID1", "WEAK", 3.0)), \
             patch.object(mgr, "close_position", return_value=False):
            result = mgr.execute_late_cap_swap("NEW", 8.0, 100.0, 98.0, 106.0)
        assert result is False
        assert mgr._swap_rotation_date is None


# ---------------------------------------------------------------------------
# B — register_late_cap_swap_opportunity() -- SHADOW vs ACTIVE
# ---------------------------------------------------------------------------

class TestB_Registration:
    def test_b01_shadow_mode_records_and_returns_false(self):
        mgr = _make_order_manager()
        weak = _make_open_rec("OID1", "WEAK")
        mgr._orders["OID1"] = weak
        with patch.object(mgr, "_smart_swap_check", return_value=("OID1", "WEAK", 3.0)):
            result = lcsb.register_late_cap_swap_opportunity(
                mgr, _signal(), _decision(), "2026-10-01",
            )
        assert result is False
        records = lcsb._load_records()
        assert len(records) == 1
        assert records[0].rejected_symbol == "NEWSTK"
        assert records[0].weak_symbol == "WEAK"
        assert records[0].status == "PENDING"
        assert mgr._orders["OID1"].status == "open"   # SHADOW is decision-only, nothing closed

    def test_b02_no_candidate_no_record(self):
        mgr = _make_order_manager()
        with patch.object(mgr, "_smart_swap_check", return_value=None):
            result = lcsb.register_late_cap_swap_opportunity(mgr, _signal(), _decision(), "2026-10-01")
        assert result is False
        assert lcsb._load_records() == []

    def test_b03_active_mode_delegates_to_execute_late_cap_swap(self):
        mgr = _make_order_manager()
        lcsb._save_state({"status": lcsb.STATUS_ACTIVE, "activated_at": "2026-10-01T00:00:00+00:00"})
        with patch.object(mgr, "execute_late_cap_swap", return_value=True) as mock_exec:
            result = lcsb.register_late_cap_swap_opportunity(mgr, _signal(), _decision(8.5), "2026-10-05")
        assert result is True
        mock_exec.assert_called_once()
        assert lcsb._load_records() == []   # ACTIVE mode doesn't shadow-record

    def test_b04_never_raises_on_internal_error(self):
        mgr = _make_order_manager()
        with patch.object(mgr, "_smart_swap_check", side_effect=RuntimeError("boom")):
            result = lcsb.register_late_cap_swap_opportunity(mgr, _signal(), _decision(), "2026-10-01")
        assert result is False


# ---------------------------------------------------------------------------
# C — resolve_matured_shadow_records()
# ---------------------------------------------------------------------------

class TestC_Resolution:
    def _pending_record(self, trade_date):
        return lcsb.LateCapSwapShadowRecord(
            swap_id="LCSB-TEST01", created_at="2026-10-01T00:00:00+00:00",
            trade_date=trade_date, rejected_symbol="NEWSTK",
            rejected_strategy="Breakout", rejected_direction="BUY",
            rejected_score=8.0, rejected_entry=100.0, rejected_stop=98.0,
            rejected_target=106.0, weak_order_id="OID1", weak_symbol="WEAK",
            weak_score=3.0, weak_direction="BUY", weak_entry_price=50.0,
            weak_quantity=20, weak_pnl_if_closed_at_decision=-40.0,
        )

    def test_c01_resolves_correct_swap_when_both_legs_available(self):
        old_date = (date.today() - timedelta(days=10)).isoformat()
        rec = self._pending_record(old_date)
        lcsb._save_records([rec])

        mgr = _make_order_manager()
        weak_closed = _make_open_rec("OID1", "WEAK")
        weak_closed.status = "closed"
        weak_closed.pnl = -80.0   # actual: weak position lost more by holding
        mgr._orders["OID1"] = weak_closed

        with patch.object(lcsb, "_simulate_candidate_exit", return_value=150.0), \
             patch.object(lcsb, "_swap_cost_estimate", return_value=10.0):
            result = lcsb.resolve_matured_shadow_records(mgr)

        assert result["resolved"] == 1
        records = lcsb._load_records()
        assert records[0].status == "RESOLVED"
        assert records[0].classification == "CORRECT_SWAP"
        # scenario_swap = -40 + 150 - 10 = 100; scenario_no_swap = -80; benefit = 180
        assert records[0].net_benefit_rs == pytest.approx(180.0)

    def test_c02_resolves_incorrect_swap(self):
        old_date = (date.today() - timedelta(days=10)).isoformat()
        rec = self._pending_record(old_date)
        lcsb._save_records([rec])

        mgr = _make_order_manager()
        weak_closed = _make_open_rec("OID1", "WEAK")
        weak_closed.status = "closed"
        weak_closed.pnl = 500.0   # actual: weak position recovered strongly
        mgr._orders["OID1"] = weak_closed

        with patch.object(lcsb, "_simulate_candidate_exit", return_value=-50.0), \
             patch.object(lcsb, "_swap_cost_estimate", return_value=10.0):
            result = lcsb.resolve_matured_shadow_records(mgr)

        records = lcsb._load_records()
        assert records[0].classification == "INCORRECT_SWAP"

    def test_c03_stays_pending_when_weak_position_still_open(self):
        old_date = (date.today() - timedelta(days=10)).isoformat()
        rec = self._pending_record(old_date)
        lcsb._save_records([rec])

        mgr = _make_order_manager()
        weak_open = _make_open_rec("OID1", "WEAK")   # still status="open"
        mgr._orders["OID1"] = weak_open

        with patch.object(lcsb, "_simulate_candidate_exit", return_value=150.0):
            result = lcsb.resolve_matured_shadow_records(mgr)

        assert result["resolved"] == 0
        assert lcsb._load_records()[0].status == "PENDING"

    def test_c04_abandons_after_max_record_age(self):
        very_old = (date.today() - timedelta(days=lcsb.MAX_RECORD_AGE_DAYS + 5)).isoformat()
        rec = self._pending_record(very_old)
        lcsb._save_records([rec])

        mgr = _make_order_manager()
        weak_open = _make_open_rec("OID1", "WEAK")
        mgr._orders["OID1"] = weak_open

        with patch.object(lcsb, "_simulate_candidate_exit", return_value=None):
            result = lcsb.resolve_matured_shadow_records(mgr)

        assert result["abandoned"] == 1
        assert lcsb._load_records()[0].status == "ABANDONED"

    def test_c05_never_raises(self):
        mgr = _make_order_manager()
        with patch.object(lcsb, "_load_records", side_effect=RuntimeError("boom")):
            result = lcsb.resolve_matured_shadow_records(mgr)
        assert result["status"] == "ERROR"


# ---------------------------------------------------------------------------
# D — advance_lifecycle()
# ---------------------------------------------------------------------------

class TestD_Lifecycle:
    def _resolved_records(self, n_correct, n_incorrect, resolved_at="2026-10-15T00:00:00+00:00"):
        records = []
        for i in range(n_correct):
            records.append(lcsb.LateCapSwapShadowRecord(
                swap_id=f"C{i}", created_at="x", trade_date="2026-10-01",
                rejected_symbol="A", rejected_strategy="s", rejected_direction="BUY",
                rejected_score=8.0, rejected_entry=100.0, rejected_stop=98.0,
                rejected_target=106.0, weak_order_id=f"O{i}", weak_symbol="W",
                weak_score=3.0, weak_direction="BUY", weak_entry_price=50.0,
                weak_quantity=10, weak_pnl_if_closed_at_decision=0.0,
                status="RESOLVED", classification="CORRECT_SWAP", resolved_at=resolved_at,
            ))
        for i in range(n_incorrect):
            records.append(lcsb.LateCapSwapShadowRecord(
                swap_id=f"I{i}", created_at="x", trade_date="2026-10-01",
                rejected_symbol="A", rejected_strategy="s", rejected_direction="BUY",
                rejected_score=8.0, rejected_entry=100.0, rejected_stop=98.0,
                rejected_target=106.0, weak_order_id=f"P{i}", weak_symbol="W",
                weak_score=3.0, weak_direction="BUY", weak_entry_price=50.0,
                weak_quantity=10, weak_pnl_if_closed_at_decision=0.0,
                status="RESOLVED", classification="INCORRECT_SWAP", resolved_at=resolved_at,
            ))
        return records

    def test_d01_insufficient_samples_stays_shadow(self):
        lcsb._save_state({"status": lcsb.STATUS_SHADOW_ACTIVE,
                           "shadow_start_date": date.today().isoformat()})
        lcsb._save_records(self._resolved_records(10, 2))
        result = lcsb.advance_lifecycle()
        assert result["status"] == lcsb.STATUS_SHADOW_ACTIVE

    def test_d02_promotes_to_active_on_sufficient_evidence(self):
        lcsb._save_state({"status": lcsb.STATUS_SHADOW_ACTIVE,
                           "shadow_start_date": date.today().isoformat()})
        n_correct = int(lcsb.MIN_SAMPLES_FOR_ACTIVATION * 0.7)
        n_incorrect = lcsb.MIN_SAMPLES_FOR_ACTIVATION - n_correct
        lcsb._save_records(self._resolved_records(n_correct, n_incorrect))
        result = lcsb.advance_lifecycle()
        assert result["status"] == lcsb.STATUS_ACTIVE
        assert lcsb.get_status() == lcsb.STATUS_ACTIVE

    def test_d03_rejects_after_max_observation_window(self):
        old_start = (date.today() - timedelta(days=lcsb.MAX_OBSERVATION_DAYS + 5)).isoformat()
        lcsb._save_state({"status": lcsb.STATUS_SHADOW_ACTIVE, "shadow_start_date": old_start})
        lcsb._save_records(self._resolved_records(2, 2))   # below activation bar
        result = lcsb.advance_lifecycle()
        assert result["status"] == lcsb.STATUS_REJECTED
        assert lcsb.get_status() == lcsb.STATUS_REJECTED

    def test_d04_rolls_back_on_post_activation_degradation(self):
        lcsb._save_state({"status": lcsb.STATUS_ACTIVE,
                           "activated_at": "2026-10-10T00:00:00+00:00"})
        # Evidence resolved AFTER activation shows poor performance
        bad_records = self._resolved_records(
            3, lcsb.MIN_SAMPLES_FOR_ROLLBACK_CHECK + 3, resolved_at="2026-10-15T00:00:00+00:00",
        )
        lcsb._save_records(bad_records)
        result = lcsb.advance_lifecycle()
        assert result["status"] == lcsb.STATUS_ROLLED_BACK
        assert lcsb.get_status() == lcsb.STATUS_ROLLED_BACK

    def test_d05_active_stays_active_when_performance_holds(self):
        lcsb._save_state({"status": lcsb.STATUS_ACTIVE,
                           "activated_at": "2026-10-10T00:00:00+00:00"})
        good_records = self._resolved_records(
            15, 2, resolved_at="2026-10-15T00:00:00+00:00",
        )
        lcsb._save_records(good_records)
        result = lcsb.advance_lifecycle()
        assert result["status"] == lcsb.STATUS_ACTIVE

    def test_d06_never_raises(self):
        with patch.object(lcsb, "_load_state", side_effect=RuntimeError("boom")):
            result = lcsb.advance_lifecycle()
        assert result["status"] == "ERROR"


# ---------------------------------------------------------------------------
# E — get_readiness_status()
# ---------------------------------------------------------------------------

class TestE_ReadinessAccessor:
    def test_e01_empty_state(self):
        status = lcsb.get_readiness_status()
        assert status["status"] == lcsb.STATUS_SHADOW_ACTIVE
        assert status["resolved"] == 0
        assert status["hit_rate"] is None

    def test_e02_reports_hit_rate(self):
        lcsb._save_records(self._records_helper())
        status = lcsb.get_readiness_status()
        assert status["resolved"] == 3
        assert status["correct_swap_count"] == 2
        assert status["hit_rate"] == pytest.approx(round(2 / 3, 3))

    def _records_helper(self):
        return [
            lcsb.LateCapSwapShadowRecord(
                swap_id=f"S{i}", created_at="x", trade_date="2026-10-01",
                rejected_symbol="A", rejected_strategy="s", rejected_direction="BUY",
                rejected_score=8.0, rejected_entry=100.0, rejected_stop=98.0,
                rejected_target=106.0, weak_order_id=f"O{i}", weak_symbol="W",
                weak_score=3.0, weak_direction="BUY", weak_entry_price=50.0,
                weak_quantity=10, weak_pnl_if_closed_at_decision=0.0,
                status="RESOLVED", classification=c,
            )
            for i, c in enumerate(["CORRECT_SWAP", "CORRECT_SWAP", "INCORRECT_SWAP"])
        ]


# ---------------------------------------------------------------------------
# F — capital_reserve_readiness_engine.py correctness fix
# ---------------------------------------------------------------------------

class TestF_ReadinessReasonFix:
    def test_f01_reads_the_real_late_cap_reason(self):
        import analysis.capital_reserve_readiness_engine as crre
        assert crre.REJECTION_REASON == "MAX_POSITIONS_CAP_FINAL"
