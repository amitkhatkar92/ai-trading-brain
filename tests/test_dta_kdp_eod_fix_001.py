"""
tests/test_dta_kdp_eod_fix_001.py
====================================
DTA-KDP-EOD-FIX-001 — root-cause fix for KDA EOD outcome evaluation.

Root cause (confirmed live 2026-09-16): run_eod_knowledge_update() defaulted
to trading_date=today, but outcome evaluation requires OHLCV bars STRICTLY
AFTER decision_date -- a same-day decision can never have any, so
outcomes_evaluated was mathematically guaranteed to be 0 every single day in
production (304 decisions/day, 0 evaluated, ~250+ wasted yfinance calls).

This test suite verifies:
  1. KDALedger.list_available_dates() lists real ledger dates, sorted.
  2. run_eod_outcome_backfill() only ever targets PAST dates (< today).
  3. run_eod_outcome_backfill() is bounded by max_dates per call.
  4. run_eod_outcome_backfill() tracks state so a date is never re-processed.
  5. Step-4 per-symbol bars are cached within one _eod_impl() run (dedup).
  6. Step-4 fetch is bounded by _MAX_SYMBOL_FETCHES_PER_RUN.
  7. run_eod_outcome_backfill() fails open (never raises) on internal error.
  8. Safety-contract source scan: no broker/order/execution imports.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_dirs(tmp_path: Path):
    data_dir = tmp_path / "data"
    kda_dir = data_dir / "klp" / "kda"
    kda_dir.mkdir(parents=True, exist_ok=True)
    return {"data": data_dir, "output": kda_dir}


@pytest.fixture
def pipeline(tmp_dirs):
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    return KnowledgeDecisionPipeline(
        data_dir=tmp_dirs["data"],
        output_dir=tmp_dirs["output"],
    )


def _write_decisions(output_dir: Path, trading_date: str, symbols: list) -> None:
    """Write minimal KDA decision records for a date (repeats allowed)."""
    path = output_dir / f"kda_decisions_{trading_date}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        for i, sym in enumerate(symbols):
            rec = {
                "decision_id": f"{trading_date}-{sym}-{i}",
                "symbol": sym,
                "direction": "BUY",
                "decision": "KNOWLEDGE_BUY",
                "target": 110.0,
                "stop_loss": 90.0,
                "entry_price": 100.0,
                "effective_sample_size": 20,
                "knowledge_authority": 0.7,
                "evidence_state": "SUFFICIENT",
                "fallback_used": False,
                "supporting_angles": [],
                "contradicting_angles": [],
                "expected_days_p50": 5,
            }
            fh.write(json.dumps(rec) + "\n")


# ── T01: list_available_dates ─────────────────────────────────────────────────

class TestT01ListAvailableDates:
    def test_lists_sorted_real_dates(self, tmp_dirs):
        from knowledge_authority.kda_ledger import KDALedger
        _write_decisions(tmp_dirs["output"], "2026-09-01", ["AAA"])
        _write_decisions(tmp_dirs["output"], "2026-08-20", ["BBB"])
        _write_decisions(tmp_dirs["output"], "2026-09-10", ["CCC"])
        ledger = KDALedger(base_dir=tmp_dirs["output"])
        dates = ledger.list_available_dates()
        assert dates == ["2026-08-20", "2026-09-01", "2026-09-10"]

    def test_empty_dir_returns_empty_list(self, tmp_dirs):
        from knowledge_authority.kda_ledger import KDALedger
        ledger = KDALedger(base_dir=tmp_dirs["output"] / "nonexistent")
        assert ledger.list_available_dates() == []


# ── T02: backfill only targets past dates, bounded, stateful ─────────────────

class TestT02BackfillTargeting:
    def test_only_processes_past_dates_not_today(self, pipeline, tmp_dirs, monkeypatch):
        import knowledge_authority.knowledge_decision_pipeline as kdp_mod
        monkeypatch.setattr(kdp_mod, "_OUTCOME_BACKFILL_STATE_PATH", tmp_dirs["data"] / "state.json")

        today = date.today().isoformat()
        past = (date.today() - timedelta(days=5)).isoformat()
        _write_decisions(tmp_dirs["output"], today, ["AAA"])
        _write_decisions(tmp_dirs["output"], past, ["BBB"])

        with patch.object(kdp_mod, "_fetch_post_decision_bars", return_value=[]):
            result = pipeline.run_eod_outcome_backfill(max_dates=5)

        assert result["status"] == "OK"
        assert today not in result["dates_processed"]
        assert past in result["dates_processed"]

    def test_bounded_by_max_dates(self, pipeline, tmp_dirs, monkeypatch):
        import knowledge_authority.knowledge_decision_pipeline as kdp_mod
        monkeypatch.setattr(kdp_mod, "_OUTCOME_BACKFILL_STATE_PATH", tmp_dirs["data"] / "state.json")

        for n in range(6, 1, -1):
            d = (date.today() - timedelta(days=n)).isoformat()
            _write_decisions(tmp_dirs["output"], d, ["AAA"])

        with patch.object(kdp_mod, "_fetch_post_decision_bars", return_value=[]):
            result = pipeline.run_eod_outcome_backfill(max_dates=2)

        assert len(result["dates_processed"]) == 2

    def test_never_reprocesses_a_completed_date(self, pipeline, tmp_dirs, monkeypatch):
        import knowledge_authority.knowledge_decision_pipeline as kdp_mod
        monkeypatch.setattr(kdp_mod, "_OUTCOME_BACKFILL_STATE_PATH", tmp_dirs["data"] / "state.json")

        past = (date.today() - timedelta(days=3)).isoformat()
        _write_decisions(tmp_dirs["output"], past, ["AAA"])

        with patch.object(kdp_mod, "_fetch_post_decision_bars", return_value=[]):
            r1 = pipeline.run_eod_outcome_backfill(max_dates=5)
            r2 = pipeline.run_eod_outcome_backfill(max_dates=5)

        assert past in r1["dates_processed"]
        assert r2["dates_processed"] == []

    def test_fails_open_never_raises(self, pipeline, monkeypatch):
        import knowledge_authority.knowledge_decision_pipeline as kdp_mod
        monkeypatch.setattr(
            pipeline._ledger, "list_available_dates",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        result = pipeline.run_eod_outcome_backfill()
        assert result["status"] == "KNOWLEDGE_PIPELINE_ERROR"


# ── T03: per-symbol caching + bound inside _eod_impl Step 4 ──────────────────

class TestT03SymbolCachingAndBound:
    def test_repeated_symbols_fetched_only_once(self, pipeline, tmp_dirs):
        import knowledge_authority.knowledge_decision_pipeline as kdp_mod
        past = (date.today() - timedelta(days=3)).isoformat()
        # 3 decisions, only 2 unique symbols
        _write_decisions(tmp_dirs["output"], past, ["AAA", "AAA", "BBB"])

        calls = []

        def _fake_fetch(symbol, decision_date, horizon=20):
            calls.append(symbol)
            return []

        with patch.object(kdp_mod, "_fetch_post_decision_bars", side_effect=_fake_fetch):
            pipeline.run_eod_knowledge_update(trading_date=past)

        assert len(calls) == 2
        assert set(calls) == {"AAA", "BBB"}

    def test_fetch_bounded_by_max_symbol_fetches_per_run(self, pipeline, tmp_dirs, monkeypatch):
        import knowledge_authority.knowledge_decision_pipeline as kdp_mod
        monkeypatch.setattr(kdp_mod, "_MAX_SYMBOL_FETCHES_PER_RUN", 2)

        past = (date.today() - timedelta(days=3)).isoformat()
        _write_decisions(tmp_dirs["output"], past, ["AAA", "BBB", "CCC", "DDD"])

        calls = []

        def _fake_fetch(symbol, decision_date, horizon=20):
            calls.append(symbol)
            return []

        with patch.object(kdp_mod, "_fetch_post_decision_bars", side_effect=_fake_fetch):
            pipeline.run_eod_knowledge_update(trading_date=past)

        assert len(calls) == 2


# ── T04: safety-contract source scan ──────────────────────────────────────────

class TestT04SafetyContract:
    def test_no_forbidden_imports_in_new_code(self):
        src = Path("knowledge_authority/knowledge_decision_pipeline.py").read_text(encoding="utf-8")
        for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker"):
            assert f"import {forbidden}" not in src
            assert f"from {forbidden}" not in src
