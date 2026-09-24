"""
tests/test_corporate_event_evidence_log.py
==============================================
Self-learning module #32 (ACQUISITION) -- evidence log for real trade
outcomes tagged with a corporate_event_score.

T01  record_corporate_event_outcome() persists correctly
T02  get_records() returns oldest-first and respects n
T03  Fail-open: a corrupt JSONL line is skipped, not fatal
T04  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import learning_system.corporate_event_evidence_log as evlog


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(evlog, "_EVIDENCE_FILE", str(tmp_path / "evidence.jsonl")), \
         patch.object(evlog, "_DATA_DIR", str(tmp_path)):
        yield


def test_t01_record_persists_correctly():
    evlog.record_corporate_event_outcome(
        order_id="O1", symbol="TEST", strategy="breakout",
        corporate_event_score=0.5, r_multiple=1.5, won=True,
    )
    records = evlog.get_records()
    assert len(records) == 1
    assert records[0]["corporate_event_score"] == 0.5
    assert records[0]["won"] is True


def test_t02_get_records_oldest_first_and_n():
    for i in range(5):
        evlog.record_corporate_event_outcome(
            order_id=f"O{i}", symbol="TEST", strategy="breakout",
            corporate_event_score=0.5, r_multiple=1.0, won=True,
        )
    all_records = evlog.get_records()
    assert [r["order_id"] for r in all_records] == [f"O{i}" for i in range(5)]
    last_two = evlog.get_records(n=2)
    assert [r["order_id"] for r in last_two] == ["O3", "O4"]


def test_t03_corrupt_line_skipped(tmp_path):
    path = tmp_path / "evidence.jsonl"
    with patch.object(evlog, "_EVIDENCE_FILE", str(path)):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not valid json\n")
            fh.write(json.dumps({"order_id": "OK", "won": True}) + "\n")
        records = evlog.get_records()
        assert len(records) == 1
        assert records[0]["order_id"] == "OK"


def test_t04_safety_contract_source_scan():
    import inspect
    src = inspect.getsource(evlog)
    forbidden = ("execution_engine", "order_manager", "dhan_feed", "broker")
    for token in forbidden:
        assert token not in src, f"forbidden import/reference found: {token}"
