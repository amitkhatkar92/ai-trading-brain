"""
tests/test_strategy_reconstruction_001.py

60 tests for STRATEGY_RECONSTRUCTION_VALIDATION_001.

Groups:
  T001-T010: Dataset integrity (30 files, 286 signals, funnel counts)
  T011-T020: Strategy assignment / signal-type inference
  T021-T030: Feature availability classification
  T031-T040: PASS / REJECT reconstruction decisions
  T041-T050: Rejection reason matching per rule
  T051-T055: Funnel count reproduction
  T056-T060: Leakage audit and production isolation

Run with:
    python -m pytest tests/test_strategy_reconstruction_001.py -v
"""

from __future__ import annotations
import json
import pathlib
import sys
from collections import Counter

import pytest

# ─── Add repo root to path ────────────────────────────────────────────────────
REPO_ROOT  = pathlib.Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "mover_discovery_v3"
TRACE_DIR  = REPO_ROOT / "simulation_logs" / "decision_trace"
sys.path.insert(0, str(REPO_ROOT))

# ─── Import reconstruction module ─────────────────────────────────────────────
from scripts.strategy_reconstruction_001 import (
    REPLAY_DAY_MAP,
    REGIME_MAP_ORIGINAL,
    HIGH_VOL_EXTRAS,
    RANGE_VOL_EXTRAS,
    STRATEGY_PARAMS,
    PASS, REJECT, INDET,
    REASON_TYPE_LOW_RR, REASON_BEAR_EQUITY, REASON_REGIME_MISMATCH, REASON_PASS_NEEDS_RR,
    infer_signal_type,
    get_active_set,
    apply_reconstruction_rules,
    load_replay_signals,
    compute_reconstruction_metrics,
    build_feature_matrix,
    compute_regime_breakdown,
    check_no_leakage,
    check_production_isolation,
    SignalRecord,
    DayRecord,
)

# ─── Shared fixtures ──────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def loaded_data():
    """Load signals and day_records once for all tests."""
    signals, day_records = load_replay_signals()
    return signals, day_records

@pytest.fixture(scope="module")
def metrics(loaded_data):
    signals, day_records = loaded_data
    return compute_reconstruction_metrics(signals, day_records)

@pytest.fixture(scope="module")
def regime_rows(loaded_data):
    _, day_records = loaded_data
    return compute_regime_breakdown(day_records)

@pytest.fixture(scope="module")
def leakage_result(loaded_data):
    signals, _ = loaded_data
    return check_no_leakage(signals)

# ─────────────────────────────────────────────────────────────────────────────
# T001-T010: DATASET INTEGRITY
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetIntegrity:
    """T001-T010: Verify 30 trace files exist and funnel counts are correct."""

    def test_T001_replay_day_map_has_30_entries(self):
        """T001: REPLAY_DAY_MAP must have exactly 30 entries."""
        assert len(REPLAY_DAY_MAP) == 30

    def test_T002_replay_starts_jan30(self):
        """T002: First replay day is 2026-01-30."""
        assert REPLAY_DAY_MAP[1] == "2026-01-30"

    def test_T003_replay_ends_mar13(self):
        """T003: Last replay day is 2026-03-13."""
        assert REPLAY_DAY_MAP[30] == "2026-03-13"

    def test_T004_all_trace_files_exist(self):
        """T004: All 30 trace files are present on disk."""
        missing = []
        for day_num, tdate in REPLAY_DAY_MAP.items():
            tf = TRACE_DIR / f"day_{day_num:02d}_{tdate}.json"
            if not tf.exists():
                missing.append(tf.name)
        assert missing == [], f"Missing trace files: {missing}"

    def test_T005_total_signals_is_286(self, loaded_data):
        """T005: Total extracted signals = 286 (matches SIMULATION_REPLAY_REPORT.md)."""
        signals, _ = loaded_data
        assert len(signals) == 286

    def test_T006_total_actual_strat_is_82(self, loaded_data):
        """T006: Sum of actual after_bt across 30 days = 82."""
        _, day_records = loaded_data
        assert sum(d.actual_strat for d in day_records) == 82

    def test_T007_all_signals_have_required_fields(self, loaded_data):
        """T007: Every signal has non-empty symbol, direction, strategy, regime."""
        signals, _ = loaded_data
        empty = [
            s for s in signals
            if not s.symbol or not s.direction or not s.strategy or not s.regime
        ]
        assert empty == [], f"{len(empty)} signals have empty required fields"

    def test_T008_30_day_records(self, loaded_data):
        """T008: Exactly 30 DayRecord objects, one per replay day."""
        _, day_records = loaded_data
        assert len(day_records) == 30

    def test_T009_day_record_sums_match_signal_count(self, loaded_data):
        """T009: Sum of day_record.raw_count equals len(signals) = 286."""
        signals, day_records = loaded_data
        total = sum(d.raw_count for d in day_records)
        assert total == len(signals) == 286

    def test_T010_day_num_sequence_is_1_to_30(self, loaded_data):
        """T010: DayRecord.day_num values are 1..30 (no gaps, no duplicates)."""
        _, day_records = loaded_data
        nums = sorted(d.day_num for d in day_records)
        assert nums == list(range(1, 31))


