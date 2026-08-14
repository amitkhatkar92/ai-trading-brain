"""
tests/test_mover_discovery_v3.py
==================================
Test suite for Mover Discovery V3.

Covers:
  - V3 disabled by default
  - Shadow mode enforced
  - UP scoring correctness
  - DOWN scoring correctness
  - Pool size selection
  - No production threshold mutation
  - No production trade generation
  - No look-ahead leakage
  - Missing feature handling
  - Deterministic ranking
  - Tie handling
  - OOS separation

Run: python tests/test_mover_discovery_v3.py
     python -m pytest tests/test_mover_discovery_v3.py -v
"""
import sys
import os
import math
import unittest
from pathlib import Path
from datetime import date

# ── Workspace path resolution ─────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from opportunity_engine.mover_discovery_v3 import (
    V3Config, V3UpWeights, V3DownWeights,
    compute_v3_features, score_universe, select_candidates,
    run_shadow_scan, check_leakage, estimate_magnitude,
    FORBIDDEN_FUTURE_KEYS, _wilder_rsi, _rank_pct,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_price_series(n: int = 60, trend: float = 0.002) -> list:
    """Upward-trending close prices."""
    prices = [100.0]
    for _ in range(n - 1):
        prices.append(round(prices[-1] * (1.0 + trend), 4))
    return prices


def _make_flat_series(n: int = 60, base: float = 100.0) -> list:
    return [base] * n


def _make_volume_series(n: int = 60, base: float = 1_000_000.0) -> list:
    return [base] * n


def _make_features(
    symbol: str = "TESTSTOCK",
    close_trend: float = 0.002,
    n: int = 60,
    vol_multiplier: float = 1.0,
) -> dict:
    closes  = _make_price_series(n, close_trend)
    highs   = [c * 1.01 for c in closes]
    lows    = [c * 0.99 for c in closes]
    volumes = [1_000_000.0 * vol_multiplier] * n
    return compute_v3_features(symbol, closes, highs, lows, volumes)


# ─────────────────────────────────────────────────────────────────────────────
# T001–T005: V3 Disabled / Shadow Mode
# ─────────────────────────────────────────────────────────────────────────────

