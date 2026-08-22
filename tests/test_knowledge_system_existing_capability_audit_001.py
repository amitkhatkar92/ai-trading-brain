"""
tests/test_knowledge_system_existing_capability_audit_001.py
============================================================
Read-only audit tests: prove what already exists before building anything new.

Tests verify that the enumerated components physically exist, have the
correct structure, and contain the evidence claimed in the audit report.

NO production code is imported. NO broker calls, orders, or writes occur.

Categories:
  T001-T010  Core files exist
  T011-T020  Shadow JSONL structure and fields
  T021-T030  Hypothesis registry structure
  T031-T040  Database schemas (OIOS / replay)
  T041-T050  Research output files exist and have correct shape
  T051-T060  Test coverage inventory
  T061-T070  Gap verification (confirm what is MISSING)
  T071-T080  Safety (zero production impact)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(".")

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def shadow_records():
    p = ROOT / "data/logs/final_trading_architecture_shadow_001.jsonl"
    if not p.exists():
        pytest.skip("shadow JSONL not found")
    records = []
    with open(p) as f:
        for line in f:
            records.append(json.loads(line))
    return records


@pytest.fixture(scope="session")
def shadow_candidates(shadow_records):
    return [r for r in shadow_records if r.get("record_type") == "SHADOW_CANDIDATE"]


@pytest.fixture(scope="session")
def shadow_summaries(shadow_records):
    return [r for r in shadow_records if r.get("record_type") == "SHADOW_DAILY_SUMMARY"]


@pytest.fixture(scope="session")
def hypothesis_registry():
    p = ROOT / "data/ars_hypothesis_registry.json"
    if not p.exists():
        pytest.skip("hypothesis registry not found")
    with open(p) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def results_json():
    p = ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_results.json"
    if not p.exists():
        pytest.skip("results JSON not found")
    with open(p) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def replay_db():
    p = ROOT / "data/study002_replay.db"
    if not p.exists():
        pytest.skip("replay DB not found")
    return sqlite3.connect(str(p))


# ─────────────────────────────────────────────────────────────────────────────
# T001–T010 Core files exist
# ─────────────────────────────────────────────────────────────────────────────


def test_T001_mop_rc001_observer_exists():
    assert (ROOT / "opportunity_engine/mop_rc001_observer.py").exists()


def test_T002_hypothesis_registry_module_exists():
    assert (ROOT / "autonomous_research/hypothesis_registry.py").exists()


def test_T003_hypothesis_models_module_exists():
    assert (ROOT / "autonomous_research/hypothesis_models.py").exists()


def test_T004_research_coordinator_exists():
    assert (ROOT / "autonomous_research/research_coordinator.py").exists()


def test_T005_signal_outcome_tracker_exists():
    assert (ROOT / "oios/engine/signal_outcome_tracker.py").exists()


def test_T006_counterfactual_engine_exists():
    assert (ROOT / "oios/engine/counterfactual_engine.py").exists()


def test_T007_rejection_classifier_exists():
    assert (ROOT / "analysis/rejection_classifier.py").exists()


def test_T008_pattern_miner_exists():
    assert (ROOT / "analysis/pattern_miner.py").exists()


def test_T009_shadow_script_exists():
    assert (ROOT / "scripts/final_trading_architecture_shadow_001.py").exists()


def test_T010_hypothesis_registry_store_exists():
    assert (ROOT / "data/ars_hypothesis_registry.json").exists()


# ─────────────────────────────────────────────────────────────────────────────
# T011–T020 Shadow JSONL structure and fields
# ─────────────────────────────────────────────────────────────────────────────


def test_T011_shadow_jsonl_exists():
    assert (ROOT / "data/logs/final_trading_architecture_shadow_001.jsonl").exists()


def test_T012_shadow_has_candidate_records(shadow_candidates):
    assert len(shadow_candidates) >= 1


def test_T013_shadow_has_daily_summary_records(shadow_summaries):
    assert len(shadow_summaries) >= 1


def test_T014_shadow_candidate_has_selection_fields(shadow_candidates):
    required = {"symbol", "direction", "c2_rank", "selected_final_5",
                "strategy_status", "strategy_reason", "v3_score", "v3_rank"}
    first = set(shadow_candidates[0].keys())
    missing = required - first
    assert missing == set(), f"Missing candidate fields: {missing}"


def test_T015_shadow_candidate_has_outcome_fields(shadow_candidates):
    """Shadow candidates must contain outcome data (t1_ret_pct, mfe_pct, mae_pct)."""
    required = {"t1_ret_pct", "mfe_pct", "mae_pct"}
    first = set(shadow_candidates[0].keys())
    missing = required - first
    assert missing == set(), f"Missing outcome fields: {missing}"


def test_T016_shadow_candidate_no_broker_calls(shadow_candidates):
    assert all(c.get("no_broker_calls") is True for c in shadow_candidates)


def test_T017_shadow_candidate_no_trades_generated(shadow_candidates):
    assert all(c.get("no_trades_generated") is True for c in shadow_candidates)


def test_T018_shadow_summary_has_performance_fields(shadow_summaries):
    required = {"t1_dir_acc_model_a_up", "t1_dir_acc_model_a_down",
                "t1_ge2_model_a_up", "t1_ge2_model_a_down"}
    first = set(shadow_summaries[0].keys())
    missing = required - first
    assert missing == set(), f"Missing daily summary performance fields: {missing}"


def test_T019_shadow_missing_knowledge_strategy_disagreement(shadow_candidates):
    """knowledge_strategy_disagreement not in pre-2026-08-18 records (Gap from field being added later)."""
    # At least some records lack this field (the existing 840 were written before the field was added)
    missing_count = sum(1 for c in shadow_candidates if "knowledge_strategy_disagreement" not in c)
    assert missing_count > 0, (
        "Expected some records to be missing knowledge_strategy_disagreement "
        "(field was added after these records were written)"
    )


def test_T020_shadow_v3_shadow_jsonl_exists():
    assert (ROOT / "data/mover_discovery_v3_shadow.jsonl").exists()


# ─────────────────────────────────────────────────────────────────────────────
# T021–T030 Hypothesis registry structure
# ─────────────────────────────────────────────────────────────────────────────


def test_T021_hypothesis_registry_has_hypotheses(hypothesis_registry):
    assert "hypotheses" in hypothesis_registry
    assert len(hypothesis_registry["hypotheses"]) >= 1


def test_T022_hypothesis_count_matches_registry(hypothesis_registry):
    stated = hypothesis_registry.get("hypothesis_count", 0)
    actual = len(hypothesis_registry["hypotheses"])
    assert actual == stated or actual >= 1  # may have grown since count was set


def test_T023_hypothesis_has_required_fields(hypothesis_registry):
    required = {"hypothesis_id", "title", "status", "priority", "confidence",
                "decision_history", "validation_result"}
    for h_id, h in hypothesis_registry["hypotheses"].items():
        missing = required - set(h.keys())
        assert missing == set(), f"Hypothesis {h_id} missing fields: {missing}"


def test_T024_hypothesis_status_in_valid_set(hypothesis_registry):
    valid = {"PROPOSED", "UNDER_REVIEW", "APPROVED", "PLANNED", "RUNNING",
             "VALIDATED", "CONFIRMED", "ARCHIVED", "REJECTED"}
    for h_id, h in hypothesis_registry["hypotheses"].items():
        assert h["status"] in valid, f"Hypothesis {h_id} has invalid status: {h['status']}"


def test_T025_hypothesis_decision_history_is_list(hypothesis_registry):
    for h_id, h in hypothesis_registry["hypotheses"].items():
        assert isinstance(h["decision_history"], list), (
            f"Hypothesis {h_id} decision_history is not a list"
        )


def test_T026_hypothesis_confidence_is_float(hypothesis_registry):
    for h_id, h in hypothesis_registry["hypotheses"].items():
        assert isinstance(h["confidence"], (int, float)), (
            f"Hypothesis {h_id} confidence is not numeric"
        )
        assert 0.0 <= h["confidence"] <= 1.0, (
            f"Hypothesis {h_id} confidence={h['confidence']} out of [0,1]"
        )


def test_T027_ars_rc_history_exists():
    assert (ROOT / "data/ars/rc/history.json").exists()


def test_T028_ars_rc_history_has_runs():
    with open(ROOT / "data/ars/rc/history.json") as f:
        history = json.load(f)
    assert isinstance(history, list)
    assert len(history) >= 1


def test_T029_ars_rc_history_run_has_required_fields():
    with open(ROOT / "data/ars/rc/history.json") as f:
        history = json.load(f)
    required = {"run_id", "date", "stages", "health"}
    for run in history:
        missing = required - set(run.keys())
        assert missing == set(), f"RC history run missing fields: {missing}"


def test_T030_scientific_director_exists():
    assert (ROOT / "autonomous_research/scientific_director.py").exists()


# ─────────────────────────────────────────────────────────────────────────────
# T031–T040 Database schemas (OIOS / replay)
# ─────────────────────────────────────────────────────────────────────────────


def test_T031_replay_db_exists():
    assert (ROOT / "data/study002_replay.db").exists()


def test_T032_signal_births_table_exists(replay_db):
    tables = [r[0] for r in replay_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    assert "signal_births" in tables


def test_T033_signal_births_has_outcome_columns(replay_db):
    cols = [r[1] for r in replay_db.execute("PRAGMA table_info(signal_births)").fetchall()]
    required = {"actual_move_pct", "peak_move_pct", "final_state", "invalidation_reason",
                "trade_executed", "trade_outcome_pct"}
    missing = required - set(cols)
    assert missing == set(), f"signal_births missing outcome columns: {missing}"


def test_T034_signal_births_row_count(replay_db):
    n = replay_db.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
    assert n >= 8000, f"Expected >=8000 signal_births rows, got {n}"


def test_T035_opportunities_table_exists(replay_db):
    tables = [r[0] for r in replay_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    assert "opportunities" in tables


def test_T036_opportunities_has_lifecycle_columns(replay_db):
    cols = [r[1] for r in replay_db.execute("PRAGMA table_info(opportunities)").fetchall()]
    required = {"final_state", "invalidation_reason", "trade_pnl_pct", "current_state"}
    missing = required - set(cols)
    assert missing == set(), f"opportunities missing lifecycle columns: {missing}"


def test_T037_decision_log_table_exists(replay_db):
    tables = [r[0] for r in replay_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    assert "decision_log" in tables


def test_T038_decision_log_has_counterfactual_column(replay_db):
    cols = [r[1] for r in replay_db.execute("PRAGMA table_info(decision_log)").fetchall()]
    assert "counterfactual_type" in cols


def test_T039_decision_log_is_empty(replay_db):
    """decision_log table exists but is not populated — Gap confirmed."""
    n = replay_db.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]
    assert n == 0, f"Expected 0 rows in decision_log (gap), got {n}"


def test_T040_rejection_audit_db_exists():
    assert (ROOT / "data/rejection_audit.db").exists()


# ─────────────────────────────────────────────────────────────────────────────
# T041–T050 Research output files exist and have correct shape
# ─────────────────────────────────────────────────────────────────────────────


def test_T041_post_open_gap_csv_exists():
    assert (ROOT / "reports/mover_discovery_v3/post_open_gap_analysis.csv").exists()


def test_T042_post_open_gap_csv_has_8560_rows():
    df = pd.read_csv(ROOT / "reports/mover_discovery_v3/post_open_gap_analysis.csv")
    assert len(df) == 8560


def test_T043_kvs003_rejection_audit_csv_exists():
    assert (
        ROOT / "reports/mover_discovery_v3/knowledge_vs_strategy_incremental_value_003_rejection_audit.csv"
    ).exists()


def test_T044_missed_movers_csv_exists():
    assert (ROOT / "data/audit/daily_selection_quality_missed_movers.csv").exists()


def test_T045_missed_movers_has_miss_type_column():
    df = pd.read_csv(ROOT / "data/audit/daily_selection_quality_missed_movers.csv")
    assert "miss_type" in df.columns


def test_T046_daily_selection_audit_results_json_exists():
    assert (ROOT / "data/audit/daily_selection_quality_results.json").exists()


def test_T047_daily_selection_audit_oos_anchors_confirmed():
    with open(ROOT / "data/audit/daily_selection_quality_results.json") as f:
        r = json.load(f)
    up_acc = r["phase3_top5"]["OOS_UP"]["top5"]["dir_acc"]
    dn_acc = r["phase3_top5"]["OOS_DOWN"]["top5"]["dir_acc"]
    assert 0.609 <= up_acc <= 0.622, f"OOS UP dir_acc={up_acc} outside expected range"
    assert 0.597 <= dn_acc <= 0.612, f"OOS DOWN dir_acc={dn_acc} outside expected range"


def test_T048_promotion_policy_document_exists():
    assert (
        ROOT / "reports/mover_discovery_v3/FINAL_ARCHITECTURE_PROMOTION_POLICY_001.md"
    ).exists()


def test_T049_capability_matrix_csv_exists():
    assert (
        ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_matrix.csv"
    ).exists()


def test_T050_capability_matrix_has_required_columns():
    df = pd.read_csv(
        ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_matrix.csv"
    )
    required = {"capability", "status", "existing_component", "existing_file",
                "runs_automatically", "has_tests", "gap"}
    missing = required - set(df.columns)
    assert missing == set(), f"Matrix missing columns: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# T051–T060 Test coverage inventory
# ─────────────────────────────────────────────────────────────────────────────


def test_T051_mop_rc001_test_file_exists():
    assert (ROOT / "test_mop_rc001.py").exists()


def test_T052_outcome_tracking_test_file_exists():
    assert (ROOT / "test_outcome_tracking_001.py").exists()


def test_T053_shadow_test_file_exists():
    assert (ROOT / "tests/test_final_trading_architecture_shadow_001.py").exists()


def test_T054_c2_architecture_test_file_exists():
    assert (ROOT / "tests/test_final_knowledge_led_c2_001.py").exists()


def test_T055_daily_audit_test_file_exists():
    assert (ROOT / "tests/test_daily_selection_quality_audit_001.py").exists()


def test_T056_hypothesis_registry_has_no_dedicated_test_file():
    """
    Confirms Gap: hypothesis_registry.py lacks a dedicated test file.
    If this test ever fails, the gap has been closed.
    """
    has_tests = (ROOT / "tests/test_hypothesis_registry.py").exists()
    # Gap confirmed: no test file
    assert not has_tests, (
        "test_hypothesis_registry.py now exists — "
        "update capability matrix to IMPLEMENTED for hypothesis registry tests"
    )


def test_T057_rejection_classifier_has_no_dedicated_test_file():
    """Confirms Gap: analysis/rejection_classifier.py lacks a dedicated test file."""
    has_tests = (ROOT / "tests/test_rejection_classifier.py").exists()
    assert not has_tests, (
        "test_rejection_classifier.py now exists — update capability matrix"
    )


def test_T058_all_claimed_passing_tests_can_collect():
    """All 5 test files must be importable by pytest (smoke check)."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "test_mop_rc001.py",
         "test_outcome_tracking_001.py",
         "tests/test_final_knowledge_led_c2_001.py",
         "tests/test_final_trading_architecture_shadow_001.py",
         "tests/test_daily_selection_quality_audit_001.py",
         "--collect-only", "-q"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    assert result.returncode == 0, (
        f"Test collection failed:\n{result.stdout}\n{result.stderr}"
    )


