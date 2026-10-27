"""
tests/test_dta_eod_live_journal_recovery_001.py
===================================================
DTA-EOD-LIVE-JOURNAL-RECOVERY-001

Verifies learning_system/live_journal_trade_recovery.py correctly
recovers missed real CLOSE events from data/live/live_orders.jsonl,
restart-safe via a persisted processed-order-id set, mirroring the
same classification rules as the existing (paper-only) CSV recovery
block in master_orchestrator.py.
"""
from __future__ import annotations

import json

import pytest

import learning_system.live_journal_trade_recovery as ljtr


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    journal = tmp_path / "live_orders.jsonl"
    state = tmp_path / "live_journal_recovery_state.json"
    monkeypatch.setattr(ljtr, "_LIVE_JOURNAL_PATH", str(journal))
    monkeypatch.setattr(ljtr, "_STATE_PATH", str(state))
    yield journal, state


def _write_journal(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def _close_row(order_id, symbol="RELIANCE", pnl=100.0, reason="close_target",
                entry_price=100.0, stop_loss=98.0, quantity=10, direction="BUY",
                target_price=106.0):
    return {
        "event": "CLOSE", "timestamp": "2026-10-20T10:00:00",
        "order_id": order_id, "symbol": symbol, "direction": direction,
        "quantity": quantity, "entry_price": entry_price, "stop_loss": stop_loss,
        "target_price": target_price, "strategy": "Mean_Reversion",
        "exit_price": entry_price + 1, "pnl": pnl, "reason": reason,
    }


class TestRecovery:
    def test_t01_recovers_new_close_event(self, _isolate):
        journal, _ = _isolate
        _write_journal(journal, [_close_row("OID1", pnl=150.0)])
        recovered = ljtr.recover_missed_closed_trades(set())
        assert len(recovered) == 1
        assert recovered[0].order_id == "OID1"
        assert recovered[0].pnl == 150.0

    def test_t02_skips_already_seen_in_memory(self, _isolate):
        journal, _ = _isolate
        _write_journal(journal, [_close_row("OID1")])
        recovered = ljtr.recover_missed_closed_trades({"OID1"})
        assert recovered == []

    def test_t03_persisted_dedup_across_runs(self, _isolate):
        journal, state = _isolate
        _write_journal(journal, [_close_row("OID1")])
        first = ljtr.recover_missed_closed_trades(set())
        assert len(first) == 1
        # Second run (simulating a later EOD cycle / restart) must not re-recover it
        second = ljtr.recover_missed_closed_trades(set())
        assert second == []
        assert state.exists()

    def test_t04_skips_skip_reasons(self, _isolate):
        journal, _ = _isolate
        _write_journal(journal, [_close_row("OID1", reason="REPLACEMENT")])
        assert ljtr.recover_missed_closed_trades(set()) == []

    def test_t05_skips_session_expired_zero_pnl(self, _isolate):
        journal, _ = _isolate
        _write_journal(journal, [_close_row("OID1", reason="SESSION_EXPIRED", pnl=0.0)])
        assert ljtr.recover_missed_closed_trades(set()) == []

    def test_t06_includes_session_expired_real_pnl(self, _isolate):
        journal, _ = _isolate
        _write_journal(journal, [_close_row("OID1", reason="SESSION_EXPIRED", pnl=42.0)])
        recovered = ljtr.recover_missed_closed_trades(set())
        assert len(recovered) == 1
        assert recovered[0].pnl == 42.0

    def test_t07_skips_malformed_pnl(self, _isolate):
        journal, _ = _isolate
        row = _close_row("OID1")
        row["pnl"] = None
        _write_journal(journal, [row])
        assert ljtr.recover_missed_closed_trades(set()) == []

    def test_t08_ignores_non_close_events(self, _isolate):
        journal, _ = _isolate
        row = _close_row("OID1")
        row["event"] = "OPEN"
        _write_journal(journal, [row])
        assert ljtr.recover_missed_closed_trades(set()) == []

    def test_t09_fails_open_missing_journal(self, _isolate):
        # journal file was never created
        assert ljtr.recover_missed_closed_trades(set()) == []

    def test_t10_fails_open_corrupt_journal(self, _isolate):
        journal, _ = _isolate
        journal.write_text("not valid json\n{also not valid", encoding="utf-8")
        assert ljtr.recover_missed_closed_trades(set()) == []

    def test_t11_computes_r_multiple(self, _isolate):
        journal, _ = _isolate
        _write_journal(journal, [_close_row(
            "OID1", pnl=40.0, entry_price=100.0, stop_loss=98.0, quantity=20,
        )])
        recovered = ljtr.recover_missed_closed_trades(set())
        assert len(recovered) == 1
        # r_risk = |100-98| = 2, r_risk*qty = 40, r_mult = 40/40 = 1.0
        assert recovered[0].r_multiple == pytest.approx(1.0)

    def test_t12_multiple_rows_mixed_eligibility(self, _isolate):
        journal, _ = _isolate
        _write_journal(journal, [
            _close_row("OID1", pnl=10.0),
            _close_row("OID2", reason="ORPHAN_CLOSE"),
            _close_row("OID3", pnl=-5.0),
        ])
        recovered = ljtr.recover_missed_closed_trades(set())
        oids = {r.order_id for r in recovered}
        assert oids == {"OID1", "OID3"}
