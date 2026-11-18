"""Mover cause attribution: tags come from observable data only; missing event data stays visible."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.knowledge_system import mover_cause_attribution as cause


def _classify(direction="UP", prev=100.0, open_=100.0, close=100.0, volume=1000.0,
              median=1000.0, market=0.0, sector=0.0, peers=5):
    return cause.classify_mover(direction, prev, open_, close, volume, median, market, sector, peers)


def test_gap_driven_move_is_observable_at_the_open():
    result = _classify(open_=105, close=106)
    assert "OPENING_GAP" in result["tags"] and result["observable_at"] == "OPEN_0915"
    assert "INTRADAY_TREND" not in result["tags"]


def test_intraday_trend_without_a_gap_is_intraday_observable():
    result = _classify(open_=100.2, close=104)
    assert "INTRADAY_TREND" in result["tags"] and "OPENING_GAP" not in result["tags"]
    assert result["observable_at"] == "INTRADAY"


def test_volume_surge_and_stock_specific():
    result = _classify(open_=100, close=103, volume=3000)
    assert "VOLUME_SURGE" in result["tags"] and "STOCK_SPECIFIC" in result["tags"]
    assert _classify(open_=100, close=103, volume=1500)["volume_ratio"] == 1.5
    assert "VOLUME_SURGE" not in _classify(open_=100, close=103, volume=1500)["tags"]


def test_market_and_sector_led_moves_are_not_stock_specific():
    market = _classify(open_=100, close=103, market=0.9)
    assert "MARKET_LED" in market["tags"] and "STOCK_SPECIFIC" not in market["tags"]
    sector = _classify(open_=100, close=103, sector=1.4)
    assert "SECTOR_LED" in sector["tags"] and "STOCK_SPECIFIC" not in sector["tags"]
    assert "SECTOR_LED" not in _classify(open_=100, close=103, sector=1.4, peers=2)["tags"]


def test_down_direction_mirrors_the_signs():
    result = _classify(direction="DOWN", open_=95, close=94, market=-1.0)
    assert {"OPENING_GAP", "MARKET_LED"} <= set(result["tags"])
    assert "MARKET_LED" not in _classify(direction="DOWN", open_=95, close=94, market=1.0)["tags"]


def test_missing_inputs_degrade_to_no_tag_not_a_guess():
    result = cause.classify_mover("UP", 100, 100, 103, None, None, None, None, 0)
    assert result["volume_ratio"] is None and "VOLUME_SURGE" not in result["tags"]
    assert result["market_ret_pct"] is None and "STOCK_SPECIFIC" in result["tags"]
    assert result["event_cause"] == cause.EVENT_CAUSE_UNVERIFIED


def _database(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv_daily(symbol TEXT, trade_date TEXT, open REAL, close REAL, volume REAL)")
    conn.execute("CREATE TABLE daily_events(event_id INTEGER)")
    conn.execute("CREATE TABLE bulk_block_deals(deal_id INTEGER)")
    history = ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-09")
    bars = {  # symbol: (T close, outcome open, outcome close, outcome volume)
        "GAPPER.NS": (100, 105, 106, 3000), "TRENDER.NS": (100, 100.2, 104, 1000),
        "LONER.NS": (100, 100, 103, 1000),
        "P1.NS": (100, 100, 102, 1000), "P2.NS": (100, 100, 102, 1000), "P3.NS": (100, 100, 102, 1000),
        "^NSEI": (20000, 20000, 20010, 0),
    }
    for symbol, (close_t, open_o, close_o, volume_o) in bars.items():
        for day in history:
            conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?,?)", (symbol, day, 100, 100, 1000))
        conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?,?)", (symbol, "2026-11-10", close_t, close_t, 1000))
        conn.execute("INSERT INTO ohlcv_daily VALUES(?,?,?,?,?)", (symbol, "2026-11-11", open_o, close_o, volume_o))
    conn.commit()
    conn.close()


SECTORS = {"GAPPER": "Tech", "TRENDER": "Tech", "P1": "Tech", "P2": "Tech", "P3": "Tech", "LONER": "Bank"}


def _report():
    symbols = ["GAPPER.NS", "TRENDER.NS", "LONER.NS", "P1.NS", "P2.NS", "P3.NS"]
    card = lambda s, inpool: {"symbol": s, "in_baseline20": inpool, "return_pct": 1.0}
    return {"version": "universe-v1", "trade_date": "2026-11-10", "outcome_date": "2026-11-11",
            "cohort_complete": True, "rows": [{"symbol": s} for s in symbols],
            "comparisons": [{"direction": "UP", "reason_cards": [
                card("GAPPER.NS", True), card("TRENDER.NS", False), card("LONER.NS", False)]},
                {"direction": "DOWN", "reason_cards": []}]}


@pytest.fixture
def setup(tmp_path):
    db = tmp_path / "market.db"
    _database(db)
    store = tmp_path / "store"
    (store / "resolved").mkdir(parents=True)
    (store / "resolved" / "2026-11-10.json").write_text(json.dumps(_report()))
    return db, store


def test_attribution_tags_each_mover_from_real_bars(setup):
    db, store = setup
    with patch.object(cause, "_sector_map", return_value=SECTORS):
        summary = cause.run_mover_cause_attribution(db, store)
    assert summary["attributed_dates"] == 1 and summary["status"] == "OK"
    result = json.loads((store / "causes" / "2026-11-10.json").read_text())
    movers = {m["symbol"]: m for m in result["directions"]["UP"]["movers"]}
    assert {"OPENING_GAP", "VOLUME_SURGE"} <= set(movers["GAPPER.NS"]["tags"])
    assert "INTRADAY_TREND" in movers["TRENDER.NS"]["tags"]
    assert "SECTOR_LED" in movers["TRENDER.NS"]["tags"]           # peers GAPPER, P1-P3: median +2%
    assert "STOCK_SPECIFIC" in movers["LONER.NS"]["tags"] and movers["LONER.NS"]["sector_peers"] == 0
    assert result["market_ret_pct"] == 0.05
    assert result["event_data_rows"] == {"daily_events": 0, "bulk_block_deals": 0}
    assert result["directions"]["UP"]["tag_counts"]["STOCK_SPECIFIC"] == 1


def test_attribution_is_idempotent_and_skips_incomplete_cohorts(setup):
    db, store = setup
    incomplete = {**_report(), "trade_date": "2026-11-09", "cohort_complete": False}
    (store / "resolved" / "2026-11-09.json").write_text(json.dumps(incomplete))
    with patch.object(cause, "_sector_map", return_value=SECTORS):
        assert cause.run_mover_cause_attribution(db, store)["attributed_dates"] == 1
        assert cause.run_mover_cause_attribution(db, store)["attributed_dates"] == 0
    assert not (store / "causes" / "2026-11-09.json").exists()


def test_attribution_never_raises_and_reports_problems(tmp_path):
    (tmp_path / "resolved").mkdir()
    (tmp_path / "resolved" / "2026-11-10.json").write_text(json.dumps(_report()))
    summary = cause.run_mover_cause_attribution(tmp_path / "missing.db", tmp_path)
    assert summary["status"].startswith("ERROR") and summary["attributed_dates"] == 0
    assert cause.run_mover_cause_attribution(tmp_path / "x.db", tmp_path / "nothing")["status"] == "NO_RESOLVED_COHORTS"


def test_summary_rolls_up_shares_and_keeps_the_event_data_gap_visible(setup):
    db, store = setup
    assert cause.get_cause_summary(store)["status"] == "NO_ATTRIBUTION_YET"
    with patch.object(cause, "_sector_map", return_value=SECTORS):
        cause.run_mover_cause_attribution(db, store)
    summary = cause.get_cause_summary(store)
    up = summary["directions"]["UP"]["intraday_ranked"]
    assert summary["days"] == 1 and summary["event_causes_verifiable"] is False
    assert up["movers"] == 3 and up["tag_share"]["OPENING_GAP"] == pytest.approx(1 / 3, abs=0.001)
    assert up["pool20_capture_rate"] == pytest.approx(1 / 3, abs=0.001)
    assert up["observable_at_share"]["OPEN_0915"] == pytest.approx(1 / 3, abs=0.001)
    down = summary["directions"]["DOWN"]["intraday_ranked"]
    assert down["movers"] == 0 and down["tag_share"]["OPENING_GAP"] is None


def test_full_day_ranking_includes_gap_driven_movers_the_intraday_ranking_misses(setup):
    db, store = setup
    report = _report()
    # The intraday ranking is built from open-to-close, so a pure gap stock is absent from it.
    report["comparisons"][0]["reason_cards"] = [
        {"symbol": "TRENDER.NS", "in_baseline20": False, "return_pct": 3.8}]
    report["comparisons"][0]["baseline20"] = {"symbols": ["GAPPER.NS"]}
    (store / "resolved" / "2026-11-10.json").write_text(json.dumps(report))
    with patch.object(cause, "_sector_map", return_value=SECTORS):
        cause.run_mover_cause_attribution(db, store)
    day = json.loads((store / "causes" / "2026-11-10.json").read_text())["directions"]["UP"]
    assert [m["symbol"] for m in day["movers"]] == ["TRENDER.NS"]
    by_total = {m["symbol"]: m for m in day["total_move_movers"]}
    assert "OPENING_GAP" in by_total["GAPPER.NS"]["tags"] and by_total["GAPPER.NS"]["in_baseline20"] is True
    assert day["total_move_movers"][0]["symbol"] == "GAPPER.NS"      # +6% is the day's biggest move
    assert day["total_move_tag_counts"]["OPENING_GAP"] == 1
    summary = cause.get_cause_summary(store)["directions"]["UP"]["total_move_ranked"]
    assert summary["observable_at_share"]["OPEN_0915"] > 0 and summary["pool20_capture_rate"] > 0


def test_implausible_full_day_moves_are_not_ranked_as_movers(setup):
    db, store = setup
    conn = sqlite3.connect(db)
    conn.execute("UPDATE ohlcv_daily SET open=40, close=41 WHERE symbol='LONER.NS' AND trade_date='2026-11-11'")
    conn.commit()
    conn.close()
    with patch.object(cause, "_sector_map", return_value=SECTORS):
        cause.run_mover_cause_attribution(db, store)
    day = json.loads((store / "causes" / "2026-11-10.json").read_text())["directions"]
    assert all(m["symbol"] != "LONER.NS" for m in day["UP"]["total_move_movers"])
    assert any(m["symbol"] == "LONER.NS" for m in day["DOWN"]["total_move_movers"]) is False


def test_summary_ignores_unreadable_files(tmp_path):
    (tmp_path / "causes").mkdir()
    (tmp_path / "causes" / "bad.json").write_text("{not json")
    assert cause.get_cause_summary(tmp_path)["status"] == "NO_ATTRIBUTION_YET"


def test_eod_runs_attribution_right_after_universe_learning():
    source = (Path(__file__).resolve().parents[1] / "orchestrator" / "master_orchestrator.py"
              ).read_text(encoding="utf-8")
    learning = source.index("run_universe_learning()")
    attribution = source.index("run_mover_cause_attribution()")
    assert 0 < attribution - learning < 1500


def _tagged(**over):
    base = {"symbol": "X.NS", "tags": ["INTRADAY_TREND", "STOCK_SPECIFIC"], "observable_at": "INTRADAY"}
    return {**base, **over}


def _event(category="Bagging/Receiving of orders/contracts", at="2026-11-10T18:00:00"):
    return {"category": category, "event_type": "ORDER_WIN", "direction": "POSITIVE", "announced_at": at}


def test_event_context_adds_tag_cause_and_pre_open_visibility():
    out = cause.apply_event_context(_tagged(), [_event()], True, [], True, "2026-11-11")
    assert "EVENT_ANNOUNCED" in out["tags"] and out["event_cause"].startswith("EVENT:Bagging")
    assert out["observable_at"] == "PRE_OPEN_EVENT" and out["events"][0]["direction"] == "POSITIVE"
    intraday = cause.apply_event_context(_tagged(), [_event(at="2026-11-11T11:00:00")], True, [], True, "2026-11-11")
    assert "EVENT_ANNOUNCED" in intraday["tags"] and intraday["observable_at"] == "INTRADAY"


def test_missing_data_is_never_reported_as_no_news():
    assert cause.apply_event_context(_tagged(), [], True, [], True, "2026-11-11")["event_cause"] == cause.EVENT_CAUSE_NONE
    unverified = cause.apply_event_context(_tagged(), [], False, [], False, "2026-11-11")
    assert unverified["event_cause"] == cause.EVENT_CAUSE_UNVERIFIED
    assert unverified["bulk_block_cause"] == cause.DEAL_CAUSE_UNVERIFIED
    assert "EVENT_ANNOUNCED" not in unverified["tags"] and "BULK_BLOCK_DEAL" not in unverified["tags"]


def test_deal_context_summarises_net_direction():
    deals = [{"buy_sell": "B", "quantity": 100.0}, {"buy_sell": "S", "quantity": 400.0}]
    out = cause.apply_event_context(_tagged(), [], True, deals, True, "2026-11-11")
    assert "BULK_BLOCK_DEAL" in out["tags"] and out["bulk_block_cause"] == "2 deal(s) NET_SELL"


def _with_event_tables(db):
    conn = sqlite3.connect(db)
    for table in ("daily_events", "bulk_block_deals"):
        conn.execute(f"DROP TABLE {table}")
    conn.execute("CREATE TABLE daily_events (symbol TEXT, event_date TEXT, event_type TEXT, direction TEXT, raw_data TEXT)")
    conn.execute("CREATE TABLE bulk_block_deals (symbol TEXT, trade_date TEXT, buy_sell TEXT, quantity REAL)")

    def event(symbol, day, at, category="Acquisition"):
        conn.execute("INSERT INTO daily_events VALUES (?,?,?,?,?)", (
            symbol, day, "OTHER", "NEUTRAL", json.dumps({"announced_at": at, "category": category})))
    event("GAPPER.NS", "2026-11-10", "2026-11-10T18:00:00", "Bagging/Receiving of orders/contracts")  # after T close
    event("TRENDER.NS", "2026-11-11", "2026-11-11T11:00:00")                                          # intraday
    event("LONER.NS", "2026-11-10", "2026-11-10T14:00:00")                                            # before T close
    event("LONER.NS", "2026-11-11", "2026-11-11T16:00:00")                                            # after outcome close
    conn.execute("INSERT INTO bulk_block_deals VALUES ('LONER.NS','2026-11-11','B',5000)")
    conn.commit()
    conn.close()


def test_attribution_links_only_in_window_events_and_same_day_deals(setup):
    db, store = setup
    _with_event_tables(db)
    with patch.object(cause, "_sector_map", return_value=SECTORS):
        cause.run_mover_cause_attribution(db, store)
    result = json.loads((store / "causes" / "2026-11-10.json").read_text())
    movers = {m["symbol"]: m for m in result["directions"]["UP"]["movers"]}
    assert movers["GAPPER.NS"]["event_cause"].startswith("EVENT:Bagging")
    assert movers["GAPPER.NS"]["observable_at"] == "PRE_OPEN_EVENT"
    assert "EVENT_ANNOUNCED" in movers["TRENDER.NS"]["tags"] and movers["TRENDER.NS"]["observable_at"] == "INTRADAY"
    loner = movers["LONER.NS"]                      # both of its filings fall outside the window
    assert loner["event_cause"] == cause.EVENT_CAUSE_NONE and "EVENT_ANNOUNCED" not in loner["tags"]
    assert "BULK_BLOCK_DEAL" in loner["tags"] and loner["bulk_block_cause"] == "1 deal(s) NET_BUY"
    assert result["event_coverage"] == {"events_in_window": 2, "deals_on_outcome_date": 1}
    summary = cause.get_cause_summary(store)
    assert summary["event_causes_verifiable"] and summary["bulk_block_causes_verifiable"]
    assert summary["directions"]["UP"]["intraday_ranked"]["observable_at_share"]["PRE_OPEN_EVENT"] == pytest.approx(1 / 3, abs=0.001)


def test_attribution_with_empty_event_tables_stays_unverified(setup):
    db, store = setup
    with patch.object(cause, "_sector_map", return_value=SECTORS):
        cause.run_mover_cause_attribution(db, store)
    movers = json.loads((store / "causes" / "2026-11-10.json").read_text())["directions"]["UP"]["movers"]
    assert {m["event_cause"] for m in movers} == {cause.EVENT_CAUSE_UNVERIFIED}
    assert {m["bulk_block_cause"] for m in movers} == {cause.DEAL_CAUSE_UNVERIFIED}
    assert cause.get_cause_summary(store)["event_causes_verifiable"] is False