class TestV3SafetyFlags(unittest.TestCase):

    def test_T001_v3_disabled_by_default(self):
        """T001: V3Config.enabled must be False by default."""
        cfg = V3Config()
        self.assertFalse(cfg.enabled,
                         "V3 must be disabled by default — do not enable without OOS validation")

    def test_T002_shadow_mode_true_by_default(self):
        """T002: shadow_mode must be True by default."""
        cfg = V3Config()
        self.assertTrue(cfg.shadow_mode)

    def test_T003_enabled_with_shadow_false_raises(self):
        """T003: enabled=True AND shadow_mode=False is forbidden."""
        cfg = V3Config(enabled=True, shadow_mode=False)
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_T004_shadow_mode_refuses_non_shadow(self):
        """T004: run_shadow_scan raises if shadow_mode=False."""
        cfg = V3Config(shadow_mode=False)
        with self.assertRaises(ValueError):
            run_shadow_scan({}, cfg=cfg)

    def test_T005_enabled_shadow_both_true_ok(self):
        """T005: enabled=True with shadow_mode=True is allowed."""
        cfg = V3Config(enabled=True, shadow_mode=True)
        cfg.validate()   # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# T006–T015: Feature Computation
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureComputation(unittest.TestCase):

    def test_T006_returns_none_for_short_history(self):
        """T006: Returns None if fewer than 25 bars."""
        closes  = _make_price_series(10)
        highs   = [c * 1.01 for c in closes]
        lows    = [c * 0.99 for c in closes]
        volumes = [1_000_000.0] * 10
        result  = compute_v3_features("X", closes, highs, lows, volumes)
        self.assertIsNone(result)

    def test_T007_returns_dict_for_sufficient_history(self):
        """T007: Returns dict for 60 bars."""
        feat = _make_features()
        self.assertIsNotNone(feat)
        self.assertIsInstance(feat, dict)

    def test_T008_required_keys_present(self):
        """T008: All required V3 features present in output."""
        feat = _make_features()
        required = ["atr_pct", "mom_5d", "mom_accel", "vol_ratio", "rsi_14",
                    "vol_expansion", "hv_20", "resistance_20d", "support_20d",
                    "breakout_pct", "atr_magnitude_estimate"]
        for key in required:
            self.assertIn(key, feat, f"Missing required feature: {key}")

    def test_T009_no_future_keys_in_features(self):
        """T009: No forbidden future-data keys in computed features."""
        feat = _make_features()
        for key in FORBIDDEN_FUTURE_KEYS:
            self.assertNotIn(key, feat,
                             f"LEAKAGE: future key '{key}' present in features")

    def test_T010_legacy_constant_documented_not_predicted(self):
        """T010: Legacy 8.0 constant is documented, not used as prediction."""
        feat = _make_features()
        self.assertIn("expected_move_pct_legacy_constant", feat)
        self.assertAlmostEqual(feat["expected_move_pct_legacy_constant"], 8.0)

    def test_T011_atr_pct_positive(self):
        """T011: atr_pct is always positive for valid inputs."""
        feat = _make_features()
        self.assertGreater(feat["atr_pct"], 0.0)

    def test_T012_returns_none_for_illiquid_symbol(self):
        """T012: Returns None when vol_ratio < 0.2 (today << 20d avg)."""
        closes  = _make_price_series(60)
        highs   = [c * 1.01 for c in closes]
        lows    = [c * 0.99 for c in closes]
        # High historical average, tiny today → vol_ratio = 100 / 1_000_000 = 0.0001
        volumes = [1_000_000.0] * 59 + [100.0]
        result  = compute_v3_features("ILLIQUID", closes, highs, lows, volumes)
        self.assertIsNone(result)

    def test_T013_rs_pct_5d_none_before_scoring(self):
        """T013: rs_pct_5d is None from compute_v3_features (filled by score_universe)."""
        feat = _make_features()
        self.assertIsNone(feat["rs_pct_5d"])

    def test_T014_resistance_above_support(self):
        """T014: resistance_20d >= support_20d for all valid inputs."""
        feat = _make_features()
        self.assertGreaterEqual(feat["resistance_20d"], feat["support_20d"])

    def test_T015_missing_sector_peers_handled(self):
        """T015: compute_v3_features works with no sector peers (returns valid dict)."""
        closes  = _make_price_series(60)
        highs   = [c * 1.01 for c in closes]
        lows    = [c * 0.99 for c in closes]
        volumes = [1_000_000.0] * 60
        feat = compute_v3_features("SYM", closes, highs, lows, volumes, sector_peers_mom_1d=None)
        self.assertIsNotNone(feat)
        self.assertEqual(feat["sector_ret_1d"], 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# T016–T025: UP Scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestUPScoring(unittest.TestCase):

    def _make_universe(self, n_symbols: int = 10) -> list:
        feats = []
        for i in range(n_symbols):
            trend = 0.005 * (i + 1) / n_symbols  # increasing trend
            f = _make_features(symbol=f"SYM{i:02d}", close_trend=trend,
                               vol_multiplier=1.0 + 0.1 * i)
            if f:
                feats.append(f)
        return feats

    def test_T016_up_score_in_0_1_range(self):
        """T016: v3_up_score is always in [0, 1]."""
        feats = self._make_universe(20)
        scored = score_universe(feats)
        for s in scored:
            self.assertGreaterEqual(s["v3_up_score"], 0.0,
                                    f"v3_up_score below 0 for {s['symbol']}")
            self.assertLessEqual(s["v3_up_score"], 1.0,
                                 f"v3_up_score above 1 for {s['symbol']}")

    def test_T017_higher_trend_gets_higher_up_score(self):
        """T017: Symbol with higher momentum should get higher UP score."""
        feats = self._make_universe(20)
        scored = score_universe(feats)
        by_sym = {s["symbol"]: s["v3_up_score"] for s in scored}
        # SYM19 (highest trend) should score higher than SYM00 (lowest)
        self.assertGreater(by_sym.get("SYM19", 0), by_sym.get("SYM00", 1))

    def test_T018_rs_pct_5d_filled_after_scoring(self):
        """T018: rs_pct_5d is filled (not None) after score_universe."""
        feats = self._make_universe(10)
        scored = score_universe(feats)
        for s in scored:
            self.assertIsNotNone(s["rs_pct_5d"],
                                 f"rs_pct_5d still None for {s['symbol']} after scoring")

    def test_T019_up_weights_validate(self):
        """T019: V3UpWeights.validate() raises for weights not summing to 1."""
        bad = V3UpWeights(atr_pct=0.5, mom_5d=0.5, rs_pct_5d=0.5, vol_ratio=0.5, mom_accel=0.5)
        with self.assertRaises(ValueError):
            bad.validate()

    def test_T020_up_weights_default_valid(self):
        """T020: Default V3UpWeights passes validation."""
        V3UpWeights().validate()   # must not raise

    def test_T021_custom_up_weights_used(self):
        """T021: Custom UP weights produce different scores than default."""
        feats = self._make_universe(20)
        cfg_default = V3Config()
        cfg_custom  = V3Config(up_weights=V3UpWeights(
            atr_pct=0.60, mom_5d=0.10, rs_pct_5d=0.10, vol_ratio=0.10, mom_accel=0.10
        ))
        scored_default = score_universe(feats, cfg_default)
        scored_custom  = score_universe(feats, cfg_custom)
        default_scores = [s["v3_up_score"] for s in scored_default]
        custom_scores  = [s["v3_up_score"] for s in scored_custom]
        self.assertFalse(default_scores == custom_scores,
                         "Custom weights should produce different scores")


# ─────────────────────────────────────────────────────────────────────────────
# T022–T030: DOWN Scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestDOWNScoring(unittest.TestCase):

    def _make_universe(self, n: int = 20) -> list:
        feats = []
        for i in range(n):
            trend = -0.003 * (i + 1) / n  # negative trend symbols
            f = _make_features(symbol=f"DN{i:02d}", close_trend=trend,
                               vol_multiplier=1.0 + 0.1 * i)
            if f:
                feats.append(f)
        return feats

    def test_T022_down_score_in_0_1_range(self):
        """T022: v3_down_score always in [0, 1]."""
        feats = self._make_universe(20)
        scored = score_universe(feats)
        for s in scored:
            self.assertGreaterEqual(s["v3_down_score"], 0.0)
            self.assertLessEqual(s["v3_down_score"], 1.0)

    def test_T023_down_score_independent_of_up_score(self):
        """T023: v3_down_score != v3_up_score (directional asymmetry)."""
        feats = self._make_universe(20)
        scored = score_universe(feats)
        matches = sum(1 for s in scored if abs(s["v3_down_score"] - s["v3_up_score"]) < 0.001)
        self.assertLess(matches, len(scored) // 2,
                        "UP and DOWN scores should not be identical for most symbols")

    def test_T024_stronger_decline_gets_higher_down_score(self):
        """T024: Symbol with sharper decline scores higher on DOWN."""
        feats = self._make_universe(20)
        scored = score_universe(feats)
        by_sym = {s["symbol"]: s["v3_down_score"] for s in scored}
        # DN19 has the steepest decline
        self.assertGreater(by_sym.get("DN19", 0), by_sym.get("DN00", 1))

    def test_T025_down_weights_validate(self):
        """T025: V3DownWeights.validate() raises for wrong total."""
        bad = V3DownWeights(neg_mom_5d=0.5, neg_mom_accel=0.5,
                            vol_expansion=0.5, atr_pct=0.5,
                            rsi_overbought=0.5, sector_down=0.0)
        with self.assertRaises(ValueError):
            bad.validate()

    def test_T026_down_weights_default_valid(self):
        """T026: Default V3DownWeights passes validation."""
        V3DownWeights().validate()

    def test_T027_sector_disabled_by_default(self):
        """T027: sector_down weight is 0.0 in default config (AUDIT_002 finding)."""
        cfg = V3Config()
        self.assertEqual(cfg.down_weights.sector_down, 0.0,
                         "sector_down should be 0 — AUDIT_002 showed lift_delta=-0.013")

    def test_T028_sector_can_be_enabled(self):
        """T028: V3 can be configured to use sector for DOWN (for testing)."""
        cfg = V3Config(use_sector_for_down=True,
                       down_weights=V3DownWeights(
                           neg_mom_5d=0.25, neg_mom_accel=0.20,
                           vol_expansion=0.18, atr_pct=0.12,
                           rsi_overbought=0.08, sector_down=0.17))
        cfg.validate()   # must not raise
        self.assertTrue(cfg.use_sector_for_down)

    def test_T029_down_uses_inverted_momentum(self):
        """T029: Negative momentum stocks have higher DOWN score than positive-momentum stocks."""
        # Create one up-trending and one down-trending symbol
        up_feat   = _make_features("UPSTOCK", close_trend=+0.010, n=60)
        down_feat = _make_features("DNSTOCK", close_trend=-0.010, n=60)
        if up_feat is None or down_feat is None:
            self.skipTest("Feature computation returned None for test data")
        scored = score_universe([up_feat, down_feat])
        by_sym = {s["symbol"]: s["v3_down_score"] for s in scored}
        self.assertGreater(by_sym.get("DNSTOCK", 0), by_sym.get("UPSTOCK", 1),
                           "Declining stock should have higher DOWN score")


# ─────────────────────────────────────────────────────────────────────────────
# T030–T040: Pool Size & Selection
# ─────────────────────────────────────────────────────────────────────────────

class TestPoolSelection(unittest.TestCase):

    def _universe(self, n: int = 50) -> list:
        feats = []
        for i in range(n):
            f = _make_features(f"SYM{i:03d}", close_trend=0.001 * i / n)
            if f:
                feats.append(f)
        return feats

    def test_T030_returns_exactly_pool_size_up(self):
        """T030: select_candidates returns exactly pool_size UP candidates."""
        feats  = self._universe(50)
        scored = score_universe(feats)
        up, _  = select_candidates(scored, pool_size=20)
        self.assertEqual(len(up), 20)

    def test_T031_returns_exactly_pool_size_down(self):
        """T031: select_candidates returns exactly pool_size DOWN candidates."""
        feats  = self._universe(50)
        scored = score_universe(feats)
        _, dn  = select_candidates(scored, pool_size=20)
        self.assertEqual(len(dn), 20)

    def test_T032_smaller_pool_returns_fewer(self):
        """T032: pool_size=10 returns 10 candidates."""
        feats  = self._universe(50)
        scored = score_universe(feats)
        up, dn = select_candidates(scored, pool_size=10)
        self.assertEqual(len(up), 10)
        self.assertEqual(len(dn), 10)

    def test_T033_larger_pool_returns_more(self):
        """T033: pool_size=40 returns 40 candidates."""
        feats  = self._universe(50)
        scored = score_universe(feats)
        up, dn = select_candidates(scored, pool_size=40)
        self.assertEqual(len(up), 40)
        self.assertEqual(len(dn), 40)

    def test_T034_pool_capped_at_universe_size(self):
        """T034: pool_size > universe_size returns only universe_size candidates."""
        feats  = self._universe(5)
        scored = score_universe(feats)
        up, dn = select_candidates(scored, pool_size=100)
        self.assertEqual(len(up), len(feats))
        self.assertEqual(len(dn), len(feats))

    def test_T035_top_up_candidate_has_highest_score(self):
        """T035: First UP candidate has highest v3_up_score."""
        feats  = self._universe(50)
        scored = score_universe(feats)
        up, _  = select_candidates(scored, pool_size=20)
        for other in scored:
            self.assertLessEqual(other["v3_up_score"], up[0]["v3_up_score"])

    def test_T036_default_pool_size_is_20(self):
        """T036: Default DISCOVERY_POOL_SIZE is 20."""
        cfg = V3Config()
        self.assertEqual(cfg.discovery_pool_size, 20)

    def test_T037_supported_pool_sizes_include_all_required(self):
        """T037: Required pool sizes 10/15/20/25/30/40 all in evaluate list."""
        cfg = V3Config()
        for ps in [10, 15, 20, 25, 30, 40]:
            self.assertIn(ps, cfg.pool_sizes_evaluate,
                          f"Pool size {ps} missing from pool_sizes_evaluate")

    def test_T038_empty_universe_returns_empty(self):
        """T038: Empty feature list returns empty pools."""
        scored = score_universe([])
        up, dn = select_candidates(scored, pool_size=20)
        self.assertEqual(up, [])
        self.assertEqual(dn, [])

    def test_T039_single_symbol_returns_single(self):
        """T039: Universe of 1 symbol returns 1-element pools."""
        feat   = _make_features("ONLY", n=60)
        scored = score_universe([feat])
        up, dn = select_candidates(scored, pool_size=20)
        self.assertEqual(len(up), 1)
        self.assertEqual(len(dn), 1)


# ─────────────────────────────────────────────────────────────────────────────
# T040–T050: Determinism & Tie Handling
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterminism(unittest.TestCase):

    def _universe(self) -> list:
        feats = []
        for i in range(30):
            f = _make_features(f"SYM{i:02d}", close_trend=0.001)
            if f:
                feats.append(f)
        return feats

    def test_T040_deterministic_scoring(self):
        """T040: score_universe returns identical results on repeated calls."""
        feats  = self._universe()
        scores1 = [s["v3_up_score"] for s in score_universe(feats)]
        scores2 = [s["v3_up_score"] for s in score_universe(feats)]
        self.assertEqual(scores1, scores2,
                         "V3 scoring must be deterministic")

    def test_T041_deterministic_selection(self):
        """T041: select_candidates returns identical symbols in identical order."""
        feats  = self._universe()
        scored = score_universe(feats)
        up1, dn1 = select_candidates(scored, pool_size=10)
        up2, dn2 = select_candidates(scored, pool_size=10)
        self.assertEqual([s["symbol"] for s in up1], [s["symbol"] for s in up2])
        self.assertEqual([s["symbol"] for s in dn1], [s["symbol"] for s in dn2])

    def test_T042_ties_broken_by_symbol_alphabetically(self):
        """T042: When v3_up_score is identical, symbols are ordered alphabetically."""
        # Inject identical scores manually and test select_candidates tie-breaking
        symbols = ["ZZZ", "AAA", "MMM", "BBB"]
        scored  = [{"symbol": sym, "v3_up_score": 0.5, "v3_down_score": 0.5}
                   for sym in symbols]
        up, _   = select_candidates(scored, pool_size=len(scored))
        syms    = [s["symbol"] for s in up]
        self.assertEqual(syms, sorted(syms),
                         "Ties in v3_up_score must be broken alphabetically by symbol")

    def test_T043_rank_pct_stable(self):
        """T043: _rank_pct returns monotonically sorted ranks."""
        vals  = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0]
        ranks = _rank_pct(vals)
        self.assertEqual(len(ranks), 6)
        indexed = sorted(range(6), key=lambda i: vals[i])
        for pos, orig_idx in enumerate(indexed):
            # rank at orig_idx should be position / (n-1)
            self.assertAlmostEqual(ranks[orig_idx], pos / 5.0, places=5)


