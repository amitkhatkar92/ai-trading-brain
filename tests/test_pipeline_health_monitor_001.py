"""Pipeline health check: detects silent breaks, repairs only missing price bars, alerts on change."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analysis import pipeline_health_monitor as health
from data_integrity import session_close_reference as reference

IST = health.IST


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=IST)


# 2026-11-16 Mon, 11-17 Tue, 11-13 Fri, 11-14 Sat are the dates used below.
EVENING = _at("2026-11-17 17:00")      # after the session is final
MORNING = _at("2026-11-17 08:10")      # before the session is final
MONDAY = _at("2026-11-16 08:10")


@pytest.fixture(autouse=True)
def _clean_reference_cache():
    reference._cache.clear()
    yield
    reference._cache.clear()


def _market(tmp_path, active=10, with_bar=10, session="2026-11-17", closes=None):
    db = tmp_path / "market_behavior.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE universe_stocks (symbol TEXT, is_active INTEGER)")
    conn.execute("CREATE TABLE ohlcv_daily (symbol TEXT, trade_date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume REAL)")
    for i in range(active):
        symbol = f"S{i:02d}.NS"
        conn.execute("INSERT INTO universe_stocks VALUES (?, 1)", (symbol,))
        if i < with_bar:
            conn.execute("INSERT INTO ohlcv_daily VALUES (?,?,100,101,99,100,1)", (symbol, session))
    for symbol, close in (closes or {}).items():
        for index in range(20):
            day = (datetime(2026, 11, 16) - timedelta(days=index)).date().isoformat()
            conn.execute("INSERT INTO ohlcv_daily VALUES (?,?,?,?,?,?,1)",
                         (f"{symbol}.NS", day, close, close * 1.01, close * 0.99, close))
    conn.commit()
    conn.close()
    return db


def _ctx(tmp_path, now=EVENING):
    return health.HealthContext(now=now, data_dir=str(tmp_path))


def test_expected_session_follows_the_trading_calendar():
    assert health.expected_session(EVENING).isoformat() == "2026-11-17"
    assert health.expected_session(MORNING).isoformat() == "2026-11-16"
    assert health.expected_session(MONDAY).isoformat() == "2026-11-13"       # skips the weekend
    assert health.expected_session(_at("2026-11-17 15:59")).isoformat() == "2026-11-16"
    assert health.expected_session(_at("2026-11-14 18:00")).isoformat() == "2026-11-13"


@pytest.mark.parametrize("with_bar,status", [(10, "OK"), (9, "WARN"), (8, "FAIL"), (5, "FAIL")])
def test_price_freshness_thresholds(tmp_path, with_bar, status):
    _market(tmp_path, active=10, with_bar=with_bar)
    result, missing = health.check_price_freshness(_ctx(tmp_path))
    assert result["status"] == status
    assert len(missing) == 10 - with_bar


def test_price_freshness_reports_a_missing_database_without_raising(tmp_path):
    result, missing = health.check_price_freshness(_ctx(tmp_path))
    assert result["status"] == "ERROR" and missing == []


def test_missing_bars_are_repaired_then_remeasured(tmp_path):
    db = _market(tmp_path, active=10, with_bar=5)
    calls = []

    def repair(symbols, today):
        calls.append((list(symbols), today))
        conn = sqlite3.connect(db)
        for symbol in symbols:
            conn.execute("INSERT INTO ohlcv_daily VALUES (?,?,100,101,99,100,1)", (symbol, "2026-11-17"))
        conn.commit()
        conn.close()
        return len(symbols)

    summary = health.run_pipeline_health_check(ctx=_ctx(tmp_path), repair_fn=repair, notifier=MagicMock())
    assert calls == [([f"S{i:02d}.NS" for i in range(5, 10)], "2026-11-17")]
    freshness = next(r for r in summary["results"] if r["name"] == "price_freshness")
    assert freshness["status"] == "OK" and "repair attempted for 5" in freshness["detail"]
    assert summary["repaired_rows"] == 5


def test_no_repair_when_coverage_is_fine_or_repair_is_disabled(tmp_path):
    _market(tmp_path, active=10, with_bar=10)
    repair = MagicMock()
    health.run_pipeline_health_check(ctx=_ctx(tmp_path), repair_fn=repair, notifier=MagicMock())
    repair.assert_not_called()
    other = tmp_path / "other"
    other.mkdir()
    _market(other, active=10, with_bar=2)
    health.run_pipeline_health_check(repair=False, ctx=_ctx(other), repair_fn=repair, notifier=MagicMock())
    repair.assert_not_called()


def test_repair_is_bounded_and_its_failure_is_reported_not_raised(tmp_path):
    _market(tmp_path, active=700, with_bar=0)
    seen = []

    def repair(symbols, today):
        seen.append(len(symbols))
        raise RuntimeError("network down")

    summary = health.run_pipeline_health_check(ctx=_ctx(tmp_path), repair_fn=repair, notifier=MagicMock())
    assert seen == [health.MAX_REPAIR_SYMBOLS]
    freshness = next(r for r in summary["results"] if r["name"] == "price_freshness")
    assert freshness["status"] == "FAIL" and "repair failed" in freshness["detail"]


def _store(tmp_path, snapshots, resolved=()):
    base = tmp_path / "universe_selection_learning"
    (base / "snapshots").mkdir(parents=True)
    (base / "resolved").mkdir()
    for day in snapshots:
        (base / "snapshots" / f"{day}.json").write_text("{}")
    for day in resolved:
        (base / "resolved" / f"{day}.json").write_text("{}")


def test_universe_learning_states(tmp_path):
    assert health.check_universe_learning(_ctx(tmp_path))["status"] == "INFO"
    _store(tmp_path, ["2026-11-16", "2026-11-17"], resolved=["2026-11-16"])
    assert health.check_universe_learning(_ctx(tmp_path))["status"] == "OK"


def test_universe_learning_flags_a_missing_snapshot_and_a_stuck_cohort(tmp_path):
    _store(tmp_path, ["2026-11-10"])
    result = health.check_universe_learning(_ctx(tmp_path))
    assert result["status"] == "WARN" and "no snapshot for 2026-11-17" in result["detail"]
    other = tmp_path / "stuck"
    other.mkdir()
    _store(other, ["2026-11-03", "2026-11-17"])
    stuck = health.check_universe_learning(_ctx(other))
    assert stuck["status"] == "FAIL" and stuck["metrics"]["oldest_pending_sessions"] >= 6


def _events(tmp_path, events):
    db = tmp_path / "control_tower.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ct_events (id INTEGER PRIMARY KEY, ts TEXT, cycle_id TEXT, "
                 "event_type TEXT, source_agent TEXT, payload TEXT)")
    for reason, symbol in events:
        conn.execute("INSERT INTO ct_events (ts, event_type, payload) VALUES (?,?,?)",
                     ("2026-11-17T10:00:00", "execution.order.not_placed",
                      json.dumps({"reason": reason, "symbol": symbol})))
    conn.commit()
    conn.close()


def test_a_gate_repeatedly_blocking_one_symbol_is_flagged(tmp_path):
    _events(tmp_path, [("PRICE_INTEGRITY_SANITY_FAILURE", "RELIANCE")] * 3
            + [("DUPLICATE_EXPOSURE_NO_SWAP_AVAILABLE", "SBIN")] * 10)
    result = health.check_order_gates(_ctx(tmp_path))
    assert result["status"] == "WARN" and "RELIANCE" in result["detail"]
    assert "SBIN" not in result["detail"]          # legitimate duplicate blocks are not a fault


def test_isolated_or_unrelated_blocks_are_not_flagged(tmp_path):
    _events(tmp_path, [("PRICE_INTEGRITY_SANITY_FAILURE", "A"), ("PRICE_INTEGRITY_SANITY_FAILURE", "B"),
                       ("EARLY_LOSS_COOLDOWN", "C")] * 1)
    assert health.check_order_gates(_ctx(tmp_path))["status"] == "OK"
    assert health.check_order_gates(_ctx(tmp_path / "none"))["status"] == "INFO"


def _journal(tmp_path, exit_price, symbol="SBIN", day="2026-11-17"):
    live = tmp_path / "live"
    live.mkdir(exist_ok=True)
    (live / "live_orders.jsonl").write_text(json.dumps(
        {"event": "CLOSE", "symbol": symbol, "exit_price": exit_price,
         "timestamp": f"{day}T05:00:00+00:00"}) + "\n")


def test_an_exit_at_a_price_the_market_never_traded_is_a_failure(tmp_path):
    _market(tmp_path, closes={"SBIN": 960.0})
    _journal(tmp_path, 819.05)
    result = health.check_exit_prices(_ctx(tmp_path))
    assert result["status"] == "FAIL" and "SBIN @ 819.05" in result["detail"]


def test_normal_unknown_and_option_exits_pass(tmp_path):
    _market(tmp_path, closes={"SBIN": 960.0})
    _journal(tmp_path, 955.0)
    assert health.check_exit_prices(_ctx(tmp_path))["status"] == "OK"
    _journal(tmp_path, 40.0, symbol="NIFTY")       # no market history: cannot judge, fails open
    assert health.check_exit_prices(_ctx(tmp_path))["status"] == "OK"
    assert health.check_exit_prices(_ctx(tmp_path / "none"))["status"] == "INFO"


def _eod(tmp_path, day, status="COMPLETED"):
    (tmp_path / "eod_status.json").write_text(json.dumps({"last_eod_date": day, "status": status}))


def _fresh_files(tmp_path):
    for _, relative, _ in health._FRESHNESS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")


def test_stores_pass_when_eod_completed_and_files_are_current(tmp_path):
    _eod(tmp_path, "2026-11-17")
    _fresh_files(tmp_path)
    ctx = _ctx(tmp_path)
    with patch("os.path.getmtime", return_value=EVENING.timestamp()):
        assert health.check_stores(ctx)["status"] == "OK"


def test_incomplete_eod_is_a_failure_and_stale_files_are_a_warning(tmp_path):
    _eod(tmp_path, "2026-11-16", status="STARTED")
    _fresh_files(tmp_path)
    with patch("os.path.getmtime", return_value=EVENING.timestamp()):
        result = health.check_stores(_ctx(tmp_path))
    assert result["status"] == "FAIL" and "EOD not completed for 2026-11-17" in result["detail"]
    _eod(tmp_path, "2026-11-17")
    with patch("os.path.getmtime", return_value=(EVENING - timedelta(days=9)).timestamp()):
        stale = health.check_stores(_ctx(tmp_path))
    assert stale["status"] == "WARN" and "not updated for 9d" in stale["detail"]


def test_price_bands_listing_is_informational(tmp_path):
    from data_integrity import instrument_registry
    _market(tmp_path, closes={"RELIANCE": 1345.0, "SBIN": 960.0})
    with patch.dict(instrument_registry._BANDS, {"RELIANCE": (2000.0, 3500.0), "SBIN": (500.0, 1100.0)}, clear=True):
        result = health.check_price_bands(_ctx(tmp_path))
    assert result["status"] == "INFO" and "RELIANCE" in result["detail"] and "SBIN" not in result["detail"]


def test_one_failing_check_does_not_stop_the_others(tmp_path):
    _market(tmp_path)
    with patch.object(health, "check_order_gates", side_effect=RuntimeError("boom")):
        summary = health.run_pipeline_health_check(ctx=_ctx(tmp_path), notifier=MagicMock())
    by_name = {r["name"]: r for r in summary["results"]}
    assert by_name["order_gates"]["status"] == "ERROR"
    assert len(summary["results"]) == 7
    assert "order_gates" in summary["issues"]


def test_alert_fires_on_new_issues_not_on_repeats_and_announces_recovery(tmp_path):
    _market(tmp_path, with_bar=5)
    notifier = MagicMock()
    run = lambda: health.run_pipeline_health_check(repair=False, ctx=_ctx(tmp_path), notifier=notifier)
    run()
    assert notifier.send_alert.call_count == 1
    assert "price_freshness" in notifier.send_alert.call_args.args[0]
    run()                                                    # same issues: silent
    assert notifier.send_alert.call_count == 1
    conn = sqlite3.connect(tmp_path / "market_behavior.db")
    for i in range(5, 10):
        conn.execute("INSERT INTO ohlcv_daily VALUES (?,?,100,101,99,100,1)", (f"S{i:02d}.NS", "2026-11-17"))
    conn.commit()
    conn.close()
    run()
    assert "Recovered" in notifier.send_alert.call_args.args[0]


def test_history_is_appended_and_readable(tmp_path):
    _market(tmp_path)
    health.run_pipeline_health_check(ctx=_ctx(tmp_path), notifier=MagicMock())
    health.run_pipeline_health_check(ctx=_ctx(tmp_path), notifier=MagicMock())
    lines = (tmp_path / "pipeline_health" / "history.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert health.get_latest_health(str(tmp_path))["checked_at"] == json.loads(lines[-1])["checked_at"]
    assert health.get_latest_health(str(tmp_path / "none")) == {}


def test_alert_delivery_failure_never_breaks_the_check(tmp_path):
    _market(tmp_path, with_bar=2)
    notifier = MagicMock()
    notifier.send_alert.side_effect = RuntimeError("telegram down")
    summary = health.run_pipeline_health_check(repair=False, ctx=_ctx(tmp_path), notifier=notifier)
    assert "price_freshness" in summary["issues"]


def test_an_empty_data_directory_returns_a_result_without_raising(tmp_path):
    summary = health.run_pipeline_health_check(ctx=_ctx(tmp_path), notifier=MagicMock())
    assert summary["overall"] in ("ERROR", "FAIL")
    assert {"price_freshness", "learning_stores"} <= set(summary["issues"])


def test_scan_hook_runs_after_the_v3_shadow_inside_the_post_market_scan():
    source = (Path(__file__).resolve().parents[1] / "orchestrator" / "master_orchestrator.py"
              ).read_text(encoding="utf-8")
    start = source.index("    def _run_post_market_scan(self)")
    end = source.index("    def _run_premarket_refiner(self)")
    body = source[start:end]
    assert body.index("[V3Shadow] Phase D shadow failed") < body.index("run_pipeline_health_check")
