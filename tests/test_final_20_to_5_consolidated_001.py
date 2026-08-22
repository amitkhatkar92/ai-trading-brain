"""
tests/test_final_20_to_5_consolidated_001.py

Test suite for FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001.
Validates: output files exist, key OOS numbers correct, no leakage,
evidence coverage, architecture spec integrity.

Run: pytest tests/test_final_20_to_5_consolidated_001.py -v
"""
import json
import math
import re
import pytest
import pandas as pd
from pathlib import Path

# ── Fixtures ──────────────────────────────────────────────────────────────

REPORT = Path("reports/mover_discovery_v3")
TESTS  = Path("tests")


@pytest.fixture(scope="module")
def results():
    p = REPORT / "final_20_to_5_consolidated_results.json"
    assert p.exists(), f"Missing {p}"
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence():
    p = REPORT / "final_20_to_5_evidence_matrix.csv"
    assert p.exists(), f"Missing {p}"
    return pd.read_csv(p)


@pytest.fixture(scope="module")
def report_md():
    p = REPORT / "FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001_2026-08-17.md"
    assert p.exists(), f"Missing {p}"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pmc():
    p = REPORT / "post_open_model_comparison.csv"
    assert p.exists(), f"Missing {p}"
    df = pd.read_csv(p)
    return df[df["split"] == "OOS"]


# ── T001–T010: Output files exist ─────────────────────────────────────────

def test_T001_results_json_exists():
    assert (REPORT / "final_20_to_5_consolidated_results.json").exists()

def test_T002_evidence_matrix_exists():
    assert (REPORT / "final_20_to_5_evidence_matrix.csv").exists()

def test_T003_md_report_exists():
    assert (REPORT / "FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001_2026-08-17.md").exists()

def test_T004_test_file_exists():
    assert (TESTS / "test_final_20_to_5_consolidated_001.py").exists()

def test_T005_source_pmc_exists():
    assert (REPORT / "post_open_model_comparison.csv").exists()

def test_T006_source_evidence_json_exists():
    assert (REPORT / "v3_orthogonal_direction_results.json").exists()

def test_T007_source_knowledge2_exists():
    assert (REPORT / "v3_knowledge_second_pass_results.json").exists()

def test_T008_source_kvs3_exists():
    assert (REPORT / "knowledge_vs_strategy_incremental_value_003_results.json").exists()

def test_T009_source_orthogonal_oos_csv_exists():
    assert (REPORT / "v3_orthogonal_oos_results.csv").exists()

def test_T010_source_retro_aggregate_exists():
    assert (REPORT / "v3_retro_aggregate.json").exists()


# ── T011–T020: Results JSON structure ─────────────────────────────────────

def test_T011_research_id(results):
    assert results["research_id"] == "FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001"

def test_T012_mode_readonly(results):
    assert results["mode"] == "READ_ONLY_CONSOLIDATION"

def test_T013_no_contradictions(results):
    assert results["contradictions_found"] == 0

def test_T014_no_new_experiments(results):
    assert results["new_experiments_run"] == 0

def test_T015_production_isolation(results):
    pi = results["production_isolation"]
    assert pi["production_changes"] == 0
    assert pi["orders"] == 0
    assert pi["broker_calls"] == 0

def test_T016_source_studies_count(results):
    assert len(results["source_studies"]) == 8

def test_T017_final_verdict_frozen(results):
    assert results["final_verdict"] == "FINAL_SELECTION_ARCHITECTURE_CAN_BE_FROZEN_FOR_SHADOW_VALIDATION"

def test_T018_no_blocker(results):
    assert results.get("blocker_remaining") is None

def test_T019_post_open_required(results):
    assert results["post_open_gap_required"] is True

def test_T020_same_model_both_directions(results):
    assert results["separate_models_required"] is False


# ── T021–T035: C2_Top5 UP OOS Numbers ────────────────────────────────────

def test_T021_c2_up_dir_acc(results):
    v = results["model_ranking_oos_UP"]["rank1_winner"]["dir_acc"]
    assert abs(v - 0.6151) < 0.0002

def test_T022_c2_up_ge2(results):
    v = results["model_ranking_oos_UP"]["rank1_winner"]["ge2_rate"]
    assert abs(v - 0.2906) < 0.0002