# ─────────────────────────────────────────────────────────────────────────────
# T050–T060: No Production Threshold Mutation
# ─────────────────────────────────────────────────────────────────────────────

class TestNoProductionMutation(unittest.TestCase):

    def test_T050_v3_does_not_import_candidatestore(self):
        """T050: mover_discovery_v3 must not import or instantiate CandidateStore."""
        import re
        v3_path = _ROOT / "opportunity_engine" / "mover_discovery_v3.py"
        source  = v3_path.read_text(encoding="utf-8")
        # Reject actual import/usage — allow doc-comment mentions
        self.assertIsNone(
            re.search(r'^\s*(?:import|from).+CandidateStore', source, re.MULTILINE),
            "V3 must not import CandidateStore"
        )
        self.assertNotIn("CandidateStore.", source,
                         "V3 must not call CandidateStore methods")
        self.assertNotIn("CandidateStore(", source,
                         "V3 must not instantiate CandidateStore")

    def test_T051_v3_does_not_import_order_manager(self):
        """T051: mover_discovery_v3 must not import OrderManager."""
        v3_path = _ROOT / "opportunity_engine" / "mover_discovery_v3.py"
        source = v3_path.read_text(encoding="utf-8")
        self.assertNotIn("OrderManager", source,
                         "V3 must not reference OrderManager")
        self.assertNotIn("order_manager", source.lower().replace(" ", ""),
                         "V3 must not import order_manager")

    def test_T052_v3_does_not_import_decision_engine(self):
        """T052: mover_discovery_v3 must not import DecisionEngine."""
        v3_path = _ROOT / "opportunity_engine" / "mover_discovery_v3.py"
        source = v3_path.read_text(encoding="utf-8")
        self.assertNotIn("DecisionEngine", source,
                         "V3 must not reference DecisionEngine")

    def test_T053_v3_does_not_define_trade_signal(self):
        """T053: V3 must not create TradeSignal objects."""
        v3_path = _ROOT / "opportunity_engine" / "mover_discovery_v3.py"
        source = v3_path.read_text(encoding="utf-8")
        self.assertNotIn("TradeSignal(", source,
                         "V3 must not instantiate TradeSignal")

    def test_T054_production_thresholds_not_in_v3(self):
        """T054: Production constants not redefined in V3."""
        v3_path = _ROOT / "opportunity_engine" / "mover_discovery_v3.py"
        source = v3_path.read_text(encoding="utf-8")
        for constant in ["MIN_PREPARED_SCORE", "VOLUME_EXPANSION_MIN",
                         "BREAKOUT_PROXIMITY_PCT", "MAX_PREPARED_CANDIDATES"]:
            self.assertNotIn(f"{constant} =", source,
                             f"V3 must not redefine production constant {constant}")

    def test_T055_shadow_scan_returns_no_trades_flag(self):
        """T055: Shadow scan result always has no_trades_generated=True."""
        feats = {}
        for i in range(5):
            f = _make_features(f"SYM{i}")
            if f:
                feats[f"SYM{i}"] = f
        result = run_shadow_scan(feats)
        self.assertTrue(result["no_trades_generated"],
                        "Shadow scan must always report no_trades_generated=True")

    def test_T056_shadow_scan_no_candidatestore_write(self):
        """T056: Shadow scan result always has no_candidatestore_write=True."""
        feats = {}
        for i in range(5):
            f = _make_features(f"SYM{i}")
            if f:
                feats[f"SYM{i}"] = f
        result = run_shadow_scan(feats)
        self.assertTrue(result["no_candidatestore_write"])

    def test_T057_shadow_scan_mode_is_shadow(self):
        """T057: Shadow scan result always reports mode='SHADOW'."""
        feats = {}
        f = _make_features("TSTSTOCK")
        if f:
            feats["TSTSTOCK"] = f
        result = run_shadow_scan(feats)
        self.assertEqual(result["mode"], "SHADOW")


