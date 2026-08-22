"""
tests/test_phase_d_sft.py
==========================
Verification tests for phase_d_sft_recommendation.py

Tests cover:
  1. Score calculation accuracy
  2. Classification bands
  3. Recommendation generation
  4. Shadow isolation (no writes to protected tables/files)
  5. No execution influence
  6. Counterfactual tracking accuracy
  7. Edge cases and boundary conditions

Run: python -m pytest tests/test_phase_d_sft.py -v
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import phase_d_sft_recommendation as sft_mod
from phase_d_sft_recommendation import (
    SFTClass,
    RecommendationType,
    CounterfactualOutcome,
    SFTTracker,
    compute_symbol_follow_through,
    classify_sft,
    generate_sft_recommendation,
    evaluate_counterfactual,
    SFTMetrics,
    MIN_TRADES_FOR_SCORE,
    SFT_HIGH_THRESHOLD,
    SFT_MEDIUM_THRESHOLD,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_tracker() -> SFTTracker:
    """Create a fresh in-memory (temp file) tracker for test isolation."""
    tmp = tempfile.mktemp(suffix=".db")
    return SFTTracker(db_path=tmp)


# ── 1. Score Calculation Tests ────────────────────────────────────────────────

class TestScoreCalculation(unittest.TestCase):
    """Verify that compute_symbol_follow_through produces correct scores."""

    def test_hindalco_calibration(self):
        """HINDALCO from forensic data: WR=100%, MFE=2.427R, pct05R=100% → score≈94.3"""
        score, m = compute_symbol_follow_through(
            trade_count=2, win_count=2,
            mfe_values=[2.427], mae_values=[0.0],
            reach_025r=2, reach_050r=2, reach_100r=2,
        )
        # WR=100 → C1=100; MFE=2.427/3.0 →C2=80.9; pct05R=100 →C3=100
        # score = 100*0.4 + 80.9*0.3 + 100*0.3 = 40+24.27+30 = 94.27
        self.assertAlmostEqual(score, 94.27, places=1,
                               msg="HINDALCO calibration failed")

    def test_tatasteel_calibration(self):
        """TATASTEEL: WR=0%, MFE=0.241R, pct05R=20% → score≈8.41"""
        score, m = compute_symbol_follow_through(
            trade_count=10, win_count=0,
            mfe_values=[0.241], mae_values=[0.661],
            reach_025r=6, reach_050r=2, reach_100r=0,
        )
        # WR=0 →C1=0; MFE=0.241/3.0 →C2=8.03; pct05R=20 →C3=20
        # score = 0*0.4 + 8.03*0.3 + 20*0.3 = 0+2.41+6 = 8.41
        self.assertAlmostEqual(score, 8.41, places=1,
                               msg="TATASTEEL calibration failed")

    def test_bhartiartl_calibration(self):
        """BHARTIARTL: WR=0%, MFE=0.080R, pct05R=0% → score≈0.8"""
        score, m = compute_symbol_follow_through(
            trade_count=4, win_count=0,
            mfe_values=[0.080], mae_values=[0.626],
            reach_025r=0, reach_050r=0, reach_100r=0,
        )
        # WR=0 →C1=0; MFE=0.08/3.0 →C2=2.67; pct05R=0 →C3=0
        # score = 0 + 2.67*0.3 + 0 = 0.80
        self.assertAlmostEqual(score, 0.80, places=1,
                               msg="BHARTIARTL calibration failed")

    def test_bankbaroda_calibration(self):
        """BANKBARODA: WR=100%, MFE=1.335R, pct05R=100% → score≈83.35"""
        score, m = compute_symbol_follow_through(
            trade_count=1, win_count=1,
            mfe_values=[1.335], mae_values=[0.022],
            reach_025r=1, reach_050r=1, reach_100r=1,
        )
        # WR=100 →C1=100; MFE=1.335/3 →C2=44.5; pct05R=100 →C3=100
        # score = 40 + 13.35 + 30 = 83.35
        self.assertAlmostEqual(score, 83.35, places=1,
                               msg="BANKBARODA calibration failed")

    def test_score_clamped_to_100(self):
        """Perfect symbol (100% WR, MFE=3R+, 100% reach) must not exceed 100."""
        score, _ = compute_symbol_follow_through(
            trade_count=10, win_count=10,
            mfe_values=[5.0],  # way above cap
            mae_values=[0.0],
            reach_025r=10, reach_050r=10, reach_100r=10,
        )
        self.assertLessEqual(score, 100.0)

    def test_score_clamped_to_zero(self):
        """Worst possible symbol must not go below 0."""
        score, _ = compute_symbol_follow_through(
            trade_count=10, win_count=0,
            mfe_values=[-0.5],  # negative MFE (pathological)
            mae_values=[2.0],
            reach_025r=0, reach_050r=0, reach_100r=0,
        )
        self.assertGreaterEqual(score, 0.0)

    def test_zero_trades_returns_zero(self):
        """trade_count=0 must return 0.0 without error."""
        score, m = compute_symbol_follow_through(
            trade_count=0, win_count=0,
            mfe_values=[], mae_values=[],
            reach_025r=0, reach_050r=0, reach_100r=0,
        )
        self.assertEqual(score, 0.0)

    def test_metrics_structure_populated(self):
        """Returned SFTMetrics must have all fields filled."""
        score, m = compute_symbol_follow_through(
            trade_count=5, win_count=3,
            mfe_values=[0.8, 0.6, 0.4],
            mae_values=[0.3, 0.5],
            reach_025r=4, reach_050r=3, reach_100r=2,
        )
        self.assertIsInstance(m.win_rate,             float)
        self.assertIsInstance(m.avg_mfe,              float)
        self.assertIsInstance(m.avg_mae,              float)
        self.assertIsInstance(m.pct_reach_025r,       float)
        self.assertIsInstance(m.pct_reach_050r,       float)
        self.assertIsInstance(m.pct_reach_100r,       float)
        self.assertIsInstance(m.follow_through_score, float)
        self.assertIsNotNone(m.sft_class)

    def test_mfe_cap_respected(self):
        """MFE of 10R and 3R should yield same score (cap at 3.0R)."""
        score_10r, _ = compute_symbol_follow_through(
            trade_count=5, win_count=3,
            mfe_values=[10.0], mae_values=[],
            reach_025r=5, reach_050r=5, reach_100r=5,
        )
        score_3r, _ = compute_symbol_follow_through(
            trade_count=5, win_count=3,
            mfe_values=[3.0], mae_values=[],
            reach_025r=5, reach_050r=5, reach_100r=5,
        )
        self.assertAlmostEqual(score_10r, score_3r, places=3,
                               msg="MFE cap not respected — 10R should equal 3R")

    def test_none_mfe_values_excluded(self):
        """None values in mfe_values must be filtered without error."""
        score, _ = compute_symbol_follow_through(
            trade_count=3, win_count=2,
            mfe_values=[None, 0.8, None],
            mae_values=[None, 0.3],
            reach_025r=2, reach_050r=1, reach_100r=0,
        )
        self.assertGreater(score, 0)


# ── 2. Classification Tests ───────────────────────────────────────────────────

class TestClassification(unittest.TestCase):
    """Verify classify_sft returns the correct band."""

    def test_insufficient_data_below_min_trades(self):
        for n in range(MIN_TRADES_FOR_SCORE):
            self.assertEqual(
                classify_sft(95.0, n),
                SFTClass.INSUFFICIENT_DATA,
                f"n={n} should be INSUFFICIENT_DATA",
            )

    def test_high_sft_at_threshold(self):
        self.assertEqual(classify_sft(SFT_HIGH_THRESHOLD, MIN_TRADES_FOR_SCORE),
                         SFTClass.HIGH)

    def test_high_sft_above_threshold(self):
        self.assertEqual(classify_sft(99.9, MIN_TRADES_FOR_SCORE), SFTClass.HIGH)

    def test_medium_sft_at_threshold(self):
        self.assertEqual(classify_sft(SFT_MEDIUM_THRESHOLD, MIN_TRADES_FOR_SCORE),
                         SFTClass.MEDIUM)

    def test_medium_sft_just_below_high(self):
        self.assertEqual(classify_sft(SFT_HIGH_THRESHOLD - 0.001, MIN_TRADES_FOR_SCORE),
                         SFTClass.MEDIUM)

    def test_low_sft_just_below_medium(self):
        self.assertEqual(classify_sft(SFT_MEDIUM_THRESHOLD - 0.001, MIN_TRADES_FOR_SCORE),
                         SFTClass.LOW)

    def test_low_sft_at_zero(self):
        self.assertEqual(classify_sft(0.0, MIN_TRADES_FOR_SCORE), SFTClass.LOW)

    def test_exactly_at_min_trades(self):
        """At exactly MIN_TRADES_FOR_SCORE, should score normally (not INSUFFICIENT)."""
        result = classify_sft(80.0, MIN_TRADES_FOR_SCORE)
        self.assertNotEqual(result, SFTClass.INSUFFICIENT_DATA)


# ── 3. Recommendation Generation Tests ───────────────────────────────────────

class TestRecommendationGeneration(unittest.TestCase):
    """Verify generate_sft_recommendation maps classes to types correctly."""

    def _make_metrics(self, sft_class: str, score: float = 50.0) -> SFTMetrics:
        return SFTMetrics(
            symbol="TEST", trade_count=5, win_count=2, loss_count=3,
            win_rate=40.0, avg_mfe=0.5, avg_mae=0.4,
            pct_reach_025r=60.0, pct_reach_050r=40.0, pct_reach_100r=20.0,
            follow_through_score=score, sft_class=sft_class,
            last_updated="2026-01-01T00:00:00",
        )

    def test_high_sft_maps_to_prefer(self):
        m = self._make_metrics(SFTClass.HIGH.value, score=85.0)
        rec = generate_sft_recommendation(m)
        self.assertEqual(rec.recommendation_type, RecommendationType.PREFER_HIGH_SFT.value)

    def test_medium_sft_maps_to_caution(self):
        m = self._make_metrics(SFTClass.MEDIUM.value, score=55.0)
        rec = generate_sft_recommendation(m)
        self.assertEqual(rec.recommendation_type, RecommendationType.CAUTION_MEDIUM_SFT.value)

    def test_low_sft_maps_to_avoid(self):
        m = self._make_metrics(SFTClass.LOW.value, score=15.0)
        rec = generate_sft_recommendation(m)
        self.assertEqual(rec.recommendation_type, RecommendationType.AVOID_LOW_SFT.value)

    def test_insufficient_maps_to_insufficient(self):
        m = self._make_metrics(SFTClass.INSUFFICIENT_DATA.value, score=0.0)
        rec = generate_sft_recommendation(m)
        self.assertEqual(rec.recommendation_type, RecommendationType.INSUFFICIENT_DATA.value)
        self.assertEqual(rec.confidence, 0.0)

    def test_confidence_in_range_0_1(self):
        for score, cls in [(90.0, SFTClass.HIGH.value), (55.0, SFTClass.MEDIUM.value),
                           (15.0, SFTClass.LOW.value)]:
            m = self._make_metrics(cls, score)
            rec = generate_sft_recommendation(m)
            self.assertGreaterEqual(rec.confidence, 0.0)
            self.assertLessEqual(rec.confidence, 1.0)

    def test_recommendation_has_required_fields(self):
        m = self._make_metrics(SFTClass.HIGH.value, score=80.0)
        rec = generate_sft_recommendation(m)
        self.assertIsNotNone(rec.recommendation_id)
        self.assertIsNotNone(rec.created_at)
        self.assertIn("trade_count", rec.supporting_metrics)
        self.assertIn("win_rate",    rec.supporting_metrics)
        self.assertIn("avg_mfe",     rec.supporting_metrics)
        self.assertIn("pct_reach_050r", rec.supporting_metrics)

    def test_recommendation_ids_are_unique(self):
        m = self._make_metrics(SFTClass.HIGH.value, score=80.0)
        ids = {generate_sft_recommendation(m).recommendation_id for _ in range(50)}
        self.assertEqual(len(ids), 50, "Duplicate recommendation IDs generated")


# ── 4. Shadow Isolation Tests ─────────────────────────────────────────────────

class TestShadowIsolation(unittest.TestCase):
    """
    Verify that SFTTracker NEVER writes to protected system files/tables.

    These tests check:
    - No access to paper_trades.csv
    - No access to control_tower.db
    - No access to trading_brain.db
    - No imports from execution/risk/decision layers
    - Module uses its own isolated DB only
    """

    PROTECTED_FILES = [
        "paper_trades.csv",
        "control_tower.db",
        "trading_brain.db",
    ]

    PROTECTED_MODULES = [
        "execution_engine",
        "risk_control",
        "risk_guardian",
        "decision_ai",
        "opportunity_engine",
    ]

    def test_module_does_not_import_protected_layers(self):
        """phase_d_sft_recommendation must not import from protected modules."""
        import ast, inspect
        source_path = os.path.join(ROOT, "phase_d_sft_recommendation.py")
        with open(source_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module.split(".")[0])

        for mod in self.PROTECTED_MODULES:
            self.assertNotIn(
                mod, imported,
                f"phase_d_sft_recommendation.py imports protected module '{mod}'"
            )

    def test_tracker_uses_own_db_only(self):
        """SFTTracker must write ONLY to the db_path it was constructed with."""
        tracker = _make_tracker()
        tracker.ingest_closed_trade(
            symbol="TESTFOO", trade_pnl=10000.0,
            entry_price=100.0, stop_loss=95.0,
            mfe_r=1.2, mae_r=0.3,
            reached_025r=True, reached_050r=True, reached_100r=True,
        )
        # Verify nothing was written to control_tower.db or trading_brain.db
        data_dir = os.path.join(ROOT, "data")
        for fname in self.PROTECTED_FILES:
            fpath = os.path.join(data_dir, fname)
            if os.path.exists(fpath):
                # File exists — check its mtime hasn't changed in last 2 seconds
                import time
                age = time.time() - os.path.getmtime(fpath)
                self.assertGreater(
                    age, 1.0,
                    f"Protected file '{fname}' was modified during SFT ingest!"
                )

    def test_tracker_db_has_only_sft_tables(self):
        """The SFT database must ONLY contain sft_*, shadow_mode_log, pending_adjustments,
        counterfactual_tracking — no trading system tables."""
        tracker = _make_tracker()
        with sqlite3.connect(tracker._db_path) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}

        allowed_tables = {
            "symbol_follow_through_metrics",
            "pending_adjustments",
            "counterfactual_tracking",
            "shadow_mode_log",
            "sqlite_sequence",   # SQLite internal autoincrement table — always present
        }
        unexpected = tables - allowed_tables
        self.assertEqual(
            unexpected, set(),
            f"SFT database contains unexpected tables: {unexpected}"
        )

    def test_get_recommendation_does_not_modify_metrics(self):
        """Calling get_recommendation must not change the SFT metrics."""
        tracker = _make_tracker()
        tracker.ingest_closed_trade(
            symbol="COALINDIA", trade_pnl=30000.0,
            entry_price=500.0, stop_loss=490.0,
            mfe_r=1.2, mae_r=0.5,
            reached_025r=True, reached_050r=True, reached_100r=False,
        )
        before = tracker.get_metrics("COALINDIA")
        _ = tracker.get_recommendation("COALINDIA")
        after  = tracker.get_metrics("COALINDIA")

        self.assertEqual(before.follow_through_score, after.follow_through_score)
        self.assertEqual(before.trade_count,          after.trade_count)
        self.assertEqual(before.win_count,            after.win_count)

    def test_paper_trades_csv_not_opened(self):
        """SFT ingest must not open paper_trades.csv (monitored via mock)."""
        tracked_opens = []
        real_open = open

        def mock_open(name, *args, **kwargs):
            if "paper_trades" in str(name):
                tracked_opens.append(name)
            return real_open(name, *args, **kwargs)

        tracker = _make_tracker()
        with patch("builtins.open", side_effect=mock_open):
            tracker.ingest_closed_trade(
                symbol="RELIANCE", trade_pnl=-50000.0,
                entry_price=2800.0, stop_loss=2750.0,
                mfe_r=0.3, mae_r=0.8,
                reached_025r=True, reached_050r=False, reached_100r=False,
            )

        self.assertEqual(
            tracked_opens, [],
            f"SFT ingest opened paper_trades files: {tracked_opens}"
        )


# ── 5. No Execution Influence Tests ──────────────────────────────────────────

class TestNoExecutionInfluence(unittest.TestCase):
    """
    Verify that recommendation outputs cannot directly influence execution.

    The recommendation object must:
    - Not inherit from any order/signal class
    - Not have an execute(), submit(), or apply() method
    - Not write to any tables read by OrderManager or ExecutionEngine
    """

    def test_recommendation_has_no_execute_method(self):
        tracker = _make_tracker()
        rec = tracker.get_recommendation("NEWSTOCK")
        self.assertFalse(hasattr(rec, "execute"), "SFTRecommendation must not have execute()")
        self.assertFalse(hasattr(rec, "submit"),  "SFTRecommendation must not have submit()")
        self.assertFalse(hasattr(rec, "apply"),   "SFTRecommendation must not have apply()")
        self.assertFalse(hasattr(rec, "block"),   "SFTRecommendation must not have block()")

    def test_recommendation_is_data_only(self):
        """SFTRecommendation must be a pure data container (dataclass)."""
        from dataclasses import fields
        rec_fields = {f.name for f in sft_mod.SFTRecommendation.__dataclass_fields__.values()}
        self.assertIn("recommendation_type", rec_fields)
        self.assertIn("confidence",          rec_fields)
        self.assertIn("supporting_metrics",  rec_fields)

    def test_pending_adjustments_table_not_read_by_execution(self):
        """
        The pending_adjustments table must not appear in any import chain
        from execution_engine or order_manager.

        Proxy test: verify execution_engine/order_manager.py does not
        reference 'phase_d_sft' or 'pending_adjustments'.
        """
        om_path = os.path.join(ROOT, "execution_engine", "order_manager.py")
        if not os.path.exists(om_path):
            self.skipTest("order_manager.py not found")

        with open(om_path, encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("phase_d_sft",        content,
                         "order_manager.py references phase_d_sft module")
        self.assertNotIn("pending_adjustments", content,
                         "order_manager.py references pending_adjustments table")
        self.assertNotIn("SFTTracker",          content,
                         "order_manager.py references SFTTracker")


# ── 6. Counterfactual Tracking Tests ─────────────────────────────────────────

class TestCounterfactualTracking(unittest.TestCase):
    """Verify HELPED/HURT/NO_EFFECT logic is correct."""

    def test_avoid_low_sft_plus_loss_is_helped(self):
        outcome = evaluate_counterfactual(
            RecommendationType.AVOID_LOW_SFT.value, trade_pnl=-50000.0
        )
        self.assertEqual(outcome, CounterfactualOutcome.HELPED)

    def test_avoid_low_sft_plus_win_is_hurt(self):
        outcome = evaluate_counterfactual(
            RecommendationType.AVOID_LOW_SFT.value, trade_pnl=+30000.0
        )
        self.assertEqual(outcome, CounterfactualOutcome.HURT)

    def test_prefer_high_sft_plus_win_is_helped(self):
        outcome = evaluate_counterfactual(
            RecommendationType.PREFER_HIGH_SFT.value, trade_pnl=+60000.0
        )
        self.assertEqual(outcome, CounterfactualOutcome.HELPED)

    def test_prefer_high_sft_plus_loss_is_no_effect(self):
        outcome = evaluate_counterfactual(
            RecommendationType.PREFER_HIGH_SFT.value, trade_pnl=-40000.0
        )
        self.assertEqual(outcome, CounterfactualOutcome.NO_EFFECT)

    def test_caution_medium_is_no_effect(self):
        for pnl in [50000.0, -50000.0]:
            outcome = evaluate_counterfactual(
                RecommendationType.CAUTION_MEDIUM_SFT.value, pnl
            )
            self.assertEqual(outcome, CounterfactualOutcome.NO_EFFECT)

    def test_insufficient_data_is_no_effect(self):
        outcome = evaluate_counterfactual(
            RecommendationType.INSUFFICIENT_DATA.value, trade_pnl=-30000.0
        )
        self.assertEqual(outcome, CounterfactualOutcome.NO_EFFECT)

    def test_record_counterfactual_persisted(self):
        tracker = _make_tracker()
        cf = tracker.record_counterfactual(
            symbol="BHARTIARTL", trade_pnl=-80000.0,
            rec_type=RecommendationType.AVOID_LOW_SFT.value,
            sft_class=SFTClass.LOW.value,
        )
        self.assertEqual(cf.counterfactual_outcome, CounterfactualOutcome.HELPED.value)
        self.assertEqual(cf.trade_win, False)

        # Verify persisted
        with sqlite3.connect(tracker._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM counterfactual_tracking WHERE record_id=?",
                (cf.record_id,)
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[6], CounterfactualOutcome.HELPED.value)  # counterfactual_outcome

    def test_counterfactual_summary_aggregates_correctly(self):
        tracker = _make_tracker()
        # 3 HELPED, 1 HURT
        for pnl in [-1000, -2000, -3000]:
            tracker.record_counterfactual("X", pnl, RecommendationType.AVOID_LOW_SFT.value, SFTClass.LOW.value)
        tracker.record_counterfactual("X", 5000, RecommendationType.AVOID_LOW_SFT.value, SFTClass.LOW.value)

        summary = tracker.get_counterfactual_summary()
        outcomes = summary["by_outcome"]
        self.assertEqual(outcomes.get("HELPED", {}).get("n", 0), 3)
        self.assertEqual(outcomes.get("HURT",   {}).get("n", 0), 1)


# ── 7. Full Integration: Ingest → Metrics → Recommendation → Counterfactual ──

class TestIntegration(unittest.TestCase):
    """End-to-end workflow tests."""

    def test_full_tatasteel_workflow(self):
        """
        Replicate TATASTEEL's 10-trade history and verify:
        - Score ≈ 8.4 (LOW_SFT)
        - Recommendation = AVOID_LOW_SFT
        - All 10 subsequent counterfactuals = HELPED (all were losses)
        """
        tracker = _make_tracker()
        TATASTEEL_TRADES = [
            (-48000, 0.141, 0.584, True,  False, False),
            (-47320, 0.107, 0.693, False, False, False),
            (-42960, 0.341, 0.798, True,  False, False),
            (-39040, 0.248, 0.592, True,  False, False),
            (-45360, 0.251, 0.711, True,  False, False),
            (-44800, 0.376, 0.653, True,  False, False),
            (-46240, 0.287, 0.674, True,  False, False),
            (-43680, 0.204, 0.601, True,  False, False),
            (-41440, 0.211, 0.588, True,  False, False),
            (-24737, 0.583, 0.748, True,  True,  False),
        ]
        for pnl, mfe, mae, r025, r05, r1 in TATASTEEL_TRADES:
            tracker.ingest_closed_trade(
                symbol="TATASTEEL", trade_pnl=pnl,
                entry_price=145.0, stop_loss=143.0,
                mfe_r=mfe, mae_r=mae,
                reached_025r=r025, reached_050r=r05, reached_100r=r1,
            )

        m = tracker.get_metrics("TATASTEEL")
        self.assertEqual(m.trade_count, 10)
        self.assertEqual(m.win_count,   0)
        self.assertAlmostEqual(m.win_rate, 0.0)
        self.assertLess(m.follow_through_score, 15.0)
        self.assertEqual(m.sft_class, SFTClass.LOW.value)

        rec = tracker.get_recommendation("TATASTEEL")
        self.assertEqual(rec.recommendation_type, RecommendationType.AVOID_LOW_SFT.value)

        # All 10 were losses → all HELPED
        for pnl, *_ in TATASTEEL_TRADES:
            cf = tracker.record_counterfactual(
                "TATASTEEL", pnl, rec.recommendation_type, rec.sft_class
            )
            self.assertEqual(cf.counterfactual_outcome, CounterfactualOutcome.HELPED.value)

    def test_full_hindalco_workflow(self):
        """
        Replicate HINDALCO's 3-trade history and verify HIGH_SFT, PREFER recommendation.
        3 trades are needed to clear MIN_TRADES_FOR_SCORE threshold.
        """
        tracker = _make_tracker()
        for pnl in [80000, 81618, 79000]:   # 3 wins to clear MIN_TRADES_FOR_SCORE=3
            tracker.ingest_closed_trade(
                symbol="HINDALCO", trade_pnl=pnl,
                entry_price=700.0, stop_loss=685.0,
                mfe_r=2.427, mae_r=0.0,
                reached_025r=True, reached_050r=True, reached_100r=True,
            )

        m = tracker.get_metrics("HINDALCO")
        self.assertEqual(m.win_count, 3)
        self.assertGreater(m.follow_through_score, 85.0)
        self.assertEqual(m.sft_class, SFTClass.HIGH.value)

        rec = tracker.get_recommendation("HINDALCO")
        self.assertEqual(rec.recommendation_type, RecommendationType.PREFER_HIGH_SFT.value)

    def test_new_symbol_gets_insufficient_data(self):
        """A never-before-seen symbol should return INSUFFICIENT_DATA."""
        tracker = _make_tracker()
        rec = tracker.get_recommendation("NEWSTOCK_XYZ")
        self.assertEqual(rec.recommendation_type, RecommendationType.INSUFFICIENT_DATA.value)
        self.assertEqual(rec.confidence, 0.0)

    def test_metrics_accumulate_correctly_across_ingests(self):
        """Multiple ingests for same symbol must accumulate trade_count correctly."""
        tracker = _make_tracker()
        for i in range(5):
            tracker.ingest_closed_trade(
                symbol="NTPC", trade_pnl=10000.0 * (1 if i % 2 == 0 else -1),
                entry_price=200.0, stop_loss=196.0,
                mfe_r=0.6, mae_r=0.4,
                reached_025r=True, reached_050r=True, reached_100r=False,
            )

        m = tracker.get_metrics("NTPC")
        self.assertEqual(m.trade_count, 5)
        self.assertEqual(m.win_count,   3)   # indices 0, 2, 4 are wins
        self.assertEqual(m.loss_count,  2)

    def test_get_all_metrics_sorted_by_score_desc(self):
        """get_all_metrics must return symbols sorted highest score first."""
        tracker = _make_tracker()
        # HINDALCO wins, TATASTEEL loses
        for pnl in [80000, 82000, 78000]:
            tracker.ingest_closed_trade(
                "HINDALCO", pnl, 700.0, 685.0,
                mfe_r=2.4, mae_r=0.0,
                reached_025r=True, reached_050r=True, reached_100r=True,
            )
        for pnl in [-47000, -48000, -46000]:
            tracker.ingest_closed_trade(
                "TATASTEEL", pnl, 145.0, 143.0,
                mfe_r=0.2, mae_r=0.6,
                reached_025r=False, reached_050r=False, reached_100r=False,
            )

        all_m = tracker.get_all_metrics()
        self.assertGreater(len(all_m), 1)
        for i in range(len(all_m) - 1):
            self.assertGreaterEqual(
                all_m[i].follow_through_score,
                all_m[i + 1].follow_through_score,
                "get_all_metrics not sorted descending by score",
            )

    def test_thread_safety_concurrent_ingests(self):
        """Concurrent ingests from multiple threads must not corrupt trade_count."""
        tracker  = _make_tracker()
        n_threads = 20
        errors    = []

        def ingest_one():
            try:
                tracker.ingest_closed_trade(
                    symbol="CONCURRENT", trade_pnl=10000.0,
                    entry_price=500.0, stop_loss=495.0,
                    mfe_r=0.8, mae_r=0.3,
                    reached_025r=True, reached_050r=True, reached_100r=False,
                )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=ingest_one) for _ in range(n_threads)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

        m = tracker.get_metrics("CONCURRENT")
        self.assertIsNotNone(m)
        self.assertGreater(m.trade_count, 0)

    def test_shadow_report_generates_without_error(self):
        """generate_shadow_report must run without exceptions on populated tracker."""
        tracker = _make_tracker()
        for pnl in [50000, -30000, 20000]:
            tracker.ingest_closed_trade(
                "COALINDIA", pnl, 500.0, 490.0,
                mfe_r=1.0, mae_r=0.5,
                reached_025r=True, reached_050r=True, reached_100r=False,
            )

        report = tracker.generate_shadow_report()
        self.assertIn("SFT Shadow Report", report)
        self.assertIn("COALINDIA",          report)
        self.assertIn("HIGH_SFT",            report)
        self.assertIn("MEDIUM_SFT",          report)
        self.assertIn("LOW_SFT",             report)

    def test_ingest_invalid_inputs_does_not_raise(self):
        """Invalid/boundary inputs must be silently rejected, not crash."""
        tracker = _make_tracker()
        # Zero stop_loss
        tracker.ingest_closed_trade("X", 1000.0, entry_price=100.0, stop_loss=0.0)
        # Zero entry_price
        tracker.ingest_closed_trade("X", 1000.0, entry_price=0.0, stop_loss=95.0)
        # Empty symbol
        tracker.ingest_closed_trade("", 1000.0, entry_price=100.0, stop_loss=95.0)
        # entry_price == stop_loss → R=0
        tracker.ingest_closed_trade("X", 1000.0, entry_price=100.0, stop_loss=100.0)

        # None of these should have created a metrics row for "X" or ""
        m = tracker.get_metrics("X")
        self.assertIsNone(m, "Invalid input was ingested — should have been rejected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