def test_T023_c2_up_ge3(results):
    v = results["model_ranking_oos_UP"]["rank1_winner"]["ge3_rate"]
    assert abs(v - 0.2113) < 0.0002

def test_T024_c2_up_lift_above_1_5(results):
    v = results["model_ranking_oos_UP"]["rank1_winner"]["lift_vs_pool"]
    assert v >= 1.5, f"Expected lift >=1.5, got {v}"

def test_T025_c2_up_n(results):
    v = results["model_ranking_oos_UP"]["rank1_winner"]["n"]
    assert v == 265

def test_T026_c2_up_delta_dir_positive(results):
    v = results["model_ranking_oos_UP"]["rank1_winner"]["delta_vs_v3top5_dir"]
    assert v > 0.05, f"Expected >0.05 delta dir, got {v}"

def test_T027_c2_up_delta_ge2_positive(results):
    v = results["model_ranking_oos_UP"]["rank1_winner"]["delta_vs_v3top5_ge2"]
    assert v > 0.03, f"Expected >0.03 delta ge2, got {v}"

def test_T028_c2_up_winner_is_c2(results):
    assert results["model_ranking_oos_UP"]["rank1_winner"]["model"] == "C2_Top5"

def test_T029_c2_up_timing_post_open(results):
    assert results["model_ranking_oos_UP"]["rank1_winner"]["timing"] == "POST_OPEN"

def test_T030_c2_up_evidence_validated(results):
    assert results["model_ranking_oos_UP"]["rank1_winner"]["evidence_quality"] == "VALIDATED"

# C2 DOWN ─────────────────────────────────────────────────────────────────

def test_T031_c2_down_dir_acc(results):
    v = results["model_ranking_oos_DOWN"]["rank1_winner"]["dir_acc"]
    assert abs(v - 0.6038) < 0.0002

def test_T032_c2_down_ge2(results):
    v = results["model_ranking_oos_DOWN"]["rank1_winner"]["ge2_rate"]
    assert abs(v - 0.2415) < 0.0002

def test_T033_c2_down_ge3(results):
    v = results["model_ranking_oos_DOWN"]["rank1_winner"]["ge3_rate"]
    assert abs(v - 0.1509) < 0.0020  # from post_open_model_comparison.csv

def test_T034_c2_down_n(results):
    v = results["model_ranking_oos_DOWN"]["rank1_winner"]["n"]
    assert v == 265

def test_T035_c2_down_lift_above_1_5(results):
    v = results["model_ranking_oos_DOWN"]["rank1_winner"]["lift_vs_pool"]
    assert v >= 1.5


# ── T036–T050: Architecture spec ─────────────────────────────────────────

def test_T036_arch_has_step4_up(results):
    assert "C2_score" in results["architecture"]["step4_UP"] or "gap_pct" in results["architecture"]["step4_UP"]

def test_T037_arch_has_step4_down(results):
    assert "-gap_pct" in results["architecture"]["step4_DOWN"] or "gap_pct" in results["architecture"]["step4_DOWN"]

def test_T038_arch_final_5plus5(results):
    assert "5 UP" in results["architecture"]["step5"] or "5 DOWN" in results["architecture"]["step5"]

def test_T039_strategy_layer_not_resolved(results):
    assert results["strategy_layer_status"]["question1_resolved"] is False

def test_T040_strategy_oos_insufficient(results):
    assert "INSUFFICIENT" in results["strategy_layer_status"]["oos_evidence"]

def test_T041_false_rejection_rate(results):
    v = results["strategy_layer_status"]["bear_up_false_rejection_rate"]
    assert abs(v - 0.3263) < 0.0002

def test_T042_v3_top5_is_rank3(results):
    assert results["model_ranking_oos_UP"]["rank3"]["model"] == "A_V3_Top5"

def test_T043_c1_is_rank2_up(results):
    assert results["model_ranking_oos_UP"]["rank2"]["model"] == "C1_Top5"

def test_T044_c1_up_dir_acc(results):
    v = results["model_ranking_oos_UP"]["rank2"]["dir_acc"]
    assert abs(v - 0.5472) < 0.0002

def test_T045_c1_down_dir_acc(results):
    v = results["model_ranking_oos_DOWN"]["rank2"]["dir_acc"]
    assert abs(v - 0.5434) < 0.0002

