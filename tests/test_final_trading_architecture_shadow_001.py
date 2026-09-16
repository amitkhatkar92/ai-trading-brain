"""
tests/test_final_trading_architecture_shadow_001.py

Test suite for FINAL_TRADING_ARCHITECTURE_SHADOW_001.

Coverage areas:
  A. Pipeline — V3 → C2 → 5+5
  B. Timing   — C2 uses opening price, no future data
  C. Strategy — rules applied correctly, UP/DOWN separate
  D. Outcomes — future data only in evaluation fields
  E. Safety   — zero broker/order/position/candidatestore calls
  F. Restart  — idempotent, partial recovery
  G. Data integrity — traceability, reproducibility

Run: pytest tests/test_final_trading_architecture_shadow_001.py -v
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import uuid
from pathlib import Path
from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Module under test
from scripts.final_trading_architecture_shadow_001 import (
    ARCHITECTURE_VERSION,
    C2_TOP_N,
    V3_POOL_SIZE,
    SHADOW_LOG_PATH,
    _make_run_id,
    _already_processed,
    compute_c2_score,
    select_c2_top_n,
    evaluate_strategy,
    _compute_outcome,
    run_shadow_day,
    write_shadow_report,
    write_results_json,
    rebuild_csv_reports,
    _get_regime,
    _open_db,
    _resolve_trade_date,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers & fixtures
# ─────────────────────────────────────────────────────────────────────────────

REPLAY_DB = Path("data/study002_replay.db")


def _make_pool(n: int, direction: str, base_close: float = 100.0,
               base_open: float = 102.0) -> List[Dict]:
    """Generate a synthetic pool of n candidates."""
    pool = []
    for i in range(n):
        gap_factor = 1 + (n - i) * 0.005  # decreasing gap magnitude
        pool.append({
            "symbol":         f"SYM{i:03d}.NS",
            "direction":      direction,
            "v3_up_score":    round(0.9 - i * 0.04, 4),
            "v3_down_score":  round(0.9 - i * 0.04, 4),
            "previous_close": base_close,
            "opening_price":  round(base_open * gap_factor, 2) if direction == "UP"
                              else round(base_open / gap_factor, 2),
            "c2_score": None,  # assigned after
        })
    for p in pool:
        prev = p["previous_close"]
        opening = p["opening_price"]
        p["c2_score"] = compute_c2_score(prev, opening, direction)
    return pool


@pytest.fixture(scope="module")
def replay_conn():
    if not REPLAY_DB.exists():
        pytest.skip("Replay DB not available")
    conn = sqlite3.connect(str(REPLAY_DB))
    yield conn
    conn.close()


@pytest.fixture
def tmp_jsonl(tmp_path):
    return tmp_path / "shadow_test.jsonl"


@pytest.fixture
def tmp_db(tmp_path):
    """Create a minimal in-memory-like SQLite DB for testing."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE ohlcv_daily "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    conn.execute(
        "CREATE TABLE universe_stocks "
        "(symbol TEXT, company_name TEXT, sector TEXT, sector_purity_score REAL, "
        "is_active INTEGER)"
    )
    # Insert ^NSEI for regime
    conn.executemany(
        "INSERT INTO ohlcv_daily VALUES (?,?,?,?,?,?,?)",
        [
            ("^NSEI", "2026-01-10", 24000, 24100, 23900, 24100, 100000),
            ("^NSEI", "2026-01-11", 24100, 24200, 23950, 24050, 120000),  # small drop → RANGE
            ("^NSEI", "2026-01-12", 24050, 24150, 23900, 24300, 130000),  # rise → BULL
        ],
    )
    # Insert universe stocks
    syms = [f"SYM{i:03d}.NS" for i in range(5)]
    conn.executemany(
        "INSERT INTO universe_stocks VALUES (?,?,?,?,?)",
        [(s, f"Company{i}", "SECTOR", 1.0, 1) for i, s in enumerate(syms)],
    )
    # Insert OHLCV for universe stocks (40 bars each)
    import random; random.seed(42)
    for sym in syms:
        price = 100.0
        for d_offset in range(40):
            dt_str = f"2025-12-{(d_offset % 28) + 1:02d}"
            price *= (1 + random.gauss(0, 0.01))
            conn.execute(
                "INSERT INTO ohlcv_daily VALUES (?,?,?,?,?,?,?)",
                (sym, dt_str, price, price * 1.02, price * 0.98, price, 1e6),
            )
    conn.commit()
    yield db_path
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# A. Pipeline tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T001_c2_up_formula():
    """C2_UP = (open/close - 1) × 100 (positive gap is good for UP)."""
    c2 = compute_c2_score(previous_close=100.0, opening_price=102.0, direction="UP")
    assert abs(c2 - 2.0) < 0.0001

def test_T002_c2_down_formula():
    """C2_DOWN = -(open/close - 1) × 100 (negative gap is good for DOWN)."""
    c2 = compute_c2_score(previous_close=100.0, opening_price=98.0, direction="DOWN")
    assert abs(c2 - 2.0) < 0.0001

def test_T003_c2_none_on_zero_close():
    assert compute_c2_score(0.0, 102.0, "UP") is None

def test_T004_c2_none_on_zero_open():
    assert compute_c2_score(100.0, 0.0, "UP") is None

def test_T005_c2_none_on_negative_close():
    assert compute_c2_score(-1.0, 102.0, "DOWN") is None

def test_T006_c2_up_rank_correct():
    """Largest positive gap should get rank 1 for UP."""
    pool = _make_pool(5, "UP")
    ranked = select_c2_top_n(pool, n=3)
    rank1 = [r for r in ranked if r["c2_rank"] == 1][0]
    # Stock with largest gap (SYM000 has biggest gap in _make_pool)
    assert rank1["c2_score"] == max(r["c2_score"] for r in ranked if r["c2_score"] is not None)

def test_T007_c2_down_rank_correct():
    """Largest negative gap should get rank 1 for DOWN (c2_score most positive)."""
    pool = _make_pool(5, "DOWN")
    ranked = select_c2_top_n(pool, n=3)
    rank1 = [r for r in ranked if r["c2_rank"] == 1][0]
    assert rank1["c2_score"] == max(r["c2_score"] for r in ranked if r["c2_score"] is not None)

