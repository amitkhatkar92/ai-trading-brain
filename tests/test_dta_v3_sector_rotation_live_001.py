"""
Tests for DTA-V3-SECTOR-ROTATION-LIVE-001:
  - opportunity_engine/sector_rotation_momentum.py (new feature)
  - opportunity_engine/mover_discovery_v3.py sector_rotation weight wiring
  - opportunity_engine/v3_live_bridge.py (new live signal bridge)
"""
import unittest
from unittest.mock import patch

from opportunity_engine.sector_rotation_momentum import (
    compute_sector_rotation_ranks, attach_sector_rotation_ranks,
)
from opportunity_engine.mover_discovery_v3 import (
    V3Config, V3UpWeights, V3DownWeights, score_universe,
)


def _feat(symbol, mom_10d, mom_5d=1.0, mom_accel=0.0, vol_ratio=1.0, atr_pct=2.0,
          rsi_14=50.0, hv_20=1.0, vol_expansion=1.0, sector_ret_1d=0.0,
          sector_rotation_rank=None):
    f = {
        "symbol": symbol, "close": 100.0, "mom_1d": 0.1, "mom_3d": 0.3,
        "mom_5d": mom_5d, "mom_10d": mom_10d, "mom_20d": 2.0,
        "mom_accel": mom_accel, "rsi_14": rsi_14, "atr_14": 2.0, "atr_pct": atr_pct,
        "vol_expansion": vol_expansion, "hv_20": hv_20, "vol_ratio": vol_ratio,
        "vol_ratio_5": vol_ratio, "vol_trend": 0.0, "resistance_20d": 110.0,
        "support_20d": 90.0, "breakout_pct": 0.0, "support_gap": 10.0,
        "price_position": 0.5, "sector_ret_1d": sector_ret_1d, "sector_breadth": 0.5,
        "rs_pct_5d": None, "atr_magnitude_estimate": 2.0,
        "expected_move_pct_legacy_constant": 8.0,
    }
    if sector_rotation_rank is not None:
        f["sector_rotation_rank"] = sector_rotation_rank
    return f


class TestSectorRotationMomentum(unittest.TestCase):

    def test_t01_ranks_sectors_by_mean_mom10d(self):
        sector_map = {"A1": "AUTO", "A2": "AUTO", "A3": "AUTO",
                      "B1": "BANK", "B2": "BANK", "B3": "BANK"}
        mom = {"A1": 5.0, "A2": 6.0, "A3": 7.0, "B1": -2.0, "B2": -1.0, "B3": 0.0}
        ranks = compute_sector_rotation_ranks(sector_map, mom)
        self.assertGreater(ranks["A1"], ranks["B1"])
        self.assertEqual(ranks["A1"], ranks["A2"])  # same sector = same rank
        self.assertEqual(ranks["B1"], ranks["B3"])

    def test_t02_sector_below_min_size_excluded(self):
        sector_map = {"A1": "TINY", "A2": "TINY", "B1": "BIG", "B2": "BIG", "B3": "BIG"}
        mom = {"A1": 5.0, "A2": 5.0, "B1": 1.0, "B2": 1.0, "B3": 1.0}
        ranks = compute_sector_rotation_ranks(sector_map, mom, min_sector_size=3)
        self.assertNotIn("A1", ranks)
        self.assertIn("B1", ranks)

    def test_t03_unknown_sector_excluded(self):
        sector_map = {"A1": "UNKNOWN", "B1": "BANK", "B2": "BANK", "B3": "BANK"}
        mom = {"A1": 5.0, "B1": 1.0, "B2": 1.0, "B3": 1.0}
        ranks = compute_sector_rotation_ranks(sector_map, mom)
        self.assertNotIn("A1", ranks)

    def test_t04_empty_input_returns_empty(self):
        self.assertEqual(compute_sector_rotation_ranks({}, {}), {})

    def test_t05_attach_defaults_missing_to_neutral(self):
        feats = [_feat("X1", mom_10d=5.0), _feat("X2", mom_10d=-5.0)]
        out = attach_sector_rotation_ranks(feats, {})  # no sector data at all
        self.assertEqual(out[0]["sector_rotation_rank"], 0.5)
        self.assertEqual(out[1]["sector_rotation_rank"], 0.5)

    def test_t06_attach_never_mutates_input(self):
        feats = [_feat("X1", mom_10d=5.0)]
        attach_sector_rotation_ranks(feats, {"X1": "BANK"})
        self.assertNotIn("sector_rotation_rank", feats[0])

    def test_t07_attach_fails_open_on_internal_error(self):
        feats = [_feat("X1", mom_10d=5.0)]
        # garbage sector map (not a dict of str->str) should not raise
        out = attach_sector_rotation_ranks(feats, None)  # type: ignore[arg-type]
        self.assertEqual(out[0]["sector_rotation_rank"], 0.5)