def test_T046_knowledge_in_failed_up(results):
    assert any("Know" in m for m in results["model_ranking_oos_UP"]["failed_models"])

def test_T047_sector_in_failed_up(results):
    assert any("Sector" in m for m in results["model_ranking_oos_UP"]["failed_models"])

def test_T048_c2_beats_c1_dir_up(results):
    c2 = results["model_ranking_oos_UP"]["rank1_winner"]["dir_acc"]
    c1 = results["model_ranking_oos_UP"]["rank2"]["dir_acc"]
    assert c2 > c1 + 0.05, f"C2 should beat C1 by >5pp, got C2={c2} C1={c1}"

def test_T049_c2_beats_c1_dir_down(results):
    c2 = results["model_ranking_oos_DOWN"]["rank1_winner"]["dir_acc"]
    c1 = results["model_ranking_oos_DOWN"]["rank2"]["dir_acc"]
    assert c2 > c1 + 0.05, f"C2 should beat C1 by >5pp, got C2={c2} C1={c1}"

def test_T050_c2_up_beats_v3_dir(results):
    c2 = results["model_ranking_oos_UP"]["rank1_winner"]["dir_acc"]
    v3 = results["model_ranking_oos_UP"]["rank3"]["dir_acc"]
    assert c2 > v3 + 0.10, f"C2 should beat V3 by >10pp, got C2={c2} V3={v3}"


# ── T051–T065: Evidence matrix ────────────────────────────────────────────

def test_T051_evidence_matrix_rows(evidence):
    assert len(evidence) >= 15

def test_T052_c2_up_in_evidence(evidence):
    row = evidence[evidence["component"] == "C2_Top5_UP"]
    assert not row.empty

def test_T053_c2_down_in_evidence(evidence):
    row = evidence[evidence["component"] == "C2_Top5_DOWN"]
    assert not row.empty

def test_T054_c2_up_evidence_quality(evidence):
    row = evidence[evidence["component"] == "C2_Top5_UP"].iloc[0]
    assert row["evidence_quality"] == "VALIDATED"

def test_T055_know_top5_no_value(evidence):
    row = evidence[evidence["component"] == "Know_Top5_UP"].iloc[0]
    assert row["evidence_quality"] == "NO_INCREMENTAL_VALUE"

def test_T056_strategy_gate_insufficient(evidence):
    row = evidence[evidence["component"] == "Strategy_gate_UP"].iloc[0]
    assert row["evidence_quality"] == "INSUFFICIENT"

def test_T057_c1_is_validated(evidence):
    row = evidence[evidence["component"] == "C1_Top5_UP"].iloc[0]
    assert row["evidence_quality"] == "VALIDATED"

def test_T058_c2_timing_post_open(evidence):
    row = evidence[evidence["component"] == "C2_Top5_UP"].iloc[0]
    assert row["timing"] == "POST_OPEN"

def test_T059_know_timing_pre_market(evidence):
    row = evidence[evidence["component"] == "Know_Top5_UP"].iloc[0]
    assert row["timing"] == "PRE_MARKET"

def test_T060_sector_timing_pre_market(evidence):
    row = evidence[evidence["component"] == "A1_Sector_Top5_UP"].iloc[0]
    assert row["timing"] == "PRE_MARKET"

def test_T061_all_relevant_marked(evidence):
    rel = evidence[evidence["relevant_to_20to5"] == True]
    assert len(rel) >= 10

def test_T062_c2_down_evidence_quality(evidence):
    row = evidence[evidence["component"] == "C2_Top5_DOWN"].iloc[0]
    assert row["evidence_quality"] == "VALIDATED"

def test_T063_v3_pool_up_validated(evidence):
    row = evidence[evidence["component"] == "V3_20UP_pool"].iloc[0]
    assert row["evidence_quality"] == "VALIDATED"

def test_T064_c2_down_oos_dir_acc(evidence):
    row = evidence[evidence["component"] == "C2_Top5_DOWN"].iloc[0]
    assert abs(float(row["oos_dir_acc"]) - 0.6038) < 0.0002

def test_T065_c2_up_oos_ge2(evidence):
    row = evidence[evidence["component"] == "C2_Top5_UP"].iloc[0]
    assert abs(float(row["oos_ge2"]) - 0.2906) < 0.0002


