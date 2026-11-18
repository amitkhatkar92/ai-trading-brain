"""live_observations.db was empty because its ingest only read paper_trades.csv while the
account trades live and journals real orders to data/live/live_orders.jsonl."""
from __future__ import annotations

import json
import sqlite3

import pytest

from analysis import live_observation_collector as collector
from analysis.live_observation_tracker import LiveObservationTracker


def _write(path, events):
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")


def _open(order_id, symbol="SBIN", fill="FILLED", ts="2026-11-18T07:34:49+00:00", **extra):
    return {"event": "OPEN", "timestamp": ts, "order_id": order_id, "symbol": symbol, "direction": "BUY",
            "entry_price": 1113.4, "stop_loss": 1081.04, "target_price": 1180.24, "strategy": "KDA_AUTHORITY",
            "fill_status": fill, "actual_fill_price": 1113.1, "initial_stop_loss": 1081.04,
            "confidence_score": 7.46, "signal_regime": "range_market", **extra}


def _close(order_id, exit_price=1100.0, pnl=-52.4, reason="EARLY_LOSS", ts="2026-11-18T09:00:00+00:00"):
    return {"event": "CLOSE", "timestamp": ts, "order_id": order_id, "exit_price": exit_price,
            "pnl": pnl, "reason": reason}


@pytest.fixture
def tracker(tmp_path):
    return LiveObservationTracker(db_path=str(tmp_path / "live.db"))


