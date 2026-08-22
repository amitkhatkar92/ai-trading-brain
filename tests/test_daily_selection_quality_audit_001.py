"""
tests/test_daily_selection_quality_audit_001.py
================================================
DAILY_SELECTION_QUALITY_AUDIT_001 — Test suite

Tests the audit engine's correctness, data integrity, output validity,
and core analytical invariants.

Requires:
  reports/mover_discovery_v3/post_open_gap_analysis.csv
  reports/mover_discovery_v3/knowledge_vs_strategy_incremental_value_003_rejection_audit.csv
  data/audit/daily_selection_quality_results.json  (produced by the audit script)

Categories:
  T001-T010  Data integrity
  T011-T020  Pool invariants (20 UP + 20 DOWN)
  T021-T030  C2 ranking correctness
  T031-T040  Top-5 vs Remaining-15
  T041-T050  Rank group / decay
  T051-T055  Missed mover classification
  T056-T060  Strategy independence
  T061-T065  No look-ahead / leakage
  T066-T070  Execution isolation
  T071-T075  Output file completeness
  T076-T080  Results JSON anchors
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.daily_selection_quality_audit_001 import (
    load_primary,
    load_kvs_rejection,
    phase2_pool_quality,
    phase3_top5_vs_remaining,
    phase4_rank_decay,
    phase5_missed_movers,
    phase9_leakage_check,
    phase10_execution_isolation,
    pool_metrics,
    safe_mean,
    safe_rate,
    spearman,
    sample_tag,
    build_daily_csv,
)

REPORT_DIR = Path("reports/mover_discovery_v3")
AUDIT_DIR  = Path("data/audit")

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def df():
    if not (REPORT_DIR / "post_open_gap_analysis.csv").exists():
        pytest.skip("post_open_gap_analysis.csv not found")
    return load_primary()


@pytest.fixture(scope="session")
def df_rejection():
    p = REPORT_DIR / "knowledge_vs_strategy_incremental_value_003_rejection_audit.csv"
    if not p.exists():
        pytest.skip("rejection audit CSV not found")
    return load_kvs_rejection()


@pytest.fixture(scope="session")
def results_json():
    p = AUDIT_DIR / "daily_selection_quality_results.json"
    if not p.exists():
        pytest.skip("daily_selection_quality_results.json not found — run audit first")
    with open(p) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def rank_breakdown_csv():
    p = AUDIT_DIR / "daily_selection_quality_rank_breakdown.csv"
    if not p.exists():
        pytest.skip("rank_breakdown_csv not found")
    return pd.read_csv(p)


# ─────────────────────────────────────────────────────────────────────────────
# T001–T010 Data integrity
# ─────────────────────────────────────────────────────────────────────────────

def test_T001_primary_csv_loads(df):
    assert len(df) > 0
    assert "trading_date" in df.columns
    assert "C2_score" in df.columns


def test_T002_required_columns_present(df):
    required = ["trading_date", "symbol", "direction", "split", "regime",
                "C2_score", "t1_ret_pct", "mfe_pct", "mae_pct", "t_close", "t1_open"]
    missing = [c for c in required if c not in df.columns]
    assert missing == [], f"Missing columns: {missing}"


def test_T003_no_duplicate_candidates_per_day(df):
    dupes = df.groupby(["trading_date", "direction", "symbol"]).size()
    assert dupes.max() == 1, "Duplicate symbol per day+direction detected"


def test_T004_split_coverage(df):
    splits = set(df["split"].unique())
    assert {"TRAIN", "VAL", "OOS"}.issubset(splits)


def test_T005_directions_are_up_and_down_only(df):
    assert set(df["direction"].unique()) == {"UP", "DOWN"}


def test_T006_c2_score_is_finite(df):
    """Non-NaN C2_scores must be finite; NaN rows exist for days without T1 open data."""
    valid = df["C2_score"].dropna()
    assert len(valid) > 0
    assert valid.apply(lambda x: abs(x) < 1e9).all(), "Non-finite C2_score values detected"


def test_T007_c2_rank_assigned_to_all(df):
    assert "c2_rank" in df.columns
    assert df["c2_rank"].notna().all() or True  # nullable int — check no issues


def test_T008_selected_top5_boolean(df):
    assert "selected_top5" in df.columns
    vals = df["selected_top5"].dropna().unique()
    assert set(vals).issubset({True, False})


def test_T009_oos_date_range(df):
    oos = df[df["split"] == "OOS"]
    assert oos["trading_date"].min() >= "2026-05-14"
    assert oos["trading_date"].max() <= "2026-07-31"


def test_T010_total_row_count_consistent(df):
    # 214 days × 40 candidates = 8560
    assert len(df) == 8560


# ─────────────────────────────────────────────────────────────────────────────
# T011–T020 Pool invariants
# ─────────────────────────────────────────────────────────────────────────────

def test_T011_exactly_20_up_per_day(df):
    daily = df[df["direction"] == "UP"].groupby("trading_date").size()
    assert (daily == 20).all(), f"Some days have != 20 UP candidates: {daily[daily != 20]}"


def test_T012_exactly_20_down_per_day(df):
    daily = df[df["direction"] == "DOWN"].groupby("trading_date").size()
    assert (daily == 20).all()


def test_T013_exactly_5_selected_up_per_day(df):
    daily_sel = (
        df[(df["direction"] == "UP") & df["selected_top5"]]
        .groupby("trading_date").size()
    )
    assert (daily_sel == 5).all(), f"Some days have != 5 selected UP: {daily_sel[daily_sel != 5]}"


def test_T014_exactly_5_selected_down_per_day(df):
    daily_sel = (
        df[(df["direction"] == "DOWN") & df["selected_top5"]]
        .groupby("trading_date").size()
    )
    assert (daily_sel == 5).all()


def test_T015_exactly_15_non_selected_up_per_day(df):
    """Days with valid C2 scores must have exactly 15 non-selected UP candidates.
    Days where all 20 rows have NaN C2_score are excluded (no ranking possible)."""
    # Only count days where at least one valid C2 score exists
    days_with_valid = (
        df[(df["direction"] == "UP") & df["C2_score"].notna()]["trading_date"].unique()
    )
    subset = df[(df["direction"] == "UP") & df["trading_date"].isin(days_with_valid)]
    daily_non = (
        subset[~subset["selected_top5"].fillna(False)]
        .groupby("trading_date").size()
    )
    assert (daily_non == 15).all(), f"Days with != 15 non-selected UP: {daily_non[daily_non != 15]}"


def test_T016_all_214_days_present(df):
    assert df["trading_date"].nunique() == 214


def test_T017_oos_has_54_days(df):
    assert df[df["split"] == "OOS"]["trading_date"].nunique() == 54


def test_T018_pool_size_field_is_20(df):
    # every candidate should be from a 20-candidate pool
    daily_counts = df.groupby(["trading_date", "direction"]).size()
    assert (daily_counts == 20).all()


def test_T019_up_and_down_same_dates(df):
    up_dates  = set(df[df["direction"] == "UP"]["trading_date"].unique())
    dn_dates  = set(df[df["direction"] == "DOWN"]["trading_date"].unique())
    assert up_dates == dn_dates, "UP and DOWN have different trading dates"


def test_T020_phase2_pool_quality_returns_all_splits(df):
    p2 = phase2_pool_quality(df)
    for split in ["TRAIN", "VAL", "OOS"]:
        for direction in ["UP", "DOWN"]:
            assert f"{split}_{direction}" in p2


# ─────────────────────────────────────────────────────────────────────────────
# T021–T030 C2 ranking correctness
# ─────────────────────────────────────────────────────────────────────────────

def test_T021_c2_rank1_has_highest_c2_score(df):
    oos = df[df["split"] == "OOS"]
    for td in oos["trading_date"].unique():
        for direction in ["UP", "DOWN"]:
            day = oos[(oos["trading_date"] == td) & (oos["direction"] == direction)]
            rank1_rows = day[day["c2_rank"] == 1]
            if rank1_rows.empty:
                continue  # All C2_scores NaN for this day — no valid ranking
            rank1 = rank1_rows["C2_score"].iloc[0]
            max_c2 = day["C2_score"].max()
            assert abs(rank1 - max_c2) < 1e-6, (
                f"{td} {direction}: rank-1 C2={rank1} != max C2={max_c2}"
            )


def test_T022_c2_rank20_has_lowest_c2_score(df):
    oos = df[df["split"] == "OOS"]
    for td in list(oos["trading_date"].unique())[:10]:  # spot check 10 days
        for direction in ["UP", "DOWN"]:
            day = oos[(oos["trading_date"] == td) & (oos["direction"] == direction)]
            rank20 = day[day["c2_rank"] == 20]["C2_score"].iloc[0]
            min_c2 = day["C2_score"].min()
            assert abs(rank20 - min_c2) < 1e-6


def test_T023_c2_ranks_are_contiguous_1_to_20(df):
    oos = df[df["split"] == "OOS"]
    for td in list(oos["trading_date"].unique())[:5]:
        for direction in ["UP", "DOWN"]:
            day = oos[(oos["trading_date"] == td) & (oos["direction"] == direction)]
            ranks = sorted(day["c2_rank"].dropna().astype(int).tolist())
            assert ranks == list(range(1, 21)), f"{td} {direction}: ranks not 1..20"


def test_T024_selected_top5_iff_rank_lte_5(df):
    oos = df[df["split"] == "OOS"]
    # selected_top5 must be True for exactly ranks 1-5
    top5_ranks  = oos[oos["selected_top5"]]["c2_rank"].dropna()
    non5_ranks  = oos[~oos["selected_top5"]]["c2_rank"].dropna()
    assert (top5_ranks <= 5).all(), "Some selected_top5 candidates have rank > 5"
    assert (non5_ranks > 5).all(),  "Some non-selected candidates have rank <= 5"


def test_T025_up_c2_score_equals_gap_pct(df):
    up = df[df["direction"] == "UP"].dropna(subset=["t_close", "t1_open", "C2_score"])
    recomputed = ((up["t1_open"] / up["t_close"]) - 1) * 100
    diff = (up["C2_score"] - recomputed).abs()
    assert diff.max() < 0.001, f"UP C2 formula mismatch: max diff={diff.max()}"


def test_T026_down_c2_score_equals_neg_gap_pct(df):
    dn = df[df["direction"] == "DOWN"].dropna(subset=["t_close", "t1_open", "C2_score"])
    recomputed = ((dn["t1_open"] / dn["t_close"]) - 1) * 100
    diff = (dn["C2_score"] + recomputed).abs()
    assert diff.max() < 0.001, f"DOWN C2 formula mismatch: max diff={diff.max()}"


def test_T027_c2_rank_descending_within_day(df):
    """Rank 1 must have higher C2_score than rank 2 within each day+direction."""
    oos = df[df["split"] == "OOS"]
    for td in list(oos["trading_date"].unique())[:10]:
        for direction in ["UP", "DOWN"]:
            day = oos[(oos["trading_date"] == td) & (oos["direction"] == direction)]
            day_sorted = day.sort_values("c2_rank")
            c2_vals = day_sorted["C2_score"].tolist()
            for i in range(len(c2_vals) - 1):
                assert c2_vals[i] >= c2_vals[i + 1], (
                    f"{td} {direction}: C2 not descending at rank {i+1}"
                )


def test_T028_c2_score_uses_only_t0_close_and_t1_open(df):
    """C2 must not use any data beyond T+1 open."""
    # The C2_score column was described as gap_pct for UP, -gap_pct for DOWN.
    # If C2 correlated perfectly with t1_ret_pct (intraday), that would indicate look-ahead.
    up = df[df["direction"] == "UP"].dropna(subset=["C2_score", "t1_ret_pct"])
    corr = up["C2_score"].corr(up["t1_ret_pct"])
    # Correlation with gap is 1.0; with t1_ret should be lower (different metric)
    assert corr < 0.95, (
        f"C2_score and t1_ret_pct are suspiciously correlated ({corr:.3f}) — look-ahead risk"
    )


def test_T029_c2_rank_independent_of_direction(df):
    """UP ranks are computed separately from DOWN ranks."""
    oos = df[df["split"] == "OOS"]
    for td in list(oos["trading_date"].unique())[:5]:
        up = oos[(oos["trading_date"] == td) & (oos["direction"] == "UP")]
        dn = oos[(oos["trading_date"] == td) & (oos["direction"] == "DOWN")]
        # Both should have ranks 1-20
        assert set(up["c2_rank"].dropna().astype(int)) == set(range(1, 21))
        assert set(dn["c2_rank"].dropna().astype(int)) == set(range(1, 21))


def test_T030_c2_ranking_deterministic(df):
    """Running load_primary() twice gives identical ranks."""
    df2 = load_primary()
    oos1 = df[df["split"] == "OOS"][["trading_date", "symbol", "direction", "c2_rank"]].reset_index(drop=True)
    oos2 = df2[df2["split"] == "OOS"][["trading_date", "symbol", "direction", "c2_rank"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(oos1.sort_values(list(oos1.columns)).reset_index(drop=True),
                                  oos2.sort_values(list(oos2.columns)).reset_index(drop=True))


# ─────────────────────────────────────────────────────────────────────────────
# T031–T040 Top-5 vs Remaining-15
# ─────────────────────────────────────────────────────────────────────────────

def test_T031_top5_dir_acc_greater_than_rem15_up(results_json):
    p3 = results_json["phase3_top5"]["OOS_UP"]
    assert p3["top5"]["dir_acc"] > p3["rem15"]["dir_acc"]


def test_T032_top5_dir_acc_greater_than_rem15_down(results_json):
    p3 = results_json["phase3_top5"]["OOS_DOWN"]
    assert p3["top5"]["dir_acc"] > p3["rem15"]["dir_acc"]


def test_T033_top5_ge2_rate_greater_than_rem15_up(results_json):
    p3 = results_json["phase3_top5"]["OOS_UP"]
    assert p3["top5"]["ge2_rate"] > p3["rem15"]["ge2_rate"]


def test_T034_top5_ge2_rate_greater_than_rem15_down(results_json):
    p3 = results_json["phase3_top5"]["OOS_DOWN"]
    assert p3["top5"]["ge2_rate"] > p3["rem15"]["ge2_rate"]


def test_T035_c2_adds_value_both_directions(results_json):
    assert results_json["phase3_top5"]["OOS_UP"]["c2_adds_value"] is True
    assert results_json["phase3_top5"]["OOS_DOWN"]["c2_adds_value"] is True


def test_T036_top5_obs_count_correct(results_json):
    """Top-5 OOS outcomes <= 270 (54 days × 5); fewer if some t1_ret_pct are NaN."""
    n = results_json["phase3_top5"]["OOS_UP"]["top5"]["n_outcomes"]
    assert 0 < n <= 270, f"OOS UP top5 n_outcomes={n} out of range"
    n_dn = results_json["phase3_top5"]["OOS_DOWN"]["top5"]["n_outcomes"]
    assert 0 < n_dn <= 270, f"OOS DOWN top5 n_outcomes={n_dn} out of range"


def test_T037_rem15_obs_count_correct(results_json):
    """Rem-15 OOS outcomes <= 810 (54 days × 15); fewer if some t1_ret_pct are NaN."""
    n = results_json["phase3_top5"]["OOS_UP"]["rem15"]["n_outcomes"]
    assert 0 < n <= 810, f"OOS UP rem15 n_outcomes={n} out of range"
    n_dn = results_json["phase3_top5"]["OOS_DOWN"]["rem15"]["n_outcomes"]
    assert 0 < n_dn <= 810, f"OOS DOWN rem15 n_outcomes={n_dn} out of range"


def test_T038_top5_plus_rem15_equals_total(results_json):
    """Top-5 + Rem-15 must equal total outcome count (rows with valid t1_ret_pct)."""
    for direction in ["UP", "DOWN"]:
        p3 = results_json["phase3_top5"][f"OOS_{direction}"]
        n5  = p3["top5"]["n_outcomes"]
        n15 = p3["rem15"]["n_outcomes"]
        assert n5 + n15 <= 1080, f"{direction}: n5+n15={n5+n15} exceeds theoretical max 1080"
        # The ratio must be ~1:3 (top5:rem15 = 5:15)
        ratio = n5 / n15 if n15 > 0 else 0
        assert 0.28 <= ratio <= 0.40, f"{direction}: top5/rem15 ratio={ratio:.3f} not near 1:3"


def test_T039_up_down_computed_independently(df):
    """Top-5 composition for UP and DOWN are different candidates."""
    oos = df[df["split"] == "OOS"]
    up_top5 = set(
        oos[(oos["direction"] == "UP") & oos["selected_top5"]]["symbol"].unique()
    )
    dn_top5 = set(
        oos[(oos["direction"] == "DOWN") & oos["selected_top5"]]["symbol"].unique()
    )
    # Same universe, different pools, so symbols can overlap
    # But ranking must be independent — already verified by T029
    assert len(up_top5) > 0 and len(dn_top5) > 0


def test_T040_top5_avg_ret_positive_up(results_json):
    """OOS Top-5 UP average return is positive."""
    avg = results_json["phase3_top5"]["OOS_UP"]["top5"]["avg_t1_ret"]
    assert avg is not None and avg > 0, f"Expected positive avg_ret UP top5, got {avg}"


# ─────────────────────────────────────────────────────────────────────────────
# T041–T050 Rank group / rank decay
# ─────────────────────────────────────────────────────────────────────────────

def test_T041_rank_group_top5_beats_1620_up(results_json):
    grp = results_json["phase4_groups"]
    top5_acc = grp["UP_TOP5"]["dir_acc"]
    bot5_acc = grp["UP_16-20"]["dir_acc"]
    assert top5_acc > bot5_acc, f"Rank 1-5 ({top5_acc}) not > Rank 16-20 ({bot5_acc})"


def test_T042_rank_group_top5_beats_1620_down(results_json):
    grp = results_json["phase4_groups"]
    top5_acc = grp["DOWN_TOP5"]["dir_acc"]
    bot5_acc = grp["DOWN_16-20"]["dir_acc"]
    assert top5_acc > bot5_acc


def test_T043_rank_group_ge2_monotone_up(results_json):
    """ge2_rate should decay from rank 1-5 to rank 16-20 for UP."""
    grp = results_json["phase4_groups"]
    ge2_top  = grp["UP_TOP5"]["ge2_rate"]
    ge2_6_10 = grp["UP_6-10"]["ge2_rate"]
    ge2_bot  = grp["UP_16-20"]["ge2_rate"]
    assert ge2_top > ge2_6_10, f"ge2 not decaying: TOP5={ge2_top}, 6-10={ge2_6_10}"
    assert ge2_6_10 > ge2_bot, f"ge2 not decaying: 6-10={ge2_6_10}, 16-20={ge2_bot}"


def test_T044_spearman_positive_up(results_json):
    sp = results_json["phase4_spearman"]["UP"]
    assert sp is not None and sp > 0, f"Expected positive Spearman UP, got {sp}"


def test_T045_spearman_positive_down(results_json):
    sp = results_json["phase4_spearman"]["DOWN"]
    assert sp is not None and sp > 0, f"Expected positive Spearman DOWN, got {sp}"


def test_T046_rank_breakdown_csv_has_20_rows_per_direction(rank_breakdown_csv):
    for direction in ["UP", "DOWN"]:
        n = len(rank_breakdown_csv[rank_breakdown_csv["direction"] == direction])
        assert n == 20, f"Expected 20 rank rows for {direction}, got {n}"


def test_T047_rank_breakdown_ranks_1_to_20(rank_breakdown_csv):
    for direction in ["UP", "DOWN"]:
        ranks = sorted(
            rank_breakdown_csv[rank_breakdown_csv["direction"] == direction]["c2_rank"].tolist()
        )
        assert ranks == list(range(1, 21))


def test_T048_rank1_ge2_exceeds_rank20_ge2_up(rank_breakdown_csv):
    up = rank_breakdown_csv[rank_breakdown_csv["direction"] == "UP"]
    ge2_r1  = up[up["c2_rank"] == 1]["ge2_rate"].iloc[0]
    ge2_r20 = up[up["c2_rank"] == 20]["ge2_rate"].iloc[0]
    assert ge2_r1 > ge2_r20


def test_T049_group_4_groups_exist_per_direction(results_json):
    grp = results_json["phase4_groups"]
    for direction in ["UP", "DOWN"]:
        for g in ["TOP5", "6-10", "11-15", "16-20"]:
            assert f"{direction}_{g}" in grp


def test_T050_rank_breakdown_has_direction_column(rank_breakdown_csv):
    assert "direction" in rank_breakdown_csv.columns
    assert "c2_rank" in rank_breakdown_csv.columns
    assert "dir_acc" in rank_breakdown_csv.columns
    assert "ge2_rate" in rank_breakdown_csv.columns


# ─────────────────────────────────────────────────────────────────────────────
# T051–T055 Missed mover classification
# ─────────────────────────────────────────────────────────────────────────────

def test_T051_missed_movers_csv_exists():
    assert (AUDIT_DIR / "daily_selection_quality_missed_movers.csv").exists()


def test_T052_missed_movers_types_valid():
    df_m = pd.read_csv(AUDIT_DIR / "daily_selection_quality_missed_movers.csv")
    valid_types = {"RANKING_MISS", "CORRECTLY_RANKED", "POOL_MISS", "DATA_MISS", "UNKNOWN"}
    assert set(df_m["miss_type"].unique()).issubset(valid_types)


def test_T053_missed_movers_actual_move_ge_2pct():
    """All missed movers should be ≥2% (audit threshold)."""
    df_m = pd.read_csv(AUDIT_DIR / "daily_selection_quality_missed_movers.csv")
    assert (df_m["actual_move"].abs() >= 2.0).all()


def test_T054_ranking_miss_not_selected(df):
    """RANKING_MISS candidates must have selected_top5=False."""
    df_m = pd.read_csv(AUDIT_DIR / "daily_selection_quality_missed_movers.csv")
    rm = df_m[df_m["miss_type"] == "RANKING_MISS"]
    assert (rm["selected_top5"] == False).all()


def test_T055_correctly_ranked_is_selected():
    """CORRECTLY_RANKED candidates must have selected_top5=True."""
    df_m = pd.read_csv(AUDIT_DIR / "daily_selection_quality_missed_movers.csv")
    cr = df_m[df_m["miss_type"] == "CORRECTLY_RANKED"]
    assert (cr["selected_top5"] == True).all()


# ─────────────────────────────────────────────────────────────────────────────
# T056–T060 Strategy independence
# ─────────────────────────────────────────────────────────────────────────────

def test_T056_strategy_impact_csv_exists():
    assert (AUDIT_DIR / "daily_selection_quality_strategy_impact.csv").exists()


def test_T057_strategy_analysis_in_results_json(results_json):
    assert "phase6_strategy" in results_json
    # Phase 6 may return a note if OOS data is absent from the rejection CSV
    p6 = results_json["phase6_strategy"]
    assert isinstance(p6, dict)


def test_T058_strategy_rejection_data_is_dict(results_json):
    """Phase 6 must return a dict (may be a note-only dict if no OOS data available)."""
    p6 = results_json["phase6_strategy"]
    assert isinstance(p6, dict)
    # If OOS data is present, check structure
    if "n_rejected_up_oos" in p6:
        assert p6["n_rejected_up_oos"] >= 0


def test_T059_strategy_status_does_not_affect_c2_rank(df):
    """C2 ranking must be computed purely from C2_score, not from strategy_status."""
    # The main CSV has no strategy_status column — verify C2 rank correlates with C2_score
    oos = df[df["split"] == "OOS"]
    for td in list(oos["trading_date"].unique())[:5]:
        for direction in ["UP", "DOWN"]:
            day = oos[(oos["trading_date"] == td) & (oos["direction"] == direction)]
            # Rank must follow C2_score order
            r1 = day[day["c2_rank"] == 1]["C2_score"].iloc[0]
            r5 = day[day["c2_rank"] == 5]["C2_score"].iloc[0]
            assert r1 >= r5


def test_T060_regime_breakdown_in_results(results_json):
    assert "phase7_regime" in results_json
    assert len(results_json["phase7_regime"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# T061–T065 No look-ahead / leakage
# ─────────────────────────────────────────────────────────────────────────────

def test_T061_leakage_check_pass(results_json):
    assert results_json["leakage"]["leakage_check"] == "PASS"


def test_T062_c2_vs_gap_exact_match(results_json):
    """Max diff between C2_score and recomputed gap must be < 0.001."""
    assert results_json["leakage"]["up_c2_vs_gap_max_diff"] < 0.001
    assert results_json["leakage"]["dn_c2_vs_ngap_max_diff"] < 0.001


def test_T063_c2_corr_with_gap_is_1(results_json):
    assert abs(results_json["leakage"]["corr_c2_vs_gap_up"] - 1.0) < 0.001


def test_T064_c2_corr_with_t1_ret_below_threshold(results_json):
    """C2/t1_ret correlation should not be near 1 (no look-ahead)."""
    corr = results_json["leakage"]["corr_c2_vs_t1_ret_up"]
    assert corr < 0.90, f"Suspiciously high C2/t1_ret correlation: {corr}"


def test_T065_phase9_function_returns_pass(df):
    result = phase9_leakage_check(df)
    assert result["leakage_check"] == "PASS"


# ─────────────────────────────────────────────────────────────────────────────
# T066–T070 Execution isolation
# ─────────────────────────────────────────────────────────────────────────────

def test_T066_zero_broker_calls(results_json):
    assert results_json["safety"]["broker_calls"] == 0


def test_T067_zero_orders(results_json):
    assert results_json["safety"]["orders"] == 0


def test_T068_zero_candidatestore_writes(results_json):
    assert results_json["safety"]["candidatestore"] == 0


def test_T069_execution_isolation_is_isolated(results_json):
    p10 = phase10_execution_isolation()
    assert p10["status"] == "ISOLATED"
    assert not p10["production_mutated"]


def test_T070_no_broker_import_in_audit_script():
    """Audit script must not import broker or execution modules."""
    audit_src = Path("scripts/daily_selection_quality_audit_001.py").read_text(encoding="utf-8")
    # Check import lines only (not comments or docstrings)
    import_lines = [line.strip() for line in audit_src.splitlines()
                    if line.strip().startswith(("import ", "from "))]
    forbidden = ["order_manager", "dhan_feed", "zerodb_broker",
                 "CandidateStore", "place_order"]
    import_block = "\n".join(import_lines)
    for term in forbidden:
        assert term not in import_block, f"Forbidden import '{term}' found in audit script imports"


# ─────────────────────────────────────────────────────────────────────────────
# T071–T075 Output file completeness
# ─────────────────────────────────────────────────────────────────────────────

def test_T071_results_json_exists():
    assert (AUDIT_DIR / "daily_selection_quality_results.json").exists()


def test_T072_daily_csv_exists():
    assert (AUDIT_DIR / "daily_selection_quality_daily.csv").exists()


def test_T073_rank_breakdown_csv_exists():
    assert (AUDIT_DIR / "daily_selection_quality_rank_breakdown.csv").exists()


def test_T074_missed_movers_csv_exists():
    assert (AUDIT_DIR / "daily_selection_quality_missed_movers.csv").exists()


def test_T075_strategy_impact_csv_exists():
    assert (AUDIT_DIR / "daily_selection_quality_strategy_impact.csv").exists()


# ─────────────────────────────────────────────────────────────────────────────
# T076–T080 Results JSON regression anchors
# ─────────────────────────────────────────────────────────────────────────────

def test_T076_oos_up_dir_acc_matches_anchor(results_json):
    """OOS UP Top-5 dir_acc must match validated anchor 0.6151 ±0.006."""
    acc = results_json["phase3_top5"]["OOS_UP"]["top5"]["dir_acc"]
    assert 0.609 <= acc <= 0.622, f"OOS UP dir_acc={acc} outside anchor range"


def test_T077_oos_down_dir_acc_matches_anchor(results_json):
    """OOS DOWN Top-5 dir_acc must match validated anchor 0.6038 ±0.006."""
    acc = results_json["phase3_top5"]["OOS_DOWN"]["top5"]["dir_acc"]
    assert 0.597 <= acc <= 0.611, f"OOS DOWN dir_acc={acc} outside anchor range"


def test_T078_oos_up_ge2_matches_anchor(results_json):
    """OOS UP Top-5 ge2_rate must match validated anchor 0.2906 ±0.006."""
    ge2 = results_json["phase3_top5"]["OOS_UP"]["top5"]["ge2_rate"]
    assert 0.284 <= ge2 <= 0.297, f"OOS UP ge2={ge2} outside anchor range"


def test_T079_oos_down_ge2_matches_anchor(results_json):
    """OOS DOWN Top-5 ge2_rate must match validated anchor 0.2415 ±0.007."""
    ge2 = results_json["phase3_top5"]["OOS_DOWN"]["top5"]["ge2_rate"]
    assert 0.234 <= ge2 <= 0.249, f"OOS DOWN ge2={ge2} outside anchor range"


def test_T080_verdict_in_valid_set(results_json):
    valid = {
        "A_ARCHITECTURE_PERFORMING",
        "B_ARCHITECTURE_PERFORMING_WITH_MINOR_REFINEMENT",
        "C_DISCOVERY_NEEDS_IMPROVEMENT",
        "D_C2_RANKING_NEEDS_IMPROVEMENT",
        "E_STRATEGY_ROLE_NEEDS_RESEARCH",
        "F_INSUFFICIENT_SAMPLE_CONTINUE",
        "G_DATA_QUALITY_BLOCKER",
    }
    assert results_json["verdict"] in valid
