"""
tests/test_debate_vote_tracker.py
====================================
Self-Learning Ecosystem -- Post-roadmap Priority 3 (part 1): ACQUISITION
+ VALIDATION for MultiAgentDebate weight self-tuning.

T01  record_debate_votes() appends a real, correctly-shaped JSONL record
T02  record_debate_votes() fails open (False) when signal has no symbol
T03  resolve_matured_votes() leaves immature records untouched (never
     calls the price fetcher for them)
T04  resolve_matured_votes() resolves a mature BUY record: favorable move
     marks high-scoring (>=6.5) votes correct, low-scoring votes incorrect
T05  resolve_matured_votes() resolves a mature SELL record with the
     inverted favorable-direction rule
T06  A resolve with no price data available stays pending (not marked
     resolved), so it can be retried on a future cycle
T07  get_debater_accuracy() aggregates sample_size/correct_count/accuracy
     correctly across multiple resolved debates
T08  get_resolved_records_for_agent() returns time-ordered (oldest-first)
     records for exactly one debater
T09  Fail-open: never raises when the vote log file is corrupt
T10  Safety contract: zero imports of execution_engine/order_manager/
     dhan_feed/broker/risk_control anywhere in this module
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

import debate_system.debate_vote_tracker as tracker


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    vote_log = tmp_path / "vote_log.jsonl"
    with patch.object(tracker, "_VOTE_LOG", str(vote_log)):
        yield vote_log


def _signal(symbol="RELIANCE", direction="BUY", entry=1000.0):
    return SimpleNamespace(symbol=symbol, direction=SimpleNamespace(value=direction), entry_price=entry)


def _vote(agent_name, score, vote="approve", modifier=1.0):
    return SimpleNamespace(agent_name=agent_name, vote=vote, score=score, suggested_position_modifier=modifier)


def _decision(approved=True, confidence=7.0, trade_type="FULL"):
    return SimpleNamespace(approved=approved, confidence_score=confidence, trade_type=trade_type)


def test_t01_record_appends_real_jsonl(_isolated_store):
    votes = [_vote("TechnicalAnalystAI", 8.0), _vote("RiskDebateAI", 6.0)]
    ok = tracker.record_debate_votes(_signal(), votes, _decision())
    assert ok is True
    records = tracker._read_jsonl(str(_isolated_store))
    assert len(records) == 1
    rec = records[0]
    assert rec["symbol"] == "RELIANCE"
    assert rec["direction"] == "BUY"
    assert rec["outcome_resolved"] is False
    assert len(rec["votes"]) == 2
    assert rec["votes"][0]["agent_name"] == "TechnicalAnalystAI"


def test_t02_fails_open_no_symbol(_isolated_store):
    bad_signal = SimpleNamespace(symbol=None, direction=SimpleNamespace(value="BUY"), entry_price=100.0)
    ok = tracker.record_debate_votes(bad_signal, [_vote("TechnicalAnalystAI", 8.0)], _decision())
    assert ok is False


def test_t03_immature_records_left_untouched(_isolated_store):
    tracker.record_debate_votes(_signal(), [_vote("TechnicalAnalystAI", 8.0)], _decision())
    with patch.object(tracker, "_fetch_ohlcv_closes") as mock_fetch:
        result = tracker.resolve_matured_votes(maturity_days=7)
    mock_fetch.assert_not_called()
    assert result["resolved"] == 0
    assert result["skipped_immature"] == 1


def test_t04_resolve_buy_favorable_and_unfavorable_votes(_isolated_store):
    votes = [_vote("TechnicalAnalystAI", 8.0), _vote("RiskDebateAI", 4.0)]
    tracker.record_debate_votes(_signal(direction="BUY", entry=1000.0), votes, _decision())
    # backdate the record so it's mature
    records = tracker._read_jsonl(str(_isolated_store))
    records[0]["decision_date"] = "2020-01-01"
    tracker._write_jsonl(str(_isolated_store), records)

    with patch.object(tracker, "_fetch_ohlcv_closes", return_value=[1050.0]):
        result = tracker.resolve_matured_votes(maturity_days=7)

    assert result["resolved"] == 1
    resolved = tracker._read_jsonl(str(_isolated_store))[0]
    assert resolved["outcome_resolved"] is True
    assert resolved["favorable"] is True   # price rose, BUY signal
    votes_by_name = {v["agent_name"]: v for v in resolved["votes"]}
    assert votes_by_name["TechnicalAnalystAI"]["correct"] is True   # scored >=6.5, favorable
    assert votes_by_name["RiskDebateAI"]["correct"] is False        # scored <6.5, favorable


def test_t05_resolve_sell_inverted_rule(_isolated_store):
    votes = [_vote("TechnicalAnalystAI", 8.0)]
    tracker.record_debate_votes(_signal(direction="SELL", entry=1000.0), votes, _decision())
    records = tracker._read_jsonl(str(_isolated_store))
    records[0]["decision_date"] = "2020-01-01"
    tracker._write_jsonl(str(_isolated_store), records)

    with patch.object(tracker, "_fetch_ohlcv_closes", return_value=[950.0]):  # price fell
        tracker.resolve_matured_votes(maturity_days=7)

    resolved = tracker._read_jsonl(str(_isolated_store))[0]
    assert resolved["favorable"] is True   # SELL + price fell = favorable
    assert resolved["votes"][0]["correct"] is True


def test_t06_no_price_data_stays_pending(_isolated_store):
    tracker.record_debate_votes(_signal(), [_vote("TechnicalAnalystAI", 8.0)], _decision())
    records = tracker._read_jsonl(str(_isolated_store))
    records[0]["decision_date"] = "2020-01-01"
    tracker._write_jsonl(str(_isolated_store), records)

    with patch.object(tracker, "_fetch_ohlcv_closes", return_value=[]):
        result = tracker.resolve_matured_votes(maturity_days=7)

    assert result["resolved"] == 0
    assert tracker._read_jsonl(str(_isolated_store))[0]["outcome_resolved"] is False


def test_t07_get_debater_accuracy_aggregates(_isolated_store):
    for i, (score, close) in enumerate([(8.0, 1100.0), (8.0, 900.0), (3.0, 900.0)]):
        tracker.record_debate_votes(_signal(symbol=f"SYM{i}", entry=1000.0),
                                     [_vote("TechnicalAnalystAI", score)], _decision())
    records = tracker._read_jsonl(str(_isolated_store))
    for r in records:
        r["decision_date"] = "2020-01-01"
    tracker._write_jsonl(str(_isolated_store), records)

    closes_seq = [[1100.0], [900.0], [900.0]]
    with patch.object(tracker, "_fetch_ohlcv_closes", side_effect=closes_seq):
        tracker.resolve_matured_votes(maturity_days=7)

    acc = tracker.get_debater_accuracy("TechnicalAnalystAI")
    stat = acc["TechnicalAnalystAI"]
    assert stat["sample_size"] == 3
    # rec0: score 8.0 (approve), price rose -> favorable=True -> correct
    # rec1: score 8.0 (approve), price fell -> favorable=False -> incorrect
    # rec2: score 3.0 (reject-leaning), price fell -> favorable=False -> correct
    assert stat["correct_count"] == 2
    assert abs(stat["accuracy"] - 2 / 3) < 1e-9


def test_t08_resolved_records_time_ordered_for_one_agent(_isolated_store):
    for i, date_str in enumerate(["2020-01-03", "2020-01-01", "2020-01-02"]):
        tracker.record_debate_votes(_signal(symbol=f"SYM{i}"),
                                     [_vote("TechnicalAnalystAI", 8.0), _vote("RiskDebateAI", 8.0)],
                                     _decision())
    records = tracker._read_jsonl(str(_isolated_store))
    for r, date_str in zip(records, ["2020-01-03", "2020-01-01", "2020-01-02"]):
        r["decision_date"] = date_str
        r["outcome_resolved"] = True
        r["favorable"] = True
        for v in r["votes"]:
            v["correct"] = True
    tracker._write_jsonl(str(_isolated_store), records)

    out = tracker.get_resolved_records_for_agent("TechnicalAnalystAI")
    assert [r["decision_date"] for r in out] == ["2020-01-01", "2020-01-02", "2020-01-03"]


def test_t09_fail_open_on_corrupt_file(tmp_path):
    bad_path = tmp_path / "corrupt.jsonl"
    bad_path.write_text("{not valid json\n", encoding="utf-8")
    with patch.object(tracker, "_VOTE_LOG", str(bad_path)):
        result = tracker.resolve_matured_votes()
    assert result["status"] == "OK"
    assert result["resolved"] == 0


def test_t10_no_forbidden_imports():
    import os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "debate_system", "debate_vote_tracker.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
        assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
