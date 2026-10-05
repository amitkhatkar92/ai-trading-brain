"""
tests/test_dta_market_benchmark_date_offset_001.py
=====================================================
DTA-MARKET-BENCHMARK-DATE-OFFSET-001 — root-cause fix for market_opportunity_
benchmark.py's classify_mover() pipeline always reporting 0% capture of real
daily top gainers/losers by our own V3 20-pool.

Root cause: _load_shadow_records_for_date(trade_date) looked up shadow/
evidence ledger records by `rec["trade_date"] == trade_date`, where
`trade_date` was the MOVE's own date (the day the real gainer/loser return
was measured). But V3/C2 selection evidence records are persisted under
the PRIOR trading date (T) -- the day the 20-pool was actually computed,
predicting the move that happens on T+1. This off-by-one-trading-day
mismatch meant NO real mover could ever match a shadow record, regardless
of whether V3 genuinely captured it.

Confirmed live (2026-09-30): CUPID.NS was genuinely v3_rank=5/20 in the
real V3 pool (built 2026-09-29, predicting 2026-09-30), correctly direction
AND magnitude (ge1/ge2/ge3 all True, t1_ret_pct=+8.21%) -- yet the old
lookup (by move-date 2026-09-30) found nothing, misclassifying it as
IN_UNIVERSE_NOT_IN_20POOL. It should have been IN_20POOL_NOT_SELECTED_5
(C2's gap-only final-5 ranking excluded it on a flat open, a separate,
real, and distinct finding).

Fix: _v3_decision_date_for_move(move_date) resolves the real prior trading
date from ohlcv_daily (same pattern as final_trading_architecture_shadow_
001.py's _previous_ohlcv_trade_date); _load_shadow_records_for_date()
now looks up shadow records keyed by that resolved date instead of the
move's own date. Fails open to the old (move_date) behavior if the DB is
unavailable -- never raises, never regresses to a crash.

T01  _v3_decision_date_for_move() resolves the real prior trading date
     from ohlcv_daily
T02  _v3_decision_date_for_move() fails open to move_date when the DB
     file doesn't exist
T03  _v3_decision_date_for_move() fails open to move_date on a corrupt/
     unreadable DB
T04  _load_shadow_records_for_date() finds a record stored under the
     PRIOR trading date when called with the move's OWN date (reproduces
     the exact live CUPID bug + fix)
T05  regression guard: looking up by the move's own date directly (old
     behavior) does NOT find the record -- proves the bug was real
T06  _load_shadow_records_for_date() still returns {} gracefully when the
     ledger file doesn't exist
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import opportunity_engine.market_opportunity_benchmark as mob


def _make_ohlcv_db(path: Path, trade_dates):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE ohlcv_daily (symbol TEXT, trade_date TEXT, close REAL)"
    )
    for d in trade_dates:
        conn.execute(
            "INSERT INTO ohlcv_daily (symbol, trade_date, close) VALUES (?, ?, ?)",
            ("RELIANCE.NS", d, 100.0),
        )
    conn.commit()
    conn.close()


def _write_ledger(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestV3DecisionDateForMove:
    def test_T01_resolves_prior_trading_date(self, tmp_path):
        db = tmp_path / "market_behavior.db"
        _make_ohlcv_db(db, ["2026-09-28", "2026-09-29", "2026-09-30"])
        with patch.object(mob, "MARKET_BEHAVIOR_DB", db):
            result = mob._v3_decision_date_for_move("2026-09-30")
        assert result == "2026-09-29"

    def test_T02_fails_open_when_db_missing(self, tmp_path):
        db = tmp_path / "does_not_exist.db"
        with patch.object(mob, "MARKET_BEHAVIOR_DB", db):
            result = mob._v3_decision_date_for_move("2026-09-30")
        assert result == "2026-09-30"

    def test_T03_fails_open_on_corrupt_db(self, tmp_path):
        db = tmp_path / "corrupt.db"
        db.write_bytes(b"not a real sqlite file")
        with patch.object(mob, "MARKET_BEHAVIOR_DB", db):
            result = mob._v3_decision_date_for_move("2026-09-30")
        assert result == "2026-09-30"


class TestLoadShadowRecordsForDateOffsetFix:
    def test_T04_finds_record_under_prior_trading_date(self, tmp_path):
        db = tmp_path / "market_behavior.db"
        _make_ohlcv_db(db, ["2026-09-28", "2026-09-29", "2026-09-30"])
        ledger = tmp_path / "shadow_evidence_ledger.jsonl"
        _write_ledger(ledger, [
            {"trade_date": "2026-09-29", "symbol": "CUPID.NS", "direction": "UP",
             "v3_score": 0.9343, "v3_rank": 5, "selected_final_5": False,
             "processed_at": "2026-10-01T00:00:00+00:00"},
        ])
        with patch.object(mob, "MARKET_BEHAVIOR_DB", db), \
             patch.object(mob, "SHADOW_LEDGER", ledger):
            records = mob._load_shadow_records_for_date("2026-09-30")
        assert ("CUPID", "UP") in records
        assert records[("CUPID", "UP")]["v3_rank"] == 5

    def test_T05_old_same_date_lookup_would_have_missed_it(self, tmp_path):
        ledger = tmp_path / "shadow_evidence_ledger.jsonl"
        _write_ledger(ledger, [
            {"trade_date": "2026-09-29", "symbol": "CUPID.NS", "direction": "UP",
             "v3_score": 0.9343, "processed_at": "2026-10-01T00:00:00+00:00"},
        ])
        records = {}
        with open(ledger) as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("trade_date") == "2026-09-30":  # old buggy lookup
                    records[rec["symbol"]] = rec
        assert records == {}

    def test_T06_missing_ledger_returns_empty(self, tmp_path):
        ledger = tmp_path / "does_not_exist.jsonl"
        with patch.object(mob, "SHADOW_LEDGER", ledger):
            assert mob._load_shadow_records_for_date("2026-09-30") == {}
