from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from scripts.knowledge_system import universe_selection_learning as learning


def _row(i):
    return {
        "symbol": f"S{i:03d}.NS", "atr_pct": 1 + i / 100, "mom_5d": i / 10,
        "mom_accel": i / 20, "vol_ratio": 1 + i / 100, "rs_pct_5d": i / 10,
        "rsi_14": 20 + i / 10, "hv_20": i / 50, "vol_expansion": i / 100,
        "v3_up_score": i / 500, "v3_down_score": 1 - i / 500, "exclusion": None,
    }


def _database(path, n=500):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv_daily(symbol TEXT, trade_date TEXT, open REAL, close REAL)")
    for i in range(n):
        symbol = f"S{i:03d}.NS"
        for day, close in (("2026-11-11", 100), ("2026-11-12", 100 + (i % 20) - 10)):
            conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?)", (symbol, day, 100, close))
    conn.commit()
    return conn


def _capture(conn, store, n=500):
    now = datetime(2026, 11, 11, 17, tzinfo=learning.IST)
    with patch.object(learning, "_now", return_value=now):
        return learning.capture_universe_snapshot(
            conn, "2026-11-11", [f"S{i:03d}.NS" for i in range(n)],
            [_row(i) for i in range(n)], store,
        )


def test_capture_all500_immutable_before_outcomes(tmp_path):
    conn = _database(tmp_path / "db")
    try:
        assert _capture(conn, tmp_path)["feature_count"] == 500
        path = tmp_path / "snapshots" / "2026-11-11.json"
        original = path.read_bytes()
        assert _capture(conn, tmp_path)["status"] == "ALREADY_CAPTURED"
        assert path.read_bytes() == original
        content = json.loads(original)
        assert len(content["rows"]) == 500
        assert all("t1_ret_pct" not in row for row in content["rows"])
    finally:
        conn.close()


@pytest.mark.parametrize("hour,day", [(14, "2026-11-11"), (17, "2026-11-10")])
def test_no_backdated_or_intraday_snapshot(tmp_path, hour, day):
    conn = _database(tmp_path / "db", 1)
    try:
        with patch.object(learning, "_now", return_value=datetime(2026, 11, 11, hour, tzinfo=learning.IST)):
            assert learning.capture_universe_snapshot(
                conn, day, ["S000.NS"], [_row(0)], tmp_path
            )["status"] == "SKIPPED_NOT_PROSPECTIVE"
        assert not (tmp_path / "snapshots").exists()
    finally:
        conn.close()


def test_exclusions_include_missing_bars_and_features(tmp_path):
    conn = _database(tmp_path / "db", 2)
    conn.execute("DELETE FROM ohlcv_daily WHERE symbol='S000.NS'")
    conn.commit()
    try:
        now = datetime(2026, 11, 11, 17, tzinfo=learning.IST)
        with patch.object(learning, "_now", return_value=now):
            learning.capture_universe_snapshot(
                conn, "2026-11-11", ["S000.NS", "S001.NS"], [_row(0)], tmp_path
            )
        rows = json.loads((tmp_path / "snapshots" / "2026-11-11.json").read_text())["rows"]
        assert [r["exclusion"] for r in rows] == ["MISSING_EXACT_DATE_BAR", "FEATURE_QUALITY_GATE"]
    finally:
        conn.close()


def test_resolution_all500_equal_size_and_idempotent(tmp_path):
    db = tmp_path / "db"
    conn = _database(db)
    _capture(conn, tmp_path)
    conn.close()
    now = datetime(2026, 11, 12, 17, tzinfo=learning.IST)
    with patch.object(learning, "_now", return_value=now):
        assert learning.run_universe_learning(db, tmp_path)["resolved_dates"] == 1
        assert learning.run_universe_learning(db, tmp_path)["resolved_dates"] == 0
    result = json.loads((tmp_path / "resolved" / "2026-11-11.json").read_text())
    assert result["evaluated_count"] == 500
    assert result["costs_included"]
    for comparison in result["comparisons"]:
        assert comparison["baseline20"]["n"] == comparison["challenger20"]["n"] == 20
        assert comparison["baseline5"]["n"] == comparison["challenger5"]["n"] == 5
        assert comparison["baseline20"]["symbols"] == comparison["challenger20"]["symbols"]
        assert comparison["baseline5"]["symbols"] == comparison["challenger5"]["symbols"]
        assert all(c["cause_status"] == "UNKNOWN_NOT_VERIFIED" for c in comparison["reason_cards"])
        assert all(e["weight"] == 0 for e in comparison["experiments"])
        assert comparison["baseline20"]["estimated_net_mean_return_pct"] < comparison[
            "baseline20"
        ]["directional_mean_return_pct"]
    assert {r["t1_ret_pct"] < 0 for r in result["rows"]} == {True, False}


