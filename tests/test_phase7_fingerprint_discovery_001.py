"""
tests/test_phase7_fingerprint_discovery_001.py
=============================================
Focused tests for DTA-PHASE7-DISCOVERY-001 — automatic, rule-based
fingerprint discovery & promotion + research lifecycle status
(scripts/knowledge_system/fingerprint_discovery_001.py).

Verifies:
  - evaluate_candidate() computes overall/rejected-only lift correctly
    on a small, hand-computable synthetic dataset.
  - build_fingerprint_from_conditions() produces a fingerprint dict whose
    "combined" rule is a correct AND of all (feature, band) conditions.
  - Promotion bar: BOTH overall_lift AND rejected_only_lift must be
    >= PROMOTION_LIFT_THRESHOLD (0.02) with n_true_rejected >= 15,
    else NOT_YET.
  - _persist_new_discovery()/_already_discovered()/load_discovered_
    fingerprints() round-trip correctly and are idempotent (never
    duplicate-promote).
  - STATICALLY_REGISTERED ("low_rsi_and_high_mom_accel", "UP") is never
    (re-)promoted by this module even if it would otherwise clear the bar.
  - append_discovery_log() is idempotent per (as_of_date, name, direction).
  - compute_lifecycle_status() maps every Phase 5/6 state combination to
    the correct lifecycle label (NOT_YET / RESEARCH_CANDIDATE /
    VALIDATED_TRACKING / CHALLENGER_ELIGIBLE / SHADOW_TEST / PASS / FAIL
    / RETIRED).
  - get_full_registry() (fingerprint_tracker_001.py) merges the static
    registry with discovered fingerprints, and Phase 3/5/6's internals
    now iterate get_full_registry() instead of the bare static list.
  - Orchestrator wiring: import/call present, ordered BEFORE Phase 2E's
    block, wrapped in its own try/except, failure does not abort EOD
    learning.
  - No trading-module references anywhere.
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

TEST_COMBO = {
    "name": "test_combo",
    "label": "test combo",
    "conditions": [("rsi_14", "low"), ("mom_accel", "high")],
    "rule": lambda bands: bands.get("rsi_14") == "low" and bands.get("mom_accel") == "high",
}

WEAK_COMBO = {
    "name": "weak_combo",
    "label": "weak combo",
    "conditions": [("hv_20", "high")],
    "rule": lambda bands: bands.get("hv_20") == "high",
}


def _rec(symbol, trade_date, selected, t1_ret_pct, rsi=50.0, accel=5.0, direction="UP"):
    return {
        "trade_date": trade_date, "symbol": symbol, "direction": direction,
        "selected_final_5": selected, "t1_ret_pct": t1_ret_pct, "regime": "RANGE",
        "rsi_14": rsi, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": accel,
        "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0,
    }


def _build_synthetic_records(n_matching_rejected_movers, n_matching_rejected_non_movers,
                              n_nonmatching_rejected):
    """Builds a UP-direction dataset where the 'test_combo' condition
    (rsi low + mom_accel high) is engineered to have a clear positive
    lift on the rejected-only slice, with enough distinct raw values that
    tertile banding still separates high/low/moderate meaningfully."""
    records = []
    i = 0
    # matching + reject + meaningful mover (t1_ret >= 2%)
    for _ in range(n_matching_rejected_movers):
        records.append(_rec(f"MOV{i}", "2026-08-20", False, 5.0, rsi=10.0 + i, accel=90.0 - i))
        i += 1
    # matching + reject + NOT a mover
    for _ in range(n_matching_rejected_non_movers):
        records.append(_rec(f"NOMOV{i}", "2026-08-20", False, 0.1, rsi=10.0 + i, accel=90.0 - i))
        i += 1
    # non-matching + reject (moderate rsi/accel, spread across the range so
    # tertile thresholds land between the two clusters) — none are movers
    for _ in range(n_nonmatching_rejected):
        records.append(_rec(f"OTHER{i}", "2026-08-20", False, 0.1, rsi=50.0 + i, accel=40.0 - (i % 5)))
        i += 1
    return records


# ── evaluate_candidate() ──────────────────────────────────────────────

def test_evaluate_candidate_promotes_when_lift_clears_bar():
    from scripts.knowledge_system.fingerprint_discovery_001 import evaluate_candidate

    records = _build_synthetic_records(
        n_matching_rejected_movers=18, n_matching_rejected_non_movers=2, n_nonmatching_rejected=30,
    )
    result = evaluate_candidate(records, TEST_COMBO, "UP")
    assert result["n_true_rejected"] >= 15
    assert result["overall_lift"] is not None and result["overall_lift"] > 0
    assert result["rejected_only_lift"] is not None and result["rejected_only_lift"] > 0
    assert result["meets_promotion_bar"] is True


def test_evaluate_candidate_does_not_promote_below_sample_bar():
    from scripts.knowledge_system.fingerprint_discovery_001 import evaluate_candidate

    # Only a handful of matching+rejected records — below MIN_SAMPLE_FOR_STATS (15)
    records = _build_synthetic_records(
        n_matching_rejected_movers=3, n_matching_rejected_non_movers=0, n_nonmatching_rejected=30,
    )
    result = evaluate_candidate(records, TEST_COMBO, "UP")
    assert result["n_true_rejected"] < 15
    assert result["meets_promotion_bar"] is False


def test_evaluate_candidate_does_not_promote_when_lift_negligible():
    from scripts.knowledge_system.fingerprint_discovery_001 import evaluate_candidate

    # Combo matches, but mover rate is identical inside/outside the match
    # (build both sides with the same, low mover density) -> lift ~ 0.
    records = []
    for i in range(20):
        records.append(_rec(f"M{i}", "2026-08-20", False, 0.1, rsi=10.0 + i, accel=90.0 - i))
    for i in range(20):
        records.append(_rec(f"N{i}", "2026-08-20", False, 0.1, rsi=50.0 + i, accel=40.0 - (i % 5)))
    result = evaluate_candidate(records, TEST_COMBO, "UP")
    assert result["meets_promotion_bar"] is False


# ── build_fingerprint_from_conditions() ───────────────────────────────

def test_build_fingerprint_from_conditions_combined_is_and():
    from scripts.knowledge_system.fingerprint_discovery_001 import build_fingerprint_from_conditions

    fp = build_fingerprint_from_conditions(
        "test_combo", "test combo", "UP", [("rsi_14", "low"), ("mom_accel", "high")]
    )
    assert fp["name"] == "test_combo" and fp["direction"] == "UP"
    combined = fp["components"]["combined"]
    assert combined({"rsi_14": "low", "mom_accel": "high"}) is True
    assert combined({"rsi_14": "low", "mom_accel": "moderate"}) is False
    assert combined({"rsi_14": "moderate", "mom_accel": "high"}) is False
    # single-component rules present and correct
    assert fp["components"]["rsi_14_alone"]({"rsi_14": "low"}) is True
    assert fp["components"]["mom_accel_alone"]({"mom_accel": "high"}) is True


# ── persistence round-trip ─────────────────────────────────────────────

def test_persist_and_load_discovered_fingerprints_roundtrip(tmp_path):
    from scripts.knowledge_system.fingerprint_discovery_001 import (
        _already_discovered,
        _persist_new_discovery,
        load_discovered_fingerprints,
    )

    path = tmp_path / "discovered.json"
    assert load_discovered_fingerprints(path) == []
    assert _already_discovered("test_combo", "UP", path) is False

    _persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low"), ("mom_accel", "high")], path)

    assert _already_discovered("test_combo", "UP", path) is True
    assert _already_discovered("test_combo", "DOWN", path) is False  # direction-specific

    fps = load_discovered_fingerprints(path)
    assert len(fps) == 1
    assert fps[0]["name"] == "test_combo"
    assert fps[0]["components"]["combined"]({"rsi_14": "low", "mom_accel": "high"}) is True


def test_persist_new_discovery_appends_not_overwrites(tmp_path):
    from scripts.knowledge_system.fingerprint_discovery_001 import _persist_new_discovery, load_discovered_fingerprints

    path = tmp_path / "discovered.json"
    _persist_new_discovery("combo_a", "A", "UP", [("rsi_14", "low")], path)
    _persist_new_discovery("combo_b", "B", "DOWN", [("hv_20", "high")], path)
    fps = load_discovered_fingerprints(path)
    assert {fp["name"] for fp in fps} == {"combo_a", "combo_b"}


# ── STATICALLY_REGISTERED exclusion ───────────────────────────────────

def test_statically_registered_combo_never_promoted(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    ledger = tmp_path / "ledger.jsonl"
    discovered_path = tmp_path / "discovered.json"
    log_path = tmp_path / "log.jsonl"

    # Strongly-engineered dataset: the ORIGINAL fingerprint's own combo
    # ("low_rsi_and_high_mom_accel", UP) would clearly clear the bar here.
    records = _build_synthetic_records(
        n_matching_rejected_movers=18, n_matching_rejected_non_movers=2, n_nonmatching_rejected=30,
    )
    ledger.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    with patch.object(fd, "DISCOVERED_FINGERPRINTS_PATH", discovered_path), \
         patch.object(fd, "DISCOVERY_LOG_PATH", log_path):
        results = fd.run_discovery_silent(ledger_path=ledger)

    original = next(r for r in results if r["name"] == "low_rsi_and_high_mom_accel" and r["direction"] == "UP")
    assert original["newly_promoted_today"] is False
    assert original["already_registered"] is True  # statically excluded, not re-promoted
    assert not discovered_path.exists() or not any(
        s["name"] == "low_rsi_and_high_mom_accel" and s["direction"] == "UP"
        for s in json.loads(discovered_path.read_text(encoding="utf-8"))
    )


# ── DTA-PHASE7-BUGFIX: combo-name vs fingerprint-name identity space ──

def test_static_fingerprint_name_resolution():
    """The static fingerprint's combo name ("low_rsi_and_high_mom_accel")
    must resolve to its actual, persisted fingerprint name
    ("UP_low_rsi_high_accel") so lifecycle lookups hit real Phase 5/6
    history instead of silently finding nothing."""
    from scripts.knowledge_system.fingerprint_discovery_001 import _resolve_fingerprint_name

    assert _resolve_fingerprint_name("low_rsi_and_high_mom_accel") == "UP_low_rsi_high_accel"
    # discovered-fingerprint combo names are identity-mapped (unaffected)
    assert _resolve_fingerprint_name("high_mom_accel_and_moderate_rsi") == "high_mom_accel_and_moderate_rsi"


def test_run_discovery_silent_uses_real_fingerprint_name_for_lifecycle(tmp_path):
    """Regression test for the name-space bug: run_discovery_silent() must
    look up the static fingerprint's Phase 5 history under its real
    fingerprint name, not its combo name, so a real VALIDATED_TRACKING/
    OBSERVE_ONLY/etc. status is reflected instead of always falling back
    to 'no Phase 5 validation check has run yet'."""
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    fake_registry_history = [{
        "status": "VALIDATED_TRACKING", "reason": "1/3 streak",
        "consecutive_validated_pass": 1,
    }]

    def _fake_load_registry_history(name, direction, *a, **kw):
        # Only the REAL fingerprint name should ever be queried for this
        # candidate — the combo name must never reach this call.
        assert name != "low_rsi_and_high_mom_accel"
        if name == "UP_low_rsi_high_accel" and direction == "UP":
            return fake_registry_history
        return []

    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history",
        side_effect=_fake_load_registry_history,
    ):
        results = fd.run_discovery_silent(ledger_path=ledger)

    original = next(r for r in results if r["name"] == "low_rsi_and_high_mom_accel" and r["direction"] == "UP")
    assert original["lifecycle_status"] == "VALIDATED_TRACKING"


# ── append_discovery_log() idempotency ────────────────────────────────

def test_append_discovery_log_idempotent(tmp_path):
    from scripts.knowledge_system.fingerprint_discovery_001 import append_discovery_log

    path = tmp_path / "log.jsonl"
    entry = {"as_of_date": "2026-08-20", "name": "test_combo", "direction": "UP"}
    assert append_discovery_log(entry, path) is True
    assert append_discovery_log(entry, path) is False
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1


# ── compute_lifecycle_status() ────────────────────────────────────────

def test_lifecycle_not_yet_when_not_discovered(tmp_path):
    from scripts.knowledge_system.fingerprint_discovery_001 import compute_lifecycle_status

    result = compute_lifecycle_status("never_discovered_combo", "UP", discovered_path=tmp_path / "none.json")
    assert result["lifecycle_status"] == "NOT_YET"


def test_lifecycle_research_candidate_when_discovered_but_no_phase5_check(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low")], discovered_path)

    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=[]
    ):
        result = fd.compute_lifecycle_status("test_combo", "UP", discovered_path=discovered_path)
    assert result["lifecycle_status"] == "RESEARCH_CANDIDATE"


def test_lifecycle_fail_on_rejected_status(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low")], discovered_path)

    fake_history = [{"status": "REJECTED", "reason": "failed validated tier", "consecutive_validated_pass": 0}]
    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=fake_history
    ):
        result = fd.compute_lifecycle_status("test_combo", "UP", discovered_path=discovered_path)
    assert result["lifecycle_status"] == "FAIL"


def test_lifecycle_validated_tracking(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low")], discovered_path)

    fake_history = [{"status": "VALIDATED_TRACKING", "reason": "1/3 streak", "consecutive_validated_pass": 1}]
    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=fake_history
    ):
        result = fd.compute_lifecycle_status("test_combo", "UP", discovered_path=discovered_path)
    assert result["lifecycle_status"] == "VALIDATED_TRACKING"


def test_lifecycle_retired_when_streak_breaks(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low")], discovered_path)

    fake_history = [
        {"status": "VALIDATED_TRACKING", "reason": "1/3", "consecutive_validated_pass": 1},
        {"status": "VALIDATED_TRACKING", "reason": "2/3", "consecutive_validated_pass": 2},
        {"status": "VALIDATED_TRACKING", "reason": "streak broken", "consecutive_validated_pass": 0},
    ]
    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=fake_history
    ):
        result = fd.compute_lifecycle_status("test_combo", "UP", discovered_path=discovered_path)
    assert result["lifecycle_status"] == "RETIRED"


def test_lifecycle_challenger_eligible_no_shadow_days(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low")], discovered_path)

    fake_history = [{"status": "CHALLENGER_ELIGIBLE", "reason": "all met", "consecutive_validated_pass": 3}]
    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=fake_history
    ), patch(
        "scripts.knowledge_system.shadow_challenger_tracker_001.load_shadow_history", return_value=[]
    ):
        result = fd.compute_lifecycle_status("test_combo", "UP", discovered_path=discovered_path)
    assert result["lifecycle_status"] == "CHALLENGER_ELIGIBLE"


def test_lifecycle_shadow_test_in_progress(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low")], discovered_path)

    fake_registry = [{"status": "CHALLENGER_ELIGIBLE", "reason": "all met", "consecutive_validated_pass": 3}]
    fake_shadow = [
        {"challenger_at_least_as_good": True},
        {"challenger_at_least_as_good": False},
    ]
    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=fake_registry
    ), patch(
        "scripts.knowledge_system.shadow_challenger_tracker_001.load_shadow_history", return_value=fake_shadow
    ):
        result = fd.compute_lifecycle_status("test_combo", "UP", discovered_path=discovered_path)
    assert result["lifecycle_status"] == "SHADOW_TEST"


def test_lifecycle_pass_after_three_consecutive_shadow_wins(tmp_path):
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("test_combo", "test combo", "UP", [("rsi_14", "low")], discovered_path)

    fake_registry = [{"status": "CHALLENGER_ELIGIBLE", "reason": "all met", "consecutive_validated_pass": 3}]
    fake_shadow = [
        {"challenger_at_least_as_good": False},
        {"challenger_at_least_as_good": True},
        {"challenger_at_least_as_good": True},
        {"challenger_at_least_as_good": True},
    ]
    with patch(
        "scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=fake_registry
    ), patch(
        "scripts.knowledge_system.shadow_challenger_tracker_001.load_shadow_history", return_value=fake_shadow
    ):
        result = fd.compute_lifecycle_status("test_combo", "UP", discovered_path=discovered_path)
    assert result["lifecycle_status"] == "PASS"


# ── get_full_registry() merge ─────────────────────────────────────────

def test_get_full_registry_merges_static_and_discovered(tmp_path):
    from scripts.knowledge_system import fingerprint_tracker_001 as ft
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    discovered_path = tmp_path / "discovered.json"
    fd._persist_new_discovery("new_combo", "new combo", "DOWN", [("hv_20", "high")], discovered_path)

    registry = ft.get_full_registry(discovered_path=discovered_path)

    names = {fp["name"] for fp in registry}
    assert "UP_low_rsi_high_accel" in names  # static, unchanged
    assert "new_combo" in names               # discovered, merged in


def test_get_full_registry_unchanged_when_nothing_discovered(tmp_path):
    from scripts.knowledge_system import fingerprint_tracker_001 as ft
    from scripts.knowledge_system import fingerprint_discovery_001 as fd

    with patch.object(fd, "DISCOVERED_FINGERPRINTS_PATH", tmp_path / "none.json"):
        registry = ft.get_full_registry()
    assert registry == ft.FINGERPRINT_REGISTRY


# ── Orchestrator wiring ──────────────────────────────────────────────

def test_discovery_import_present():
    assert (
        "from scripts.knowledge_system.fingerprint_discovery_001 import (" in BODY
        and "run_discovery_silent as _run_fp_discovery" in BODY
    )


def test_discovery_call_present():
    assert "_run_fp_discovery()" in BODY


def test_discovery_runs_before_phase2e_tracker():
    idx_discovery = BODY.index("_run_fp_discovery()")
    idx_phase2e = BODY.index("_run_fp_tracking()")
    assert idx_discovery < idx_phase2e


def test_discovery_wrapped_in_try_except():
    idx_call = BODY.index("_run_fp_discovery()")
    preceding = BODY[max(0, idx_call - 300):idx_call]
    following = BODY[idx_call:idx_call + 900]
    assert "try:" in preceding
    assert "except Exception as _disc_exc:" in following
    assert (
        'log.warning("[Phase7-Discovery] fingerprint discovery failed (non-critical): %s", _disc_exc)'
        in following
    )


def test_completed_write_not_permanently_nested_after_discovery_except():
    idx_except = BODY.index("except Exception as _disc_exc:")
    idx_after_except = idx_except + len("except Exception as _disc_exc:")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    between = BODY[idx_after_except:idx_completed]
    assert between.count("try:") == between.count("except Exception")


def test_discovery_block_references_no_trading_modules():
    idx_call = BODY.index("_run_fp_discovery()")
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
        assert term not in code_only, f"Phase 7 integration block must not reference {term!r}"


def test_discovery_module_has_no_trading_imports():
    src = (ROOT / "scripts" / "knowledge_system" / "fingerprint_discovery_001.py").read_text(
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
            assert term not in line, f"fingerprint_discovery_001.py must not import {term!r}"
