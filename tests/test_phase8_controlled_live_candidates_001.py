"""
tests/test_phase8_controlled_live_candidates_001.py
=============================================
Focused tests for DTA-PHASE8-LIVE-CANDIDATE-001 — controlled live-path
consideration mechanism (scripts/knowledge_system/controlled_live_
candidates_001.py). Registry-only, dormant — nothing in this phase
reads or writes to V3 discovery, C2 selection, KDA, DecisionEngine, or
any trading path.

Verifies:
  - evaluate_live_candidacy() only returns controlled_live_candidate=True
    when ALL of: base lifecycle == PASS, shadow days >= 10, cumulative
    win-rate >= 0.6, and zero FAIL/RETIRED occurrences ever.
  - _ever_regressed() detects both a REJECTED verdict anywhere in history
    and a broken consecutive-validated-pass streak anywhere in history.
  - run_live_candidate_check_silent() rebuilds the export file fresh
    every run (a regression immediately removes a prior entry —
    "rollback").
  - LIFECYCLE_LIVE is never returned by this module's own logic.
  - config.ENABLE_CONTROLLED_LIVE_CANDIDATES exists and defaults False.
  - mover_discovery_v3.py / final_c2_selector.py are NOT modified to
    import or read anything from this module or its export file.
  - Orchestrator wiring: import/call present, ordered after Phase 6 and
    before the EOD-COMPLETED write, wrapped in its own try/except,
    failure does not abort EOD learning.
  - No trading-module references anywhere in this module or its
    integration block.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

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


# ── _ever_regressed() ──────────────────────────────────────────────────

def test_ever_regressed_false_for_clean_history():
    from scripts.knowledge_system.controlled_live_candidates_001 import _ever_regressed

    history = [
        {"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 1},
        {"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 2},
        {"status": "CHALLENGER_ELIGIBLE", "consecutive_validated_pass": 3},
    ]
    assert _ever_regressed(history) is False


def test_ever_regressed_true_for_rejected():
    from scripts.knowledge_system.controlled_live_candidates_001 import _ever_regressed

    history = [
        {"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 1},
        {"status": "REJECTED", "consecutive_validated_pass": 0},
    ]
    assert _ever_regressed(history) is True


def test_ever_regressed_true_for_broken_streak():
    from scripts.knowledge_system.controlled_live_candidates_001 import _ever_regressed

    history = [
        {"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 1},
        {"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 2},
        {"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 0},  # streak broke
    ]
    assert _ever_regressed(history) is True


# ── evaluate_live_candidacy() ─────────────────────────────────────────

def _patch_all(base_status, registry_history, shadow_history):
    return (
        patch(
            "scripts.knowledge_system.controlled_live_candidates_001.compute_lifecycle_status",
            return_value={"name": "FP", "direction": "UP", "lifecycle_status": base_status, "reason": "x"},
        ),
        patch(
            "scripts.knowledge_system.champion_challenger_001.load_registry_history",
            return_value=registry_history,
        ),
        patch(
            "scripts.knowledge_system.shadow_challenger_tracker_001.load_shadow_history",
            return_value=shadow_history,
        ),
    )


def test_not_candidate_when_base_status_not_pass():
    from scripts.knowledge_system.controlled_live_candidates_001 import evaluate_live_candidacy

    p1, p2, p3 = _patch_all("SHADOW_TEST", [], [])
    with p1, p2, p3:
        result = evaluate_live_candidacy("FP", "UP")
    assert result["controlled_live_candidate"] is False
    assert result["lifecycle_status"] == "SHADOW_TEST"


def test_not_candidate_when_insufficient_shadow_days():
    from scripts.knowledge_system.controlled_live_candidates_001 import evaluate_live_candidacy

    shadow_history = [{"challenger_at_least_as_good": True}] * 5  # only 5 days, need >=10
    p1, p2, p3 = _patch_all("PASS", [], shadow_history)
    with p1, p2, p3:
        result = evaluate_live_candidacy("FP", "UP")
    assert result["controlled_live_candidate"] is False
    assert "shadow days tracked" in result["live_entry_reason"]


def test_not_candidate_when_win_rate_below_threshold():
    from scripts.knowledge_system.controlled_live_candidates_001 import evaluate_live_candidacy

    shadow_history = [{"challenger_at_least_as_good": i % 2 == 0} for i in range(12)]  # 50% < 60%
    p1, p2, p3 = _patch_all("PASS", [], shadow_history)
    with p1, p2, p3:
        result = evaluate_live_candidacy("FP", "UP")
    assert result["controlled_live_candidate"] is False
    assert "win-rate" in result["live_entry_reason"]


def test_not_candidate_when_ever_regressed():
    from scripts.knowledge_system.controlled_live_candidates_001 import evaluate_live_candidacy

    shadow_history = [{"challenger_at_least_as_good": True}] * 12
    registry_history = [
        {"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 1},
        {"status": "REJECTED", "consecutive_validated_pass": 0},
    ]
    p1, p2, p3 = _patch_all("PASS", registry_history, shadow_history)
    with p1, p2, p3:
        result = evaluate_live_candidacy("FP", "UP")
    assert result["controlled_live_candidate"] is False
    assert "FAIL or RETIRED" in result["live_entry_reason"]


def test_qualifies_as_controlled_live_candidate_when_all_criteria_met():
    from scripts.knowledge_system.controlled_live_candidates_001 import evaluate_live_candidacy

    shadow_history = [{"challenger_at_least_as_good": True}] * 12  # 100% win-rate, 12 days
    registry_history = [{"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 1}]
    p1, p2, p3 = _patch_all("PASS", registry_history, shadow_history)
    with p1, p2, p3:
        result = evaluate_live_candidacy("FP", "UP")
    assert result["controlled_live_candidate"] is True
    assert result["lifecycle_status"] == "CONTROLLED_LIVE_CANDIDATE"


# ── LIFECYCLE_LIVE never reachable ────────────────────────────────────

def test_lifecycle_live_never_returned():
    from scripts.knowledge_system.controlled_live_candidates_001 import (
        LIFECYCLE_LIVE,
        evaluate_live_candidacy,
    )

    shadow_history = [{"challenger_at_least_as_good": True}] * 100
    registry_history = [{"status": "VALIDATED_TRACKING", "consecutive_validated_pass": 1}]
    p1, p2, p3 = _patch_all("PASS", registry_history, shadow_history)
    with p1, p2, p3:
        result = evaluate_live_candidacy("FP", "UP")
    assert result["lifecycle_status"] != LIFECYCLE_LIVE
    assert LIFECYCLE_LIVE == "LIVE"  # constant exists, purely as a future placeholder


# ── run_live_candidate_check_silent() — fresh rebuild / rollback ──────

def test_export_rebuilt_fresh_each_run_rollback(tmp_path):
    from scripts.knowledge_system import controlled_live_candidates_001 as clc

    export_path = tmp_path / "export.json"

    fake_registry = [{"name": "FP1", "direction": "UP", "components": {}}]
    with patch.object(clc, "LIVE_CANDIDATE_PATH", export_path), \
         patch.object(clc, "get_full_registry", return_value=fake_registry), \
         patch.object(clc, "evaluate_live_candidacy", return_value={
             "name": "FP1", "direction": "UP", "lifecycle_status": "CONTROLLED_LIVE_CANDIDATE",
             "controlled_live_candidate": True, "live_entry_reason": "qualifies",
         }):
        clc.run_live_candidate_check_silent()

    entries = json.loads(export_path.read_text(encoding="utf-8"))
    assert len(entries) == 1 and entries[0]["name"] == "FP1"

    # Now simulate a regression on the next run — the entry must disappear.
    with patch.object(clc, "LIVE_CANDIDATE_PATH", export_path), \
         patch.object(clc, "get_full_registry", return_value=fake_registry), \
         patch.object(clc, "evaluate_live_candidacy", return_value={
             "name": "FP1", "direction": "UP", "lifecycle_status": "PASS",
             "controlled_live_candidate": False, "live_entry_reason": "regressed",
         }):
        clc.run_live_candidate_check_silent()

    entries_after = json.loads(export_path.read_text(encoding="utf-8"))
    assert entries_after == []


def test_load_export_empty_when_missing(tmp_path):
    from scripts.knowledge_system.controlled_live_candidates_001 import load_export
    assert load_export(tmp_path / "does_not_exist.json") == []


# ── config flag ────────────────────────────────────────────────────────

def test_config_flag_exists_and_defaults_false():
    import config
    assert hasattr(config, "ENABLE_CONTROLLED_LIVE_CANDIDATES")
    assert config.ENABLE_CONTROLLED_LIVE_CANDIDATES is False


# ── V3/C2 must remain untouched ────────────────────────────────────────

def test_v3_and_c2_do_not_reference_phase8():
    forbidden_terms = ("controlled_live_candidates_001", "ENABLE_CONTROLLED_LIVE_CANDIDATES")
    candidates = list(ROOT.glob("**/mover_discovery_v3.py")) + list(ROOT.glob("**/final_c2_selector.py"))
    checked_any = False
    for path in candidates:
        if "data" in path.parts or "frz" in path.parts or "backups" in path.parts:
            continue  # skip any archived/backup copies, only check live source
        checked_any = True
        src = path.read_text(encoding="utf-8", errors="replace")
        for term in forbidden_terms:
            assert term not in src, f"{path} must not reference {term!r} (Phase 8 is dormant)"
    assert checked_any, "expected to find mover_discovery_v3.py / final_c2_selector.py in the workspace"


# ── Orchestrator wiring ──────────────────────────────────────────────

def test_live_candidate_import_present():
    assert (
        "from scripts.knowledge_system.controlled_live_candidates_001 import (" in BODY
        and "run_live_candidate_check_silent as _run_live_candidate_check" in BODY
    )


def test_live_candidate_call_present():
    assert "_run_live_candidate_check()" in BODY


def test_live_candidate_runs_after_shadow_and_before_completed():
    idx_lc = BODY.index("_run_live_candidate_check()")
    idx_shadow = BODY.index("_run_shadow_tracking()")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    assert idx_shadow < idx_lc < idx_completed


def test_live_candidate_wrapped_in_try_except():
    idx_call = BODY.index("_run_live_candidate_check()")
    preceding = BODY[max(0, idx_call - 300):idx_call]
    following = BODY[idx_call:idx_call + 900]
    assert "try:" in preceding
    assert "except Exception as _lc_exc:" in following
    assert (
        'log.warning("[Phase8-LiveCandidate] live-candidate check failed (non-critical): %s", _lc_exc)'
        in following
    )


def test_completed_write_not_permanently_nested_after_live_candidate_except():
    idx_except = BODY.index("except Exception as _lc_exc:")
    idx_after_except = idx_except + len("except Exception as _lc_exc:")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    between = BODY[idx_after_except:idx_completed]
    assert between.count("try:") == between.count("except Exception")


def test_live_candidate_block_references_no_trading_modules():
    idx_call = BODY.index("_run_live_candidate_check()")
    block = BODY[max(0, idx_call - 500):idx_call + 900]
    code_lines = [
        line for line in block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code_only = "\n".join(code_lines)
    forbidden = (
        "mover_discovery_v3", "final_c2_selector", "strategy_lab",
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine", "StrategyLab", "DecisionEngine",
        "knowledge_decision_pipeline",
    )
    for term in forbidden:
        assert term not in code_only, f"Phase 8 integration block must not reference {term!r}"


def test_live_candidate_module_has_no_trading_imports():
    src = (ROOT / "scripts" / "knowledge_system" / "controlled_live_candidates_001.py").read_text(
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
            assert term not in line, f"controlled_live_candidates_001.py must not import {term!r}"