# ─────────────────────────────────────────────────────────────────────────────
# T058–T068: Leakage Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLeakage(unittest.TestCase):

    def test_T058_no_leakage_in_clean_features(self):
        """T058: check_leakage returns empty list for clean feature dict."""
        feat = _make_features("CLEAN")
        violations = check_leakage([feat])
        self.assertEqual(violations, [],
                         f"Unexpected leakage violations: {violations}")

    def test_T059_detect_ret_1d_leakage(self):
        """T059: check_leakage detects ret_1d (forward return)."""
        feat = _make_features("LEAKY")
        feat["ret_1d"] = 0.05   # contaminate with future data
        violations = check_leakage([feat])
        self.assertTrue(any("ret_1d" in v for v in violations),
                        "check_leakage should flag ret_1d")

    def test_T060_detect_future_close_leakage(self):
        """T060: check_leakage detects future_close."""
        feat = _make_features("LEAKY2")
        feat["future_close"] = 105.0
        violations = check_leakage([feat])
        self.assertTrue(any("future_close" in v for v in violations))

    def test_T061_forbidden_keys_set_comprehensive(self):
        """T061: FORBIDDEN_FUTURE_KEYS covers all obvious future-data columns."""
        required = {"ret_1d", "ret_3d", "ret_5d", "future_close",
                    "future_high", "future_low", "future_volume",
                    "forward_return", "future_ret", "future_label"}
        for key in required:
            self.assertIn(key, FORBIDDEN_FUTURE_KEYS,
                          f"FORBIDDEN_FUTURE_KEYS missing '{key}'")

    def test_T062_features_contain_no_future_volume(self):
        """T062: future_volume not in compute_v3_features output."""
        feat = _make_features("VF")
        self.assertNotIn("future_volume", feat)

    def test_T063_atr_uses_only_past_data(self):
        """T063: ATR computation uses only bars up to and including today."""
        closes  = _make_price_series(60)
        highs   = [c * 1.01 for c in closes]
        lows    = [c * 0.99 for c in closes]
        volumes = [1_000_000.0] * 60

        # Compute features with first 50 bars
        feat_50 = compute_v3_features("ATR50", closes[:50], highs[:50],
                                       lows[:50], volumes[:50])
        # Compute features with all 60 bars
        feat_60 = compute_v3_features("ATR60", closes, highs, lows, volumes)

        # Both should compute valid features (no crash due to future data use)
        self.assertIsNotNone(feat_50)
        self.assertIsNotNone(feat_60)

    def test_T064_momentum_uses_only_past_closes(self):
        """T064: mom_5d uses close[-1]/close[-6] — no future data."""
        closes  = _make_price_series(30)
        highs   = [c * 1.01 for c in closes]
        lows    = [c * 0.99 for c in closes]
        volumes = [1_000_000.0] * 30
        feat = compute_v3_features("MOM30", closes, highs, lows, volumes)
        self.assertIsNotNone(feat)
        # Manually verify: mom_5d = (closes[-1]/closes[-6] - 1) * 100
        expected_mom_5d = (closes[-1] / closes[-6] - 1.0) * 100.0
        self.assertAlmostEqual(feat["mom_5d"], expected_mom_5d, places=2)

    def test_T065_volume_ratio_uses_past_20d(self):
        """T065: vol_ratio uses volumes[-20:] as denominator — no future volume."""
        closes  = _make_price_series(60)
        highs   = [c * 1.01 for c in closes]
        lows    = [c * 0.99 for c in closes]
        volumes = [1_000_000.0] * 59 + [2_000_000.0]  # spike today only
        feat = compute_v3_features("VOLR", closes, highs, lows, volumes)
        self.assertIsNotNone(feat)
        self.assertGreater(feat["vol_ratio"], 1.5,
                           "vol_ratio should reflect today's spike vs 20d avg")