def test_incomplete_or_intraday_outcomes_retry_not_freeze(tmp_path):
    db = tmp_path / "db"
    conn = _database(db, 2)
    _capture(conn, tmp_path, 2)
    conn.execute("DELETE FROM ohlcv_daily WHERE symbol='S001.NS' AND trade_date='2026-11-12'")
    conn.commit()
    conn.close()
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 12, 14, tzinfo=learning.IST)):
        assert learning.run_universe_learning(db, tmp_path)["resolved_dates"] == 0
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 12, 17, tzinfo=learning.IST)):
        result = learning.run_universe_learning(db, tmp_path)
    assert result["status"] == "WAITING_FOR_PRICES"
    assert result["pending_dates"] == 1
    assert not (tmp_path / "resolved" / "2026-11-11.json").exists()


def test_missing_db_reported_explicitly(tmp_path, caplog):
    result = learning.run_universe_learning(tmp_path / "missing", tmp_path)
    assert result["status"] == "ERROR"
    assert "Evidence processing failed" in caplog.text


def test_budget_zero_never_resolves(tmp_path):
    conn = _database(tmp_path / "db", 1)
    _capture(conn, tmp_path, 1)
    conn.close()
    assert learning.run_universe_learning(tmp_path / "db", tmp_path, max_dates=0)["resolved_dates"] == 0


def test_missing_outcomes_have_finite_data_quality_verdict(tmp_path):
    db = tmp_path / "db"
    conn = _database(db, 2)
    _capture(conn, tmp_path, 2)
    conn.execute("DELETE FROM ohlcv_daily WHERE symbol='S001.NS' AND trade_date='2026-11-12'")
    conn.commit()
    conn.close()
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 20, 17, tzinfo=learning.IST)):
        learning.run_universe_learning(db, tmp_path)
    result = json.loads((tmp_path / "resolved" / "2026-11-11.json").read_text())
    assert result["status"] == "DATA_INCOMPLETE"
    assert result["rows"] == result["comparisons"] == []


def test_sandy_read_only_surface_reports_coverage_and_no_fake_improvement(tmp_path):
    from sandy.sandy_supervisor import SandySupervisor
    with patch.object(learning, "STORE", tmp_path):
        status = learning.get_learning_status()
        assert status["snapshot_dates"] == 0
        report = SandySupervisor()._poll_universe_selection_learning()
    assert report.evidence_count == 0
    assert "not proven improvement" in report.summary


def _history(days=30):
    rows = []
    start = datetime(2026, 1, 1)
    for d in range(days):
        for i in range(60):
            row = _row(i)
            row.update(trade_date=(start + timedelta(days=d)).date().isoformat(),
                       outcome_date=(start + timedelta(days=d + 1)).date().isoformat(),
                       t1_ret_pct=4.0 if i > 40 else -1.0,
                       net_up_ret_pct=3.0 if i > 40 else -2.0,
                       net_down_ret_pct=-5.0 if i > 40 else 0.0)
            rows.append(row)
    return rows


def test_rules_reuse_real_bands_train_oos_and_bounded_effect():
    rules = learning._research_rules(_history(20), "UP")
    momentum = next(r for r in rules if r["name"] == "high_momentum_and_high_rs")
    assert momentum["status"] == "VALIDATED_RESEARCH_ONLY"
    assert momentum["weight"] == learning.MAX_RESEARCH_WEIGHT
    assert momentum["train_lift"] > 0
    assert momentum["oos_lift"] > 0


def test_failed_research_gets_finite_verdict_then_independent_epoch():
    rows = _history()
    for row in rows:
        row["t1_ret_pct"] = -1
    rules = learning._research_rules(rows, "UP")
    assert all(r["status"] == "REJECTED" for r in rules)
    next_rules = learning._research_rules(_history(31), "UP")
    assert all(r["evidence_days"] == 1 and r["weight"] == 0 for r in next_rules)
    assert next_rules[0]["experiment_id"] != rules[0]["experiment_id"]
    missing = learning._research_rules([], "UP", epoch_complete=True)
    assert all(r["status"] == "INSUFFICIENT_DATA_AT_DEADLINE" for r in missing)