# ─────────────────────────────────────────────────────────────────────────────
# T011-T020: STRATEGY ASSIGNMENT & SIGNAL TYPE INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

class TestStrategyAssignment:
    """T011-T020: Signal type inference and strategy catalogue."""

    def test_T011_equity_strategies_infer_equity(self):
        """T011: Equity base strategies infer signal_type=EQUITY."""
        for strat in ["Breakout_Volume", "Momentum_Retest", "Trend_Pullback",
                      "Mean_Reversion", "Hedging_Model"]:
            assert infer_signal_type(strat) == "EQUITY", f"Failed for {strat}"

    def test_T012_options_strategies_infer_options(self):
        """T012: Options strategies infer signal_type=OPTIONS."""
        for strat in ["Short_Straddle_IV_Spike", "Long_Straddle_Pre_Event",
                      "Bull_Call_Spread", "Iron_Condor_Range"]:
            assert infer_signal_type(strat) == "OPTIONS", f"Failed for {strat}"

    def test_T013_arb_strategies_infer_arb(self):
        """T013: Arb strategies infer signal_type=ARB."""
        for strat in ["Futures_Basis_Arb", "ETF_NAV_Arb"]:
            assert infer_signal_type(strat) == "ARB", f"Failed for {strat}"

    def test_T014_unknown_strategy_defaults_to_equity(self):
        """T014: Unknown strategy name defaults to EQUITY (safe fallback)."""
        assert infer_signal_type("Unknown_Strategy_XYZ") == "EQUITY"

    def test_T015_all_replay_signals_have_known_type(self, loaded_data):
        """T015: All 286 signals have signal_type in {EQUITY, OPTIONS, ARB}."""
        signals, _ = loaded_data
        valid = {"EQUITY", "OPTIONS", "ARB"}
        bad = [s for s in signals if s.signal_type not in valid]
        assert bad == [], f"{len(bad)} signals have unknown signal_type"

    def test_T016_options_arb_count_is_180(self, loaded_data):
        """T016: Exactly 6 non-equity signals per day × 30 days = 180 total."""
        signals, _ = loaded_data
        non_eq = sum(1 for s in signals if s.signal_type in ("OPTIONS", "ARB"))
        assert non_eq == 180

    def test_T017_equity_count_is_106(self, loaded_data):
        """T017: 286 total - 180 non-equity = 106 equity signals."""
        signals, _ = loaded_data
        eq = sum(1 for s in signals if s.signal_type == "EQUITY")
        assert eq == 106

    def test_T018_strategy_params_has_11_base_entries(self):
        """T018: STRATEGY_PARAMS has exactly 11 base strategy entries."""
        assert len(STRATEGY_PARAMS) == 11

    def test_T019_all_regime_map_strategies_in_params(self):
        """T019: All strategies in REGIME_MAP are in STRATEGY_PARAMS."""
        all_regime_strats = set()
        for strats in REGIME_MAP_ORIGINAL.values():
            all_regime_strats.update(strats)
        missing = all_regime_strats - set(STRATEGY_PARAMS.keys())
        assert missing == set(), f"Strategies in regime map but not in params: {missing}"

    def test_T020_high_vol_extras_in_params(self):
        """T020: HIGH_VOL_EXTRAS and RANGE_VOL_EXTRAS strategies are in STRATEGY_PARAMS."""
        for strat in HIGH_VOL_EXTRAS | RANGE_VOL_EXTRAS:
            assert strat in STRATEGY_PARAMS, f"{strat} not in STRATEGY_PARAMS"


