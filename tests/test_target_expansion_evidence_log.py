"""
tests/test_target_expansion_evidence_log.py
===============================================
Self-learning module #29 (ACQUISITION) -- evidence log for Dynamic
Target Expansion outcomes.

T01  record_expansion_outcome() persists a correctly-classified WIN
T02  record_expansion_outcome() persists a correctly-classified LOSS
T03  risk_per_share<=0 is skipped (never crashes, never writes garbage)
T04  get_records() returns oldest-first and respects n
T05  get_evidence_summary() computes sample size / win rate / mean delta
T06  get_evidence_summary() with zero records returns Nones, not a crash
T07  Fail-open: a corrupt JSONL line is skipped, not fatal
T08  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import learning_system.target_expansion_evidence_log as evlog


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(evlog, "_EVIDENCE_FILE", str(tmp_path / "evidence.jsonl")), \
         patch.object(evlog, "_DATA_DIR", str(tmp_path)):
        yield


def test_t01_win_classified_correctly():
    # entry=100, risk_per_share=10 -> original target at 130 implies 3R.
    # Trade actually closed at 150 -> final_r=5R >= 3R -> WIN.
    evlog.record_expansion_outcome(
        order_id="O1", symbol="TEST", strategy="breakout", direction="BUY",
        entry_price=100.0, risk_per_share=10.0,
        original_target=130.0, expanded_target=200.0,
        exit_price=150.0, final_r_multiple=5.0,
    )
    records = evlog.get_records()
    assert len(records) == 1
    assert records[0]["outcome"] == "WIN"
    assert records[0]["original_target_r"] == 3.0


def test_t02_loss_classified_correctly():
    # Expanded but gave back gains below the original target's implied R.
    evlog.record_expansion_outcome(
        order_id="O2", symbol="TEST", strategy="breakout", direction="BUY",
        entry_price=100.0, risk_per_share=10.0,
        original_target=130.0, expanded_target=200.0,
        exit_price=115.0, final_r_multiple=1.5,
    )
    records = evlog.get_records()
    assert records[0]["outcome"] == "LOSS"


def test_t03_zero_risk_skipped_not_crashed():
    evlog.record_expansion_outcome(
        order_id="O3", symbol="TEST", strategy="breakout", direction="BUY",
        entry_price=100.0, risk_per_share=0.0,
        original_target=130.0, expanded_target=200.0,
        exit_price=150.0, final_r_multiple=5.0,
    )
    assert evlog.get_records() == []


def test_t04_get_records_oldest_first_and_n():
    for i in range(5):
        evlog.record_expansion_outcome(
            order_id=f"O{i}", symbol="TEST", strategy="breakout", direction="BUY",
            entry_price=100.0, risk_per_share=10.0,
            original_target=130.0, expanded_target=200.0,
            exit_price=150.0, final_r_multiple=5.0,
        )
    all_records = evlog.get_records()
    assert [r["order_id"] for r in all_records] == [f"O{i}" for i in range(5)]
    last_two = evlog.get_records(n=2)
    assert [r["order_id"] for r in last_two] == ["O3", "O4"]


def test_t05_summary_computes_win_rate_and_mean_delta():
    evlog.record_expansion_outcome(
        order_id="A", symbol="X", strategy="s", direction="BUY",
        entry_price=100.0, risk_per_share=10.0,
        original_target=130.0, expanded_target=200.0,
        exit_price=150.0, final_r_multiple=5.0,   # WIN, delta=+2.0
    )
    evlog.record_expansion_outcome(
        order_id="B", symbol="X", strategy="s", direction="BUY",
        entry_price=100.0, risk_per_share=10.0,
        original_target=130.0, expanded_target=200.0,
        exit_price=115.0, final_r_multiple=1.5,   # LOSS, delta=-1.5
    )
    summary = evlog.get_evidence_summary()
    assert summary["sample_size"] == 2
    assert summary["win_rate"] == 0.5
    assert summary["mean_r_delta"] == pytest.approx(0.25, abs=1e-6)


def test_t06_empty_summary_no_crash():
    summary = evlog.get_evidence_summary()
    assert summary == {"sample_size": 0, "win_rate": None, "mean_r_delta": None}


def test_t07_corrupt_line_skipped(tmp_path):
    path = tmp_path / "evidence.jsonl"
    with patch.object(evlog, "_EVIDENCE_FILE", str(path)):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not valid json\n")
            fh.write(json.dumps({"order_id": "OK", "outcome": "WIN",
                                  "final_r_multiple": 5.0, "original_target_r": 3.0}) + "\n")
        records = evlog.get_records()
        assert len(records) == 1
        assert records[0]["order_id"] == "OK"


def test_t08_safety_contract_source_scan():
    import inspect
    src = inspect.getsource(evlog)
    forbidden = ("execution_engine", "order_manager", "dhan_feed", "broker")
    for token in forbidden:
        assert token not in src, f"forbidden import/reference found: {token}"

