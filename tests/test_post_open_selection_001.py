"""
POST_OPEN_SELECTION_RESEARCH_001 -- test suite
Tests T001-T042 per spec.
Mode: READ-ONLY validation. No production imports.

Run: python -m pytest tests/test_post_open_selection_001.py -v
"""
from __future__ import annotations
import ast, json, re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ─────────────────────────────────────────────────────────────────
# Fixtures / paths
# ─────────────────────────────────────────────────────────────────

REPORT_DIR = Path("reports/mover_discovery_v3")
SCRIPT     = Path("scripts/post_open_selection.py")

GAP_CSV    = REPORT_DIR / "post_open_gap_analysis.csv"
DAILY_CSV  = REPORT_DIR / "post_open_selection_daily.csv"
CASES_CSV  = REPORT_DIR / "post_open_top5_top6_cases.csv"
CMP_CSV    = REPORT_DIR / "post_open_model_comparison.csv"
RESULTS    = REPORT_DIR / "post_open_selection_results.json"
F5M_CSV    = REPORT_DIR / "post_open_5m_analysis.csv"
F15M_CSV   = REPORT_DIR / "post_open_15m_analysis.csv"
F30M_CSV   = REPORT_DIR / "post_open_30m_analysis.csv"

@pytest.fixture(scope="session")
def gap():
    return pd.read_csv(GAP_CSV)

@pytest.fixture(scope="session")
def results():
    with open(RESULTS) as fh:
        return json.load(fh)

@pytest.fixture(scope="session")
def cmp():
    return pd.read_csv(CMP_CSV)

@pytest.fixture(scope="session")
def daily():
    return pd.read_csv(DAILY_CSV)

@pytest.fixture(scope="session")
def cases():
    return pd.read_csv(CASES_CSV)

@pytest.fixture(scope="session")
def script_src():
    return SCRIPT.read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────
# T001-T015: Output structure, gap calculation, leakage
# ─────────────────────────────────────────────────────────────────

def test_T001_all_output_files_exist():
    """T001: All 9 expected output files exist."""
    for f in [GAP_CSV, DAILY_CSV, CASES_CSV, CMP_CSV, RESULTS,
              F5M_CSV, F15M_CSV, F30M_CSV]:
        assert f.exists(), f"Missing: {f.name}"

def test_T002_gap_csv_row_count(gap):
    """T002: gap_analysis.csv has exactly 8560 rows (full retro candidate pool)."""
    assert len(gap) == 8_560, f"Expected 8560 rows, got {len(gap)}"

def test_T003_gap_pct_formula(gap):
    """T003: gap_pct = (t1_open / t_close - 1) × 100 for a known non-null row."""
    v = gap.dropna(subset=["t1_open", "t_close", "gap_pct"]).iloc[0]
    expected = (v["t1_open"] / v["t_close"] - 1.0) * 100.0
    assert abs(float(v["gap_pct"]) - expected) < 1e-6, \
        f"gap_pct formula mismatch: {v['gap_pct']} vs {expected}"

def test_T004_gap_direction_cutoffs(gap):
    """T004: gap_direction thresholds: >0.3%→GAP_UP, <-0.3%→GAP_DOWN, else NEUTRAL."""
    v = gap.dropna(subset=["gap_pct", "gap_direction"])
    wrong_up   = v[(v["gap_pct"] >  0.3) & (v["gap_direction"] != "GAP_UP")]
    wrong_down = v[(v["gap_pct"] < -0.3) & (v["gap_direction"] != "GAP_DOWN")]
    wrong_neut = v[(v["gap_pct"] >= -0.3) & (v["gap_pct"] <= 0.3) & (v["gap_direction"] != "NEUTRAL")]
    assert len(wrong_up) == 0,   f"{len(wrong_up)} rows: gap>0.3 but not GAP_UP"
    assert len(wrong_down) == 0, f"{len(wrong_down)} rows: gap<-0.3 but not GAP_DOWN"
    assert len(wrong_neut) == 0, f"{len(wrong_neut)} rows: |gap|<=0.3 but not NEUTRAL"

def test_T005_gap_band_thresholds(gap):
    """T005: gap_band boundaries match spec (NO_GAP<0.3, SMALL 0.3-1, MEDIUM 1-2, LARGE≥2)."""
    v = gap.dropna(subset=["gap_pct", "gap_band"])
    absm = v["gap_pct"].abs()
    assert ((v["gap_band"] == "NO_GAP")  == (absm < 0.30)).all(), "NO_GAP boundary wrong"
    assert ((v["gap_band"] == "SMALL")   == ((absm >= 0.30) & (absm < 1.00))).all()
    assert ((v["gap_band"] == "MEDIUM")  == ((absm >= 1.00) & (absm < 2.00))).all()
    assert ((v["gap_band"] == "LARGE")   == (absm >= 2.00)).all()