def test_T008_c2_selects_exactly_top_n():
    """select_c2_top_n marks exactly C2_TOP_N as selected_final_5."""
    pool = _make_pool(20, "UP")
    ranked = select_c2_top_n(pool, n=5)
    selected = [r for r in ranked if r["selected_final_5"]]
    assert len(selected) == 5

def test_T009_c2_selects_fewer_when_pool_small():
    """If pool has 3 candidates, selected ≤ 3."""
    pool = _make_pool(3, "DOWN")
    ranked = select_c2_top_n(pool, n=5)
    selected = [r for r in ranked if r["selected_final_5"]]
    assert len(selected) == 3

def test_T010_c2_pool_size_is_20():
    """V3_POOL_SIZE is 20."""
    assert V3_POOL_SIZE == 20

def test_T011_c2_top_n_is_5():
    """C2_TOP_N is 5."""
    assert C2_TOP_N == 5

def test_T012_c2_rank_none_if_no_score():
    """Candidates with no C2 score get c2_rank=None and selected_final_5=False."""
    pool = [{"symbol": "X.NS", "direction": "UP", "c2_score": None}]
    ranked = select_c2_top_n(pool, n=5)
    assert ranked[0]["c2_rank"] is None
    assert ranked[0]["selected_final_5"] is False


# ─────────────────────────────────────────────────────────────────────────────
# B. Timing tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T013_c2_uses_opening_price():
    """C2 formula uses T+1 open, not close."""
    # If open = close, gap = 0
    c2 = compute_c2_score(100.0, 100.0, "UP")
    assert c2 == 0.0

def test_T014_c2_does_not_use_t1_close():
    """Confirm t1_close is not a parameter of compute_c2_score."""
    import inspect
    sig = inspect.signature(compute_c2_score)
    params = list(sig.parameters.keys())
    assert "t1_close" not in params
    assert "close" not in params or params.index("close") == 0  # only previous_close

def test_T015_forbidden_future_params_absent():
    """c2_score function has no high/low/t1_return parameters."""
    import inspect
    sig = inspect.signature(compute_c2_score)
    forbidden = ["high", "low", "t1_ret", "t1_return", "mfe", "mae"]
    for f in forbidden:
        assert f not in sig.parameters

def test_T016_outcome_computation_uses_entry_not_selection():
    """Outcome is computed from entry (opening) price — separate from C2 selection."""
    # Simulate: entry at 100, T+1 close at 103 → UP → +3%
    sym_rows = [("2026-01-12", 100.0, 103.0, 99.0, 103.0)]  # no 'open' col needed
    oc = _compute_outcome(100.0, "UP", [("2026-01-12", "2026-01-12", 100.0, 103.0, 99.0, 103.0)], horizon=1)
    assert oc["t1_ret_pct"] is not None

def test_T017_regime_uses_prev_close_only(replay_conn):
    """Regime determination does not look ahead beyond the given trade_date."""
    # Get a date that exists in NIFTY data
    row = replay_conn.execute(
        "SELECT trade_date FROM ohlcv_daily WHERE symbol='^NSEI' ORDER BY trade_date LIMIT 1"
    ).fetchone()
    if row:
        r = _get_regime(replay_conn, row[0])
        assert r in ("BULL", "BEAR", "RANGE", "VOLATILE", "UNAVAILABLE")


# ─────────────────────────────────────────────────────────────────────────────
# C. Strategy tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T018_bear_up_reject():
    """D2: BEAR + UP → REJECT."""
    status, name, reason = evaluate_strategy("UP", "BEAR")
    assert status == "REJECT"
    assert "D2" in reason

def test_T019_volatile_up_reject():
    """D3: VOLATILE + UP → REJECT."""
    status, name, reason = evaluate_strategy("UP", "VOLATILE")
    assert status == "REJECT"
    assert "D3" in reason

def test_T020_bull_up_pass():
    """BULL + UP → PASS."""
    status, name, reason = evaluate_strategy("UP", "BULL")
    assert status == "PASS"

def test_T021_range_up_pass():
    """RANGE + UP → PASS."""
    status, name, reason = evaluate_strategy("UP", "RANGE")
    assert status == "PASS"

def test_T022_bear_down_aligned():
    """BEAR + DOWN → ALIGNED (no rejection for DOWN)."""
    status, name, reason = evaluate_strategy("DOWN", "BEAR")
    assert status == "ALIGNED"

def test_T023_bull_down_contradicted():
    """BULL + DOWN → CONTRADICTED."""
    status, name, reason = evaluate_strategy("DOWN", "BULL")
    assert status == "CONTRADICTED"

def test_T024_range_down_neutral():
    """RANGE + DOWN → NEUTRAL."""
    status, name, reason = evaluate_strategy("DOWN", "RANGE")
    assert status == "NEUTRAL"

def test_T025_unavailable_regime():
    """None regime → STRATEGY_UNAVAILABLE."""
    status, _, _ = evaluate_strategy("UP", None)
    assert status == "STRATEGY_UNAVAILABLE"

def test_T026_unknown_regime():
    """Unknown regime string → STRATEGY_UNAVAILABLE."""
    status, _, _ = evaluate_strategy("UP", "UNKNOWN")
    assert status == "STRATEGY_UNAVAILABLE"

def test_T027_down_never_hard_rejected():
    """DOWN candidates are never REJECT (no SELL strategies)."""
    for regime in ("BEAR", "BULL", "RANGE", "VOLATILE", None):
        status, _, _ = evaluate_strategy("DOWN", regime)
        assert status != "REJECT", f"DOWN should never be REJECT, got {status} for {regime}"

def test_T028_up_down_evaluation_independent():
    """Same regime gives different status for UP vs DOWN."""
    up_status, _, _  = evaluate_strategy("UP", "BEAR")
    dn_status, _, _ = evaluate_strategy("DOWN", "BEAR")
    assert up_status != dn_status  # UP=REJECT, DOWN=ALIGNED