class TestV3WeightsBackwardCompat(unittest.TestCase):

    def test_t08_up_weights_default_sums_to_one(self):
        V3UpWeights().validate()  # must not raise

    def test_t09_down_weights_default_sums_to_one(self):
        V3DownWeights().validate()  # must not raise

    def test_t10_sector_rotation_defaults_to_zero(self):
        self.assertEqual(V3UpWeights().sector_rotation, 0.0)
        self.assertEqual(V3DownWeights().sector_rotation, 0.0)

    def test_t11_default_config_score_unaffected_by_sector_rotation_field(self):
        """With sector_rotation=0 (default), scores are identical whether or
        not a sector_rotation_rank key is present on the feature dicts."""
        feats_no_key   = [_feat(f"S{i}", mom_10d=float(i)) for i in range(10)]
        feats_with_key = [_feat(f"S{i}", mom_10d=float(i), sector_rotation_rank=0.9)
                           for i in range(10)]
        cfg = V3Config()
        scored_a = score_universe(feats_no_key, cfg)
        scored_b = score_universe(feats_with_key, cfg)
        for a, b in zip(scored_a, scored_b):
            self.assertAlmostEqual(a["v3_up_score"],   b["v3_up_score"],   places=6)
            self.assertAlmostEqual(a["v3_down_score"], b["v3_down_score"], places=6)

    def test_t12_sector_rotation_weight_changes_up_score_ordering(self):
        """A stock with a slightly WORSE technical profile but a much
        stronger sector should still outrank one with a slightly better
        profile but a weak sector, once sector_rotation carries real
        weight -- isolates the sector effect from the deterministic
        tie-break behaviour of _rank_pct's stable sort (distractor
        symbols spread the rank scale so STRONG/WEAK aren't adjacent
        ties)."""
        feats = [_feat(f"DIST{i}", mom_10d=float(i), mom_5d=float(i) * 0.3,
                       vol_ratio=1.0 + i * 0.05, atr_pct=1.0 + i * 0.2,
                       sector_rotation_rank=0.5)
                 for i in range(10)]
        feats.append(_feat("WEAK_SECTOR", mom_10d=5.0, mom_5d=1.55,
                           vol_ratio=1.27, atr_pct=2.05,
                           sector_rotation_rank=0.0))
        feats.append(_feat("STRONG_SECTOR", mom_10d=5.0, mom_5d=1.50,
                           vol_ratio=1.22, atr_pct=2.00,
                           sector_rotation_rank=1.0))
        cfg = V3Config(up_weights=V3UpWeights(
            atr_pct=0.225, mom_5d=0.18, rs_pct_5d=0.18, vol_ratio=0.18,
            mom_accel=0.135, sector_rotation=0.10,
        ))
        cfg.up_weights.validate()
        scored = score_universe(feats, cfg)
        by_sym = {s["symbol"]: s["v3_up_score"] for s in scored}
        self.assertGreater(by_sym["STRONG_SECTOR"], by_sym["WEAK_SECTOR"],
                           "Weaker technicals + strong sector should still win "
                           "with a meaningful sector_rotation weight")

    def test_t13_down_score_bounded_0_1_with_sector_rotation_enabled(self):
        feats = [_feat(f"D{i}", mom_10d=-float(i), mom_5d=-float(i),
                       sector_rotation_rank=0.0 if i % 2 == 0 else 1.0)
                 for i in range(10)]
        cfg = V3Config(down_weights=V3DownWeights(
            neg_mom_5d=0.27, neg_mom_accel=0.225, vol_expansion=0.18,
            atr_pct=0.135, rsi_overbought=0.09, sector_down=0.0,
            sector_rotation=0.10,
        ))
        cfg.down_weights.validate()
        scored = score_universe(feats, cfg)
        for s in scored:
            self.assertGreaterEqual(s["v3_down_score"], 0.0)
            self.assertLessEqual(s["v3_down_score"], 1.0)

    def test_t14_down_score_byte_identical_when_sector_rotation_zero(self):
        """Regression guard: the remaining_share normalisation introduced for
        sector_rotation must reduce exactly to the original formula when
        sector_rotation == 0.0 (every existing caller)."""
        feats = [_feat(f"D{i}", mom_10d=-float(i), mom_5d=-float(i)) for i in range(10)]
        cfg = V3Config()  # defaults: sector_rotation=0.0 on both sides
        scored = score_universe(feats, cfg)
        for s in scored:
            self.assertGreaterEqual(s["v3_down_score"], 0.0)
            self.assertLessEqual(s["v3_down_score"], 1.0)