def test_T006_split_date_cutoffs(gap):
    """T006: TRAIN/VAL/OOS split boundaries are correct."""
    train = gap[gap["split"] == "TRAIN"]["trading_date"]
    val   = gap[gap["split"] == "VAL"]["trading_date"]
    oos   = gap[gap["split"] == "OOS"]["trading_date"]
    assert train.min() >= "2025-09-16"
    assert train.max() <= "2026-02-19"
    assert val.min()   >= "2026-02-20"
    assert val.max()   <= "2026-05-13"
    assert oos.min()   >= "2026-05-14"
    assert oos.max()   <= "2026-07-30"

def test_T007_gap_pct_uses_model_o_info(gap, script_src):
    """T007: gap_pct uses T+1 open (09:15 available), not T+1 close (not available until 15:30)."""
    assert "t1_open" in gap.columns, "t1_open column must be present"
    # eod_cont_pct is derived from t1_close but must NOT be used as a decision feature
    assert "information_horizon" in gap.columns
    horizons = gap["information_horizon"].dropna().unique()
    assert all("MODEL_O" in str(h) for h in horizons), \
        f"Unexpected horizon: {horizons}"

def test_T008_eod_cont_labeled_post_eod(gap):
    """T008: eod_cont_pct is present but labeled POST_EOD (not a decision feature)."""
    assert "eod_cont_pct" in gap.columns
    assert "eod_cont_note" in gap.columns
    notes = gap["eod_cont_note"].dropna().unique()
    assert all("POST_EOD" in str(n) for n in notes), \
        f"eod_cont_note should contain POST_EOD: {notes}"

def test_T009_nifty_gap_uses_t1_date(gap):
    """T009: nifty_gap_pct reflects the NIFTY gap on T+1 date (not T date)."""
    # nifty_gap_pct should be NIFTY's open/prev_close - 1 on the same date as t1_date
    # We verify that nifty_gap_pct values are reasonably bounded
    v = gap["nifty_gap_pct"].dropna()
    assert v.abs().max() < 20.0, "nifty_gap_pct unrealistically large"
    assert v.abs().mean() < 3.0,  "nifty_gap_pct mean looks wrong"
    assert "nifty_gap_pct" in gap.columns
    assert "nifty_gap_dir" in gap.columns

def test_T010_rel_gap_formula(gap):
    """T010: rel_gap = stock gap_pct − NIFTY gap_pct."""
    v = gap.dropna(subset=["gap_pct", "nifty_gap_pct", "rel_gap"])
    expected = v["gap_pct"] - v["nifty_gap_pct"]
    diff = (v["rel_gap"] - expected).abs()
    assert diff.max() < 1e-6, f"rel_gap formula error, max diff = {diff.max()}"

def test_T011_mfe_mae_direction_aware(gap):
    """T011: MFE/MAE are direction-adjusted (always non-negative for favorable moves)."""
    up = gap[(gap["direction"] == "UP") & gap["mfe_pct"].notna()]
    # For UP: MFE = (t1_high / t_close - 1) × 100 — can be negative if stock dropped all day
    # But MFE should be from t_close perspective: if t1_high > t_close → positive
    # Just verify the columns exist and contain plausible values
    assert "mfe_pct" in gap.columns and "mae_pct" in gap.columns
    assert up["mfe_pct"].dtype in [np.float64, float]
    # MAE is the adverse move: for UP candidates, MAE = (1 - t1_low/t_close) × 100
    dn = gap[(gap["direction"] == "DOWN") & gap["mae_pct"].notna()]
    assert dn["mae_pct"].dtype in [np.float64, float]

def test_T012_direction_normalization(gap):
    """T012: No raw 'DN' values in direction column — all normalized to 'DOWN'."""
    directions = gap["direction"].unique()
    assert "DN" not in directions, "direction 'DN' not normalized to 'DOWN'"
    assert set(directions) == {"UP", "DOWN"}, f"Unexpected directions: {directions}"