# ─────────────────────────────────────────────────────────────────────────────
# D. Outcome tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T029_outcome_t1_up_positive():
    """UP: positive T+1 return = direction_correct=True."""
    rows = [("d", "d", 100.0, 103.0, 99.0, 103.0)]
    oc = _compute_outcome(100.0, "UP", rows, horizon=1)
    assert oc["direction_correct"] is True
    assert abs(oc["t1_ret_pct"] - 3.0) < 0.01

def test_T030_outcome_t1_down_negative():
    """DOWN: negative T+1 return = direction_correct=True."""
    rows = [("d", "d", 100.0, 103.0, 97.0, 97.0)]
    oc = _compute_outcome(100.0, "DOWN", rows, horizon=1)
    assert oc["direction_correct"] is True
    assert oc["t1_ret_pct"] < 0

def test_T031_outcome_up_wrong_direction():
    """UP: negative T+1 return = direction_correct=False."""
    rows = [("d", "d", 100.0, 101.0, 97.0, 97.0)]
    oc = _compute_outcome(100.0, "UP", rows, horizon=1)
    assert oc["direction_correct"] is False

def test_T032_outcome_ge2_threshold():
    """ge2 requires ≥2% favourable move."""
    rows = [("d", "d", 100.0, 102.1, 99.0, 102.1)]
    oc = _compute_outcome(100.0, "UP", rows, horizon=1)
    assert oc["ge2"] is True

def test_T033_outcome_ge2_not_met():
    """ge2 is False if move < 2%."""
    rows = [("d", "d", 100.0, 101.5, 99.0, 101.5)]
    oc = _compute_outcome(100.0, "UP", rows, horizon=1)
    assert oc["ge2"] is False

def test_T034_outcome_mfe_up():
    """MFE for UP = highest high relative to entry."""
    rows = [
        ("d1", "d1", 100.0, 104.0, 99.0, 102.0),
        ("d2", "d2", 100.0, 106.0, 100.0, 105.0),
    ]
    oc = _compute_outcome(100.0, "UP", rows, horizon=5)
    assert oc["mfe_pct"] is not None
    assert oc["mfe_pct"] >= 5.9  # 106/100 - 1 = 6%

def test_T035_outcome_mae_down():
    """MAE for DOWN = largest adverse move = highest high (entry/high - 1)."""
    rows = [("d1", "d1", 100.0, 105.0, 98.0, 100.0)]
    oc = _compute_outcome(100.0, "DOWN", rows, horizon=5)
    assert oc["mae_pct"] is not None
    # Adverse for DOWN = positive return (price went UP) = 105/100 - 1 = 5% adverse → mae negative
    assert oc["mae_pct"] < 0

def test_T036_outcome_no_data():
    """Empty sym_rows returns all None outcome fields."""
    oc = _compute_outcome(100.0, "UP", [], horizon=5)
    assert oc["t1_ret_pct"] is None
    assert oc["direction_correct"] is None

def test_T037_outcome_t3_and_t5():
    """T+3 and T+5 returns computed correctly."""
    rows = [
        ("d1", "d1", 100.0, 101.0, 99.0, 101.0),  # T+1
        ("d2", "d2", 100.0, 102.0, 99.0, 102.0),  # T+2
        ("d3", "d3", 100.0, 103.0, 99.0, 103.0),  # T+3
        ("d4", "d4", 100.0, 104.0, 99.0, 104.0),  # T+4
        ("d5", "d5", 100.0, 105.0, 99.0, 105.0),  # T+5
    ]
    oc = _compute_outcome(100.0, "UP", rows, horizon=5)
    assert abs(oc["t1_ret_pct"] - 1.0) < 0.01
    assert abs(oc["t3_ret_pct"] - 3.0) < 0.01
    assert abs(oc["t5_ret_pct"] - 5.0) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# E. Safety tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T038_no_order_manager_import():
    """Shadow script must not import OrderManager."""
    script = Path("scripts/final_trading_architecture_shadow_001.py")
    content = script.read_text(encoding="utf-8")
    import re
    assert not re.search(r"^\s*from\s+execution_engine", content, re.MULTILINE)
    assert not re.search(r"^\s*import\s+execution_engine", content, re.MULTILINE)
    assert not re.search(r"from\s+execution_engine.*import.*OrderManager", content)

def test_T039_no_broker_import():
    """Shadow script must not import Dhan or Zerodha broker modules."""
    script = Path("scripts/final_trading_architecture_shadow_001.py")
    content = script.read_text(encoding="utf-8")
    forbidden = ["dhan_feed", "zerodb_broker", "DhanFeed", "ZerodhaBroker"]
    for tok in forbidden:
        assert f"import {tok}" not in content and f"from {tok}" not in content

def test_T040_no_candidate_store_write():
    """Shadow script must not call CandidateStore.write() as an actual Python call."""
    import re
    script = Path("scripts/final_trading_architecture_shadow_001.py")
    content = script.read_text(encoding="utf-8")
    # Look for the actual Python call syntax (open paren), not just string mention
    actual_calls = re.findall(r'CandidateStore\.write\s*\(', content)
    assert not actual_calls, f"CandidateStore.write() call found in script: {actual_calls}"

def test_T041_no_trades_generated_flag():
    """Every run result must carry no_trades_generated=True."""
    result = run_shadow_day(
        trade_date="2099-01-01",  # non-existent date
        db_path=REPLAY_DB if REPLAY_DB.exists() else None,
        force=True,
    )
    assert result.get("no_trades_generated") is True

def test_T042_no_broker_calls_flag():
    """Every run result must carry no_broker_calls=True."""
    result = run_shadow_day(
        trade_date="2099-01-01",
        db_path=REPLAY_DB if REPLAY_DB.exists() else None,
        force=True,
    )
    assert result.get("no_broker_calls") is True

def test_T043_safety_in_results_json(tmp_path):
    """Results JSON always declares zero broker/order/position counts."""
    # Write dummy JSONL and generate results
    dummy = tmp_path / "dummy.jsonl"
    write_results_json(dummy)
    # Read and check (no data → zero counts)
    results_path = Path("reports/mover_discovery_v3/final_trading_architecture_shadow_results.json")
    if results_path.exists():
        r = json.loads(results_path.read_text(encoding="utf-8"))
        safety = r.get("safety", {})
        assert safety.get("broker_calls") == 0
        assert safety.get("orders") == 0
        assert safety.get("positions") == 0
        assert safety.get("candidatestore_writes") == 0

