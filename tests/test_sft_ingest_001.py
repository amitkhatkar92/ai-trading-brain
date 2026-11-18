"""Symbol follow-through store was empty: ingest_closed_trade() had no caller, nothing tracked
best/worst excursion while a position was held, and the readers queried tables that never existed."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from learning_system import sft_ingest
from phase_d_sft_recommendation import SFTTracker
from trade_monitoring.trade_monitor import TradeMonitor


def _trade(direction="BUY", entry=100.0, stop=98.0, high=103.0, low=99.0, pnl=50.0, **kw):
    base = dict(symbol="SBIN", direction=direction, actual_fill_price=entry, entry_price=entry,
                initial_stop_loss=stop, stop_loss=stop, mfe_price=high, mae_price=low, pnl=pnl)
    base.update(kw)
    return SimpleNamespace(**base)


def test_buy_excursions_are_measured_in_r():
    got = sft_ingest.excursion_inputs(_trade())
    assert got["mfe_r"] == 1.5 and got["mae_r"] == 0.5          # risk = 2; +3 up, -1 down
    assert (got["reached_025r"], got["reached_050r"], got["reached_100r"]) == (True, True, True)


def test_short_excursions_use_the_opposite_extremes():
    got = sft_ingest.excursion_inputs(_trade("SELL", entry=100, stop=102, high=101, low=99.4))
    assert got["mfe_r"] == pytest.approx(0.3) and got["mae_r"] == 0.5
    assert (got["reached_025r"], got["reached_050r"]) == (True, False)


def test_untracked_or_unmeasurable_trades_are_skipped_not_counted_as_failures():
    assert sft_ingest.excursion_inputs(_trade(high=0.0, low=0.0)) is None      # restored after a restart
    assert sft_ingest.excursion_inputs(_trade(stop=100.0)) is None             # zero risk
    assert sft_ingest.excursion_inputs(_trade(direction="")) is None
    assert sft_ingest.record_trade_excursion(_trade(high=0.0, low=0.0), tracker=object()) is False


def test_ingest_builds_a_scored_symbol_record(tmp_path):
    tracker = SFTTracker(db_path=str(tmp_path / "sft.db"))
    for pnl in (40.0, 30.0, -10.0):
        assert sft_ingest.record_trade_excursion(_trade(pnl=pnl), tracker=tracker) is True
    metrics = tracker.get_metrics("SBIN")
    assert metrics.trade_count == 3 and metrics.win_count == 2 and metrics.sft_class != "INSUFFICIENT_DATA"
    assert metrics.pct_reach_050r == 100.0


def test_ingest_never_raises_when_the_tracker_fails():
    class Broken:
        def ingest_closed_trade(self, **_):
            raise RuntimeError("db locked")
    assert sft_ingest.record_trade_excursion(_trade(), tracker=Broken()) is False


def test_monitor_tracks_the_high_and_low_since_entry_but_not_before_the_fill():
    order = SimpleNamespace(fill_status="FILLED", mfe_price=0.0, mae_price=0.0)
    for price in (100.0, 103.0, 99.0, 101.0):
        TradeMonitor._track_excursion(order, price)
    assert (order.mfe_price, order.mae_price) == (103.0, 99.0)
    pending = SimpleNamespace(fill_status="PENDING", mfe_price=0.0, mae_price=0.0)
    TradeMonitor._track_excursion(pending, 100.0)
    assert (pending.mfe_price, pending.mae_price) == (0.0, 0.0)


def test_readers_query_the_real_table(tmp_path, monkeypatch):
    from analysis import live_observation_collector as collector
    from analysis import daily_observation_report as report
    db = str(tmp_path / "sft.db")
    tracker = SFTTracker(db_path=db)
    for _ in range(3):
        sft_ingest.record_trade_excursion(_trade(), tracker=tracker)
    monkeypatch.setattr(collector, "SFT_DB", db)
    sft_class, score = collector._sft_for_symbol("SBIN")
    assert sft_class != "UNKNOWN" and score > 0
    text = "\n".join(report._section_sft_leaderboard(db))
    assert "SBIN" in text and "schema mismatch" not in text


def test_eod_loop_feeds_the_tracker():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")
    assert "record_trade_excursion(trade)" in source