def test_training_rejects_negative_oos_not_just_positive_train():
    rows = _history(20)
    for row in rows:
        if row["trade_date"] >= "2026-01-15":
            row["t1_ret_pct"] *= -1
    assert all(r["weight"] == 0 for r in learning._research_rules(rows, "UP"))


def test_validated_prior_knowledge_actually_changes_research_selection():
    current = []
    for i in range(60):
        row = _row(i)
        row.update(mom_5d=0, mom_accel=0, rs_pct_5d=0, hv_20=0, rsi_14=0,
                   vol_expansion=0, t1_ret_pct=0, gap_pct=0,
                   net_up_ret_pct=-0.5, net_down_ret_pct=-0.5)
        if i == 39:
            row.update(mom_5d=99, rs_pct_5d=99)
        current.append(row)
    original = json.dumps(current, sort_keys=True)
    result = learning._evaluate_snapshot(
        {"captured_at": "2026-11-11T17:00:00+05:30"}, current, _history(20)
    )[0]
    assert "S039.NS" not in result["baseline20"]["symbols"]
    assert "S039.NS" in result["challenger20"]["symbols"]
    assert len(result["challenger20"]["symbols"]) == 20
    assert json.dumps(current, sort_keys=True) == original


def test_quality_excluded_winner_still_counts_in_full_universe_leaderboard(tmp_path):
    db = tmp_path / "db"
    conn = _database(db, 25)
    conn.execute("UPDATE ohlcv_daily SET close=150 WHERE symbol='S024.NS' AND trade_date='2026-11-12'")
    conn.commit()
    now = datetime(2026, 11, 11, 17, tzinfo=learning.IST)
    with patch.object(learning, "_now", return_value=now):
        learning.capture_universe_snapshot(
            conn, "2026-11-11", [f"S{i:03d}.NS" for i in range(25)],
            [_row(i) for i in range(24)], tmp_path,
        )
    conn.close()
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 12, 17, tzinfo=learning.IST)):
        learning.run_universe_learning(db, tmp_path)
    result = json.loads((tmp_path / "resolved" / "2026-11-11.json").read_text())
    winner = result["comparisons"][0]["reason_cards"][0]
    assert winner["symbol"] == "S024.NS"
    assert winner["feature_exclusion"] == "FEATURE_QUALITY_GATE"
    assert not winner["in_baseline20"]


def test_future_resolutions_cannot_train_an_earlier_selection(tmp_path):
    db = tmp_path / "db"
    conn = _database(db, 2)
    _capture(conn, tmp_path, 2)
    conn.close()
    resolved = tmp_path / "resolved"
    resolved.mkdir()
    future = {**_row(0), "trade_date": "2026-11-10", "outcome_date": "2026-11-12",
              "t1_ret_pct": 999}
    (resolved / "2026-11-10.json").write_text(json.dumps({"rows": [future]}))
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 12, 17, tzinfo=learning.IST)), \
         patch.object(learning, "_evaluate_snapshot", wraps=learning._evaluate_snapshot) as evaluate:
        result = learning.run_universe_learning(db, tmp_path)
    assert result["resolved_dates"] == 1
    assert evaluate.call_args.args[2] == []


def test_weekend_rows_cannot_be_used_as_next_session_outcomes(tmp_path):
    db = tmp_path / "db"
    conn = _database(db, 2)
    for symbol in ("S000.NS", "S001.NS"):
        for day, close in (("2026-11-13", 100), ("2026-11-14", 999), ("2026-11-16", 102)):
            conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?)", (symbol, day, 100, close))
    conn.commit()
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 13, 17, tzinfo=learning.IST)):
        learning.capture_universe_snapshot(
            conn, "2026-11-13", ["S000.NS", "S001.NS"], [_row(0), _row(1)], tmp_path
        )
    conn.close()
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 16, 17, tzinfo=learning.IST)):
        learning.run_universe_learning(db, tmp_path)
    result = json.loads((tmp_path / "resolved" / "2026-11-13.json").read_text())
    assert result["outcome_date"] == "2026-11-16"
    assert all(r["t1_ret_pct"] == pytest.approx(2.0) for r in result["rows"])


def test_eod_wiring_and_capture_are_present():
    root = learning.ROOT
    source = (root / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")
    assert source.index("_universe_learning = run_universe_learning()") < source.index(
        "_disc_results = _run_fp_discovery()"
    )
    source = (root / "scripts" / "final_trading_architecture_shadow_001.py").read_text(encoding="utf-8")
    assert "capture_universe_snapshot(conn, trade_date, symbols, scored)" in source