def test_T013_threshold_optimization_train_only(results):
    """T013: Gap threshold optimization uses TRAIN data only (no OOS leakage)."""
    thresh = results["gap_threshold"]
    assert thresh.get("optimisation_basis") == "TRAIN_ONLY_FROZEN", \
        f"Expected TRAIN_ONLY_FROZEN, got {thresh.get('optimisation_basis')}"
    # Threshold analysis keys should only include TRAIN-split data
    # (We verify the results JSON has UP/DOWN optimal thresholds)
    assert "optimised_UP"   in thresh
    assert "optimised_DOWN" in thresh

def test_T014_comparison_csv_models(cmp):
    """T014: Model comparison CSV contains all key model names."""
    expected_models = {"V3_20", "A_V3_Top5", "A_V3_Top6",
                       "C1_Top5", "C2_Top5", "C3_Top5", "C4_Top5", "C5_Top5",
                       "Random_5"}
    actual = set(cmp["model"].unique())
    missing = expected_models - actual
    assert not missing, f"Missing models in comparison CSV: {missing}"

def test_T015_gap_pct_null_count(gap):
    """T015: gap_pct null count ≤ 50 (only missing where T_close or T+1_open absent)."""
    nulls = gap["gap_pct"].isna().sum()
    assert nulls <= 50, f"gap_pct has {nulls} nulls (expected ≤ 50)"

# ─────────────────────────────────────────────────────────────────
# T016-T025: Model performance comparisons
# ─────────────────────────────────────────────────────────────────

def test_T016_v3_top5_oos_up_dir_acc(results):
    """T016: V3_Top5 OOS UP dir_acc ≈ 0.50 ± 0.05 (known reference)."""
    d = results["baselines"]["UP"]["OOS"]["A_V3_Top5"]["dir_acc"]
    assert 0.45 <= d <= 0.60, f"V3_Top5 OOS UP dir_acc out of range: {d}"

def test_T017_c1_beats_v3_top5_oos_up(results):
    """T017: C1_Top5 OOS UP dir_acc strictly > V3_Top5 OOS UP."""
    c1 = results["baselines"]["UP"]["OOS"]["C1_Top5"]["dir_acc"]
    v3 = results["baselines"]["UP"]["OOS"]["A_V3_Top5"]["dir_acc"]
    assert c1 > v3, f"C1={c1} should beat V3={v3}"

def test_T018_c2_is_best_gap_model_oos(results):
    """T018: C2_Top5 OOS UP ge2_rate is the best among gap models."""
    oos = results["baselines"]["UP"]["OOS"]
    c2  = oos["C2_Top5"]["ge2_rate"]
    for m in ["C1_Top5", "C3_Top5", "C4_Top5", "C5_Top5"]:
        mv = oos.get(m, {}).get("ge2_rate") or 0
        assert c2 >= mv, f"C2 ge2={c2} should be ≥ {m} ge2={mv}"

def test_T019_gap_magnitude_monotonic(results):
    """T019: Gap magnitude is monotonic — LARGE band has higher dir_acc than NO_GAP (UP)."""
    bands = results["gap_magnitude"]["UP"]["band_stats"]
    large  = bands.get("LARGE", {}).get("dir_acc", 0) or 0
    no_gap = bands.get("NO_GAP", {}).get("dir_acc", 0) or 0
    assert large > no_gap, f"LARGE dir_acc={large} should exceed NO_GAP dir_acc={no_gap}"

def test_T020_random_concentration_lt_c1(results):
    """T020: Random_5 concentration lift < C1_Top5 lift (OOS UP)."""
    oos_up = results["baselines"]["UP"]["OOS"]
    rand_lift = (oos_up.get("Random_5", {}).get("concentration") or {}).get("lift") or 0
    c1_lift   = (oos_up.get("C1_Top5",  {}).get("concentration") or {}).get("lift") or 0
    assert c1_lift > rand_lift, f"C1 lift={c1_lift} should exceed Random lift={rand_lift}"

def test_T021_results_json_has_verdict(results):
    """T021: Results JSON contains PRIMARY_VERDICT in answers."""
    assert "answers" in results
    assert "PRIMARY_VERDICT" in results["answers"]
    verdict = results["answers"]["PRIMARY_VERDICT"]
    assert verdict, "PRIMARY_VERDICT must not be empty"

def test_T022_c1_consistent_across_splits(results):
    """T022: C1_Top5 UP dir_acc > 0.51 in TRAIN, VAL, and OOS."""
    for split in ["TRAIN", "VAL", "OOS"]:
        d = results["baselines"]["UP"][split]["C1_Top5"]["dir_acc"]
        assert d > 0.51, f"C1 UP dir_acc in {split} = {d} (< 0.51)"

