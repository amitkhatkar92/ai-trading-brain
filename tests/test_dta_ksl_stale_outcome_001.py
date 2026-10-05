"""
tests/test_dta_ksl_stale_outcome_001.py
==========================================
Root-cause fix: scripts/knowledge_system/shadow_evidence_consumer_001.py's
consume_new_records() used a plain set-membership dedup check keyed on
(run_id, symbol, trade_date, direction). run_shadow_day()'s run_id is
DETERMINISTIC per trade_date (_make_run_id = sha256(version:trade_date)),
so the same-day run (always t1_ret_pct=None at creation) and the later
backfill/backlog-catchup run (resolved t1_ret_pct) for the SAME candidate
share the IDENTICAL dedup key. The old set-based check therefore silently
discarded the resolved duplicate FOREVER once the unresolved occurrence
had been consumed -- confirmed live: every evidence-ledger record for
2026-09-22 through 2026-10-02 was permanently stuck at t1_ret_pct=None,
even though the raw shadow log had real resolved values for the same
keys, because the resolved duplicate was written to the raw log AFTER
the unresolved one had already been consumed and dedup-marked.

Fix: _load_existing_keys() now returns a Dict[str, bool] mapping dedup_key
-> "has a RESOLVED record for this key already been consumed". The main
loop only skips a key when it was already resolved, or the new occurrence
is itself still unresolved -- a previously-unresolved key paired with a
newly-resolved raw occurrence is now processed and appended as a
correction (never rewrites the old entry -- downstream consumers, e.g.
selection_characteristic_analyzer_001.load_records(), already dedupe by
(trade_date,symbol,direction) keeping the latest processed_at and already
skip unresolved rows, so the correction is picked up automatically).

T01  first-time key (not in ledger) is always processed regardless of
     resolution state
T02  key already resolved in the ledger is always skipped, even if a
     later raw occurrence also claims a (possibly different) resolved
     value -- never double-counts an already-settled key
T03  key previously consumed as UNRESOLVED, new raw occurrence ALSO
     unresolved -> skipped (no spurious duplicate appended)
T04  key previously consumed as UNRESOLVED, new raw occurrence IS
     resolved -> processed, appended as a correction
T05  end-to-end: consume_new_records() across a raw file with the exact
     same-day-then-backfill shape reproduces the fix (2 passes: first
     pass consumes the unresolved row, second pass -- simulating the
     backfill being appended later -- correctly appends the resolved row)
T06  _load_existing_keys() correctly OR-accumulates resolved state when
     multiple ledger lines already exist for the same key
"""
from __future__ import annotations

import json

from scripts.knowledge_system.shadow_evidence_consumer_001 import (
    _load_existing_keys,
    consume_new_records,
)


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _append_jsonl(path, records):
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _candidate(run_id="r1", symbol="FOO.NS", trade_date="2026-09-25",
               direction="UP", t1_ret_pct=None, selected_final_5=False):
    return {
        "record_type": "SHADOW_CANDIDATE",
        "run_id": run_id,
        "symbol": symbol,
        "trade_date": trade_date,
        "direction": direction,
        "t1_ret_pct": t1_ret_pct,
        "selected_final_5": selected_final_5,
        "atr_pct": 1.0, "mom_5d": 1.0, "mom_accel": 1.0, "vol_ratio": 1.0,
        "rs_pct_5d": 1.0, "rsi_14": 50.0, "hv_20": 10.0, "vol_expansion": 1.0,
    }


