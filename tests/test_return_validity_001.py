"""Return validity: index points, splits/bonuses/demergers and holiday bars must not
count as stock winners, losers or evidence."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from data_integrity import return_validity as rv
from scripts.knowledge_system import universe_selection_learning as learning


@pytest.mark.parametrize("symbol,expected", [
    ("NIFTY", True), ("BANKNIFTY", True), ("^NSEI", True), ("NIFTY.NS", True),
    ("RELIANCE", False), ("NIFTYBEES.NS", False), (None, False), ("", False),
])
def test_index_symbols(symbol, expected):
    assert rv.is_index_symbol(symbol) is expected


@pytest.mark.parametrize("value,horizon,expected", [
    (19.9, 1, False), (-20.0, 1, False), (30.0, 1, False), (30.1, 1, True), (-88.6, 1, True),
    (35.0, 3, False), (45.0, 3, True), (45.0, 5, False), (55.0, 5, True),
    (float("nan"), 1, True), (None, 1, True), ("x", 1, True),
])
def test_implausible_return_thresholds(value, horizon, expected):
    assert rv.is_implausible_return(value, horizon) is expected


def test_corporate_action_step():
    assert rv.is_corporate_action_step(100, 35)           # demerger
    assert rv.is_corporate_action_step(100, 1000)         # reverse split
    assert not rv.is_corporate_action_step(100, 80)       # 20% circuit move
    assert not rv.is_corporate_action_step(0, 80) and not rv.is_corporate_action_step(None, 80)


def test_holiday_placeholder_bars_are_skipped_not_treated_as_a_reference():
    series = [("d1", 100, 5), ("d2", 100, 0), ("d3", 40, 7)]
    assert rv.find_corporate_actions(series) == ["d3"]      # 100 -> 40 across a placeholder
    assert rv.find_corporate_actions([("d1", 100, 5), ("d2", 100, 0), ("d3", 101, 5)]) == []


def _db(path, with_volume=True):
    conn = sqlite3.connect(path)
    cols = "symbol TEXT, trade_date TEXT, open REAL, close REAL" + (", volume REAL" if with_volume else "")
    conn.execute(f"CREATE TABLE ohlcv_daily({cols})")
    return conn


def _put(conn, symbol, day, close, volume=100, with_volume=True):
    if with_volume:
        conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?,?)", (symbol, day, close, close, volume))
    else:
        conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?)", (symbol, day, close, close))


@pytest.mark.parametrize("with_volume", [True, False])
def test_symbols_with_corporate_action_detects_split_in_window(tmp_path, with_volume):
    conn = _db(tmp_path / "db", with_volume)
    for day, close in (("2026-11-09", 1000), ("2026-11-10", 1010), ("2026-11-11", 250)):
        _put(conn, "SPLIT.NS", day, close, with_volume=with_volume)
    for day, close in (("2026-11-09", 100), ("2026-11-10", 108), ("2026-11-11", 97)):
        _put(conn, "NORMAL.NS", day, close, with_volume=with_volume)
    _put(conn, "NIFTY", "2026-11-10", 24000, with_volume=with_volume)
    _put(conn, "NIFTY", "2026-11-11", 100, with_volume=with_volume)
    found = rv.symbols_with_corporate_action(
        conn, ["SPLIT.NS", "NORMAL.NS", "NIFTY"], "2026-11-01", "2026-11-11")
    assert found == {"SPLIT.NS": ["2026-11-11"]}
    assert rv.symbols_with_corporate_action(conn, ["SPLIT.NS"], "2026-11-11", "2026-11-11") == {}


def test_feature_window_start():
    assert rv.feature_window_start("2026-11-17", 60) == "2026-09-18"


def test_validate_and_filter_records():
    rows = [
        {"symbol": "OK", "t1_ret_pct": 2.0, "t3_ret_pct": 3.0},
        {"symbol": "NIFTY", "t1_ret_pct": 55348.7},
        {"symbol": "SPLIT", "t1_ret_pct": -88.6},
        {"symbol": "LATE", "t1_ret_pct": 1.0, "t5_ret_pct": 80.0},
        {"symbol": "PENDING", "t1_ret_pct": None},
    ]
    assert rv.validate_outcome_record(rows[0]) is None
    assert rv.validate_outcome_record(rows[1]) == rv.REASON_INDEX
    assert rv.validate_outcome_record(rows[2]) == rv.REASON_IMPLAUSIBLE
    assert rv.validate_outcome_record(rows[3]) == rv.REASON_IMPLAUSIBLE
    usable, excluded = rv.filter_valid_records(rows)
    assert [r["symbol"] for r in usable] == ["OK", "PENDING"]
    assert excluded == {rv.REASON_INDEX: 1, rv.REASON_IMPLAUSIBLE: 2}


def _ledger(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def _rec(symbol, t1, day="2026-11-10", **extra):
    return {"symbol": symbol, "direction": "UP", "trade_date": day, "atr_pct": 2.0,
            "t1_ret_pct": t1, "processed_at": "2026-11-11T00:00:00", **extra}


def test_analyzer_loader_excludes_invalid_rows_and_counts_them(tmp_path):
    from scripts.knowledge_system import selection_characteristic_analyzer_001 as analyzer
    ledger = tmp_path / "ledger.jsonl"
    _ledger(ledger, [_rec("GOOD", 2.5), _rec("NIFTY", 55000.0), _rec("SPLIT", -85.0),
                     _rec("GOOD", 2.5, day="2026-11-09")])
    records = analyzer.load_records(ledger)
    assert sorted((r["symbol"], r["trade_date"]) for r in records) == [
        ("GOOD", "2026-11-09"), ("GOOD", "2026-11-10")]
    assert analyzer.LAST_LOAD_EXCLUSIONS == {rv.REASON_INDEX: 1, rv.REASON_IMPLAUSIBLE: 1}


def test_latest_record_for_a_key_is_authoritative_for_validity(tmp_path):
    from scripts.knowledge_system import selection_characteristic_analyzer_001 as analyzer
    ledger = tmp_path / "ledger.jsonl"
    older = _rec("X", 2.0, processed_at="2026-11-11T00:00:00")
    newer = _rec("X", -90.0, processed_at="2026-11-12T00:00:00")
    _ledger(ledger, [older, newer])
    assert analyzer.load_records(ledger) == []


def test_pattern_miner_and_shadow_loader_exclude_invalid_rows(tmp_path):
    from scripts.knowledge_system import knowledge_pattern_miner_001 as miner
    from scripts.knowledge_system import ranking_adjustment_engine_001 as engine
    ledger = tmp_path / "ledger.jsonl"
    _ledger(ledger, [_rec("GOOD", 1.0), _rec("BANKNIFTY", 61000.0), _rec("SPLIT", 70.0),
                     _rec("PENDING", None)])
    assert [r["symbol"] for r in miner.load_evidence(ledger)] == ["GOOD", "PENDING"]
    shadow = tmp_path / "shadow.jsonl"
    _ledger(shadow, [{**_rec("GOOD", 1.0), "record_type": "SHADOW_CANDIDATE"},
                     {**_rec("NIFTY", 55000.0), "record_type": "SHADOW_CANDIDATE"},
                     {**_rec("SPLIT", -88.0), "record_type": "SHADOW_CANDIDATE"}])
    with patch.object(engine, "SHADOW_JSONL_PATH", shadow):
        assert [r["symbol"] for r in engine._load_raw_shadow_records()] == ["GOOD"]


FEATURES = {"atr_pct": 2.0, "mom_5d": 1.0, "mom_accel": 0.5, "vol_ratio": 1.1, "rs_pct_5d": 0.3,
            "rsi_14": 55.0, "hv_20": 1.2, "vol_expansion": 0.1, "v3_up_score": 0.5, "v3_down_score": 0.5}


def test_snapshot_excludes_symbols_with_a_corporate_action_in_the_feature_window(tmp_path):
    conn = _db(tmp_path / "db", with_volume=False)
    for symbol, closes in (("SPLIT.NS", (1000, 250)), ("FINE.NS", (100, 104))):
        for day, close in zip(("2026-11-10", "2026-11-11"), closes):
            _put(conn, symbol, day, close, with_volume=False)
    scored = [{"symbol": s, **FEATURES} for s in ("SPLIT.NS", "FINE.NS")]
    now = datetime(2026, 11, 11, 17, tzinfo=learning.IST)
    with patch.object(learning, "_now", return_value=now):
        learning.capture_universe_snapshot(conn, "2026-11-11", ["SPLIT.NS", "FINE.NS"], scored, tmp_path)
    rows = {r["symbol"]: r for r in json.loads(
        (tmp_path / "snapshots" / "2026-11-11.json").read_text())["rows"]}
    assert rows["FINE.NS"]["exclusion"] is None
    assert rows["SPLIT.NS"]["exclusion"] == rv.REASON_CORP_ACTION_WINDOW
    assert rows["SPLIT.NS"]["corporate_action_dates"] == ["2026-11-11"]
    assert "atr_pct" not in rows["SPLIT.NS"]


def test_outcome_day_corporate_action_is_excluded_from_winners_and_the_pool(tmp_path):
    conn = _db(tmp_path / "db", with_volume=False)
    symbols = [f"S{i:03d}.NS" for i in range(30)]
    for i, symbol in enumerate(symbols):
        conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?)", (symbol, "2026-11-11", 100, 100))
        # S000 gaps up 80% (a reverse split / bad open), everything else moves a few percent.
        open_, close = (180, 182) if i == 0 else (100, 100 + (i % 7) - 3)
        conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?)", (symbol, "2026-11-12", open_, close))
    conn.commit()
    scored = [{"symbol": s, **FEATURES, "v3_up_score": i / 30, "v3_down_score": 1 - i / 30}
              for i, s in enumerate(symbols)]
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 11, 17, tzinfo=learning.IST)):
        learning.capture_universe_snapshot(conn, "2026-11-11", symbols, scored, tmp_path)
    conn.close()
    with patch.object(learning, "_now", return_value=datetime(2026, 11, 12, 17, tzinfo=learning.IST)):
        learning.run_universe_learning(tmp_path / "db", tmp_path)
    report = json.loads((tmp_path / "resolved" / "2026-11-11.json").read_text())
    bad = next(r for r in report["rows"] if r["symbol"] == "S000.NS")
    assert bad["outcome_exclusion"] == rv.REASON_IMPLAUSIBLE and bad["exclusion"] == rv.REASON_IMPLAUSIBLE
    assert report["invalid_outcome_count"] == 1 and report["evaluated_count"] == 30
    for comparison in report["comparisons"]:
        assert "S000.NS" not in {c["symbol"] for c in comparison["reason_cards"]}
        assert "S000.NS" not in comparison["baseline20"]["symbols"]


def _move(symbol, ret):
    return SimpleNamespace(symbol=symbol, daily_return_pct=ret, data_source="LOCAL")


def test_benchmark_movers_skip_corporate_actions_and_refill_to_top_n():
    from opportunity_engine import market_opportunity_benchmark as bench
    moves = {s: _move(s, r) for s, r in {
        "SPLIT": -64.9, "BONUS": 70.0, "A": 9.0, "B": 8.0, "C": 7.0, "D": -6.0, "E": -7.5, "F": -2.0}.items()}
    ordered = sorted(moves.values(), key=lambda m: m.daily_return_pct, reverse=True)
    daily = SimpleNamespace(universe_symbols=list(moves), all_moves=moves,
                            gainers=ordered[:3], losers=ordered[::-1][:3])
    membership = {"universe_identity": "T", "membership_is_pit": False}
    with patch("predictive_gap.pga_collector.collect_daily", return_value=daily):
        gainers, losers, coverage = bench._collect_nifty500_movers("2026-11-12", 3, list(moves), membership)
    assert [g.symbol for g in gainers] == ["A", "B", "C"]
    assert [l.symbol for l in losers] == ["E", "D", "F"]
    assert coverage["corporate_action_suspects"] == ["BONUS", "SPLIT"]


def test_benchmark_is_unchanged_when_there_are_no_suspects():
    from opportunity_engine import market_opportunity_benchmark as bench
    moves = {s: _move(s, r) for s, r in {"A": 9.0, "B": 8.0, "D": -6.0, "E": -7.5}.items()}
    daily = SimpleNamespace(universe_symbols=list(moves), all_moves=moves,
                            gainers=[moves["A"], moves["B"]], losers=[moves["E"], moves["D"]])
    with patch("predictive_gap.pga_collector.collect_daily", return_value=daily):
        gainers, losers, coverage = bench._collect_nifty500_movers(
            "2026-11-12", 2, list(moves), {"universe_identity": "T", "membership_is_pit": False})
    assert [g.symbol for g in gainers] == ["A", "B"] and [l.symbol for l in losers] == ["E", "D"]
    assert coverage["corporate_action_suspects"] == []