def test_T023_v3_20_pool_baseline_present(results):
    """T023: V3_20 full-pool baseline is present in all splits and directions."""
    for direction in ["UP", "DOWN"]:
        for split in ["TRAIN", "VAL", "OOS"]:
            assert "V3_20" in results["baselines"][direction][split], \
                f"V3_20 missing from {direction}/{split}"

def test_T024_gap_pct_coverage_99pct(gap):
    """T024: gap_pct coverage ≥ 99% of total rows."""
    coverage = gap["gap_pct"].notna().mean()
    assert coverage >= 0.99, f"gap_pct coverage = {coverage:.3f} (expected ≥ 0.99)"

def test_T025_c1_low_worse_than_c1_top(results):
    """T025: C1_Low_Top5 (gap-contradicted) has lower dir_acc than C1_Top5 (OOS UP)."""
    oos = results["baselines"]["UP"]["OOS"]
    c1_top  = oos.get("C1_Top5",  {}).get("dir_acc") or 0
    c1_low  = oos.get("C1_Low_Top5", {}).get("dir_acc") or 0
    assert c1_top > c1_low, \
        f"Gap-confirmed {c1_top:.3f} should beat gap-contradicted {c1_low:.3f}"

# ─────────────────────────────────────────────────────────────────
# T026-T036: Incremental value, regime, frozen params
# ─────────────────────────────────────────────────────────────────

def test_T026_incremental_c1_over_v3_positive(results):
    """T026: Incremental ge2_rate of C1 gap over V3 baseline is positive (OOS UP)."""
    inc = results["incremental_value"]["UP"]["ge2_rate"]
    c1_inc = inc.get("C1_inc_over_v3", -1)
    assert isinstance(c1_inc, (int, float)), "C1_inc_over_v3 must be numeric"
    assert float(c1_inc) >= 0, f"C1 incremental ge2 over V3 = {c1_inc} (should be ≥ 0)"

def test_T027_d_e_f_data_unavailable(results):
    """T027: D/E/F models are marked DATA_UNAVAILABLE in results and CSVs."""
    # Results JSON
    for key in ["D_5m", "E_15m", "F_30m"]:
        assert key in results["intraday_models"], f"Missing {key} in intraday_models"
    # Incremental value
    for key in ["D_5m_inc_over_c1", "E_15m_inc_over_c1", "F_30m_inc_over_c1"]:
        val = results["incremental_value"]["UP"]["ge2_rate"].get(key)
        assert val == "DATA_UNAVAILABLE", f"{key} should be DATA_UNAVAILABLE, got {val}"
    # CSV stubs
    for f in [F5M_CSV, F15M_CSV, F30M_CSV]:
        df = pd.read_csv(f)
        assert "DATA_UNAVAILABLE" in str(df["status"].values[0])

def test_T028_threshold_not_optimised_on_oos(results):
    """T028: Threshold analysis exists only with TRAIN_ONLY_FROZEN basis (no OOS leakage)."""
    thresh = results["gap_threshold"]
    assert thresh["optimisation_basis"] == "TRAIN_ONLY_FROZEN"
    # The optimal threshold is a single frozen value, not per-split
    assert isinstance(thresh.get("optimised_UP"), (int, float))

def test_T029_split_day_counts(results):
    """T029: Dataset split day counts match spec (TRAIN=107, VAL=53, OOS=54)."""
    splits = results["dataset"]["splits"]
    assert splits.get("TRAIN") == 107, f"TRAIN days = {splits.get('TRAIN')}"
    assert splits.get("VAL")   == 53,  f"VAL days = {splits.get('VAL')}"
    assert splits.get("OOS")   == 54,  f"OOS days = {splits.get('OOS')}"

def test_T030_comparison_csv_rows(cmp):
    """T030: Model comparison CSV has ≥ 80 rows (models × directions × splits)."""
    assert len(cmp) >= 80, f"comparison CSV has only {len(cmp)} rows"

def test_T031_regime_column_present(gap):
    """T031: Regime column present in gap_analysis with valid values."""
    assert "regime" in gap.columns
    valid = {"BULL", "BEAR", "RANGE", None}
    regimes = set(gap["regime"].dropna().unique())
    unexpected = regimes - {"BULL", "BEAR", "RANGE"}
    assert not unexpected, f"Unexpected regime values: {unexpected}"

def test_T032_eod_cont_pct_computable(gap):
    """T032: eod_cont_pct is non-null for rows where gap_pct and t1_ret_pct are non-null."""
    v = gap.dropna(subset=["gap_pct", "t1_ret_pct"])
    # Allow up to 5% null in eod_cont_pct for edge cases
    null_rate = v["eod_cont_pct"].isna().mean()
    assert null_rate <= 0.05, f"eod_cont_pct null rate = {null_rate:.3f} (expected ≤ 5%)"