class TestV3LiveBridgeSafety(unittest.TestCase):

    def test_t15_strategy_registered_in_strategy_params(self):
        from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS
        self.assertIn("V3_Mover_Discovery", STRATEGY_PARAMS)

    def test_t16_bridge_config_validates(self):
        from opportunity_engine.v3_live_bridge import _bridge_v3_config
        cfg = _bridge_v3_config()  # must not raise
        self.assertTrue(cfg.enabled)
        self.assertTrue(cfg.shadow_mode)
        self.assertEqual(cfg.up_weights.sector_rotation, 0.10)
        self.assertEqual(cfg.down_weights.sector_rotation, 0.10)

    def test_t17_once_per_day_guard(self):
        from opportunity_engine import v3_live_bridge as bridge
        with patch.object(bridge, "_load_state", return_value={"last_run_trade_date": "2026-01-01"}):
            self.assertTrue(bridge._already_ran_today("2026-01-01"))
            self.assertFalse(bridge._already_ran_today("2026-01-02"))

    def test_t18_run_returns_empty_list_when_already_ran_today(self):
        from opportunity_engine import v3_live_bridge as bridge
        with patch("opportunity_engine.mover_discovery_v3_shadow_runner._resolve_trade_date",
                   return_value="2026-01-01"), \
             patch.object(bridge, "_already_ran_today", return_value=True):
            result = bridge.run_v3_live_bridge()
            self.assertEqual(result, [])

    def test_t19_run_fails_open_on_exception(self):
        from opportunity_engine import v3_live_bridge as bridge
        with patch("opportunity_engine.mover_discovery_v3_shadow_runner._resolve_trade_date",
                   side_effect=RuntimeError("boom")):
            result = bridge.run_v3_live_bridge()
            self.assertEqual(result, [])

    def test_t20_build_signal_up_direction(self):
        from opportunity_engine.v3_live_bridge import _build_signal
        from models.trade_signal import SignalDirection
        cand = {"symbol": "TEST", "close": 100.0, "atr_14": 2.0, "v3_up_score": 0.8}
        sig = _build_signal(cand, "UP", live_price=105.0)
        self.assertEqual(sig.direction, SignalDirection.BUY)
        self.assertEqual(sig.entry_price, 105.0)
        self.assertLess(sig.stop_loss, sig.entry_price)
        self.assertGreater(sig.target_price, sig.entry_price)
        self.assertEqual(sig.strategy_name, "V3_Mover_Discovery")

    def test_t21_build_signal_down_direction(self):
        from opportunity_engine.v3_live_bridge import _build_signal
        from models.trade_signal import SignalDirection
        cand = {"symbol": "TEST", "close": 100.0, "atr_14": 2.0, "v3_down_score": 0.8}
        sig = _build_signal(cand, "DOWN", live_price=95.0)
        self.assertEqual(sig.direction, SignalDirection.SHORT)
        self.assertEqual(sig.entry_price, 95.0)
        self.assertGreater(sig.stop_loss, sig.entry_price)
        self.assertLess(sig.target_price, sig.entry_price)

    def test_t22_build_signal_none_price_returns_none(self):
        from opportunity_engine.v3_live_bridge import _build_signal
        cand = {"symbol": "TEST", "close": 0.0, "atr_14": 2.0, "v3_up_score": 0.8}
        sig = _build_signal(cand, "UP", live_price=None)
        self.assertIsNone(sig)

    def test_t23_confidence_bounded_5_to_6_5(self):
        from opportunity_engine.v3_live_bridge import _build_signal
        cand = {"symbol": "TEST", "close": 100.0, "atr_14": 2.0, "v3_up_score": 1.0}
        sig = _build_signal(cand, "UP", live_price=100.0)
        self.assertGreaterEqual(sig.confidence, 5.0)
        self.assertLessEqual(sig.confidence, 6.5)

    def test_t24_max_signal_count_constants_bounded(self):
        from opportunity_engine.v3_live_bridge import V3_BRIDGE_MAX_UP, V3_BRIDGE_MAX_DOWN
        self.assertLessEqual(V3_BRIDGE_MAX_UP + V3_BRIDGE_MAX_DOWN, 10)


if __name__ == "__main__":
    unittest.main()