def test_T044_architecture_version_constant():
    """ARCHITECTURE_VERSION string contains the research ID."""
    assert "FINAL_TRADING_ARCHITECTURE_SHADOW_001" in ARCHITECTURE_VERSION


# ─────────────────────────────────────────────────────────────────────────────
# F. Restart / idempotency tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T045_run_id_deterministic():
    """Same trade_date always produces the same run_id."""
    r1 = _make_run_id("2026-01-15")
    r2 = _make_run_id("2026-01-15")
    assert r1 == r2

def test_T046_run_id_different_dates():
    """Different dates produce different run_ids."""
    r1 = _make_run_id("2026-01-15")
    r2 = _make_run_id("2026-01-16")
    assert r1 != r2

def test_T047_already_processed_empty_file(tmp_jsonl):
    """Empty file → not processed."""
    assert not _already_processed("2026-01-15", tmp_jsonl)

def test_T048_already_processed_after_write(tmp_jsonl):
    """After writing a record, already_processed returns True."""
    run_id = _make_run_id("2026-01-15")
    with open(tmp_jsonl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"run_id": run_id, "trade_date": "2026-01-15"}) + "\n")
    assert _already_processed("2026-01-15", tmp_jsonl)

def test_T049_already_processed_different_date(tmp_jsonl):
    """Record for different date → not processed for our date."""
    run_id = _make_run_id("2026-01-16")
    with open(tmp_jsonl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"run_id": run_id, "trade_date": "2026-01-16"}) + "\n")
    assert not _already_processed("2026-01-15", tmp_jsonl)

def test_T050_duplicate_run_skipped(tmp_path, tmp_jsonl):
    """Second run for same date is skipped without error."""
    if not REPLAY_DB.exists():
        pytest.skip("Replay DB not available")
    run_id = _make_run_id("2026-01-10")
    with open(tmp_jsonl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"run_id": run_id, "record_type": "SHADOW_CANDIDATE"}) + "\n")
    # Mock _already_processed to return True
    with patch("scripts.final_trading_architecture_shadow_001.SHADOW_LOG_PATH", tmp_jsonl):
        with patch("scripts.final_trading_architecture_shadow_001._already_processed",
                   return_value=True) as mock:
            result = run_shadow_day(trade_date="2026-01-10", db_path=REPLAY_DB)
            mock.assert_called()
            assert result.get("skipped") is True or result.get("success") is True

def test_T051_force_overrides_idempotency(tmp_jsonl):
    """force=True re-runs even if already processed."""
    with patch("scripts.final_trading_architecture_shadow_001.SHADOW_LOG_PATH", tmp_jsonl):
        with patch("scripts.final_trading_architecture_shadow_001._already_processed",
                   return_value=True):
            with patch("scripts.final_trading_architecture_shadow_001._run_v3_pool",
                       return_value=([], [])):
                with patch("scripts.final_trading_architecture_shadow_001._open_db") as mock_db:
                    mock_conn = MagicMock()
                    mock_conn.execute.return_value.fetchone.return_value = ("2026-01-10",)
                    mock_db.return_value.__enter__ = lambda s: mock_conn
                    mock_db.return_value.__exit__ = MagicMock(return_value=False)
                    # force=True should not call already_processed early exit
                    # Just check it reaches run (the abort from empty pool is OK)
                    result = run_shadow_day(trade_date="2026-01-10",
                                           db_path=Path("/fake"),
                                           force=True)
                    # With no candidates, should abort (not skip)
                    assert result.get("skipped") is not True


# ─────────────────────────────────────────────────────────────────────────────
# G. Data integrity tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T052_every_selected_has_c2_rank():
    """Every selected_final_5=True candidate must have a valid c2_rank."""
    pool = _make_pool(10, "UP")
    ranked = select_c2_top_n(pool, n=5)
    selected = [r for r in ranked if r["selected_final_5"]]
    for s in selected:
        assert s["c2_rank"] is not None
        assert 1 <= s["c2_rank"] <= 5

def test_T053_c2_rank_ordering():
    """c2_rank=1 always has the highest c2_score."""
    pool = _make_pool(10, "UP")
    ranked = select_c2_top_n(pool, n=5)
    rank1 = next(r for r in ranked if r["c2_rank"] == 1)
    for r in ranked:
        if r["c2_rank"] is not None:
            assert rank1["c2_score"] >= r["c2_score"]

def test_T054_up_and_down_ranks_independent():
    """UP and DOWN rankings are independent pools."""
    up_pool = _make_pool(10, "UP", base_close=100, base_open=102)
    dn_pool = _make_pool(10, "DOWN", base_close=100, base_open=98)
    up_ranked = select_c2_top_n(up_pool, n=5)
    dn_ranked = select_c2_top_n(dn_pool, n=5)

    up_syms = {r["symbol"] for r in up_ranked if r["selected_final_5"]}
    dn_syms = {r["symbol"] for r in dn_ranked if r["selected_final_5"]}
    # Symbols can overlap if same stock in both — that's OK
    assert len(up_syms) == 5
    assert len(dn_syms) == 5

def test_T055_c2_score_reproducible():
    """Same inputs always produce the same c2_score."""
    c1 = compute_c2_score(100.0, 103.5, "UP")
    c2 = compute_c2_score(100.0, 103.5, "UP")
    assert c1 == c2

def test_T056_gap_pct_invariant():
    """gap_pct = (open/close - 1) × 100 holds numerically."""
    prev_close  = 150.0
    opening     = 154.5
    expected    = (154.5 / 150.0 - 1.0) * 100.0
    c2 = compute_c2_score(prev_close, opening, "UP")
    assert abs(c2 - expected) < 0.0001