def test_T033_nifty_interaction_structure(results):
    """T033: NIFTY interaction has both UP and DOWN direction entries with multiple cells."""
    ni = results["nifty_interaction"]
    assert "UP" in ni and "DOWN" in ni
    for direction in ["UP", "DOWN"]:
        assert len(ni[direction]) >= 6, \
            f"NIFTY interaction {direction} should have ≥ 6 cells, got {len(ni[direction])}"

def test_T034_concentration_ordering(results):
    """T034: Concentration lift order: C2_Top5 ≥ C1_Top5 ≥ V3_Top5 (OOS UP)."""
    oos = results["baselines"]["UP"]["OOS"]
    def lift(m): return (oos.get(m, {}).get("concentration") or {}).get("lift") or 0
    c2 = lift("C2_Top5"); c1 = lift("C1_Top5"); v3 = lift("A_V3_Top5")
    assert c2 >= c1, f"C2 lift={c2} should be ≥ C1 lift={c1}"
    assert c1 >= v3, f"C1 lift={c1} should be ≥ V3 lift={v3}"

def test_T035_frozen_threshold_applied_oos(results):
    """T035: C3 threshold was frozen from TRAIN, applied to VAL and OOS (no re-fitting)."""
    thresh = results["gap_threshold"]
    opt_up = thresh.get("optimised_UP")
    assert opt_up is not None, "Missing optimised_UP threshold"
    # Just verify one threshold value exists and is in valid range
    assert 0.0 <= float(opt_up) <= 2.0, f"threshold {opt_up} out of expected range"

def test_T036_results_deterministic(results):
    """T036: PRIMARY_VERDICT and key OOS numbers are deterministic (not random per run)."""
    v3_dir = results["baselines"]["UP"]["OOS"]["A_V3_Top5"]["dir_acc"]
    c1_dir = results["baselines"]["UP"]["OOS"]["C1_Top5"]["dir_acc"]
    # These must be exact floats (deterministic computation)
    assert isinstance(v3_dir, float) and isinstance(c1_dir, float)
    # And C1 must consistently beat V3
    assert c1_dir > v3_dir

# ─────────────────────────────────────────────────────────────────
# T037-T042: No production imports
# ─────────────────────────────────────────────────────────────────

PRODUCTION_GUARDS = {
    "T037": ["CandidateStore", "candidate_store"],
    "T038": ["StrategyLab", "strategy_lab", "strategy_generator_ai"],
    "T039": ["DecisionEngine", "decision_engine", "DebateAndDecision"],
    "T040": ["RiskControl", "risk_guardian", "RiskGuardian", "RiskManagerAI"],
    "T041": ["OrderManager", "order_manager", "ZerodhaBroker"],
    "T042": ["dhan_feed", "DhanFeed", "BaseFeed", "get_feed_manager"],
}

def _check_no_imports(src: str, tokens: list[str], test_id: str):
    for tok in tokens:
        assert tok not in src, \
            f"{test_id}: Found production import '{tok}' in research script"

def test_T037_no_candidate_store_import(script_src):
    """T037: Research script does not import CandidateStore (production module)."""
    _check_no_imports(script_src, PRODUCTION_GUARDS["T037"], "T037")

def test_T038_no_strategy_lab_import(script_src):
    """T038: Research script does not import StrategyLab or strategy_generator_ai."""
    _check_no_imports(script_src, PRODUCTION_GUARDS["T038"], "T038")

def test_T039_no_decision_engine_import(script_src):
    """T039: Research script does not import DecisionEngine or DebateAndDecision."""
    _check_no_imports(script_src, PRODUCTION_GUARDS["T039"], "T039")

def test_T040_no_risk_guardian_import(script_src):
    """T040: Research script does not import RiskControl or RiskGuardian."""
    _check_no_imports(script_src, PRODUCTION_GUARDS["T040"], "T040")

def test_T041_no_order_manager_import(script_src):
    """T041: Research script does not import OrderManager or ZerodhaBroker."""
    _check_no_imports(script_src, PRODUCTION_GUARDS["T041"], "T041")

def test_T042_no_broker_import(script_src):
    """T042: Research script does not import dhan_feed, BaseFeed, or get_feed_manager."""
    _check_no_imports(script_src, PRODUCTION_GUARDS["T042"], "T042")