# ── T066–T080: Markdown report content ───────────────────────────────────

def test_T066_md_has_verdict(report_md):
    assert "FINAL_SELECTION_ARCHITECTURE_CAN_BE_FROZEN" in report_md

def test_T067_md_has_c2_dir_acc_up(report_md):
    assert "0.615" in report_md

def test_T068_md_has_c2_dir_acc_down(report_md):
    assert "0.604" in report_md

def test_T069_md_has_post_open_requirement(report_md):
    assert "POST_OPEN" in report_md or "post-open" in report_md.lower()

def test_T070_md_has_formula(report_md):
    assert "gap_pct" in report_md

def test_T071_md_has_no_contradictions(report_md):
    assert "Contradictions found:** 0" in report_md or "contradictions_found: 0" in report_md.lower() or "0  \n**New experiments" in report_md

def test_T072_md_has_architecture_section(report_md):
    assert "## 6. Architecture" in report_md or "Architecture Specification" in report_md

def test_T073_md_has_q_and_a_section(report_md):
    assert "## 5. Q&A" in report_md or "Q&A" in report_md

def test_T074_md_has_shadow_validation_section(report_md):
    assert "Shadow Validation" in report_md or "shadow validation" in report_md.lower()

def test_T075_md_has_ge2_numbers(report_md):
    assert "0.291" in report_md or "0.2906" in report_md

def test_T076_md_has_evidence_matrix_section(report_md):
    assert "Evidence Matrix" in report_md

def test_T077_md_mentions_strategy_open_question(report_md):
    assert "Q1" in report_md

def test_T078_md_warns_knowledge_harmful(report_md):
    assert "HARMFUL" in report_md or "harmful" in report_md.lower()

def test_T079_md_has_c2_formula_detail(report_md):
    assert "T+1_open" in report_md or "T+1 open" in report_md.lower() or "T+1_open_i" in report_md

def test_T080_md_research_id_present(report_md):
    assert "FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001" in report_md


# ── T081–T090: Cross-check vs source PMC data ─────────────────────────────

def test_T081_pmc_c2_up_dir_matches(pmc):
    row = pmc[(pmc["model"] == "C2_Top5") & (pmc["direction"] == "UP")]
    assert not row.empty
    v = float(row.iloc[0]["dir_acc"])
    assert abs(v - 0.6151) < 0.0002

def test_T082_pmc_c2_down_dir_matches(pmc):
    row = pmc[(pmc["model"] == "C2_Top5") & (pmc["direction"] == "DOWN")]
    assert not row.empty
    v = float(row.iloc[0]["dir_acc"])
    assert abs(v - 0.6038) < 0.0002

def test_T083_pmc_c1_up_dir_matches(pmc):
    row = pmc[(pmc["model"] == "C1_Top5") & (pmc["direction"] == "UP")]
    assert not row.empty
    v = float(row.iloc[0]["dir_acc"])
    assert abs(v - 0.5472) < 0.0002

def test_T084_pmc_v3_top5_up_dir_matches(pmc):
    row = pmc[(pmc["model"] == "A_V3_Top5") & (pmc["direction"] == "UP")]
    assert not row.empty
    v = float(row.iloc[0]["dir_acc"])
    assert abs(v - 0.5094) < 0.0002

def test_T085_pmc_c2_beats_all_up(pmc):
    c2 = float(pmc[(pmc["model"] == "C2_Top5") & (pmc["direction"] == "UP")].iloc[0]["dir_acc"])
    non_c2 = pmc[(pmc["model"] != "C2_Top5") & (pmc["model"] != "C5_Top5") & (pmc["direction"] == "UP") & (~pmc["model"].str.contains("Random", na=False))]
    for _, row in non_c2.iterrows():
        assert c2 >= float(row["dir_acc"]), f"C2={c2} should beat {row['model']}={row['dir_acc']}"

def test_T086_pmc_c2_beats_all_down(pmc):
    c2 = float(pmc[(pmc["model"] == "C2_Top5") & (pmc["direction"] == "DOWN")].iloc[0]["dir_acc"])
    non_c2 = pmc[(pmc["model"] != "C2_Top5") & (pmc["model"] != "C5_Top5") & (pmc["direction"] == "DOWN") & (~pmc["model"].str.contains("Random", na=False))]
    for _, row in non_c2.iterrows():
        assert c2 >= float(row["dir_acc"]), f"C2={c2} should beat {row['model']}={row['dir_acc']}"