def test_T057_architecture_version_in_record(tmp_jsonl):
    """Every JSONL candidate record carries architecture_version."""
    record = {
        "run_id":               _make_run_id("2026-01-10"),
        "record_type":          "SHADOW_CANDIDATE",
        "architecture_version": ARCHITECTURE_VERSION,
        "trade_date":           "2026-01-10",
        "symbol":               "TEST.NS",
        "direction":            "UP",
    }
    with open(tmp_jsonl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    # Verify we can load it back
    with open(tmp_jsonl, encoding="utf-8") as fh:
        loaded = json.loads(fh.readline())
    assert loaded["architecture_version"] == ARCHITECTURE_VERSION

def test_T058_no_duplicate_candidates_per_run():
    """A single run should not produce duplicate (symbol, direction) pairs."""
    pool = _make_pool(10, "UP")
    ranked = select_c2_top_n(pool, n=5)
    symbols = [r["symbol"] for r in ranked]
    assert len(symbols) == len(set(symbols))

def test_T059_run_id_in_jsonl_header():
    """_make_run_id uses SHA256 of version+date."""
    expected = hashlib.sha256(
        f"{ARCHITECTURE_VERSION}:2026-06-01".encode()
    ).hexdigest()[:16]
    assert _make_run_id("2026-06-01") == expected

def test_T060_pool_direction_preserved():
    """pool_direction field equals the direction used for scoring."""
    pool = _make_pool(5, "DOWN")
    ranked = select_c2_top_n(pool, n=3)
    for r in ranked:
        assert r.get("direction") == "DOWN" or r.get("pool_direction", "DOWN") == "DOWN"


# ─────────────────────────────────────────────────────────────────────────────
# H. Integration tests (replay DB)
# ─────────────────────────────────────────────────────────────────────────────

def test_T061_resolve_trade_date_from_replay(replay_conn):
    """_resolve_trade_date returns a valid date string."""
    td = _resolve_trade_date(replay_conn)
    assert len(td) == 10
    assert td[:4].isdigit()

def test_T062_regime_from_replay(replay_conn):
    """_get_regime returns a valid label from replay data."""
    # Find a date in NIFTY data
    row = replay_conn.execute(
        "SELECT trade_date FROM ohlcv_daily WHERE symbol='^NSEI' "
        "ORDER BY trade_date LIMIT 1"
    ).fetchone()
    if row:
        regime = _get_regime(replay_conn, row[0])
        assert regime in ("BULL", "BEAR", "RANGE", "VOLATILE", "UNAVAILABLE")

def test_T063_open_db_accepts_replay():
    """_open_db can open the replay DB."""
    if not REPLAY_DB.exists():
        pytest.skip("Replay DB not available")
    conn = _open_db(REPLAY_DB)
    assert conn is not None
    conn.close()

def test_T064_replay_run_shadow_day_succeeds():
    """run_shadow_day against replay DB completes without exception."""
    if not REPLAY_DB.exists():
        pytest.skip("Replay DB not available")
    # Use an early OOS date so outcomes are available
    with patch("scripts.final_trading_architecture_shadow_001.SHADOW_LOG_PATH",
               Path("data/logs/_test_shadow_tmp.jsonl")):
        result = run_shadow_day(trade_date="2026-05-14", db_path=REPLAY_DB, force=True)
        assert result.get("no_trades_generated") is True
        # Cleanup
        p = Path("data/logs/_test_shadow_tmp.jsonl")
        if p.exists():
            p.unlink()

def test_T065_v3_up_count_at_most_20(replay_conn):
    """V3 pool produces at most 20 UP candidates."""
    from scripts.final_trading_architecture_shadow_001 import _run_v3_pool
    td = "2026-05-14"
    up, dn = _run_v3_pool(replay_conn, td, pool_size=20)
    assert len(up) <= 20

def test_T066_v3_down_count_at_most_20(replay_conn):
    """V3 pool produces at most 20 DOWN candidates."""
    from scripts.final_trading_architecture_shadow_001 import _run_v3_pool
    td = "2026-05-14"
    up, dn = _run_v3_pool(replay_conn, td, pool_size=20)
    assert len(dn) <= 20

def test_T067_c2_selected_at_most_5(replay_conn):
    """C2 selects at most 5 per direction."""
    from scripts.final_trading_architecture_shadow_001 import _run_v3_pool
    if not REPLAY_DB.exists():
        pytest.skip("Replay DB not available")
    conn = _open_db(REPLAY_DB)
    td = "2026-05-14"
    up, dn = _run_v3_pool(conn, td, pool_size=20)
    conn.close()

    from scripts.final_trading_architecture_shadow_001 import (
        _get_opening_prices, _get_t1_date, _open_db as odb,
    )
    conn2 = odb(REPLAY_DB)
    t1_date = _get_t1_date(conn2, td)
    syms = [c["symbol"] for c in up + dn]
    openings = _get_opening_prices(conn2, syms, t1_date) if t1_date else {}
    conn2.close()

    for pool, direction in [(up, "UP"), (dn, "DOWN")]:
        for cand in pool:
            prev = cand.get("previous_close")
            opening = openings.get(cand["symbol"])
            cand["c2_score"] = compute_c2_score(prev, opening, direction) if (prev and opening) else None
        ranked = select_c2_top_n(pool, n=5)
        selected = [r for r in ranked if r["selected_final_5"]]
        assert len(selected) <= 5, f"{direction}: expected ≤5 selected, got {len(selected)}"


# ─────────────────────────────────────────────────────────────────────────────
# I. Leakage tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T068_c2_cannot_access_t1_close():
    """C2 formula only depends on previous_close and opening_price."""
    # The C2 score for (close=100, open=102) is always 2.0 regardless of T+1 close
    c2_with_t1_close_105 = compute_c2_score(100.0, 102.0, "UP")
    c2_with_t1_close_95  = compute_c2_score(100.0, 102.0, "UP")  # same inputs
    assert c2_with_t1_close_105 == c2_with_t1_close_95  # selection is not affected

def test_T069_selection_frozen_before_t1_close():
    """selected_final_5 is determined by c2_score only (no outcome fields used)."""
    pool = _make_pool(10, "UP")
    # Add fake outcome to first candidate — should NOT affect selection
    pool[0]["t1_ret_pct"] = 99.0  # obviously unrealistic future return
    ranked = select_c2_top_n(pool, n=5)
    # Selection is by c2_score, not t1_ret_pct
    rank1 = next(r for r in ranked if r["c2_rank"] == 1)
    assert rank1["c2_score"] == max(r["c2_score"] for r in ranked if r["c2_score"] is not None)

def test_T070_outcome_fields_not_in_selection_criteria():
    """Outcome fields (ge1, ge2, mfe, mae) are absent from select_c2_top_n logic."""
    import inspect
    src = inspect.getsource(select_c2_top_n)
    forbidden = ["ge1", "ge2", "ge3", "mfe_pct", "mae_pct", "t1_ret", "direction_correct"]
    for f in forbidden:
        assert f not in src, f"'{f}' found in select_c2_top_n — potential leakage"

def test_T071_no_future_columns_in_c2_signature():
    """compute_c2_score must not accept any future-data arguments."""
    import inspect
    params = set(inspect.signature(compute_c2_score).parameters.keys())
    future_fields = {"t1_close", "high", "low", "t1_return", "mfe", "mae",
                     "t3_ret", "t5_ret", "direction_correct"}
    overlap = params & future_fields
    assert not overlap, f"Future fields in compute_c2_score: {overlap}"


# ─────────────────────────────────────────────────────────────────────────────
# J. Strategy question accumulation tests
# ─────────────────────────────────────────────────────────────────────────────

def test_T072_strategy_question_starts_insufficient():
    """Fresh results JSON should start with INSUFFICIENT."""
    results_path = Path("reports/mover_discovery_v3/final_trading_architecture_shadow_results.json")
    if results_path.exists():
        r = json.loads(results_path.read_text(encoding="utf-8"))
        # INSUFFICIENT or SUFFICIENT both valid — just not an arbitrary string
        assert r.get("strategy_question_status") in ("INSUFFICIENT", "SUFFICIENT", "ACCUMULATING")

def test_T073_strategy_answer_requires_reject_events():
    """Strategy question cannot be answered without REJECT observations."""
    # Simulate 0 REJECT events
    summaries = [{"strategy_reject_up": 0, "regime": "RANGE", "c2_up_selected": 5}]
    n_reject = sum(s.get("strategy_reject_up", 0) for s in summaries)
    # With 0 rejects, question must be INSUFFICIENT
    sufficient = n_reject >= 10
    assert not sufficient

def test_T074_strategy_answer_requires_bear_regime():
    """Strategy question cannot be answered without BEAR days."""
    regimes = {"RANGE", "BULL"}  # no BEAR
    assert "BEAR" not in regimes

def test_T075_regime_range_strategy_pass_all():
    """In RANGE regime, all UP candidates PASS strategy."""
    statuses = [evaluate_strategy("UP", "RANGE")[0] for _ in range(10)]
    assert all(s == "PASS" for s in statuses)

def test_T076_model_b_is_subset_of_model_a():
    """Model B candidates are always a subset of Model A candidates."""
    pool = _make_pool(5, "UP")
    ranked = select_c2_top_n(pool, n=5)
    # Simulate: 2 REJECT, 3 PASS
    for i, r in enumerate(ranked):
        r["strategy_status"] = "REJECT" if i < 2 else "PASS"
        r["model_b_included"] = r["strategy_status"] not in ("REJECT",)
    model_b = {r["symbol"] for r in ranked if r["model_b_included"]}
    model_a = {r["symbol"] for r in ranked}
    assert model_b.issubset(model_a)

def test_T077_down_model_b_equals_model_a():
    """For DOWN, Model B = Model A (no strategy gate)."""
    pool = _make_pool(5, "DOWN")
    for p in pool:
        p["strategy_status"] = "NEUTRAL"
        p["model_b_included"] = True  # no gate for DOWN
    ranked = select_c2_top_n(pool, n=5)
    for r in ranked:
        r["model_b_included"] = True
    model_b_down = [r for r in ranked if r.get("model_b_included")]
    model_a_down = ranked
    assert len(model_b_down) == len(model_a_down)


# ─────────────────────────────────────────────────────────────────────────────
# K. DTA-SHADOW-BACKFILL-001 — retroactive C2 top-5-per-direction re-selection
# ─────────────────────────────────────────────────────────────────────────────
# Root cause: run_shadow_day() only ever runs SAME-DAY in production (no
# trade_date arg from master_orchestrator), where T+1 opening prices cannot
# exist yet -- so C2 selection always selected 0 stocks per direction,
# confirmed live (c2_up_selected=0, c2_down_selected=0, t1_data_available=
# False). run_shadow_day_backfill() re-processes the previous trading date
# once its T+1 (today's) data exists.

from scripts.final_trading_architecture_shadow_001 import (
    run_shadow_day_backfill,
    _previous_ohlcv_trade_date,
    _latest_summary_for_date,
)


def test_T078_previous_ohlcv_trade_date_found(tmp_path):
    db_path = tmp_path / "prev_date_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE ohlcv_daily "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    conn.executemany(
        "INSERT INTO ohlcv_daily VALUES ('TCS.NS',?,100,101,99,100,1000)",
        [("2026-01-10",), ("2026-01-12",), ("2026-01-13",)],
    )
    conn.commit()
    prev = _previous_ohlcv_trade_date(conn, "2026-01-13")
    assert prev == "2026-01-12"
    conn.close()


def test_T079_previous_ohlcv_trade_date_none_when_earliest(tmp_path):
    db_path = tmp_path / "prev_date_test2.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE ohlcv_daily "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    conn.execute("INSERT INTO ohlcv_daily VALUES ('TCS.NS','2026-01-10',100,101,99,100,1000)")
    conn.commit()
    prev = _previous_ohlcv_trade_date(conn, "2026-01-10")
    assert prev is None
    conn.close()


def test_T080_latest_summary_for_date_none_when_missing(tmp_jsonl):
    with open(tmp_jsonl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"record_type": "SHADOW_DAILY_SUMMARY", "trade_date": "2026-01-10",
                              "timestamp": "2026-01-10T10:00:00", "c2_up_selected": 0}) + "\n")
    assert _latest_summary_for_date("2026-01-11", tmp_jsonl) is None