# ─────────────────────────────────────────────────────────────────────────────
# T021-T030: FEATURE AVAILABILITY
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureAvailability:
    """T021-T030: Feature classification in the availability matrix."""

    @pytest.fixture(scope="class")
    def feature_matrix(self):
        return build_feature_matrix()

    def test_T021_feature_matrix_not_empty(self, feature_matrix):
        """T021: Feature matrix has entries."""
        assert len(feature_matrix) > 0

    def test_T022_rr_is_unavailable(self, feature_matrix):
        """T022: risk_reward_ratio is classified UNAVAILABLE."""
        rr = next((f for f in feature_matrix if f["feature"] == "risk_reward_ratio"), None)
        assert rr is not None, "risk_reward_ratio not in matrix"
        assert rr["availability"] == "UNAVAILABLE"

    def test_T023_regime_is_available_exact(self, feature_matrix):
        """T023: regime is classified AVAILABLE_EXACT."""
        r = next((f for f in feature_matrix if f["feature"] == "regime"), None)
        assert r is not None
        assert r["availability"] == "AVAILABLE_EXACT"

    def test_T024_strategy_name_is_available_exact(self, feature_matrix):
        """T024: strategy_name is classified AVAILABLE_EXACT."""
        r = next((f for f in feature_matrix if f["feature"] == "strategy_name"), None)
        assert r is not None
        assert r["availability"] == "AVAILABLE_EXACT"

    def test_T025_signal_type_is_available_derived(self, feature_matrix):
        """T025: signal_type is classified AVAILABLE_DERIVED (inferred from strategy)."""
        r = next((f for f in feature_matrix if f["feature"] == "signal_type"), None)
        assert r is not None
        assert r["availability"] == "AVAILABLE_DERIVED"

    def test_T026_entry_price_is_unavailable(self, feature_matrix):
        """T026: entry_price is classified UNAVAILABLE."""
        r = next((f for f in feature_matrix if f["feature"] == "entry_price"), None)
        assert r is not None
        assert r["availability"] == "UNAVAILABLE"

    def test_T027_active_set_is_derived(self, feature_matrix):
        """T027: active_strategy_set is classified AVAILABLE_DERIVED."""
        r = next((f for f in feature_matrix if f["feature"] == "active_strategy_set"), None)
        assert r is not None
        assert r["availability"] == "AVAILABLE_DERIVED"

    def test_T028_all_availability_values_are_valid(self, feature_matrix):
        """T028: All availability values are valid enumeration members."""
        valid = {"AVAILABLE_EXACT", "AVAILABLE_DERIVED", "AVAILABLE_PROXY", "UNAVAILABLE"}
        bad = [f for f in feature_matrix if f["availability"] not in valid]
        assert bad == [], f"Invalid availability values: {[b['feature'] for b in bad]}"

    def test_T029_at_least_3_unavailable_features(self, feature_matrix):
        """T029: At least 3 UNAVAILABLE features (rr, entry, target are all missing)."""
        count = sum(1 for f in feature_matrix if f["availability"] == "UNAVAILABLE")
        assert count >= 3

    def test_T030_confidence_is_available_exact(self, feature_matrix):
        """T030: confidence is classified AVAILABLE_EXACT."""
        r = next((f for f in feature_matrix if f["feature"] == "confidence"), None)
        assert r is not None
        assert r["availability"] == "AVAILABLE_EXACT"


# ─────────────────────────────────────────────────────────────────────────────
# T031-T040: PASS/REJECT RECONSTRUCTION
# ─────────────────────────────────────────────────────────────────────────────

