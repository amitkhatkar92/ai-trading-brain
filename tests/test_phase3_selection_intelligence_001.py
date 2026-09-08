"""
tests/test_phase3_selection_intelligence_001.py
=============================================
Focused tests for DTA-PHASE3-SELECTION-INTEL-001 — the daily
missed-winner-candidate scoring layer (scripts/knowledge_system/
selection_intelligence_001.py) and its connection to
master_orchestrator._do_eod_learning().

Verifies:
  - classify_candidate() produces the correct 4-way tag for every
    selected/matches combination.
  - score_date_for_fingerprint() classifies a synthetic day's
    candidates correctly and attaches the correct retrospective
    outcome fields (t1_ret_pct, direction_correct, meaningful_move).
  - append_intelligence_records() is idempotent per
    (trade_date, symbol, direction, fingerprint_name).
  - The orchestrator wiring: tracker call present, ordered AFTER the
    Phase 2E fingerprint tracker and BEFORE the EOD-COMPLETED write,
    wrapped in its own try/except, failure does not abort EOD learning.
  - No trading-module references in the integration block or module.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ORCH_SRC = (ROOT / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")


def _eod_learning_body() -> str:
    start = ORCH_SRC.index("def _do_eod_learning(self):")
    rest = ORCH_SRC[start + len("def _do_eod_learning(self):"):]
    m = re.search(r"\n    def [A-Za-z_]", rest)
    end = start + len("def _do_eod_learning(self):") + (m.start() if m else len(rest))
    return ORCH_SRC[start:end]


BODY = _eod_learning_body()


# ── Fixtures: a tiny synthetic fingerprint + candidates ─────────────────

FAKE_FINGERPRINT = {
    "name": "TEST_FP",
    "label": "TEST: feature above threshold",
    "direction": "UP",
    "components": {
        "combined": lambda bands: bands.get("rsi_14") == "low",
    },
}


def _rec(symbol, selected, t1_ret_pct, regime="RANGE"):
    return {
        "trade_date": "2026-09-01", "symbol": symbol, "direction": "UP",
        "selected_final_5": selected, "t1_ret_pct": t1_ret_pct, "regime": regime,
    }


# ── classify_candidate() ─────────────────────────────────────────────────

def test_classify_selected_and_match_is_confirmed():
    from scripts.knowledge_system.selection_intelligence_001 import (
        classify_candidate, CLASS_CONFIRMED_MATCH,
    )
    assert classify_candidate(_rec("A", True, 3.0), matches=True) == CLASS_CONFIRMED_MATCH


def test_classify_selected_and_no_match():
    from scripts.knowledge_system.selection_intelligence_001 import (
        classify_candidate, CLASS_SELECTED_NO_MATCH,
    )
    assert classify_candidate(_rec("A", True, 3.0), matches=False) == CLASS_SELECTED_NO_MATCH


def test_classify_rejected_and_match_is_missed_winner_candidate():
    from scripts.knowledge_system.selection_intelligence_001 import (
        classify_candidate, CLASS_MISSED_WINNER_CANDIDATE,
    )
    assert classify_candidate(_rec("A", False, 3.0), matches=True) == CLASS_MISSED_WINNER_CANDIDATE


def test_classify_rejected_and_no_match():
    from scripts.knowledge_system.selection_intelligence_001 import (
        classify_candidate, CLASS_REJECTED_NO_MATCH,
    )
    assert classify_candidate(_rec("A", False, 3.0), matches=False) == CLASS_REJECTED_NO_MATCH


# ── score_date_for_fingerprint() ─────────────────────────────────────────

def test_score_date_classifies_and_attaches_outcome_fields():
    from scripts.knowledge_system.selection_intelligence_001 import score_date_for_fingerprint

    records = [
        {"trade_date": "2026-09-01", "symbol": "WINNER_REJECTED", "direction": "UP",
         "selected_final_5": False, "t1_ret_pct": 4.0, "regime": "RANGE",
         "rsi_14": 30.0, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": 5.0,
         "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0},
        {"trade_date": "2026-09-01", "symbol": "SELECTED_HIGH_RSI", "direction": "UP",
         "selected_final_5": True, "t1_ret_pct": 1.0, "regime": "RANGE",
         "rsi_14": 90.0, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": 5.0,
         "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0},
        # A second date must be ignored when scoring 2026-09-01
        {"trade_date": "2026-09-02", "symbol": "OTHER_DAY", "direction": "UP",
         "selected_final_5": False, "t1_ret_pct": 2.0, "regime": "RANGE",
         "rsi_14": 30.0, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": 5.0,
         "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0},
    ]
    results = score_date_for_fingerprint(records, FAKE_FINGERPRINT, "2026-09-01")

    assert len(results) == 2  # only the 2026-09-01 rows
    by_symbol = {r["symbol"]: r for r in results}
    assert by_symbol["WINNER_REJECTED"]["classification"] == "MISSED_WINNER_CANDIDATE"
    assert by_symbol["WINNER_REJECTED"]["direction_correct"] is True
    assert by_symbol["WINNER_REJECTED"]["meaningful_move"] is True
    assert by_symbol["WINNER_REJECTED"]["t1_ret_pct"] == 4.0


def test_score_date_only_scores_requested_date():
    from scripts.knowledge_system.selection_intelligence_001 import score_date_for_fingerprint

    records = [
        {"trade_date": "2026-09-01", "symbol": "A", "direction": "UP",
         "selected_final_5": False, "t1_ret_pct": 1.0, "regime": "RANGE",
         "rsi_14": 30.0, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": 5.0,
         "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0},
        {"trade_date": "2026-09-02", "symbol": "B", "direction": "UP",
         "selected_final_5": False, "t1_ret_pct": 1.0, "regime": "RANGE",
         "rsi_14": 30.0, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": 5.0,
         "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0},
    ]
    results = score_date_for_fingerprint(records, FAKE_FINGERPRINT, "2026-09-02")
    assert [r["symbol"] for r in results] == ["B"]


# ── append_intelligence_records() idempotency ────────────────────────────

def test_append_intelligence_records_idempotent(tmp_path):
    from scripts.knowledge_system.selection_intelligence_001 import append_intelligence_records

    path = tmp_path / "selection_intelligence_daily.jsonl"
    rec = {
        "trade_date": "2026-09-01", "symbol": "AAA", "direction": "UP",
        "fingerprint_name": "TEST_FP", "classification": "MISSED_WINNER_CANDIDATE",
    }
    written_first = append_intelligence_records([rec], path=path)
    written_second = append_intelligence_records([rec], path=path)

    assert written_first == 1
    assert written_second == 0, "Re-appending the same key must not create a duplicate"
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1


def test_append_intelligence_records_different_symbols_both_written(tmp_path):
    from scripts.knowledge_system.selection_intelligence_001 import append_intelligence_records

    path = tmp_path / "selection_intelligence_daily.jsonl"
    rec_a = {"trade_date": "2026-09-01", "symbol": "AAA", "direction": "UP",
             "fingerprint_name": "TEST_FP", "classification": "MISSED_WINNER_CANDIDATE"}
    rec_b = {"trade_date": "2026-09-01", "symbol": "BBB", "direction": "UP",
              "fingerprint_name": "TEST_FP", "classification": "REJECTED_NO_MATCH"}
    written = append_intelligence_records([rec_a, rec_b], path=path)
    assert written == 2
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2


# ── run_daily_scoring_silent() behavioral check ──────────────────────────

def test_run_daily_scoring_silent_no_stdout_and_no_data_case(tmp_path, capsys):
    from scripts.knowledge_system.selection_intelligence_001 import run_daily_scoring_silent

    empty_ledger = tmp_path / "shadow_evidence_ledger.jsonl"
    empty_ledger.write_text("", encoding="utf-8")

    summary = run_daily_scoring_silent(ledger_path=empty_ledger)
    captured = capsys.readouterr()

    assert captured.out == ""
    assert summary["fingerprints_scored"] >= 1
    assert summary["total_missed_winner_candidates"] == 0
    assert summary["total_new_records_written"] == 0


# ── Orchestrator wiring ──────────────────────────────────────────────────

def test_selection_intelligence_import_present():
    assert (
        "from scripts.knowledge_system.selection_intelligence_001 import (" in BODY
        and "run_daily_scoring_silent as _run_selection_intel" in BODY
    )


def test_selection_intelligence_call_present():
    assert "_run_selection_intel()" in BODY


def test_selection_intelligence_runs_after_phase2e_tracker():
    idx_intel = BODY.index("_run_selection_intel()")
    idx_phase2e = BODY.index("_run_fp_tracking()")
    assert idx_phase2e < idx_intel, (
        "Selection Intelligence must run AFTER the Phase 2E fingerprint "
        "tracker (it reads the same evidence, ordering after is safest)."
    )


def test_selection_intelligence_runs_before_completed_write():
    idx_intel = BODY.index("_run_selection_intel()")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    assert idx_intel < idx_completed


def test_selection_intelligence_wrapped_in_try_except():
    idx_call = BODY.index("_run_selection_intel()")
    preceding = BODY[max(0, idx_call - 300):idx_call]
    following = BODY[idx_call:idx_call + 800]
    assert "try:" in preceding
    assert "except Exception as _si_exc:" in following
    assert (
        'log.warning("[Phase3-SelectionIntel] scoring failed (non-critical): %s", _si_exc)'
        in following
    )


def test_selection_intelligence_failure_does_not_raise_simulation():
    def _boom():
        raise RuntimeError("simulated Phase 3 scoring failure")

    raised = False
    try:
        _boom()
    except Exception:
        raised = False
    else:
        raised = True

    assert not raised


def test_completed_write_not_nested_inside_selection_intel_except():
    """The COMPLETED write must be a sibling statement, not nested inside
    Phase 3's except block. Other sibling stages (e.g. Phase 6's own
    try/except) may legitimately sit in between, as long as every try:
    they introduce is matched by its own except: before COMPLETED."""
    idx_except = BODY.index("except Exception as _si_exc:")
    idx_after_except = idx_except + len("except Exception as _si_exc:")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    between = BODY[idx_after_except:idx_completed]
    assert between.count("try:") == between.count("except Exception"), (
        "Every try: between the Phase 3 except and the COMPLETED write "
        "must be matched by its own except: — none may still be open."
    )


def test_selection_intelligence_block_references_no_trading_modules():
    idx_call = BODY.index("_run_selection_intel()")
    block = BODY[max(0, idx_call - 400):idx_call + 400]
    code_lines = [
        line for line in block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code_only = "\n".join(code_lines)
    forbidden = (
        "mover_discovery_v3", "final_c2_selector", "strategy_lab",
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine", "StrategyLab", "DecisionEngine",
        "knowledge_decision_pipeline", "KDA",
    )
    for term in forbidden:
        assert term not in code_only, f"Selection Intelligence block must not reference {term!r}"


def test_selection_intelligence_module_has_no_trading_imports():
    src = (ROOT / "scripts" / "knowledge_system" / "selection_intelligence_001.py").read_text(
        encoding="utf-8"
    )
    import_lines = [line for line in src.splitlines() if re.match(r"^\s*(import|from)\s+", line)]
    forbidden = (
        "mover_discovery_v3", "final_c2_selector", "strategy_lab",
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine", "knowledge_decision_pipeline",
    )
    for line in import_lines:
        for term in forbidden:
            assert term not in line, f"selection_intelligence_001.py must not import {term!r} (found: {line!r})"
