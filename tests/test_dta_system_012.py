"""
DTA-SYSTEM-012-FIX — Regression test suite
==========================================
Covers defects confirmed and fixed in DTA-012-FIX:

  D12-001  carry expiry record_trade_result missing in check_and_expire_carries()
             (RiskGuardian 2% daily-loss kill-switch bypassed for overnight positions)
  D12-002  Test T092 created real FailSafeRiskGuardian without isolated state_file
             (poisoned production data/risk_guardian_state.json with trading_halted=true)

D12-001 tests (T001–T010)
D12-002 tests (T011–T015)
Total: 15 new tests
"""
from __future__ import annotations

import csv
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeRiskGuardian:
    """Minimal fake — only the methods wired by D11-001 / D12-001."""

    def __init__(self):
        self._trading_halted = False
        self._halt_reason    = ""
        self.trade_results: List[tuple] = []   # [(pnl, won), ...]
        self.open_count:    int         = 0
        self.closed_count:  int         = 0

    def record_trade_result(self, pnl: float, won: bool) -> None:
        self.trade_results.append((pnl, won))

    def record_open_trade(self) -> None:
        self.open_count += 1

    def record_closed_trade(self) -> None:
        self.closed_count += 1

    def get_position_governor_factor(self) -> float:
        return 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_om_paper():
    """Create OrderManager in paper mode with all filesystem I/O patched out."""
    with patch("execution_engine.order_manager.OrderManager._restore_from_journal"):
        with patch("execution_engine.order_manager.OrderManager._prefetch_restored_ltps"):
            with patch("execution_engine.order_manager.OrderManager._restore_from_live_journal"):
                with patch("execution_engine.order_manager.OrderManager.reconcile_startup_fills",
                           return_value=0):
                    with patch("execution_engine.order_manager.OrderManager."
                               "_reconcile_sim_paper_artifacts"):
                        import config as cfg
                        orig = getattr(cfg, "PAPER_TRADING", True)
                        cfg.PAPER_TRADING = True
                        try:
                            from execution_engine.order_manager import OrderManager
                            return OrderManager()
                        finally:
                            cfg.PAPER_TRADING = orig


def _make_carry_record(oid: str, symbol: str = "RELIANCENS",
                       direction: str = "BUY",
                       entry_price: float = 2000.0,
                       actual_fill_price: float = 2000.0,
                       quantity: int = 10,
                       days_ago: int = 10,
                       strategy: str = "MomentumLong") -> Any:
    """Return an OrderRecord that looks like an aged carry position."""
    from execution_engine.order_manager import OrderRecord
    return OrderRecord(
        order_id=oid,
        symbol=symbol,
        direction=direction,
        quantity=quantity,
        entry_price=entry_price,
        stop_loss=entry_price * 0.97,
        target=entry_price * 1.05,
        strategy=strategy,
        status="open",
        placed_at=datetime.now() - timedelta(days=days_ago),
        actual_fill_price=actual_fill_price,
    )


def _run_expire(om, tmp_path, live_prices: Dict[str, float],
                td_elapsed: int = 5, carry_limit: int = 1):
    """
    Run check_and_expire_carries() with all filesystem side-effects isolated.
    Returns (n_expired, rg) where rg is whatever was injected (or None).
    """
    csv_path = str(tmp_path / "trades.csv")
    with patch("execution_engine.order_manager.PAPER_TRADE_LOG", csv_path), \
         patch("execution_engine.order_manager._trading_days_elapsed",
               return_value=td_elapsed), \
         patch("execution_engine.order_manager._carry_days_for",
               return_value=carry_limit), \
         patch.object(om, "_update_expiry_retry_sidecar"), \
         patch.object(om, "_review_carry_extension_dryrun"):
        n = om.check_and_expire_carries(live_prices=live_prices)
    return n


# ===========================================================================
# D12-001 — carry expiry must call record_trade_result
# ===========================================================================