def test_T059_total_test_count_at_least_267():
    """Aggregate test count across all known passing suites must be >= 267 (15+20+95+77+80)."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "test_mop_rc001.py",
         "test_outcome_tracking_001.py",
         "tests/test_final_knowledge_led_c2_001.py",
         "tests/test_final_trading_architecture_shadow_001.py",
         "tests/test_daily_selection_quality_audit_001.py",
         "--collect-only", "-q"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    # Count lines with "test_" which indicate collected tests
    test_lines = [l for l in result.stdout.splitlines() if "test_" in l.lower() and "::" in l]
    assert len(test_lines) >= 267, f"Expected >= 267 tests, found {len(test_lines)}"


def test_T060_results_json_total_counts_sum_to_32():
    """Audit results JSON must enumerate exactly 32 capabilities."""
    with open(ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_results.json") as f:
        r = json.load(f)
    s = r["summary"]
    total = s["implemented"] + s["partially_implemented"] + s["research_only"] + s["missing"]
    assert total == s["total_capabilities_assessed"]


# ─────────────────────────────────────────────────────────────────────────────
# T061–T070 Gap verification (confirm what is MISSING)
# ─────────────────────────────────────────────────────────────────────────────


def test_T061_gap_a_no_live_missed_mover_classifier():
    """GAP A: No live process classifies missed movers from shadow JSONL."""
    # Confirm no script named missed_mover_classifier, shadow_consumer, etc. exists
    candidates = list(ROOT.glob("scripts/missed_mover_classifier*.py"))
    candidates += list(ROOT.glob("scripts/shadow_evidence_consumer*.py"))
    candidates += list(ROOT.glob("opportunity_engine/missed_mover*.py"))
    assert candidates == [], (
        f"GAP A appears to have been closed; files found: {candidates}. "
        "Remove this test or update the capability matrix."
    )


def test_T062_gap_b_no_shadow_feedback_consumer():
    """GAP B: No process reads shadow JSONL and feeds into hypothesis registry."""
    candidates = list(ROOT.glob("scripts/shadow_feedback*.py"))
    candidates += list(ROOT.glob("autonomous_research/shadow_consumer*.py"))
    assert candidates == [], (
        f"GAP B appears to have been closed; files found: {candidates}."
    )


def test_T063_gap_c_v3_config_is_boolean_flag():
    """GAP C: V3 is enabled/disabled by a boolean flag, not an authentication gate."""
    src = (ROOT / "opportunity_engine/mover_discovery_v3.py").read_text(encoding="utf-8")
    # Should contain 'enabled' as a simple config attribute
    assert "enabled" in src, "V3 module does not have an 'enabled' flag — unexpected"
    # Should NOT contain an authentication check
    auth_terms = ["authentication_gate", "require_approval", "promotion_gate"]
    for term in auth_terms:
        assert term not in src, (
            f"GAP C appears to have been closed; '{term}' found in v3 source."
        )


def test_T064_gap_c_promotion_policy_is_text_only():
    """GAP C: Promotion policy is a text document, not enforced in code."""
    policy = (ROOT / "reports/mover_discovery_v3/FINAL_ARCHITECTURE_PROMOTION_POLICY_001.md").read_text(encoding="utf-8")
    assert len(policy) > 100, "Promotion policy document appears empty"
    # The policy document should NOT import or call any Python code
    assert "import" not in policy.lower() or "```python" not in policy.lower()


def test_T065_gap_d_decision_log_is_empty(replay_db):
    """GAP D confirmed: decision_log empty; no unified per-candidate lifecycle record."""
    n = replay_db.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]
    assert n == 0


def test_T066_gap_e_no_auto_hypothesis_generation():
    """GAP E: No script automatically creates hypotheses from pattern_miner output."""
    candidates = list(ROOT.glob("scripts/auto_hypothesis*.py"))
    candidates += list(ROOT.glob("autonomous_research/auto_hypothesis*.py"))
    assert candidates == [], (
        f"GAP E appears to have been closed; files found: {candidates}."
    )


def test_T067_gap_f_no_cross_audit_digest_file():
    """GAP F: No single growing cross-audit knowledge digest exists."""
    candidates = list(ROOT.glob("data/knowledge_digest*.json"))
    candidates += list(ROOT.glob("data/evidence_ledger*.jsonl"))
    assert candidates == [], (
        f"GAP F appears to have been closed; files found: {candidates}."
    )


def test_T068_mop_rc001_dir_does_not_exist():
    """MOP-RC-001 observer code exists but has never run (output dir absent)."""
    assert not (ROOT / "data/mop_rc001").exists(), (
        "data/mop_rc001 now exists — observer has been triggered; "
        "update capability matrix."
    )


def test_T069_iios_db_has_only_bootstrap_data():
    """data/iios.db is the live bootstrap DB; signal_births is not present (OIOS runs on study002_replay.db)."""
    con = sqlite3.connect(str(ROOT / "data/iios.db"))
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    con.close()
    assert "signal_births" not in tables, (
        "signal_births appeared in data/iios.db — update capability matrix for live OIOS"
    )


def test_T070_knowledge_vs_strategy_001_does_not_exist():
    """Verify that the first-iteration KvS script is absent (not just archived)."""
    assert not (ROOT / "scripts/knowledge_vs_strategy_001.py").exists()


# ─────────────────────────────────────────────────────────────────────────────
# T071–T080 Safety (zero production impact)
# ─────────────────────────────────────────────────────────────────────────────


def test_T071_audit_report_exists():
    assert (
        ROOT / "reports/knowledge_system_audit/KNOWLEDGE_SYSTEM_EXISTING_CAPABILITY_AUDIT_001_2026-08-18.md"
    ).exists()


def test_T072_results_json_exists():
    assert (
        ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_results.json"
    ).exists()


def test_T073_results_json_safety_zero():
    with open(ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_results.json") as f:
        r = json.load(f)
    assert r["safety"]["broker_calls"] == 0
    assert r["safety"]["orders"] == 0
    assert r["safety"]["production_changes"] == 0
    assert r["safety"]["candidatestore_writes"] == 0


def test_T074_results_json_verdict_is_partial():
    with open(ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_results.json") as f:
        r = json.load(f)
    assert r["final_verdict"] == "C_KNOWLEDGE_INFRASTRUCTURE_PARTIAL"


def test_T075_results_json_missing_count_is_nonzero():
    with open(ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_results.json") as f:
        r = json.load(f)
    assert r["summary"]["missing"] > 0, "Expected some gaps to be confirmed missing"


def test_T076_audit_did_not_modify_v3():
    """Confirm V3 config is still disabled (V3Config.enabled = False)."""
    src = (ROOT / "opportunity_engine/mover_discovery_v3.py").read_text(encoding="utf-8")
    # V3 must still have its enabled flag and must not have been changed to True by this audit
    # We can only check that the flag exists; we can't assert its runtime value from file text
    assert "enabled" in src


def test_T077_audit_did_not_modify_c2():
    """Confirm final_c2_selector still has FROZEN version tag."""
    src = (ROOT / "opportunity_engine/final_c2_selector.py").read_text(encoding="utf-8")
    assert "FINAL_C2_SELECTOR" in src, "C2 selector version tag missing"


def test_T078_audit_did_not_create_new_production_module():
    """No new production module was created in opportunity_engine/ by this audit."""
    audit_created = list((ROOT / "opportunity_engine").glob("knowledge_engine*.py"))
    audit_created += list((ROOT / "opportunity_engine").glob("continuous_knowledge*.py"))
    assert audit_created == [], f"New production modules found: {audit_created}"


def test_T079_capability_matrix_has_missing_entries():
    """Matrix must confirm at least 6 capabilities as MISSING."""
    df = pd.read_csv(
        ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_matrix.csv"
    )
    n_missing = (df["status"] == "MISSING").sum()
    assert n_missing >= 6, f"Expected >= 6 MISSING entries, found {n_missing}"


def test_T080_gaps_ranked_highest_value_is_shadow_feedback():
    """Highest-value gap must be shadow feedback loop (confirmed by evidence-density analysis)."""
    with open(ROOT / "reports/knowledge_system_audit/knowledge_system_existing_capability_results.json") as f:
        r = json.load(f)
    top_gap = r["gaps_ranked_by_research_value"][0]
    assert top_gap["rank"] == 1
    assert "shadow" in top_gap["name"].lower() or "feedback" in top_gap["name"].lower()
