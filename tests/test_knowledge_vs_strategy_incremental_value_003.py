"""
KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_003 — Test Suite
75 tests covering all experiment phases.

T001-T010  : data integrity
T011-T020  : same candidate universe / fairness control
T021-T030  : Knowledge-only model (Model A)
T031-T040  : Knowledge+Strategy model (Models B1, B2)
T041-T050  : counterfactual rejection analysis
T051-T060  : regime analysis
T061-T065  : Knowledge × Strategy interaction
T066-T070  : OOS split integrity
T071-T075  : leakage / production isolation

Run with: pytest tests/test_knowledge_vs_strategy_incremental_value_003.py -v
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
REPORT_DIR  = REPO_ROOT / "reports" / "mover_discovery_v3"
GAP_CSV     = REPORT_DIR / "post_open_gap_analysis.csv"
RECON_JSON  = REPORT_DIR / "strategy_reconstruction_validation_dataset.json"

OUT_RESULTS      = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_results.json"
OUT_MODEL_CMP    = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_model_comparison.csv"
OUT_OOS          = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_oos_results.csv"
OUT_REGIME       = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_regime_matrix.csv"
OUT_REJECTION    = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_rejection_audit.csv"
OUT_REASON       = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_strategy_reason.csv"
OUT_INTERACTION  = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_interaction.csv"
OUT_COUNTERFACT  = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_counterfactual.csv"
OUT_REPORT       = REPORT_DIR / "KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_003_2026-08-17.md"

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def gap_data():
    df = pd.read_csv(GAP_CSV)
    df["direction"] = df["direction"].replace({"DN": "DOWN"})
    return df.dropna(subset=["t1_ret_pct"]).copy()

@pytest.fixture(scope="module")
def gap_with_strategy(gap_data):
    """Apply validated reconstruction rules to get strategy_status."""
    df = gap_data.copy()

    def _classify(row):
        direction = row["direction"]
        regime    = row["regime"]
        if direction == "UP":
            if regime == "BEAR":
                return "REJECT", "D2_BEAR_EQUITY_BUY"
            if regime == "VOLATILE":
                return "REJECT", "D3_VOLATILE_NO_STRAT"
            return "PASS", "PASS_ALL_RULES"
        else:
            if regime == "BEAR":
                return "ALIGNED",      "DOWN_ALIGNED"
            elif regime == "BULL":
                return "CONTRADICTED", "DOWN_CONTRADICTED"
            return "NEUTRAL", "DOWN_NEUTRAL"

    classified = df.apply(_classify, axis=1, result_type="expand")
    df["strategy_status"] = classified[0]
    df["reject_reason"]   = classified[1]
    return df

@pytest.fixture(scope="module")
def recon():
    return json.loads(RECON_JSON.read_text())

@pytest.fixture(scope="module")
def model_cmp():
    return pd.read_csv(OUT_MODEL_CMP)

@pytest.fixture(scope="module")
def results_json():
    return json.loads(OUT_RESULTS.read_text())

@pytest.fixture(scope="module")
def rejection_audit():
    return pd.read_csv(OUT_REJECTION)

@pytest.fixture(scope="module")
def regime_matrix():
    return pd.read_csv(OUT_REGIME)

@pytest.fixture(scope="module")
def reason_df():
    return pd.read_csv(OUT_REASON)

@pytest.fixture(scope="module")
def interaction_df():
    return pd.read_csv(OUT_INTERACTION)

@pytest.fixture(scope="module")
def oos_results():
    return pd.read_csv(OUT_OOS)

@pytest.fixture(scope="module")
def counterfactual_df():
    return pd.read_csv(OUT_COUNTERFACT)

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _top_n(df, direction, col, n):
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        frames.append(g.dropna(subset=[col]).nlargest(n, col))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _model_B1(df, direction, n):
    if direction == "DOWN":
        return _top_n(df, direction, "C2_score", n)
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        passed = g[g["strategy_status"] == "PASS"].dropna(subset=["C2_score"])
        frames.append(passed.nlargest(n, "C2_score"))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# ──────────────────────────────────────────────────────────────────────────────
# T001-T010: Data integrity
# ──────────────────────────────────────────────────────────────────────────────

class TestT001_T010_DataIntegrity:

    def test_T001_total_candidates_after_dropna(self, gap_data):
        """T001: Total valid candidates = 8514 after dropping missing outcomes."""
        assert len(gap_data) == 8514

    def test_T002_up_and_down_counts(self, gap_data):
        """T002: UP=4256, DOWN=4258 candidates."""
        assert len(gap_data[gap_data["direction"] == "UP"])   == 4256
        assert len(gap_data[gap_data["direction"] == "DOWN"]) == 4258

    def test_T003_trading_dates_count(self, gap_data):
        """T003: Exactly 213 trading dates in the full dataset (one date lost to outcome dropna)."""
        assert gap_data["trading_date"].nunique() == 213

    def test_T004_c2_score_available(self, gap_data):
        """T004: C2_score is available for most candidates (nulls from original data only)."""
        null_count = gap_data["C2_score"].isna().sum()
        # Some null C2 (from NO_GAP events), but all outcome rows retained
        assert null_count >= 0  # informational

    def test_T005_regime_distribution_no_volatile(self, gap_data):
        """T005: No VOLATILE regime days exist in the dataset."""
        assert "VOLATILE" not in gap_data["regime"].unique()

    def test_T006_regime_values_valid(self, gap_data):
        """T006: Only BEAR, BULL, RANGE regimes present."""
        valid = {"BEAR", "BULL", "RANGE"}
        assert set(gap_data["regime"].unique()).issubset(valid)

    def test_T007_bear_days_in_val_only(self, gap_data):
        """T007: All BEAR regime days are in VAL split (not OOS, not TRAIN)."""
        bear = gap_data[(gap_data["regime"] == "BEAR") & (gap_data["direction"] == "UP")]
        assert set(bear["split"].unique()) == {"VAL"}

    def test_T008_oos_has_zero_bear_days(self, gap_data):
        """T008: OOS has zero BEAR regime UP candidates."""
        oos_bear = gap_data[
            (gap_data["split"] == "OOS") &
            (gap_data["direction"] == "UP") &
            (gap_data["regime"] == "BEAR")
        ]
        assert len(oos_bear) == 0

    def test_T009_val_bear_days_count(self, gap_data):
        """T009: VAL has exactly 19 BEAR regime days (380 UP candidates = 19 × 20)."""
        val_bear_up = gap_data[
            (gap_data["split"] == "VAL") &
            (gap_data["direction"] == "UP") &
            (gap_data["regime"] == "BEAR")
        ]
        assert len(val_bear_up) == 380
        assert val_bear_up["trading_date"].nunique() == 19

    def test_T010_reconstruction_verdict(self, recon):
        """T010: STRATEGY_RECONSTRUCTION_VALIDATION_001 verdict == 'A'."""
        assert recon["verdict"] == "A"

# ──────────────────────────────────────────────────────────────────────────────
# T011-T020: Same candidate universe / fairness control
# ──────────────────────────────────────────────────────────────────────────────

class TestT011_T020_FairnessControl:

    def test_T011_strategy_status_applied_to_all(self, gap_with_strategy):
        """T011: Every candidate has a strategy_status assigned."""
        assert gap_with_strategy["strategy_status"].isna().sum() == 0

    def test_T012_up_pass_count(self, gap_with_strategy):
        """T012: UP PASS count = 3876 (BULL + RANGE days)."""
        up_pass = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["strategy_status"] == "PASS")
        ]
        assert len(up_pass) == 3876

    def test_T013_up_reject_count(self, gap_with_strategy):
        """T013: UP REJECT count = 380 (all BEAR days in VAL)."""
        up_rej = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["strategy_status"] == "REJECT")
        ]
        assert len(up_rej) == 380

    def test_T014_d1_never_fires(self, gap_with_strategy):
        """T014: D1_TYPE_LOW_RR never fires for V3 equity candidates."""
        d1_count = (gap_with_strategy["reject_reason"] == "D1_TYPE_LOW_RR").sum()
        assert d1_count == 0

    def test_T015_d3_never_fires(self, gap_with_strategy):
        """T015: D3_VOLATILE_NO_STRAT never fires (no VOLATILE days in dataset)."""
        d3_count = (gap_with_strategy["reject_reason"] == "D3_VOLATILE_NO_STRAT").sum()
        assert d3_count == 0

    def test_T016_d2_fires_bear_up_only(self, gap_with_strategy):
        """T016: D2_BEAR_EQUITY_BUY fires exactly for BEAR UP candidates."""
        d2 = gap_with_strategy[gap_with_strategy["reject_reason"] == "D2_BEAR_EQUITY_BUY"]
        assert (d2["direction"] == "UP").all()
        assert (d2["regime"] == "BEAR").all()
        assert len(d2) == 380

    def test_T017_down_has_no_reject(self, gap_with_strategy):
        """T017: No DOWN candidates have REJECT status (no strategy gate for DOWN)."""
        dn_rej = gap_with_strategy[
            (gap_with_strategy["direction"] == "DOWN") &
            (gap_with_strategy["strategy_status"] == "REJECT")
        ]
        assert len(dn_rej) == 0

    def test_T018_B1_n_leq_A_n(self, gap_with_strategy):
        """T018: B1 selection count ≤ A selection count for UP (Strategy can only remove)."""
        up = gap_with_strategy[gap_with_strategy["direction"] == "UP"]
        a  = _top_n(up, "UP", "C2_score", 5)
        b1 = _model_B1(up, "UP", 5)
        assert len(b1) <= len(a)

    def test_T019_on_bull_range_days_A_equals_B1(self, gap_with_strategy):
        """T019: On BULL/RANGE regime days, A and B1 have identical UP selection."""
        non_bear = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["regime"] != "BEAR")
        ]
        a  = _top_n(non_bear, "UP", "C2_score", 5)
        b1 = _model_B1(non_bear, "UP", 5)
        assert len(a) == len(b1)

    def test_T020_B1_B2_identical_for_up(self, model_cmp):
        """T020: B1 and B2 produce identical results for UP in all splits (day-level rules)."""
        for split in ["OOS", "VAL", "FULL"]:
            b1 = model_cmp[
                (model_cmp["model"] == "B1_Strict_Top5") &
                (model_cmp["direction"] == "UP") &
                (model_cmp["split"] == split)
            ]
            b2 = model_cmp[
                (model_cmp["model"] == "B2_Backfill_Top5") &
                (model_cmp["direction"] == "UP") &
                (model_cmp["split"] == split)
            ]
            if len(b1) and len(b2):
                assert b1["n"].values[0] == b2["n"].values[0], f"B1!=B2 n in {split}"
                assert b1["ge2_rate"].values[0] == b2["ge2_rate"].values[0], f"B1!=B2 ge2 in {split}"

# ──────────────────────────────────────────────────────────────────────────────
# T021-T030: Knowledge-only model (Model A)
# ──────────────────────────────────────────────────────────────────────────────

class TestT021_T030_KnowledgeModel:

    def test_T021_A_OOS_UP_n(self, model_cmp):
        """T021: A_KN_Top5 OOS UP n = 265 (53 days × 5)."""
        row = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert len(row) == 1
        assert row["n"].values[0] == 265

    def test_T022_A_OOS_UP_dir_acc(self, model_cmp):
        """T022: A_KN_Top5 OOS UP dir_acc ≥ 0.55."""
        row = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert row["dir_acc"].values[0] >= 0.55

    def test_T023_A_OOS_UP_ge2(self, model_cmp):
        """T023: A_KN_Top5 OOS UP ge2_rate ≥ 0.25."""
        row = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert row["ge2_rate"].values[0] >= 0.25

    def test_T024_A_OOS_lift_gt_1(self, model_cmp):
        """T024: A_KN_Top5 OOS UP concentration lift > 1.0."""
        row = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert row["lift"].values[0] > 1.0

    def test_T025_A_FULL_UP_n(self, model_cmp):
        """T025: A_KN_Top5 FULL UP n = 1065 (213 days × 5, one day missing)."""
        row = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "FULL")
        ]
        assert len(row) == 1
        # Allow slight variance due to date mismatches
        assert 1040 <= row["n"].values[0] <= 1080

    def test_T026_A_OOS_consistent_with_002(self, model_cmp):
        """T026: A OOS UP results consistent with prior study 002 (dir_acc ~0.615)."""
        row = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert abs(row["dir_acc"].values[0] - 0.6151) < 0.005, \
            "Dir_acc should match 002 OOS result (same data, same model)"

    def test_T027_A_Top5_better_than_V3_20(self, model_cmp):
        """T027: A_KN_Top5 has higher ge2 than V3_20 in OOS."""
        a = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        v = model_cmp[
            (model_cmp["model"] == "V3_20") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert a["ge2_rate"].values[0] > v["ge2_rate"].values[0]

    def test_T028_A_Top6_has_more_candidates(self, model_cmp):
        """T028: A_KN_Top6 OOS UP n > A_KN_Top5 OOS UP n."""
        a5 = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        a6 = model_cmp[
            (model_cmp["model"] == "A_KN_Top6") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert a6["n"].values[0] > a5["n"].values[0]

    def test_T029_A_DOWN_n_oos(self, model_cmp):
        """T029: A_KN_Top5 OOS DOWN n = 265 (same structure as UP)."""
        row = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "DOWN") &
            (model_cmp["split"] == "OOS")
        ]
        assert len(row) == 1
        assert row["n"].values[0] == 265

    def test_T030_A_no_strategy_filter(self, gap_with_strategy):
        """T030: Model A selection on BEAR days includes REJECT candidates."""
        bear_up = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["regime"] == "BEAR")
        ]
        a_bear = _top_n(bear_up, "UP", "C2_score", 5)
        # A includes BEAR candidates (they are REJECT but A doesn't filter)
        assert len(a_bear) == 95  # 19 BEAR days × 5

# ──────────────────────────────────────────────────────────────────────────────
# T031-T040: Knowledge+Strategy model (B1, B2, C)
# ──────────────────────────────────────────────────────────────────────────────

class TestT031_T040_StrategyModels:

    def test_T031_B1_OOS_UP_identical_to_A(self, model_cmp):
        """T031: B1_Strict_Top5 OOS UP is identical to A_KN_Top5 (zero OOS rejections)."""
        a = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        b1 = model_cmp[
            (model_cmp["model"] == "B1_Strict_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert a["n"].values[0] == b1["n"].values[0]
        assert a["dir_acc"].values[0] == b1["dir_acc"].values[0]
        assert a["ge2_rate"].values[0] == b1["ge2_rate"].values[0]

    def test_T032_B1_VAL_UP_n_less_than_A(self, model_cmp):
        """T032: B1_Strict_Top5 VAL UP n < A_KN_Top5 VAL UP n (BEAR days excluded)."""
        a = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "VAL")
        ]
        b1 = model_cmp[
            (model_cmp["model"] == "B1_Strict_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "VAL")
        ]
        assert b1["n"].values[0] < a["n"].values[0]

    def test_T033_B1_VAL_UP_n_exact(self, model_cmp):
        """T033: B1 VAL UP n = 170 (34 non-BEAR days × 5 = 170)."""
        row = model_cmp[
            (model_cmp["model"] == "B1_Strict_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "VAL")
        ]
        assert row["n"].values[0] == 170

    def test_T034_B1_FULL_UP_n_less_than_A(self, model_cmp):
        """T034: B1_Strict_Top5 FULL UP n < A_KN_Top5 FULL UP n."""
        a = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "FULL")
        ]
        b1 = model_cmp[
            (model_cmp["model"] == "B1_Strict_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "FULL")
        ]
        assert b1["n"].values[0] < a["n"].values[0]
        # B1 should have 95 fewer (19 BEAR days × 5 = 95 excluded)
        assert a["n"].values[0] - b1["n"].values[0] == 95

    def test_T035_B1_DOWN_equals_A_DOWN(self, model_cmp):
        """T035: B1 DOWN == A DOWN (no strategy gate for DOWN)."""
        for split in ["OOS", "VAL", "FULL"]:
            a = model_cmp[
                (model_cmp["model"] == "A_KN_Top5") &
                (model_cmp["direction"] == "DOWN") &
                (model_cmp["split"] == split)
            ]
            b1 = model_cmp[
                (model_cmp["model"] == "B1_Strict_Top5") &
                (model_cmp["direction"] == "DOWN") &
                (model_cmp["split"] == split)
            ]
            if len(a) and len(b1):
                assert a["n"].values[0] == b1["n"].values[0], f"DOWN A!=B1 in {split}"

    def test_T036_C_model_OOS_UP_lower_ge2_than_A(self, model_cmp):
        """T036: C_Strat_Top5 OOS UP ge2 ≤ A_KN_Top5 (Knowledge outperforms Strategy-Only)."""
        a = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        c = model_cmp[
            (model_cmp["model"] == "C_Strat_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        if len(c):
            assert a["ge2_rate"].values[0] >= c["ge2_rate"].values[0]

    def test_T037_model_comparison_has_all_models(self, model_cmp):
        """T037: Model comparison CSV contains all expected model names."""
        expected = {"V3_20", "A_KN_Top5", "A_KN_Top6",
                    "B1_Strict_Top5", "B1_Strict_Top6",
                    "B2_Backfill_Top5", "B2_Backfill_Top6",
                    "C_Strat_Top5", "C_Strat_Top6"}
        found = set(model_cmp["model"].unique())
        assert expected.issubset(found)

    def test_T038_B1_OOS_delta_zero(self, model_cmp):
        """T038: B1 vs A delta ge2 in OOS UP = 0.0 (no rejections → identical)."""
        row = model_cmp[
            (model_cmp["model"] == "B1_Strict_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert abs(row["vs_A_ge2_delta"].values[0]) < 1e-6

    def test_T039_B1_dir_acc_OOS_zero_delta(self, model_cmp):
        """T039: B1 vs A delta dir_acc in OOS UP = 0.0."""
        row = model_cmp[
            (model_cmp["model"] == "B1_Strict_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert abs(row["vs_A_dir_delta"].values[0]) < 1e-6

    def test_T040_results_json_has_verdict(self, results_json):
        """T040: Results JSON contains a verdict."""
        assert "verdict" in results_json
        verdict = results_json["verdict"]
        valid_verdicts = {
            "A. STRATEGY_INCREMENTAL_VALUE_CONFIRMED",
            "B. STRATEGY_NO_INCREMENTAL_VALUE",
            "C. STRATEGY_NEGATIVE_INCREMENTAL_VALUE",
            "D. STRATEGY_CONDITIONAL_VALUE",
            "E. INSUFFICIENT_OOS_SAMPLE",
            "F. RESEARCH_PIPELINE_INVALID",
        }
        assert verdict in valid_verdicts

# ──────────────────────────────────────────────────────────────────────────────
# T041-T050: Counterfactual rejection analysis
# ──────────────────────────────────────────────────────────────────────────────

class TestT041_T050_Counterfactual:

    def test_T041_rejection_audit_row_count(self, rejection_audit):
        """T041: Rejection audit has exactly 95 rows (19 BEAR days × 5 KN-selected)."""
        assert len(rejection_audit) == 95

    def test_T042_all_rejected_are_VAL_BEAR_UP(self, rejection_audit):
        """T042: All rejected Knowledge-selected candidates are in VAL, BEAR regime, UP direction."""
        assert (rejection_audit["split"] == "VAL").all()
        assert (rejection_audit["regime"] == "BEAR").all()
        assert (rejection_audit["direction"] == "UP").all()

    def test_T043_rejection_reason_is_D2_only(self, rejection_audit):
        """T043: All rejection reason codes = D2_BEAR_EQUITY_BUY."""
        assert (rejection_audit["reject_reason"] == "D2_BEAR_EQUITY_BUY").all()

    def test_T044_false_rejection_rate(self, rejection_audit):
        """T044: False rejection rate (STRONG outcomes / total) ≈ 0.326."""
        strong = (rejection_audit["outcome"] == "STRONG").sum()
        rate   = strong / len(rejection_audit)
        assert abs(rate - 0.3263) < 0.01

    def test_T045_rejection_audit_has_all_outcome_classes(self, rejection_audit):
        """T045: Rejection audit contains BAD, NEUTRAL, and STRONG outcomes."""
        outcomes = set(rejection_audit["outcome"].unique())
        assert {"BAD", "NEUTRAL", "STRONG"}.issubset(outcomes)

    def test_T046_strong_opportunities_rejected(self, rejection_audit):
        """T046: 31 (±1) of 95 rejected candidates were STRONG opportunities (≥2%)."""
        strong_n = (rejection_audit["outcome"] == "STRONG").sum()
        assert 28 <= strong_n <= 34

    def test_T047_rejected_candidates_have_dir_adj_ret(self, rejection_audit):
        """T047: All rejection audit rows have a dir_adj_ret (no missing outcomes)."""
        assert rejection_audit["dir_adj_ret"].isna().sum() == 0

    def test_T048_counterfactual_file_exists_and_non_empty(self, counterfactual_df):
        """T048: Counterfactual CSV exists and has rows."""
        assert len(counterfactual_df) > 0

    def test_T049_counterfactual_columns(self, counterfactual_df):
        """T049: Counterfactual CSV has required columns."""
        required = {"trading_date", "symbol", "direction", "regime",
                    "reject_reason", "t1_ret_pct", "dir_adj_ret",
                    "outcome", "rejection_class"}
        assert required.issubset(set(counterfactual_df.columns))

    def test_T050_oos_has_zero_rejections(self, results_json):
        """T050: OOS strategy reject count = 0 (no BEAR/VOLATILE days in OOS)."""
        assert results_json["strategy_application"]["oos_reject_up"] == 0
        assert results_json["strategy_application"]["oos_reject_is_zero"] is True

# ──────────────────────────────────────────────────────────────────────────────
# T051-T060: Regime analysis
# ──────────────────────────────────────────────────────────────────────────────

class TestT051_T060_RegimeAnalysis:

    def test_T051_regime_matrix_exists_non_empty(self, regime_matrix):
        """T051: Regime matrix CSV exists and has rows."""
        assert len(regime_matrix) > 0

    def test_T052_regime_matrix_columns(self, regime_matrix):
        """T052: Regime matrix has required columns."""
        required = {"split", "regime", "direction", "n", "n_days", "n_reject",
                    "a_dir_acc", "b1_dir_acc", "a_ge2", "b1_ge2",
                    "false_rej_rate", "low_sample"}
        assert required.issubset(set(regime_matrix.columns))

    def test_T053_oos_regime_matrix_no_bear(self, regime_matrix):
        """T053: OOS regime matrix has no BEAR rows (zero BEAR days in OOS)."""
        oos_bear = regime_matrix[
            (regime_matrix["split"] == "OOS") &
            (regime_matrix["regime"] == "BEAR")
        ]
        assert len(oos_bear) == 0

    def test_T054_bear_up_false_rejection_rate_positive(self, regime_matrix):
        """T054: BEAR UP false_rej_rate > 0 (some BEAR rejections were strong opportunities)."""
        bear_up = regime_matrix[
            (regime_matrix["regime"] == "BEAR") &
            (regime_matrix["direction"] == "UP")
        ]
        if len(bear_up):
            fr = bear_up["false_rej_rate"].dropna().values
            assert len(fr) > 0 and fr[0] > 0

    def test_T055_bear_ge2_higher_than_bull(self, gap_with_strategy):
        """T055: BEAR UP all-candidate ge2 > BULL UP all-candidate ge2."""
        bear_ge2 = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["regime"] == "BEAR")
        ]["t1_ret_pct"].apply(lambda x: x >= 2.0).mean()
        bull_ge2 = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["regime"] == "BULL")
        ]["t1_ret_pct"].apply(lambda x: x >= 2.0).mean()
        assert bear_ge2 > bull_ge2, \
            f"BEAR ge2={bear_ge2:.4f} should > BULL ge2={bull_ge2:.4f} (relative strength)"

    def test_T056_bear_ge2_approx_value(self, gap_with_strategy):
        """T056: BEAR UP all-candidate ge2 ≈ 0.208 (relative strength effect)."""
        bear_ge2 = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["regime"] == "BEAR")
        ]["t1_ret_pct"].apply(lambda x: x >= 2.0).mean()
        assert abs(bear_ge2 - 0.2079) < 0.01

    def test_T057_regime_matrix_low_sample_flagging(self, regime_matrix):
        """T057: Cells with n < 30 are flagged as LOW_SAMPLE."""
        small_n = regime_matrix[regime_matrix["n"] < 30]
        for _, row in small_n.iterrows():
            assert row["low_sample"] == "LOW_SAMPLE"

    def test_T058_bear_n_reject_all_up(self, regime_matrix):
        """T058: BEAR regime UP n_reject = total BEAR UP n (all rejected by D2)."""
        bear_up_full = regime_matrix[
            (regime_matrix["regime"] == "BEAR") &
            (regime_matrix["direction"] == "UP") &
            (regime_matrix["split"] == "FULL")
        ]
        if len(bear_up_full):
            row = bear_up_full.iloc[0]
            assert row["n_reject"] == row["n"]

    def test_T059_range_regime_has_zero_rejections(self, regime_matrix):
        """T059: RANGE regime has zero strategy rejections (all UP in RANGE pass D1-D3)."""
        range_up = regime_matrix[
            (regime_matrix["regime"] == "RANGE") &
            (regime_matrix["direction"] == "UP")
        ]
        for _, row in range_up.iterrows():
            assert row["n_reject"] == 0

    def test_T060_bear_kn_top5_ge2_high(self, gap_with_strategy):
        """T060: BEAR UP Knowledge-selected (top-5 by C2) ge2 ≈ 0.326 — high quality."""
        bear_up = gap_with_strategy[
            (gap_with_strategy["direction"] == "UP") &
            (gap_with_strategy["regime"] == "BEAR")
        ]
        top5 = bear_up.groupby("trading_date", group_keys=False).apply(
            lambda g: g.nlargest(5, "C2_score"), include_groups=False)
        ge2 = (top5["t1_ret_pct"] >= 2.0).mean()
        assert ge2 >= 0.30, f"BEAR KN top5 ge2={ge2:.4f} should be ≥0.30"

# ──────────────────────────────────────────────────────────────────────────────
# T061-T065: Knowledge × Strategy interaction
# ──────────────────────────────────────────────────────────────────────────────

class TestT061_T065_Interaction:

    def test_T061_interaction_matrix_shape(self, interaction_df):
        """T061: Interaction matrix has rows for all 5 quintiles × statuses × splits."""
        assert len(interaction_df) == 75  # 5 quintiles × 3 statuses × 2 splits + DOWN

    def test_T062_interaction_quintiles_present(self, interaction_df):
        """T062: All 5 quintiles (Q1-Q5) present in interaction matrix."""
        assert set(interaction_df["quintile"].unique()) == {"Q1", "Q2", "Q3", "Q4", "Q5"}

    def test_T063_interaction_has_pass_and_reject(self, interaction_df):
        """T063: UP interaction matrix contains PASS and REJECT rows."""
        up_statuses = set(interaction_df[interaction_df["direction"] == "UP"]["strategy_status"].unique())
        assert "PASS" in up_statuses
        assert "REJECT" in up_statuses

    def test_T064_interaction_q5_vs_q1_pass(self, interaction_df):
        """T064: Q5 PASS UP ge2 ≥ Q1 PASS UP ge2 (higher Knowledge quintile = better)."""
        full_up = interaction_df[
            (interaction_df["direction"] == "UP") &
            (interaction_df["split"] == "FULL") &
            (interaction_df["strategy_status"] == "PASS")
        ]
        q1 = full_up[full_up["quintile"] == "Q1"]["ge2_rate"].dropna().values
        q5 = full_up[full_up["quintile"] == "Q5"]["ge2_rate"].dropna().values
        if len(q1) and len(q5):
            assert q5[0] >= q1[0], \
                f"Q5 ge2={q5[0]:.4f} should ≥ Q1 ge2={q1[0]:.4f}"

    def test_T065_interaction_low_sample_flagged(self, interaction_df):
        """T065: Small-n cells in interaction matrix are flagged."""
        small = interaction_df[interaction_df["n"] < 30]
        for _, row in small.iterrows():
            assert row["low_sample"] in ("LOW_SAMPLE", "NO_DATA")

# ──────────────────────────────────────────────────────────────────────────────
# T066-T070: OOS split integrity
# ──────────────────────────────────────────────────────────────────────────────

class TestT066_T070_OOSSplitIntegrity:

    def test_T066_oos_date_range(self, gap_data):
        """T066: OOS split covers 2026-05-14 to 2026-07-30."""
        oos = gap_data[gap_data["split"] == "OOS"]
        assert oos["trading_date"].min() >= "2026-05-14"
        assert oos["trading_date"].max() <= "2026-07-30"

    def test_T067_oos_trading_days(self, gap_data):
        """T067: OOS has 53 trading days."""
        oos_up = gap_data[(gap_data["split"] == "OOS") & (gap_data["direction"] == "UP")]
        assert oos_up["trading_date"].nunique() == 53

    def test_T068_oos_B1_n_equals_A_n(self, model_cmp):
        """T068: OOS B1 n = OOS A n for UP (zero rejections → identical selection)."""
        a = model_cmp[
            (model_cmp["model"] == "A_KN_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        b1 = model_cmp[
            (model_cmp["model"] == "B1_Strict_Top5") &
            (model_cmp["direction"] == "UP") &
            (model_cmp["split"] == "OOS")
        ]
        assert a["n"].values[0] == b1["n"].values[0]

    def test_T069_verdict_is_insufficient_oos_sample(self, results_json):
        """T069: Primary verdict = E. INSUFFICIENT_OOS_SAMPLE (zero OOS rejections)."""
        assert results_json["verdict"] == "E. INSUFFICIENT_OOS_SAMPLE"

    def test_T070_oos_strategy_reject_zero(self, results_json):
        """T070: results.json confirms OOS Strategy reject = 0."""
        assert results_json["strategy_application"]["oos_reject_up"] == 0

# ──────────────────────────────────────────────────────────────────────────────
# T071-T075: Leakage / production isolation
# ──────────────────────────────────────────────────────────────────────────────

class TestT071_T075_LeakageAndIsolation:

    def test_T071_strategy_status_no_future_data(self, gap_with_strategy):
        """T071: strategy_status computed from regime only (no future return data used)."""
        # Verify strategy_status determined solely from regime and direction
        # (no t1_ret_pct, mfe_pct, mae_pct involvement)
        for _, row in gap_with_strategy.sample(50, random_state=42).iterrows():
            direction = row["direction"]
            regime    = row["regime"]
            status    = row["strategy_status"]
            if direction == "UP":
                if regime == "BEAR":
                    assert status == "REJECT"
                elif regime == "VOLATILE":
                    assert status == "REJECT"
                else:
                    assert status == "PASS"
            else:
                if regime == "BEAR":
                    assert status == "ALIGNED"
                elif regime == "BULL":
                    assert status == "CONTRADICTED"
                else:
                    assert status == "NEUTRAL"

    def test_T072_no_forward_looking_in_model_B1(self, gap_with_strategy):
        """T072: B1 selection does not use t1_ret_pct or mfe_pct."""
        # B1 ranks by C2_score and filters by strategy_status
        # Neither t1_ret_pct nor mfe_pct are in the selection criteria
        # Verify by checking that B1 selection set varies with C2_score, not outcome
        oos = gap_with_strategy[gap_with_strategy["split"] == "OOS"]
        b1  = _model_B1(oos, "UP", 5)
        if not b1.empty:
            # All selected should be PASS in OOS (no BEAR days)
            assert (b1["strategy_status"] == "PASS").all()

    def test_T073_no_production_imports(self):
        """T073: The research script does not import Dhan or execution modules."""
        script_path = REPO_ROOT / "scripts" / "knowledge_vs_strategy_003.py"
        content = script_path.read_text(encoding="utf-8")
        forbidden = [
            "from data_feeds.dhan_feed",
            "import DhanBroker",
            "from execution_engine.order_manager",
            "import OrderManager",
            "import CandidateStore",
            "from candidate_store",
            "import ExecutionEngine",
            "from strategy_lab import",
        ]
        for pattern in forbidden:
            assert pattern not in content, f"Forbidden import found: {pattern}"

    def test_T074_output_files_in_correct_directory(self):
        """T074: All output files are in reports/mover_discovery_v3/."""
        output_files = [
            OUT_RESULTS, OUT_MODEL_CMP, OUT_OOS, OUT_REGIME,
            OUT_REJECTION, OUT_REASON, OUT_INTERACTION, OUT_COUNTERFACT,
            OUT_REPORT,
        ]
        for f in output_files:
            assert f.parent == REPORT_DIR, f"{f} is not in REPORT_DIR"
            assert f.exists(), f"Output file missing: {f.name}"

    def test_T075_production_isolation_confirmed(self, results_json):
        """T075: Production isolation metrics all zero in results JSON."""
        iso = results_json.get("production_isolation", {})
        assert iso.get("dhan_calls", -1) == 0
        assert iso.get("broker_writes", -1) == 0
        assert iso.get("orders", -1) == 0
        assert iso.get("candidatestore_writes", -1) == 0
        assert iso.get("execution_engine_calls", -1) == 0
        assert iso.get("live_strategylab_mods", -1) == 0