class TestD12001CarryExpiryRecordsTrade:
    """
    Verify that check_and_expire_carries() reports P&L to RiskGuardian.
    Before the fix, every SESSION_EXPIRED close silently bypassed
    record_trade_result(); the 2% daily-loss kill-switch was blind to
    all overnight-carry losses.
    """

    def test_T001_carry_expiry_calls_record_trade_result_exactly_once(self, tmp_path):
        """D12-001: one aged carry position → record_trade_result called exactly once."""
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        rec = _make_carry_record("C001", entry_price=2000.0, actual_fill_price=2000.0,
                                 quantity=10)
        om._orders["C001"] = rec

        n = _run_expire(om, tmp_path, live_prices={"RELIANCENS": 2050.0})

        assert n == 1, "Expected 1 position expired"
        assert len(rg.trade_results) == 1, "record_trade_result must be called exactly once"

    def test_T002_profitable_carry_reports_won_true(self, tmp_path):
        """Profitable carry expiry → pnl > 0 and won=True."""
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        rec = _make_carry_record("C002", entry_price=2000.0, actual_fill_price=2000.0,
                                 quantity=10)
        om._orders["C002"] = rec

        _run_expire(om, tmp_path, live_prices={"RELIANCENS": 2060.0})

        assert len(rg.trade_results) == 1
        pnl, won = rg.trade_results[0]
        assert pnl == pytest.approx(600.0)   # (2060-2000)*10
        assert won is True

    def test_T003_losing_carry_reports_won_false(self, tmp_path):
        """Losing carry expiry → pnl < 0 and won=False."""
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        rec = _make_carry_record("C003", entry_price=2000.0, actual_fill_price=2000.0,
                                 quantity=10)
        om._orders["C003"] = rec

        _run_expire(om, tmp_path, live_prices={"RELIANCENS": 1950.0})

        assert len(rg.trade_results) == 1
        pnl, won = rg.trade_results[0]
        assert pnl == pytest.approx(-500.0)  # (1950-2000)*10
        assert won is False

    def test_T004_short_carry_pnl_sign_is_inverted(self, tmp_path):
        """SHORT direction: pnl = (entry - exit) * qty."""
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        rec = _make_carry_record("C004", direction="SELL",
                                 entry_price=2000.0, actual_fill_price=2000.0,
                                 quantity=10)
        om._orders["C004"] = rec

        _run_expire(om, tmp_path, live_prices={"RELIANCENS": 1980.0})

        assert len(rg.trade_results) == 1
        pnl, won = rg.trade_results[0]
        # SHORT: profit when price falls
        assert pnl == pytest.approx(200.0)  # (2000-1980)*10
        assert won is True

    def test_T005_record_closed_trade_also_called(self, tmp_path):
        """record_closed_trade() must also fire for carry expiry (StrategyPerf wiring)."""
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        rec = _make_carry_record("C005")
        om._orders["C005"] = rec

        _run_expire(om, tmp_path, live_prices={"RELIANCENS": 2010.0})

        assert rg.closed_count == 1, "record_closed_trade() must be called exactly once"

    def test_T006_no_rg_injected_does_not_crash(self, tmp_path):
        """Without an injected RiskGuardian the method must succeed silently."""
        om = _make_om_paper()
        # no inject_risk_guardian()

        rec = _make_carry_record("C006")
        om._orders["C006"] = rec

        n = _run_expire(om, tmp_path, live_prices={"RELIANCENS": 2010.0})

        assert n == 1, "Expiry should succeed even with no RiskGuardian wired"

    def test_T007_idempotency_second_call_same_oid_not_double_counted(self, tmp_path):
        """
        If the same order_id somehow reaches check_and_expire_carries twice
        (e.g. via _closed_ids_today dedup failure), record_trade_result must
        only be called once — the _rg_recorded_oids set prevents double-counting.
        """
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        rec = _make_carry_record("C007")
        om._orders["C007"] = rec

        # First expiry
        _run_expire(om, tmp_path, live_prices={"RELIANCENS": 2010.0})
        first_count = len(rg.trade_results)

        # Simulate second call: re-add the record (bypass the normal closed_ids_today guard)
        rec2 = _make_carry_record("C007")
        rec2.status = "open"
        om._orders["C007"] = rec2
        om._closed_ids_today.discard("C007")  # remove from dedup set to force retry path

        _run_expire(om, tmp_path, live_prices={"RELIANCENS": 2010.0})

        # _rg_recorded_oids guard must prevent a second record_trade_result call
        assert len(rg.trade_results) == first_count, \
            "_rg_recorded_oids must prevent double-counting carry P&L"

    def test_T008_multiple_positions_each_recorded_once(self, tmp_path):
        """Three aged positions in one batch → three record_trade_result calls."""
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        for i, sym in enumerate(["RELIANCENS", "TATASTEEL", "INFY"]):
            rec = _make_carry_record(f"C00{i+1}", symbol=sym,
                                     entry_price=1000.0 + i * 500,
                                     actual_fill_price=1000.0 + i * 500,
                                     quantity=5)
            om._orders[f"C00{i+1}"] = rec

        prices = {"RELIANCENS": 1050.0, "TATASTEEL": 1530.0, "INFY": 2010.0}
        n = _run_expire(om, tmp_path, live_prices=prices)

        assert n == 3
        assert len(rg.trade_results) == 3, "One record_trade_result per expired position"

    def test_T009_csv_row_written_before_rg_call(self, tmp_path):
        """
        The D12-001 fix adds the RG call INSIDE the try block, AFTER the CSV write
        succeeds.  Verify the CSV row exists when we check the RG was called.
        """
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        rec = _make_carry_record("C009")
        om._orders["C009"] = rec

        csv_path = str(tmp_path / "trades.csv")
        with patch("execution_engine.order_manager.PAPER_TRADE_LOG", csv_path), \
             patch("execution_engine.order_manager._trading_days_elapsed", return_value=5), \
             patch("execution_engine.order_manager._carry_days_for", return_value=1), \
             patch.object(om, "_update_expiry_retry_sidecar"), \
             patch.object(om, "_review_carry_extension_dryrun"):
            om.check_and_expire_carries(live_prices={"RELIANCENS": 2050.0})

        # CSV row must exist.  check_and_expire_carries() appends data rows only
        # (no header), so use csv.reader to count raw lines.
        assert os.path.exists(csv_path), "CSV journal must be written"
        with open(csv_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert len(rows) == 1, f"Expected 1 CSV row, got {len(rows)}"
        # EVENT and REASON are in _JOURNAL_HEADER — look them up by position
        from execution_engine.order_manager import _JOURNAL_HEADER
        event_idx  = _JOURNAL_HEADER.index("event")
        reason_idx = _JOURNAL_HEADER.index("reason")
        assert rows[0][event_idx]  == "CLOSE"
        assert rows[0][reason_idx] == "SESSION_EXPIRED"

        # RG also called
        assert len(rg.trade_results) == 1

    def test_T010_pnl_uses_actual_fill_price_when_set(self, tmp_path):
        """PnL is computed from actual_fill_price (not entry_price) when > 0."""
        om = _make_om_paper()
        rg = _FakeRiskGuardian()
        om.inject_risk_guardian(rg)

        # entry_price=2000 but actual_fill=2010 (slippage was 10)
        rec = _make_carry_record("C010", entry_price=2000.0, actual_fill_price=2010.0,
                                 quantity=10)
        om._orders["C010"] = rec

        _run_expire(om, tmp_path, live_prices={"RELIANCENS": 2060.0})

        pnl, won = rg.trade_results[0]
        # PnL should use actual_fill_price=2010, not entry_price=2000
        assert pnl == pytest.approx(500.0)   # (2060-2010)*10
        assert won is True


# ===========================================================================
# D12-002 — test isolation (RiskGuardian state file must not poison prod)
# ===========================================================================

class TestD12002TestIsolation:
    """
    Verify that tests creating FailSafeRiskGuardian use isolated state files.
    Before D12-002 fix, T092 in test_dta_system_011.py wrote trading_halted=true
    with halt_reason="VIX=50.0 ≥ 45.0" to data/risk_guardian_state.json.
    """

    def test_T011_rg_with_tmp_state_does_not_touch_prod_file(self, tmp_path):
        """FailSafeRiskGuardian with isolated state_file must not write to production path."""
        import execution_engine.order_manager as _om_mod
        prod_path = "data/risk_guardian_state.json"

        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        from models import MarketSnapshot
        from datetime import datetime as _dt2

        rg = FailSafeRiskGuardian(total_capital=50000,
                                   state_file=str(tmp_path / "rg_isolated.json"))

        snap = MagicMock(spec=["vix", "timestamp", "indices"])
        snap.vix = 50.0
        snap.timestamp = _dt2.now()
        snap.indices = {}

        # Before evaluate: record mtime of prod file (if it exists)
        prod_mtime_before = (os.path.getmtime(prod_path)
                             if os.path.exists(prod_path) else None)

        rg.evaluate([], snap)

        prod_mtime_after = (os.path.getmtime(prod_path)
                            if os.path.exists(prod_path) else None)

        assert prod_mtime_before == prod_mtime_after, \
            "Isolated RiskGuardian must not modify the production state file"

    def test_T012_isolated_rg_writes_only_to_tmp(self, tmp_path):
        """Isolated FailSafeRiskGuardian must write state to the tmp file, not elsewhere."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian

        isolated = str(tmp_path / "rg_test.json")
        rg = FailSafeRiskGuardian(total_capital=50000, state_file=isolated)
        rg._trading_halted = True
        rg._halt_reason    = "TEST_HALT"
        rg._save_state()

        assert os.path.exists(isolated), "State must be written to isolated path"

        import json
        state = json.loads(open(isolated).read())
        assert state["trading_halted"] is True
        assert state["halt_reason"] == "TEST_HALT"

    def test_T013_prod_state_readable_after_test_suite(self, tmp_path):
        """
        After running test T092 with the isolation fix applied, the production
        state file must be valid JSON with trading_halted=False.
        """
        prod_path = "data/risk_guardian_state.json"
        if not os.path.exists(prod_path):
            pytest.skip("Production state file not present — cannot verify.")

        import json
        state = json.loads(open(prod_path).read())
        # Verify the file is valid and not poisoned
        assert isinstance(state, dict)
        assert "trading_halted" in state
        # After D12-002 fix: production state must not be in a test-induced halt
        # (if it IS halted, the halt_reason should be a real market reason, not
        # "VIX=50.0 ≥ 45.0" which was injected by a test)
        if state.get("trading_halted"):
            assert state.get("halt_reason") != "VIX=50.0 \u2265 45.0", \
                "trading_halted=True with VIX=50 reason was injected by test T092 — D12-002 not fixed"

    def test_T014_t092_uses_tmp_path_state_file(self):
        """
        Regression: confirm test T092 in test_dta_system_011 now passes
        state_file=str(tmp_path / ...) to FailSafeRiskGuardian.
        """
        import ast, inspect
        import sys
        # Load source of test file
        test_path = os.path.join("tests", "test_dta_system_011.py")
        src = open(test_path, encoding="utf-8").read()
        # Find the T092 method
        idx = src.find("def test_T092_no_execution_from_blocked_signal")
        assert idx != -1, "T092 not found in test_dta_system_011.py"
        # Extract ~50 lines after the def line
        body = src[idx: idx + 2000]
        assert "state_file=" in body, \
            "T092 must pass state_file= to FailSafeRiskGuardian (D12-002 isolation fix)"
        assert "tmp_path" in body, \
            "T092 must use tmp_path for the isolated state file"

    def test_T015_no_failsafe_rg_without_state_file_in_tests(self):
        """
        All FailSafeRiskGuardian instantiations in the tests/ directory must
        either pass state_file= or be in a function that receives tmp_path.
        """
        import ast, re
        tests_dir = "tests"
        violations = []
        for fname in os.listdir(tests_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(tests_dir, fname)
            src = open(fpath, encoding="utf-8").read()
            # Search for bare instantiations lacking an isolated state_file
            for m in re.finditer(r"FailSafeRiskGuardian\([^)]*\)", src):
                call = m.group()
                # Skip comment lines — the comment text is not executable code
                pos = m.start()
                line_start = src.rfind("\n", 0, pos) + 1
                line_text = src[line_start:src.find("\n", pos)]
                if line_text.lstrip().startswith("#"):
                    continue
                if "state_file" not in call:
                    # Find enclosing function to check for tmp_path parameter
                    pos = m.start()
                    preceding = src[:pos]
                    # Walk back to find def line
                    func_start = preceding.rfind("\n    def ")
                    func_sig = src[func_start: func_start + 200] if func_start != -1 else ""
                    if "tmp_path" not in func_sig:
                        line_no = src[:pos].count("\n") + 1
                        violations.append(f"{fname}:{line_no}: {call}")

        assert not violations, (
            "FailSafeRiskGuardian without state_file= (and without tmp_path) found:\n"
            + "\n".join(violations)
        )
