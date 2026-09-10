"""
tests/test_dta_market_benchmark_001.py
=========================================
DTA-MARKET-BENCHMARK-001 — Daily Market Opportunity Benchmark & Learning.

Tests: classification taxonomy (A-F), broad-market universe loader (test-
symbol filtering), collector failure handling (never raises), evidence-
feed wiring (missed movers reach rejection_tracker, non-misses do not),
persistence (JSONL + markdown), and EOD orchestrator wiring (import/call
present, try/except containment, no trading-module references).

READ-ONLY with respect to real trading state -- all tests use tmp_path /
mocks, never touch real data/ files except through explicit monkeypatching.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from opportunity_engine.market_opportunity_benchmark import (
    MoverCategory, MoverRecord, ClassifiedMover, classify_mover,
    _feed_miss_into_rejection_tracker, _write_outputs, run_daily_market_benchmark,
    collect_broad_market_movers, collect_nifty500_movers,
)


# ── Classification taxonomy (A-F) ─────────────────────────────────────────

def test_A_outside_universe():
    cat, detail = classify_mover("NOTINUNIVERSE", "UP", "2026-09-10",
                                  {"RELIANCE"}, {}, set(), {})
    assert cat == MoverCategory.OUTSIDE_UNIVERSE
    assert "not in nifty500_universe.json" in detail["reason"]


def test_B_in_universe_no_shadow_record():
    cat, detail = classify_mover("RELIANCE", "UP", "2026-09-10",
                                  {"RELIANCE"}, {}, set(), {})
    assert cat == MoverCategory.IN_UNIVERSE_NOT_IN_20POOL


def test_B_in_universe_shadow_record_no_v3_score():
    shadow = {("RELIANCE", "UP"): {"v3_score": None}}
    cat, detail = classify_mover("RELIANCE", "UP", "2026-09-10",
                                  {"RELIANCE"}, shadow, set(), {})
    assert cat == MoverCategory.IN_UNIVERSE_NOT_IN_20POOL
    assert "v3_score is None" in detail["reason"]


def test_C_in_20pool_not_selected_5():
    shadow = {("RELIANCE", "UP"): {"v3_score": 0.85, "selected_final_5": False,
                                    "c2_rank": 12, "miss_reason": "LOW_C2_SCORE"}}
    cat, detail = classify_mover("RELIANCE", "UP", "2026-09-10",
                                  {"RELIANCE"}, shadow, set(), {})
    assert cat == MoverCategory.IN_20POOL_NOT_SELECTED_5
    assert detail["c2_rank"] == 12


def test_D_selected_5_no_live_decision():
    shadow = {("RELIANCE", "UP"): {"v3_score": 0.9, "selected_final_5": True,
                                    "classification": "UNKNOWN_STATE", "t1_ret_pct": 1.0}}
    cat, detail = classify_mover("RELIANCE", "UP", "2026-09-10",
                                  {"RELIANCE"}, shadow, set(), {})
    assert cat == MoverCategory.SELECTED_5_REJECTED_DOWNSTREAM


def test_E_selected_traded_failed():
    shadow = {("RELIANCE", "UP"): {"v3_score": 0.9, "selected_final_5": True,
                                    "classification": "SELECTED_BUT_FAILED", "t1_ret_pct": -2.5}}
    cat, detail = classify_mover("RELIANCE", "UP", "2026-09-10",
                                  {"RELIANCE"}, shadow, set(), {})
    assert cat == MoverCategory.SELECTED_TRADED_FAILED
    assert detail["t1_ret_pct"] == -2.5


def test_F_selected_traded_success():
    shadow = {("RELIANCE", "UP"): {"v3_score": 0.9, "selected_final_5": True,
                                    "classification": "CORRECT_SELECT", "t1_ret_pct": 3.5}}
    cat, detail = classify_mover("RELIANCE", "UP", "2026-09-10",
                                  {"RELIANCE"}, shadow, set(), {})
    assert cat == MoverCategory.SELECTED_TRADED_SUCCESS


def test_unresolved_outcome():
    shadow = {("RELIANCE", "UP"): {"v3_score": 0.9, "selected_final_5": True,
                                    "classification": "UNRESOLVED", "t1_ret_pct": None}}
    cat, detail = classify_mover("RELIANCE", "UP", "2026-09-10",
                                  {"RELIANCE"}, shadow, set(), {})
    assert cat == MoverCategory.UNRESOLVED


def test_symbol_case_and_suffix_normalized():
    """symbol.NS or lowercase must match the same universe/shadow entries."""
    cat, _ = classify_mover("reliance.ns", "UP", "2026-09-10", {"RELIANCE"}, {}, set(), {})
    assert cat == MoverCategory.IN_UNIVERSE_NOT_IN_20POOL


# ── Broad-market universe loader ──────────────────────────────────────────

def test_broad_universe_excludes_test_symbols(tmp_path):
    from predictive_gap.broad_market_universe import load_broad_nse_equity_symbols
    csv_content = (
        "SEM_EXM_EXCH_ID,SEM_SERIES,SEM_TRADING_SYMBOL\n"
        "NSE,EQ,RELIANCE\n"
        "NSE,EQ,011NSETEST\n"
        "NSE,EQ,TCS\n"
        "NSE,SG,SOMEBOND\n"
        "BSE,EQ,BSESTOCK\n"
    )
    p = tmp_path / "sec.csv"
    p.write_text(csv_content, encoding="utf-8")
    syms = load_broad_nse_equity_symbols(csv_path=p, force_reload=True)
    assert syms == ["RELIANCE", "TCS"]
    assert "011NSETEST" not in syms
    assert "SOMEBOND" not in syms   # wrong series
    assert "BSESTOCK" not in syms   # wrong exchange


def test_broad_universe_missing_file_returns_empty(tmp_path):
    from predictive_gap.broad_market_universe import load_broad_nse_equity_symbols
    missing = tmp_path / "does_not_exist.csv"
    syms = load_broad_nse_equity_symbols(csv_path=missing, force_reload=True)
    assert syms == []


# ── Collector failure handling (never raises) ─────────────────────────────

def test_collect_broad_market_movers_empty_universe_fails_safe():
    with patch("predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
               return_value=[]):
        gainers, losers = collect_broad_market_movers("2026-09-10")
    assert gainers == [] and losers == []


def test_collect_broad_market_movers_fetch_exception_fails_safe():
    with patch("predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
               return_value=["RELIANCE"]):
        with patch("predictive_gap.pga_collector._fetch_price_data",
                   side_effect=RuntimeError("network down")):
            gainers, losers = collect_broad_market_movers("2026-09-10")
    assert gainers == [] and losers == []


def test_collect_nifty500_movers_exception_fails_safe():
    with patch("predictive_gap.pga_collector.collect_daily",
               side_effect=RuntimeError("boom")):
        gainers, losers = collect_nifty500_movers("2026-09-10")
    assert gainers == [] and losers == []


# ── Evidence feed wiring ───────────────────────────────────────────────────

def _mover(symbol="RELIANCE", benchmark_type="NIFTY500", move_type="GAINER", pct=5.0):
    return MoverRecord(
        trade_date="2026-09-10", symbol=symbol, benchmark_type=benchmark_type,
        move_type=move_type, daily_return_pct=pct, direction="UP",
        source="yfinance", methodology="test", universe_size=230,
    )


def test_miss_category_feeds_rejection_tracker():
    cm = ClassifiedMover(mover=_mover(), category=MoverCategory.IN_20POOL_NOT_SELECTED_5,
                          detail={"c2_rank": 15})
    mock_tracker = MagicMock()
    with patch("analysis.rejection_tracker.get_rejection_tracker", return_value=mock_tracker):
        _feed_miss_into_rejection_tracker(cm)
    mock_tracker.ingest_rejection.assert_called_once()
    kwargs = mock_tracker.ingest_rejection.call_args.kwargs
    assert kwargs["quality_tier"] == "MARKET_BENCHMARK_MISS"
    assert kwargs["rejected_reason"] == "IN_20POOL_NOT_SELECTED_5"


def test_non_miss_category_does_not_feed_rejection_tracker():
    """SELECTED_TRADED_SUCCESS (F) and UNRESOLVED are not misses -- must not
    be written to rejection_audit.db."""
    for cat in (MoverCategory.SELECTED_TRADED_SUCCESS, MoverCategory.UNRESOLVED):
        cm = ClassifiedMover(mover=_mover(), category=cat, detail={})
        mock_tracker = MagicMock()
        with patch("analysis.rejection_tracker.get_rejection_tracker", return_value=mock_tracker):
            _feed_miss_into_rejection_tracker(cm)
        mock_tracker.ingest_rejection.assert_not_called()


def test_rejection_tracker_failure_does_not_raise():
    cm = ClassifiedMover(mover=_mover(), category=MoverCategory.OUTSIDE_UNIVERSE, detail={})
    with patch("analysis.rejection_tracker.get_rejection_tracker",
               side_effect=RuntimeError("db locked")):
        _feed_miss_into_rejection_tracker(cm)  # must not raise


# ── Persistence ────────────────────────────────────────────────────────────

def test_write_outputs_creates_jsonl_and_markdown(tmp_path):
    import opportunity_engine.market_opportunity_benchmark as mob
    with patch.object(mob, "BENCHMARK_DIR", tmp_path):
        classified = [
            ClassifiedMover(mover=_mover(symbol="RELIANCE"), category=MoverCategory.SELECTED_TRADED_SUCCESS),
            ClassifiedMover(mover=_mover(symbol="TCS", move_type="LOSER", pct=-3.0),
                             category=MoverCategory.OUTSIDE_UNIVERSE),
        ]
        counts = mob._write_outputs("2026-09-10", classified)
    jsonl_path = tmp_path / "MARKET_BENCHMARK_2026-09-10.jsonl"
    md_path = tmp_path / "MARKET_BENCHMARK_2026-09-10.md"
    assert jsonl_path.exists() and md_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["symbol"] == "RELIANCE"
    assert counts["SELECTED_TRADED_SUCCESS"] == 1
    assert counts["OUTSIDE_UNIVERSE"] == 1


# ── Full orchestration never raises ────────────────────────────────────────

def test_run_daily_market_benchmark_never_raises_on_total_failure(tmp_path):
    import opportunity_engine.market_opportunity_benchmark as mob
    with patch.object(mob, "UNIVERSE_FILE", tmp_path / "missing.json"), \
         patch.object(mob, "SHADOW_LEDGER", tmp_path / "missing.jsonl"), \
         patch.object(mob, "CT_DB", tmp_path / "missing.db"), \
         patch.object(mob, "BENCHMARK_DIR", tmp_path), \
         patch("predictive_gap.broad_market_universe.load_broad_nse_equity_symbols", return_value=[]), \
         patch("predictive_gap.pga_collector.collect_daily", side_effect=RuntimeError("no data")):
        result = mob.run_daily_market_benchmark("2026-09-10")
    assert "trade_date" in result  # completes without raising


# ── EOD orchestrator wiring ─────────────────────────────────────────────────

def test_eod_wiring_present_and_safely_contained():
    import inspect
    import orchestrator.master_orchestrator as mo_mod
    src = inspect.getsource(mo_mod)
    assert "market_opportunity_benchmark" in src or "run_daily_market_benchmark" in src, (
        "run_daily_market_benchmark must be called from master_orchestrator.py's "
        "EOD learning hook"
    )
    # Must be inside a try/except so a failure never aborts EOD.
    call_idx = src.find("run_daily_market_benchmark_silent")
    assert call_idx != -1, "must call the *_silent() EOD-safe wrapper, not the raw function"
    preceding = src[max(0, call_idx - 400):call_idx]
    assert "try:" in preceding, "call site must be inside a try block"


def test_module_does_not_reference_live_trading_control_flow():
    """This module must never import/touch OrderManager, DecisionEngine,
    RiskManagerAI, or CapitalRiskEngine's decision-making entry points --
    it is read/observe/record only."""
    import opportunity_engine.market_opportunity_benchmark as mob
    import inspect
    src = inspect.getsource(mob)
    forbidden = ["OrderManager(", "DecisionEngine(", ".execute(signal",
                 "place_order(", "CapitalRiskEngine().allocate("]
    for f in forbidden:
        assert f not in src, f"market_opportunity_benchmark.py must not reference {f}"