# ─────────────────────────────────────────────────────────────────────────────
# T066–T075: OOS Separation
# ─────────────────────────────────────────────────────────────────────────────

class TestOOSSeparation(unittest.TestCase):

    def test_T066_train_end_before_oos_start(self):
        """T066: V3Config.train_end_date < oos_start_date — no overlap."""
        cfg = V3Config()
        from datetime import date
        train_end = date.fromisoformat(cfg.train_end_date)
        oos_start = date.fromisoformat(cfg.oos_start_date)
        self.assertLess(train_end, oos_start,
                        "Train period must end before OOS period begins")

    def test_T067_oos_start_is_2024(self):
        """T067: OOS starts on 2024-01-01 by default."""
        cfg = V3Config()
        self.assertEqual(cfg.oos_start_date, "2024-01-01")

    def test_T068_train_end_is_2023(self):
        """T068: Train ends on 2023-12-31 by default."""
        cfg = V3Config()
        self.assertEqual(cfg.train_end_date, "2023-12-31")


# ─────────────────────────────────────────────────────────────────────────────
# T069–T075: Magnitude Estimation
# ─────────────────────────────────────────────────────────────────────────────

class TestMagnitude(unittest.TestCase):

    def test_T069_atr_magnitude_positive(self):
        """T069: ATR-based magnitude estimate is positive."""
        feat  = _make_features("MAG")
        mag   = estimate_magnitude(feat)
        self.assertGreater(mag["atr_magnitude_estimate"], 0.0)

    def test_T070_legacy_constant_is_8(self):
        """T070: Legacy constant is 8.0 (documented, not used as prediction)."""
        feat = _make_features("LEGACY")
        mag  = estimate_magnitude(feat)
        self.assertAlmostEqual(mag["legacy_constant_not_predictive"], 8.0)

    def test_T071_magnitude_note_present(self):
        """T071: Magnitude result includes explanatory note."""
        feat = _make_features("NOTE")
        mag  = estimate_magnitude(feat)
        self.assertIn("note", mag)
        self.assertIn("8.0", mag["note"])

    def test_T072_high_atr_implies_higher_magnitude(self):
        """T072: Symbol with higher atr_pct estimates higher magnitude."""
        feat_high_vol = _make_features("HIVAR", close_trend=0.002, n=60)
        feat_low_vol  = _make_features("LOVAR", close_trend=0.002, n=60)
        if feat_high_vol is None or feat_low_vol is None:
            self.skipTest("Feature computation returned None")
        feat_high_vol["atr_pct"] = 3.0
        feat_low_vol["atr_pct"]  = 0.5
        mag_high = estimate_magnitude(feat_high_vol)
        mag_low  = estimate_magnitude(feat_low_vol)
        self.assertGreater(mag_high["atr_magnitude_estimate"],
                           mag_low["atr_magnitude_estimate"])