class TestLoadExistingKeys:
    def test_T02_resolved_state_or_accumulates(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        _write_jsonl(ledger, [
            {"source_run_id": "r1", "symbol": "A", "trade_date": "d1", "direction": "UP", "t1_ret_pct": None},
            {"source_run_id": "r1", "symbol": "A", "trade_date": "d1", "direction": "UP", "t1_ret_pct": 3.0},
        ])
        keys = _load_existing_keys(ledger)
        assert keys["r1|A|d1|UP"] is True

    def test_T06_unresolved_only_stays_false(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        _write_jsonl(ledger, [
            {"source_run_id": "r1", "symbol": "A", "trade_date": "d1", "direction": "UP", "t1_ret_pct": None},
        ])
        keys = _load_existing_keys(ledger)
        assert keys["r1|A|d1|UP"] is False


class TestConsumeNewRecordsStaleOutcomeFix:
    def _paths(self, tmp_path):
        return (
            tmp_path / "shadow.jsonl",
            tmp_path / "ledger.jsonl",
            tmp_path / "knowledge.jsonl",
            tmp_path / "state.json",
        )

    def test_T01_first_time_key_always_processed(self, tmp_path):
        shadow, ledger, knowledge, state = self._paths(tmp_path)
        _write_jsonl(shadow, [_candidate(t1_ret_pct=None)])
        new = consume_new_records(shadow, ledger, knowledge, state)
        assert len(new) == 1
        assert new[0].t1_ret_pct is None

    def test_T04_unresolved_then_resolved_is_corrected(self, tmp_path):
        shadow, ledger, knowledge, state = self._paths(tmp_path)
        _write_jsonl(shadow, [_candidate(run_id="rX", t1_ret_pct=None)])
        first = consume_new_records(shadow, ledger, knowledge, state)
        assert len(first) == 1 and first[0].t1_ret_pct is None

        # Simulate the backfill run appending a resolved duplicate with the
        # SAME deterministic run_id/symbol/trade_date/direction.
        _append_jsonl(shadow, [_candidate(run_id="rX", t1_ret_pct=4.25)])
        second = consume_new_records(shadow, ledger, knowledge, state)
        assert len(second) == 1
        assert second[0].t1_ret_pct == 4.25

        # Ledger now holds both the original unresolved row AND the
        # corrective resolved row (append-only, never rewritten).
        with open(ledger) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 2
        assert lines[0]["t1_ret_pct"] is None
        assert lines[1]["t1_ret_pct"] == 4.25

    def test_T03_unresolved_then_still_unresolved_is_skipped(self, tmp_path):
        shadow, ledger, knowledge, state = self._paths(tmp_path)
        _write_jsonl(shadow, [_candidate(run_id="rY", t1_ret_pct=None)])
        consume_new_records(shadow, ledger, knowledge, state)
        _append_jsonl(shadow, [_candidate(run_id="rY", t1_ret_pct=None)])
        second = consume_new_records(shadow, ledger, knowledge, state)
        assert second == []
        with open(ledger) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1

    def test_T02_already_resolved_never_reprocessed(self, tmp_path):
        shadow, ledger, knowledge, state = self._paths(tmp_path)
        _write_jsonl(shadow, [_candidate(run_id="rZ", t1_ret_pct=1.5)])
        consume_new_records(shadow, ledger, knowledge, state)
        _append_jsonl(shadow, [_candidate(run_id="rZ", t1_ret_pct=9.9)])
        second = consume_new_records(shadow, ledger, knowledge, state)
        assert second == []
        with open(ledger) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        assert lines[0]["t1_ret_pct"] == 1.5

    def test_T05_full_scan_rescan_picks_up_all_corrections(self, tmp_path):
        shadow, ledger, knowledge, state = self._paths(tmp_path)
        _write_jsonl(shadow, [
            _candidate(run_id="rA", symbol="A.NS", t1_ret_pct=None),
            _candidate(run_id="rB", symbol="B.NS", t1_ret_pct=None),
        ])
        consume_new_records(shadow, ledger, knowledge, state)
        _append_jsonl(shadow, [
            _candidate(run_id="rA", symbol="A.NS", t1_ret_pct=2.0),
            _candidate(run_id="rB", symbol="B.NS", t1_ret_pct=-3.0),
        ])
        second = consume_new_records(shadow, ledger, knowledge, state)
        assert {r.symbol: r.t1_ret_pct for r in second} == {"A.NS": 2.0, "B.NS": -3.0}
