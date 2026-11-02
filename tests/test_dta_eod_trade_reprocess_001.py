"""
tests/test_dta_eod_trade_reprocess_001.py
=============================================
DTA-EOD-TRADE-REPROCESS-001

Root cause: TradeMonitor._closed_orders is never pruned after a trade is
processed by the daily EOD learning loop, so get_closed_trades() keeps
returning every trade ever closed since the process last restarted --
every EOD cycle silently re-feeds the SAME already-processed real trade
into learning_engine.learn()/regime_map_evidence_log/sizing_bounds_
refinement_engine (neither of which dedup on their own), inflating
evidence counts. Confirmed live: CASTROLIND order_id 221261028295303
was written into regime_map_evidence_log on 3 separate consecutive days.

Verifies learning_system/eod_trade_dedup.py: filter_unprocessed() /
mark_processed() correctly prevent a trade from being fed into learning
more than once, restart-safe via a persisted order_id set.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import learning_system.eod_trade_dedup as dedup


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    state = tmp_path / "eod_trade_dedup_state.json"
    monkeypatch.setattr(dedup, "_STATE_PATH", str(state))
    yield state


def _trade(order_id):
    return SimpleNamespace(order_id=order_id, strategy="Mean_Reversion", pnl=100.0)


class TestEodTradeDedup:
    def test_t01_first_pass_all_trades_unprocessed(self, _isolate):
        trades = [_trade("A"), _trade("B")]
        out = dedup.filter_unprocessed(trades)
        assert [t.order_id for t in out] == ["A", "B"]

    def test_t02_mark_processed_then_filtered_out_next_run(self, _isolate):
        trades = [_trade("A"), _trade("B")]
        dedup.mark_processed(trades)
        # Simulates the EXACT live bug scenario: same trade, same object
        # shape, reappearing in get_closed_trades() on a LATER EOD run.
        out = dedup.filter_unprocessed([_trade("A"), _trade("B"), _trade("C")])
        assert [t.order_id for t in out] == ["C"]

    def test_t03_persists_across_module_reload(self, _isolate):
        dedup.mark_processed([_trade("A")])
        # Re-import style: load state fresh from disk, not relying on any
        # in-memory cache, to prove this is genuinely restart-safe.
        processed = dedup._load_processed_ids()
        assert "A" in processed

    def test_t04_empty_order_id_never_tracked(self, _isolate):
        dedup.mark_processed([_trade(""), _trade(None)])
        processed = dedup._load_processed_ids()
        assert processed == set()

    def test_t05_filter_fails_open_on_corrupt_state_file(self, _isolate, tmp_path):
        state_path = str(tmp_path / "eod_trade_dedup_state.json")
        import os
        with open(state_path, "w") as f:
            f.write("{not valid json")
        import unittest.mock as mock
        with mock.patch.object(dedup, "_STATE_PATH", state_path):
            out = dedup.filter_unprocessed([_trade("A")])
        assert [t.order_id for t in out] == ["A"]  # fails open, never blocks real learning

    def test_t06_mark_processed_never_raises_on_bad_input(self, _isolate):
        # Objects without order_id attribute at all
        dedup.mark_processed([object(), object()])  # must not raise

    def test_t07_filter_unprocessed_never_raises_on_bad_state(self, _isolate, monkeypatch):
        monkeypatch.setattr(dedup, "_load_processed_ids", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        out = dedup.filter_unprocessed([_trade("A")])
        assert [t.order_id for t in out] == ["A"]

    def test_t08_mixed_already_processed_and_new(self, _isolate):
        dedup.mark_processed([_trade("X")])
        out = dedup.filter_unprocessed([_trade("X"), _trade("Y"), _trade("Z")])
        assert sorted(t.order_id for t in out) == ["Y", "Z"]

    def test_t09_state_file_written_with_expected_shape(self, _isolate):
        dedup.mark_processed([_trade("A"), _trade("B")])
        with open(_isolate) as f:
            data = json.load(f)
        assert sorted(data["processed_order_ids"]) == ["A", "B"]