def _rows(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM live_observations ORDER BY order_id")]


def test_only_filled_orders_become_trades_with_real_entry_data(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write(journal, [_open("A"), _open("B", fill="PENDING"), _open("C", fill="API_ERROR"),
                     {"event": "CANCELLED", "order_id": "B", "timestamp": "2026-11-18T08:00:00+00:00"}])
    rows = collector.live_journal_rows(str(journal))
    assert [r["order_id"] for r in rows] == ["A"]
    row = rows[0]
    assert row["entry_price"] == 1113.1 and row["stop_loss"] == 1081.04 and row["confidence"] == 7.46
    assert row["rr"] == pytest.approx((1180.24 - 1113.1) / (1113.1 - 1081.04), abs=0.001)
    assert row["exit_price"] is None


def test_trade_date_is_the_ist_date(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write(journal, [_open("A", ts="2026-11-17T20:00:00+00:00")])           # 01:30 IST the next day
    assert collector.live_journal_rows(str(journal))[0]["trade_date"] == "2026-11-18"


def test_ingest_stores_live_rows_idempotently_with_the_signal_regime(tmp_path, tracker):
    journal = tmp_path / "j.jsonl"
    _write(journal, [_open("A"), _open("B", symbol="COALINDIA")])
    first = collector.ingest_from_live_journal(str(journal), tracker)
    again = collector.ingest_from_live_journal(str(journal), tracker)
    assert first["new"] == 2 and first["errors"] == 0 and again["new"] == 0 and again["skipped"] == 2
    stored = _rows(tracker)
    assert {r["data_source"] for r in stored} == {"LIVE"}
    assert {r["market_regime"] for r in stored} == {"range_market"}
    assert {(r["vix"], r["vix_bucket"]) for r in stored} == {(0.0, "UNKNOWN")}     # not a made-up 15.0/MEDIUM


def test_outcome_is_recorded_when_the_order_closes_and_not_rewritten(tmp_path, tracker):
    journal = tmp_path / "j.jsonl"
    _write(journal, [_open("A")])
    collector.ingest_from_live_journal(str(journal), tracker)
    assert _rows(tracker)[0]["outcome"] in (None, "", "OPEN")
    _write(journal, [_open("A"), _close("A")])
    collector.ingest_from_live_journal(str(journal), tracker)
    row = _rows(tracker)[0]
    assert row["outcome"] == "LOSS" and row["exit_price"] == 1100.0 and row["close_reason"] == "EARLY_LOSS"
    closed_at = row["closed_at"]
    collector.ingest_from_live_journal(str(journal), tracker)
    assert _rows(tracker)[0]["closed_at"] == closed_at


def test_missing_or_corrupt_journal_is_harmless(tmp_path, tracker):
    assert collector.ingest_from_live_journal(str(tmp_path / "none.jsonl"), tracker)["processed"] == 0
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not json\n" + json.dumps(_open("A")), encoding="utf-8")
    assert collector.ingest_from_live_journal(str(bad), tracker)["new"] == 1


def test_repair_duplicates_are_not_trades(tmp_path, tracker):
    journal = tmp_path / "j.jsonl"
    _write(journal, [_open("A"), _open("REPAIR-A-1234")])
    assert [r["order_id"] for r in collector.live_journal_rows(str(journal))] == ["A"]


def test_filled_then_system_cancelled_is_cancelled_not_open_and_has_no_made_up_exit(tmp_path, tracker):
    journal = tmp_path / "j.jsonl"
    cancel = {"event": "CANCELLED", "order_id": "A", "timestamp": "2026-11-18T09:00:00+00:00",
              "fill_status": "BROKER_NO_POSITION_FOUND"}
    _write(journal, [_open("A"), cancel, _open("B")])
    collector.ingest_from_live_journal(str(journal), tracker)
    by_id = {r["order_id"]: r for r in _rows(tracker)}
    assert by_id["A"]["outcome"] == "CANCELLED" and by_id["A"]["close_reason"] == "BROKER_NO_POSITION_FOUND"
    assert by_id["A"]["exit_price"] is None and by_id["A"]["r_multiple"] is None
    assert by_id["B"]["outcome"] == "OPEN"
    assert tracker.summary()["open"] == 1
    collector.ingest_from_live_journal(str(journal), tracker)
    assert {r["order_id"]: r["outcome"] for r in _rows(tracker)} == {"A": "CANCELLED", "B": "OPEN"}


def test_a_close_after_a_cancel_wins_and_a_refill_supersedes_the_cancel(tmp_path, tracker):
    journal = tmp_path / "j.jsonl"
    cancel = {"event": "CANCELLED", "order_id": "A", "timestamp": "2026-11-18T08:00:00+00:00",
              "fill_status": "FILLED"}
    _write(journal, [_open("A"), cancel, _close("A"), _open("B"), dict(cancel, order_id="B"), _open("B")])
    collector.ingest_from_live_journal(str(journal), tracker)
    by_id = {r["order_id"]: r["outcome"] for r in _rows(tracker)}
    assert by_id == {"A": "LOSS", "B": "OPEN"}


def test_close_recorded_only_in_the_paper_csv_is_used(tmp_path, tracker):
    journal = tmp_path / "j.jsonl"
    _write(journal, [_open("A")])
    paper = tmp_path / "paper.csv"
    paper.write_text(
        "2026-11-19 09:20:39,A,SBIN,BUY,8,1113.4,1081.04,1180.24,KDA_AUTHORITY,,,CLOSE,1100.0,-105.6,SESSION_EXPIRED\n"
        "2026-11-19 11:20:27,A,SBIN,BUY,8,1113.4,1081.04,1180.24,KDA_AUTHORITY,,,CLOSE,1120.0,54.4,SESSION_EXPIRED\n",
        encoding="utf-8")
    collector.ingest_from_live_journal(str(journal), tracker, csv_path=str(paper))
    row = _rows(tracker)[0]
    assert row["outcome"] == "LOSS" and row["exit_price"] == 1100.0 and row["close_reason"] == "SESSION_EXPIRED"


def test_eod_calls_the_live_journal_ingest_next_to_the_paper_one():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "orchestrator" / "master_orchestrator.py"
              ).read_text(encoding="utf-8")
    assert 0 < source.index("_ingest_live_journal()") - source.index("_ingest_live_obs()") < 1500