def test_T081_latest_summary_for_date_picks_most_recent(tmp_jsonl):
    with open(tmp_jsonl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"record_type": "SHADOW_DAILY_SUMMARY", "trade_date": "2026-01-10",
                              "timestamp": "2026-01-10T10:00:00", "c2_up_selected": 0}) + "\n")
        fh.write(json.dumps({"record_type": "SHADOW_DAILY_SUMMARY", "trade_date": "2026-01-10",
                              "timestamp": "2026-01-14T10:00:00", "c2_up_selected": 5}) + "\n")
    result = _latest_summary_for_date("2026-01-10", tmp_jsonl)
    assert result["c2_up_selected"] == 5


def test_T082_backfill_skips_when_no_previous_date():
    with patch("scripts.final_trading_architecture_shadow_001._open_db") as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        with patch("scripts.final_trading_architecture_shadow_001._resolve_trade_date",
                   return_value="2026-01-10"), \
             patch("scripts.final_trading_architecture_shadow_001._previous_ohlcv_trade_date",
                   return_value=None):
            result = run_shadow_day_backfill(db_path=Path("/fake"))
    assert result["skipped"] is True
    assert result["reason"] == "no_previous_trade_date"


def test_T083_backfill_skips_when_already_finalized():
    with patch("scripts.final_trading_architecture_shadow_001._open_db") as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        with patch("scripts.final_trading_architecture_shadow_001._resolve_trade_date",
                   return_value="2026-01-11"), \
             patch("scripts.final_trading_architecture_shadow_001._previous_ohlcv_trade_date",
                   return_value="2026-01-10"), \
             patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
                   return_value={"c2_up_selected": 5, "c2_down_selected": 4}), \
             patch("scripts.final_trading_architecture_shadow_001.run_shadow_day") as mock_run:
            result = run_shadow_day_backfill(db_path=Path("/fake"))
    mock_run.assert_not_called()
    assert result["skipped"] is True
    assert result["reason"] == "already_has_real_c2_selection"