class TestPassRejectReconstruction:
    """T031-T040: Verify reconstruction decisions for specific scenarios."""

    def test_T031_options_signal_always_reject(self):
        """T031: OPTIONS signal → REJECT regardless of regime."""
        for regime in ("bull_trend", "range_market", "bear_market", "volatile"):
            for vol in ("VolatilityLevel.LOW", "VolatilityLevel.HIGH"):
                active = get_active_set(regime, vol)
                dec, reason = apply_reconstruction_rules(
                    "NIFTY", "SELL", "Short_Straddle_IV_Spike", regime, vol, "OPTIONS", active
                )
                assert dec == REJECT, f"OPTIONS should REJECT on {regime}"
                assert reason == REASON_TYPE_LOW_RR

    def test_T032_arb_signal_always_reject(self):
        """T032: ARB signal → REJECT regardless of regime."""
        for regime, vol in [
            ("bull_trend", "VolatilityLevel.LOW"),
            ("range_market", "VolatilityLevel.MEDIUM"),
            ("bear_market", "VolatilityLevel.HIGH"),
        ]:
            active = get_active_set(regime, vol)
            dec, _ = apply_reconstruction_rules(
                "NIFTY", "SHORT", "Futures_Basis_Arb", regime, vol, "ARB", active
            )
            assert dec == REJECT, f"ARB should REJECT on {regime}"

    def test_T033_bear_equity_buy_reject(self):
        """T033: BEAR_MARKET + EQUITY + BUY → REJECT."""
        active = get_active_set("bear_market", "VolatilityLevel.LOW")
        dec, reason = apply_reconstruction_rules(
            "TATASTEEL", "BUY", "Mean_Reversion", "bear_market",
            "VolatilityLevel.LOW", "EQUITY", active
        )
        assert dec == REJECT
        assert reason == REASON_BEAR_EQUITY

    def test_T034_bear_equity_short_not_d2(self):
        """T034: BEAR_MARKET + EQUITY + SHORT → NOT D2 (SHORT allowed, may fail D3)."""
        active = get_active_set("bear_market", "VolatilityLevel.LOW")
        dec, reason = apply_reconstruction_rules(
            "TATASTEEL", "SHORT", "Mean_Reversion", "bear_market",
            "VolatilityLevel.LOW", "EQUITY", active
        )
        # Mean_Reversion not in bear_market map → D3 reject
        assert reason != REASON_BEAR_EQUITY

    def test_T035_regime_mismatch_reject(self):
        """T035: Mean_Reversion on bull_trend → REGIME_MISMATCH."""
        active = get_active_set("bull_trend", "VolatilityLevel.LOW")
        dec, reason = apply_reconstruction_rules(
            "HDFC", "BUY", "Mean_Reversion", "bull_trend",
            "VolatilityLevel.LOW", "EQUITY", active
        )
        assert dec == REJECT
        assert reason == REASON_REGIME_MISMATCH

    def test_T036_equity_in_bull_map_is_indet(self):
        """T036: Equity signal in BULL map → INDETERMINATE (passes D1-D3, RR unknown)."""
        active = get_active_set("bull_trend", "VolatilityLevel.LOW")
        dec, reason = apply_reconstruction_rules(
            "AXISBANK", "BUY", "Breakout_Volume", "bull_trend",
            "VolatilityLevel.LOW", "EQUITY", active
        )
        assert dec == INDET
        assert reason == REASON_PASS_NEEDS_RR

    def test_T037_equity_in_range_map_is_indet(self):
        """T037: Mean_Reversion signal on range_market → INDETERMINATE."""
        active = get_active_set("range_market", "VolatilityLevel.MEDIUM")
        dec, reason = apply_reconstruction_rules(
            "RELIANCE", "BUY", "Mean_Reversion", "range_market",
            "VolatilityLevel.MEDIUM", "EQUITY", active
        )
        assert dec == INDET
        assert reason == REASON_PASS_NEEDS_RR

    def test_T038_volatile_mean_reversion_is_d3(self):
        """T038: Mean_Reversion on volatile → D3 (REGIME_MISMATCH)."""
        active = get_active_set("volatile", "VolatilityLevel.EXTREME")
        dec, reason = apply_reconstruction_rules(
            "HDFCBANK", "BUY", "Mean_Reversion", "volatile",
            "VolatilityLevel.EXTREME", "EQUITY", active
        )
        assert dec == REJECT
        assert reason == REASON_REGIME_MISMATCH

    def test_T039_bear_options_is_d1_not_d2(self):
        """T039: OPTIONS signal on bear_market is rejected by D1, not D2 (direction check)."""
        active = get_active_set("bear_market", "VolatilityLevel.HIGH")
        dec, reason = apply_reconstruction_rules(
            "NIFTY", "SELL", "Short_Straddle_IV_Spike", "bear_market",
            "VolatilityLevel.HIGH", "OPTIONS", active
        )
        assert dec == REJECT
        assert reason == REASON_TYPE_LOW_RR  # D1 fires before D2

    def test_T040_all_signals_have_decision(self, loaded_data):
        """T040: No signal has empty decision or reason."""
        signals, _ = loaded_data
        bad = [s for s in signals if not s.decision or not s.reason]
        assert bad == [], f"{len(bad)} signals missing decision/reason"


