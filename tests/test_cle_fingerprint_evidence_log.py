"""
tests/test_cle_fingerprint_evidence_log.py
=============================================
DTA-RESEARCH-QUALITY-001 -- ACQUISITION layer.

T01  record + get_records round-trip
T02  get_records(n) returns last n, oldest-first order preserved
T03  fail-open on I/O error (never raises)
T04  corrupt lines are skipped, not fatal
"""
from __future__ import annotations

import json
from unittest.mock import patch

from learning_system import cle_fingerprint_evidence_log as _log


def test_t01_record_and_read_roundtrip(tmp_path):
    p = str(tmp_path / "evidence.jsonl")
    with patch.object(_log, "_STORE_PATH", p), patch.object(_log, "_STORE_DIR", str(tmp_path)):
        _log.record_fingerprint_used("CLE-ABC-UP-20260101", "ABC", "UP",
                                      "low_rsi_high_mom_accel", "2026-01-01")
        records = _log.get_records()
    assert len(records) == 1
    assert records[0]["dna_id"] == "CLE-ABC-UP-20260101"
    assert records[0]["fingerprint_name"] == "low_rsi_high_mom_accel"


def test_t02_get_records_n_and_order(tmp_path):
    p = str(tmp_path / "evidence.jsonl")
    with patch.object(_log, "_STORE_PATH", p), patch.object(_log, "_STORE_DIR", str(tmp_path)):
        for i in range(5):
            _log.record_fingerprint_used(f"DNA-{i}", "SYM", "UP", "volume_momentum", "2026-01-01")
        last2 = _log.get_records(n=2)
    assert [r["dna_id"] for r in last2] == ["DNA-3", "DNA-4"]


def test_t03_fail_open_on_read_error(tmp_path):
    with patch.object(_log, "_STORE_PATH", str(tmp_path / "nonexistent" / "x.jsonl")):
        assert _log.get_records() == []


def test_t04_corrupt_lines_skipped(tmp_path):
    p = tmp_path / "evidence.jsonl"
    p.write_text('{"dna_id": "OK1"}\nNOT JSON\n{"dna_id": "OK2"}\n', encoding="utf-8")
    with patch.object(_log, "_STORE_PATH", str(p)):
        records = _log.get_records()
    assert [r["dna_id"] for r in records] == ["OK1", "OK2"]