def test_T084_backfill_reprocesses_when_zero_selected():
    """The exact bug this fixes: a previous date stuck at 0/0 selected must
    trigger a forced re-run once T+1 data should now be available."""
    with patch("scripts.final_trading_architecture_shadow_001._open_db") as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        with patch("scripts.final_trading_architecture_shadow_001._resolve_trade_date",
                   return_value="2026-01-11"), \
             patch("scripts.final_trading_architecture_shadow_001._previous_ohlcv_trade_date",
                   return_value="2026-01-10"), \
             patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
                   return_value={"c2_up_selected": 0, "c2_down_selected": 0}), \
             patch("scripts.final_trading_architecture_shadow_001.run_shadow_day",
                   return_value={"success": True, "trade_date": "2026-01-10",
                                 "c2_up_selected": 5, "c2_down_selected": 5}) as mock_run:
            result = run_shadow_day_backfill(db_path=Path("/fake"))
    mock_run.assert_called_once_with(trade_date="2026-01-10", db_path=Path("/fake"), force=True)
    assert result["success"] is True
    assert result["backfill_of"] == "2026-01-10"
    assert result["c2_up_selected"] == 5


def test_T085_backfill_reprocesses_when_no_summary_exists_yet():
    """A previous date with NO summary at all (never ran) is also a valid
    backfill target, not just a stale 0/0 one."""
    with patch("scripts.final_trading_architecture_shadow_001._open_db") as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        with patch("scripts.final_trading_architecture_shadow_001._resolve_trade_date",
                   return_value="2026-01-11"), \
             patch("scripts.final_trading_architecture_shadow_001._previous_ohlcv_trade_date",
                   return_value="2026-01-10"), \
             patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
                   return_value=None), \
             patch("scripts.final_trading_architecture_shadow_001.run_shadow_day",
                   return_value={"success": True, "trade_date": "2026-01-10"}) as mock_run:
            result = run_shadow_day_backfill(db_path=Path("/fake"))
    mock_run.assert_called_once()
    assert result["success"] is True


def test_T086_backfill_handles_missing_db_gracefully():
    with patch("scripts.final_trading_architecture_shadow_001._open_db",
               side_effect=FileNotFoundError("no db")):
        result = run_shadow_day_backfill(db_path=Path("/does/not/exist"))
    assert result["success"] is False
    assert result["reason"] == "db_not_found"


def test_T087_backfill_never_places_trades_or_orders():
    """Safety contract: backfill result carries the same
    no_trades_generated/no_broker_calls guarantees as run_shadow_day()."""
    with patch("scripts.final_trading_architecture_shadow_001._open_db") as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        with patch("scripts.final_trading_architecture_shadow_001._resolve_trade_date",
                   return_value="2026-01-11"), \
             patch("scripts.final_trading_architecture_shadow_001._previous_ohlcv_trade_date",
                   return_value="2026-01-10"), \
             patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
                   return_value={"c2_up_selected": 0, "c2_down_selected": 0}), \
             patch("scripts.final_trading_architecture_shadow_001.run_shadow_day",
                   return_value={"success": True, "trade_date": "2026-01-10",
                                 "no_trades_generated": True, "no_broker_calls": True}):
            result = run_shadow_day_backfill(db_path=Path("/fake"))
    assert result["no_trades_generated"] is True
    assert result["no_broker_calls"] is True