# ─────────────────────────────────────────────────────────────────────────────
# T041-T050: REJECTION REASON MATCHING
# ─────────────────────────────────────────────────────────────────────────────

class TestRejectionReasonMatching:
    """T041-T050: Verify rejection reason distribution matches expectations."""

    def test_T041_d1_count_is_180(self, loaded_data):
        """T041: D1 TYPE_LOW_RR should be exactly 180 (6 per day × 30 days)."""
        signals, _ = loaded_data
        n = sum(1 for s in signals if s.reason == REASON_TYPE_LOW_RR)
        assert n == 180

    def test_T042_d2_count_is_zero(self, loaded_data):
        """T042: D2 BEAR_EQUITY_BUY should be 0 (bear days had equity=0 from scanner)."""
        signals, _ = loaded_data
        n = sum(1 for s in signals if s.reason == REASON_BEAR_EQUITY)
        assert n == 0

    def test_T043_d3_count_is_positive(self, loaded_data):
        """T043: D3 REGIME_MISMATCH should be >0 (volatile equity signals)."""
        signals, _ = loaded_data
        n = sum(1 for s in signals if s.reason == REASON_REGIME_MISMATCH)
        assert n > 0

    def test_T044_indet_count_is_92(self, loaded_data):
        """T044: INDETERMINATE count should be 92 (all equity that passes D1-D3)."""
        signals, _ = loaded_data
        n = sum(1 for s in signals if s.decision == INDET)
        assert n == 92

    def test_T045_d1_signals_are_options_or_arb(self, loaded_data):
        """T045: All D1 rejections are OPTIONS or ARB signal type."""
        signals, _ = loaded_data
        d1 = [s for s in signals if s.reason == REASON_TYPE_LOW_RR]
        bad = [s for s in d1 if s.signal_type not in ("OPTIONS", "ARB")]
        assert bad == []

    def test_T046_d3_signals_not_in_regime_map(self, loaded_data):
        """T046: All D3 rejections have strategy NOT in their regime's active set."""
        signals, _ = loaded_data
        d3 = [s for s in signals if s.reason == REASON_REGIME_MISMATCH]
        bad = []
        for s in d3:
            active = get_active_set(s.regime, s.vol_level)
            if s.strategy in active:
                bad.append(s)
        assert bad == [], f"{len(bad)} D3 signals incorrectly have strategy in active set"

    def test_T047_indet_signals_pass_d1_d2_d3(self, loaded_data):
        """T047: All INDET signals pass all deterministic checks."""
        signals, _ = loaded_data
        indet = [s for s in signals if s.decision == INDET]
        for s in indet:
            active = get_active_set(s.regime, s.vol_level)
            assert s.signal_type not in ("OPTIONS", "ARB"), f"INDET signal is OPTIONS/ARB: {s}"
            assert not (s.regime == "bear_market" and s.direction == "BUY" and s.signal_type == "EQUITY"), \
                f"INDET signal fails D2: {s}"
            assert s.strategy in active, f"INDET signal strategy not in active set: {s}"

    def test_T048_options_straddle_signals_always_d1(self, loaded_data):
        """T048: Short_Straddle_IV_Spike strategy always gets D1 rejection."""
        signals, _ = loaded_data
        straddle = [s for s in signals if s.strategy == "Short_Straddle_IV_Spike"]
        assert len(straddle) > 0, "No Short_Straddle signals found"
        all_d1 = all(s.reason == REASON_TYPE_LOW_RR for s in straddle)
        assert all_d1

    def test_T049_etf_nav_arb_signals_d1_or_d3(self, loaded_data):
        """T049: ETF_NAV_Arb signals are D1 (ARB type always rejected)."""
        signals, _ = loaded_data
        etf = [s for s in signals if s.strategy == "ETF_NAV_Arb"]
        assert len(etf) > 0
        all_d1 = all(s.reason == REASON_TYPE_LOW_RR for s in etf)
        assert all_d1

    def test_T050_total_rejects_is_194(self, loaded_data):
        """T050: Deterministic rejects (D1+D2+D3) = 194.
        The remaining 10 rejects are INDETERMINATE (RR check — not classifiable from trace)."""
        signals, _ = loaded_data
        n = sum(1 for s in signals if s.decision == REJECT)
        assert n == 194