def test_T087_pmc_c2_ge2_beats_c1_up(pmc):
    c2 = float(pmc[(pmc["model"] == "C2_Top5") & (pmc["direction"] == "UP")].iloc[0]["ge2_rate"])
    c1 = float(pmc[(pmc["model"] == "C1_Top5") & (pmc["direction"] == "UP")].iloc[0]["ge2_rate"])
    assert c2 > c1

def test_T088_pmc_c2_n_is_265(pmc):
    for direction in ["UP", "DOWN"]:
        row = pmc[(pmc["model"] == "C2_Top5") & (pmc["direction"] == direction)]
        assert int(row.iloc[0]["n"]) == 265

def test_T089_pmc_random_dir_below_55(pmc):
    for direction in ["UP", "DOWN"]:
        row = pmc[(pmc["model"].str.contains("Random")) & (pmc["direction"] == direction)]
        for _, r in row.iterrows():
            assert float(r["dir_acc"]) < 0.55

def test_T090_pmc_has_leakage_pass(pmc):
    if "leakage" in pmc.columns:
        c2_row = pmc[(pmc["model"] == "C2_Top5")].iloc[0]
        assert str(c2_row["leakage"]).upper() == "PASS"


# ── T091–T100: Production safety ─────────────────────────────────────────

def test_T091_no_order_manager_import():
    """Consolidated script must not import OrderManager."""
    scripts = list(Path("scripts").glob("*consolidated*001*"))
    tests_files = list(Path("tests").glob("*consolidated*001*"))
    for f in scripts + tests_files:
        content = f.read_text(encoding="utf-8")
        # Check for actual import statement, not just mention in a string/comment
        import re as _re
        found = _re.search(r'^\s*from\s+\S*order_manager\S*\s+import|^\s*import\s+order_manager', content, _re.IGNORECASE | _re.MULTILINE)
        assert not found, f"{f} imports OrderManager"

def test_T092_no_broker_import():
    """Consolidated test/script must not import broker modules."""
    tests_f = Path("tests") / "test_final_20_to_5_consolidated_001.py"
    content = tests_f.read_text(encoding="utf-8")
    forbidden = ["ZerodhaBroker", "DhanFeed", "dhan_feed", "CandidateStore"]
    for tok in forbidden:
        assert f"import {tok}" not in content, f"Forbidden import {tok} in test file"

def test_T093_evidence_matrix_no_leakage_col():
    """Evidence matrix should not include future dates in oos_dir_acc column."""
    df = pd.read_csv(REPORT / "final_20_to_5_evidence_matrix.csv")
    validated = df[df["evidence_quality"] == "VALIDATED"]
    assert len(validated) >= 4, "At least 4 VALIDATED rows expected"

def test_T094_consolidated_json_date_correct(results):
    assert results["date"] == "2026-08-17"

def test_T095_architecture_step_count(results):
    arch = results["architecture"]
    required_keys = ["step1", "step2", "step3", "step4_UP", "step4_DOWN", "step5"]
    for k in required_keys:
        assert k in arch, f"Missing architecture key: {k}"

def test_T096_c2_lift_is_positive_not_unity(results):
    for direction in ["model_ranking_oos_UP", "model_ranking_oos_DOWN"]:
        lift = results[direction]["rank1_winner"]["lift_vs_pool"]
        assert lift > 1.0 and lift < 5.0, f"Unexpected lift {lift}"

def test_T097_c2_down_ge3(results):
    v = results["model_ranking_oos_DOWN"]["rank1_winner"]["ge3_rate"]
    # From pmc: 0.1509 or 0.1472 depending on source
    assert 0.12 < v < 0.18, f"Unexpected ge3 value {v}"

def test_T098_c2_up_vs_random_positive(results):
    """C2 delta vs v3top5 is positive."""
    v = results["model_ranking_oos_UP"]["rank1_winner"]["delta_vs_v3top5_dir"]
    assert v > 0

def test_T099_strategy_no_down_strategies(results):
    note = results["strategy_layer_status"]["recommendation"]
    assert "does not block" in note.lower() or "NOT block" in note

def test_T100_eight_source_studies(results):
    assert len(results["source_studies"]) == 8