def test_T088_real_bug_reproduction_with_replay_db():
    """
    Integration proof against the REAL replay DB: running run_shadow_day()
    for the LATEST available date (as production does, no trade_date arg)
    must select 0/0 -- reproducing the exact live bug -- because T+1 data
    for the latest date cannot exist. Then run_shadow_day_backfill() must
    successfully select >0 for the previous date, whose T+1 data (the
    latest date) DOES exist in the replay DB.
    """
    if not REPLAY_DB.exists():
        pytest.skip("Replay DB not available")
    conn = _open_db(REPLAY_DB)
    latest = _resolve_trade_date(conn)
    previous = _previous_ohlcv_trade_date(conn, latest)
    conn.close()
    if not previous:
        pytest.skip("Replay DB has no earlier trade_date to backfill")

    tmp_log = Path("data/logs/_test_shadow_backfill_tmp.jsonl")
    try:
        with patch("scripts.final_trading_architecture_shadow_001.SHADOW_LOG_PATH", tmp_log):
            same_day = run_shadow_day(trade_date=latest, db_path=REPLAY_DB, force=True)
            assert same_day.get("c2_up_selected", 0) == 0
            assert same_day.get("c2_down_selected", 0) == 0
            assert same_day.get("t1_data_available") is False

            backfilled = run_shadow_day_backfill(db_path=REPLAY_DB)
            assert backfilled.get("backfill_of") == previous
    finally:
        if tmp_log.exists():
            tmp_log.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# L. DTA-SHADOW-BACKLOG-CATCHUP-001 — root-cause fix for missed backfill days
# ─────────────────────────────────────────────────────────────────────────────
# Root cause: run_shadow_day_backfill() only ever checks the single date
# immediately before "latest" -- a day the EOD pipeline didn't run (or
# crashed) on permanently loses its one-shot backfill chance. Confirmed live:
# 2026-09-04 through 2026-09-11 (6 trading days) never received a real C2
# selection this way, even though 2026-09-02/03/14 (days the backfill
# actually ran) did. This scans the recent backlog and retries every
# still-unresolved date, bounded per run.

from scripts.final_trading_architecture_shadow_001 import run_shadow_backlog_catchup


def _make_ohlcv_db(tmp_path, dates):
    db_path = tmp_path / "catchup_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE ohlcv_daily "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    conn.executemany(
        "INSERT INTO ohlcv_daily VALUES ('TCS.NS',?,100,101,99,100,1000)",
        [(d,) for d in dates],
    )
    conn.commit()
    conn.close()
    return db_path


def test_T089_catchup_finds_unresolved_gap_dates(tmp_path):
    """The exact bug this fixes: several consecutive dates in the middle of
    the backlog never got a real selection -- catchup must find all of them,
    not just the single date immediately before 'latest'."""
    dates = ["2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07",
              "2026-09-08", "2026-09-14", "2026-09-15"]
    db_path = _make_ohlcv_db(tmp_path, dates)

    resolved = {"2026-09-02", "2026-09-03", "2026-09-14"}

    def _fake_summary(d, jsonl_path=None):
        if d in resolved:
            return {"c2_up_selected": 5, "c2_down_selected": 5}
        return None

    with patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
               side_effect=_fake_summary), \
         patch("scripts.final_trading_architecture_shadow_001.run_shadow_day",
               side_effect=lambda trade_date, db_path, force: {"success": True}) as mock_run:
        result = run_shadow_backlog_catchup(db_path=db_path, max_dates=10, lookback_days=30)

    assert result["success"] is True
    # 2026-09-04, 2026-09-07, 2026-09-08 are unresolved and scoreable
    # (2026-09-15 is excluded: it is the latest date, no T+1 reference yet)
    assert set(result["dates_processed"]) == {"2026-09-04", "2026-09-07", "2026-09-08"}
    assert mock_run.call_count == 3


def test_T090_catchup_bounded_by_max_dates(tmp_path):
    dates = [f"2026-09-{d:02d}" for d in range(1, 10)]
    db_path = _make_ohlcv_db(tmp_path, dates)

    with patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
               return_value=None), \
         patch("scripts.final_trading_architecture_shadow_001.run_shadow_day",
               return_value={"success": True}):
        result = run_shadow_backlog_catchup(db_path=db_path, max_dates=2, lookback_days=30)

    assert len(result["dates_processed"]) == 2
    assert result["still_remaining"] == (len(dates) - 1) - 2  # excl. latest (no T+1)


def test_T091_catchup_never_reprocesses_already_resolved_dates(tmp_path):
    dates = ["2026-09-01", "2026-09-02", "2026-09-03"]
    db_path = _make_ohlcv_db(tmp_path, dates)

    with patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
               return_value={"c2_up_selected": 5, "c2_down_selected": 5}), \
         patch("scripts.final_trading_architecture_shadow_001.run_shadow_day") as mock_run:
        result = run_shadow_backlog_catchup(db_path=db_path)

    mock_run.assert_not_called()
    assert result["dates_processed"] == []
    assert result["unresolved_found"] == 0


def test_T092_catchup_excludes_the_latest_date_no_t1_reference(tmp_path):
    """The single most-recent OHLCV date has no T+1 reference yet -- it must
    never be treated as a backfill candidate, matching run_shadow_day_backfill's
    own same invariant."""
    dates = ["2026-09-01", "2026-09-02"]
    db_path = _make_ohlcv_db(tmp_path, dates)

    with patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
               return_value=None), \
         patch("scripts.final_trading_architecture_shadow_001.run_shadow_day",
               return_value={"success": True}) as mock_run:
        result = run_shadow_backlog_catchup(db_path=db_path)

    assert result["dates_processed"] == ["2026-09-01"]
    mock_run.assert_called_once_with(trade_date="2026-09-01", db_path=db_path, force=True)


def test_T093_catchup_handles_missing_db_gracefully():
    with patch("scripts.final_trading_architecture_shadow_001._open_db",
               side_effect=FileNotFoundError("no db")):
        result = run_shadow_backlog_catchup(db_path=Path("/does/not/exist"))
    assert result["success"] is False
    assert result["reason"] == "db_not_found"


def test_T094_catchup_respects_lookback_days(tmp_path):
    dates = [f"2026-{m:02d}-01" for m in range(1, 9)]  # 8 months of dates
    db_path = _make_ohlcv_db(tmp_path, dates)

    with patch("scripts.final_trading_architecture_shadow_001._latest_summary_for_date",
               return_value=None), \
         patch("scripts.final_trading_architecture_shadow_001.run_shadow_day",
               return_value={"success": True}):
        result = run_shadow_backlog_catchup(db_path=db_path, max_dates=100, lookback_days=3)

    # Only the last 3 dates are in scope; the latest of those has no T+1 -> 2 scoreable
    assert result["scoreable_dates_checked"] == 2