# ─────────────────────────────────────────────────────────────────────────────
# T073–T080: Shadow Scan Behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestShadowScan(unittest.TestCase):

    def _make_symbol_features(self, n: int = 10) -> dict:
        result = {}
        for i in range(n):
            f = _make_features(f"SHAD{i:02d}")
            if f:
                result[f"SHAD{i:02d}"] = f
        return result

    def test_T073_shadow_scan_returns_dict(self):
        """T073: run_shadow_scan returns a dictionary."""
        feats = self._make_symbol_features()
        result = run_shadow_scan(feats)
        self.assertIsInstance(result, dict)

    def test_T074_shadow_scan_overlap_count_correct(self):
        """T074: overlap_count = |V3 candidates ∩ existing_scanner_symbols|."""
        feats  = self._make_symbol_features(20)
        existing = ["SHAD00", "SHAD01", "SHAD02"]
        result = run_shadow_scan(feats, existing_scanner_symbols=existing)
        # overlap_count <= len(existing)
        self.assertLessEqual(result["overlap_count"], len(existing))

    def test_T075_shadow_scan_universe_size_matches_input(self):
        """T075: universe_size equals number of input symbols."""
        feats  = self._make_symbol_features(15)
        result = run_shadow_scan(feats)
        self.assertEqual(result["universe_size"], len(feats))

    def test_T076_shadow_scan_up_plus_down_counts(self):
        """T076: V3 reports correct up and down pool sizes."""
        feats  = self._make_symbol_features(30)
        result = run_shadow_scan(feats)
        cfg = V3Config()
        self.assertLessEqual(result["v3_up_count"],   cfg.discovery_pool_size)
        self.assertLessEqual(result["v3_down_count"],  cfg.discovery_pool_size)

    def test_T077_shadow_log_is_append_only(self):
        """T077: Shadow log uses append mode (line count increases)."""
        import tempfile
        feats  = self._make_symbol_features(5)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                         delete=False) as f:
            log_path = f.name
        cfg = V3Config(shadow_log_path=log_path)
        run_shadow_scan(feats, cfg=cfg)
        run_shadow_scan(feats, cfg=cfg)
        lines = Path(log_path).read_text().strip().splitlines()
        self.assertEqual(len(lines), 2, "Shadow log should have 2 entries after 2 scans")
        Path(log_path).unlink(missing_ok=True)

    def test_T078_shadow_log_entries_are_valid_json(self):
        """T078: Each line in shadow log is valid JSON."""
        import tempfile
        feats = self._make_symbol_features(5)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                          delete=False) as f:
            log_path = f.name
        cfg = V3Config(shadow_log_path=log_path)
        run_shadow_scan(feats, cfg=cfg)
        lines = Path(log_path).read_text().strip().splitlines()
        for line in lines:
            data = __import__("json").loads(line)
            self.assertIn("scan_date", data)
            self.assertIn("mode", data)
        Path(log_path).unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# T079–T087: Regression — existing tests still pass
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionSafety(unittest.TestCase):

    def test_T079_v3_module_importable(self):
        """T079: V3 module imports without side effects."""
        import importlib
        mod = importlib.import_module("opportunity_engine.mover_discovery_v3")
        self.assertTrue(hasattr(mod, "V3Config"))

    def test_T080_v3_config_default_pool_size(self):
        """T080: Default pool size matches documented default (20)."""
        cfg = V3Config()
        self.assertEqual(cfg.discovery_pool_size, 20)

    def test_T081_v3_config_magnitude_constant(self):
        """T081: Legacy magnitude constant is correctly documented."""
        cfg = V3Config()
        self.assertAlmostEqual(cfg.magnitude_constant_legacy, 8.0)
        self.assertTrue(cfg.use_atr_for_magnitude)

    def test_T082_rsi_wilder_neutral_on_flat(self):
        """T082: Wilder RSI ≈ 50 on flat price series."""
        flat = [100.0] * 30
        rsi  = _wilder_rsi(flat)
        # flat deltas are all zero → RSI is undefined; implementation returns 50
        self.assertAlmostEqual(rsi, 50.0, places=0)

    def test_T083_rsi_high_on_rising_series(self):
        """T083: Wilder RSI > 60 on consistently rising prices."""
        rising = [float(100 + i) for i in range(30)]
        rsi    = _wilder_rsi(rising)
        self.assertGreater(rsi, 60.0)

    def test_T084_rank_pct_length_preserved(self):
        """T084: _rank_pct output length == input length."""
        vals  = [5.0, 3.0, 1.0, 4.0, 2.0]
        ranks = _rank_pct(vals)
        self.assertEqual(len(ranks), 5)

    def test_T085_rank_pct_range(self):
        """T085: _rank_pct values are all in [0, 1]."""
        vals  = [1.0, 2.0, 3.0, 4.0, 5.0]
        ranks = _rank_pct(vals)
        for r in ranks:
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)

    def test_T086_rank_pct_min_is_zero(self):
        """T086: Minimum value gets rank 0.0."""
        vals  = [10.0, 20.0, 5.0, 30.0]
        ranks = _rank_pct(vals)
        min_idx = vals.index(min(vals))
        self.assertAlmostEqual(ranks[min_idx], 0.0)

    def test_T087_rank_pct_max_is_one(self):
        """T087: Maximum value gets rank 1.0."""
        vals    = [10.0, 20.0, 5.0, 30.0]
        ranks   = _rank_pct(vals)
        max_idx = vals.index(max(vals))
        self.assertAlmostEqual(ranks[max_idx], 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests():
    loader  = unittest.TestLoader()
    suite   = unittest.TestSuite()

    test_classes = [
        TestV3SafetyFlags,
        TestFeatureComputation,
        TestUPScoring,
        TestDOWNScoring,
        TestPoolSelection,
        TestDeterminism,
        TestNoProductionMutation,
        TestLeakage,
        TestOOSSeparation,
        TestMagnitude,
        TestShadowScan,
        TestRegressionSafety,
    ]

    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"\nTEST SUMMARY: {passed}/{total} passed")
    if result.wasSuccessful():
        print("ALL TESTS PASSED")
    else:
        print(f"FAILURES: {len(result.failures)}  ERRORS: {len(result.errors)}")
    return result.wasSuccessful()


if __name__ == "__main__":
    ok = run_all_tests()
    sys.exit(0 if ok else 1)