# ─────────────────────────────────────────────────────────────────────────────
# T051-T055: FUNNEL REPRODUCTION
# ─────────────────────────────────────────────────────────────────────────────

class TestFunnelReproduction:
    """T051-T055: Verify funnel counts are reproduced correctly."""

    def test_T051_funnel_raw_is_286(self, loaded_data):
        """T051: Raw signal count = 286."""
        signals, _ = loaded_data
        assert len(signals) == 286

    def test_T052_funnel_strat_is_82(self, loaded_data):
        """T052: Actual StrategyLab survivors = 82."""
        _, day_records = loaded_data
        assert sum(d.actual_strat for d in day_records) == 82

    def test_T053_signal_accuracy_is_at_least_95(self, metrics):
        """T053: Signal-level reconstruction accuracy >= 95% (verdict A threshold)."""
        assert metrics["signal_accuracy"] >= 0.95

    def test_T054_verdict_is_A(self, metrics):
        """T054: Reconstruction verdict is A (RECONSTRUCTION_VALIDATED)."""
        assert metrics["verdict"] == "A"

    def test_T055_indet_actual_rr_fail_is_10(self, metrics):
        """T055: Exactly 10 indeterminate signals actually failed the RR check."""
        assert metrics["n_indet_actual_reject"] == 10


# ─────────────────────────────────────────────────────────────────────────────
# T056-T060: LEAKAGE AND PRODUCTION ISOLATION
# ─────────────────────────────────────────────────────────────────────────────

class TestLeakageAndIsolation:
    """T056-T060: No look-ahead bias, no production contamination."""

    def test_T056_leakage_all_checks_pass(self, leakage_result):
        """T056: All leakage checks pass (no look-ahead contamination)."""
        assert leakage_result["all_pass"] is True

    def test_T057_regime_available_before_lab(self, leakage_result):
        """T057: Regime is available before strategy lab runs (no look-ahead)."""
        assert leakage_result["checks"]["regime_available_before_lab"]

    def test_T058_rr_unavailable_confirmed(self, leakage_result):
        """T058: risk_reward_ratio unavailability is confirmed in leakage audit."""
        assert leakage_result["checks"]["rr_unavailable_confirmed"]

    def test_T059_production_isolation_has_no_violations(self):
        """T059: No production execution/broker modules imported in this test context."""
        result = check_production_isolation()
        assert result["is_isolated"] is True

    def test_T060_output_files_written_to_report_dir_only(self):
        """T060: All 6 output files are in reports/mover_discovery_v3/ only."""
        expected_files = [
            "strategy_reconstruction_validation_dataset.json",
            "strategy_reconstruction_results.csv",
            "strategy_feature_availability_matrix.csv",
            "strategy_reconstruction_funnel.json",
            "strategy_reconstruction_regime_breakdown.csv",
        ]
        for fname in expected_files:
            path = REPORT_DIR / fname
            assert path.exists(), f"Output file missing: {fname}"
            # Verify NOT in any other directory
            wrong_place = REPO_ROOT / fname
            assert not wrong_place.exists(), f"Output file in wrong location: {fname}"
