"""
tests/test_cle.py — CLE-001 Cat-E Automatic DNA Learning Executor test suite.

Coverage:
  Safety boundaries (SB-*): lifecycle, trading isolation, capital-constraint filter
  Executor logic (EX-*):    direction extraction, idempotency, registry update
  Research logic (RS-*):    OHLCV failure, feature compute, evidence gates
  Integration (IT-*):       pga_learning hook, orchestrator wiring
  End-to-end (E2E-*):       full dry-run pass

Run with:  python -m pytest tests/test_cle.py -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── Stub heavy dependencies so tests load without full environment ─────────

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)
    return mod


_stub("utils", get_logger=MagicMock(return_value=MagicMock()))
# Note: yfinance and pandas are NOT stubbed globally — individual tests
# mock specific functions to keep real pandas available for RS tests.


# ── SB (Safety Boundary) Tests ─────────────────────────────────────────────

class TestSafetyBoundary(unittest.TestCase):
    """Verify that CLE never violates core safety constraints."""

    def test_sb001_lifecycle_is_always_discovered(self):
        """InstitutionalDNA created by CLE must have lifecycle='DISCOVERED'."""
        import cle_learning_executor.cle_research as _res
        from cle_learning_executor.cle_research import _create_dna_candidate

        created_dna = {}

        class MockRepo:
            def get(self, dna_id):
                raise _not_found()
            def save(self, dna, study_id="", operator="system"):
                created_dna["lifecycle"] = dna.lifecycle
                created_dna["id"]        = dna.id
                return MagicMock()

        class _not_found(Exception):
            pass

        original_repo = _res.IDRRepository
        original_nfe  = _res.IDRNotFoundError
        original_dna  = _res.InstitutionalDNA
        try:
            _res.IDRRepository    = MockRepo
            _res.IDRNotFoundError = _not_found
            # Use a simple stub for InstitutionalDNA that stores kwargs
            class MockDNA:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            _res.InstitutionalDNA = MockDNA
            result = _create_dna_candidate(
                symbol="TESTSTOCK", direction="UP", feature_name="vol_momentum_up",
                sample_count=15, win_rate=0.65, effect_size=0.20, lift=2.0,
                action_id="PGA-TESTTEST", today="2026-08-11",
            )
        finally:
            _res.IDRRepository    = original_repo
            _res.IDRNotFoundError = original_nfe
            _res.InstitutionalDNA = original_dna

        self.assertIsNotNone(result, "DNA create should return an ID")
        self.assertEqual(created_dna.get("lifecycle"), "DISCOVERED",
                         "lifecycle MUST be 'DISCOVERED' — never 'INSTITUTIONAL'")

    def test_sb002_lifecycle_is_never_institutional(self):
        """Explicitly assert lifecycle is not INSTITUTIONAL, VERIFIED, or REPLICATED."""
        import cle_learning_executor.cle_research as _res
        from cle_learning_executor.cle_research import _create_dna_candidate

        created_dna = {}

        class MockRepo:
            def get(self, dna_id):
                raise _nfe()
            def save(self, dna, study_id="", operator="system"):
                created_dna["lifecycle"] = dna.lifecycle
                return MagicMock()

        class _nfe(Exception):
            pass

        class MockDNA:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        original_repo = _res.IDRRepository
        original_nfe  = _res.IDRNotFoundError
        original_dna  = _res.InstitutionalDNA
        try:
            _res.IDRRepository    = MockRepo
            _res.IDRNotFoundError = _nfe
            _res.InstitutionalDNA = MockDNA
            _create_dna_candidate(
                symbol="TEST2", direction="DOWN", feature_name="vol_momentum_down",
                sample_count=12, win_rate=0.60, effect_size=0.15, lift=1.8,
                action_id="PGA-TEST0002", today="2026-08-11",
            )
        finally:
            _res.IDRRepository    = original_repo
            _res.IDRNotFoundError = original_nfe
            _res.InstitutionalDNA = original_dna

        forbidden_lifecycles = {"INSTITUTIONAL", "VERIFIED", "REPLICATED", "WEAKENING",
                                "DRIFTING", "PROMOTED", "ACTIVE"}
        self.assertNotIn(created_dna.get("lifecycle"), forbidden_lifecycles)

    def test_sb003_no_live_trading_imports(self):
        """CLE modules must not have import statements for live-trading modules."""
        import re
        live_trading_modules = {
            "risk_guardian", "execution_engine", "order_manager",
            "dhan_feed", "execution", "broker", "zerodha",
        }
        cle_executor_path = os.path.join(ROOT, "cle_learning_executor", "cle_executor.py")
        with open(cle_executor_path, encoding="utf-8") as f:
            source = f.read()

        # Only check actual import statements (not comments or docstrings)
        import_lines = [
            line.strip() for line in source.split("\n")
            if re.match(r"^\s*(import |from )", line)
        ]
        import_text = "\n".join(import_lines)

        for mod_name in live_trading_modules:
            self.assertNotIn(f"import {mod_name}", import_text,
                             f"cle_executor.py must not import {mod_name}")
            self.assertNotIn(f"from {mod_name}", import_text,
                             f"cle_executor.py must not import from {mod_name}")

    def test_sb004_no_live_trading_imports_research(self):
        """cle_research.py must not have import statements for live-trading modules."""
        import re
        live_trading_modules = {
            "risk_guardian", "execution_engine", "order_manager",
            "dhan_feed", "execution", "broker",
        }
        cle_research_path = os.path.join(ROOT, "cle_learning_executor", "cle_research.py")
        with open(cle_research_path, encoding="utf-8") as f:
            source = f.read()

        import_lines = [
            line.strip() for line in source.split("\n")
            if re.match(r"^\s*(import |from )", line)
        ]
        import_text = "\n".join(import_lines)
        for mod_name in live_trading_modules:
            self.assertNotIn(f"import {mod_name}", import_text)
            self.assertNotIn(f"from {mod_name}", import_text)

    def test_sb005_capital_constraint_not_processed(self):
        """Records with capital/portfolio constraint descriptions must be skipped."""
        from cle_learning_executor.cle_executor import _is_capital_constraint

        capital_descriptions = [
            "Cat-E: DNA gap for STOCK — PortfolioConstraint blocked execution",
            "missed because max position limit reached",
            "capital constraint prevented trade",
            "riskfilter rejected signal",
        ]
        for desc in capital_descriptions:
            record = {"description": desc, "category": "E"}
            self.assertTrue(_is_capital_constraint(record),
                            f"Should detect capital constraint: {desc}")

    def test_sb006_non_constraint_not_skipped(self):
        """Normal DNA gap misses must NOT be classified as capital constraints."""
        from cle_learning_executor.cle_executor import _is_capital_constraint

        normal_descriptions = [
            "Create candidate DNA for DRREDDY: moved +4.0% with zero DNA coverage",
            "Cat-E: HDFC moved -3.5%, DNA=0, candidate needed",
        ]
        for desc in normal_descriptions:
            record = {"description": desc, "category": "E"}
            self.assertFalse(_is_capital_constraint(record),
                             f"Should NOT detect capital constraint: {desc}")


# ── EX (Executor Logic) Tests ──────────────────────────────────────────────

class TestExecutorLogic(unittest.TestCase):
    """Unit tests for cle_executor.py logic."""

    def test_ex001_direction_extraction_up(self):
        """Positive percentage → direction UP."""
        from cle_learning_executor.cle_executor import _extract_direction
        record = {
            "description": "Create candidate DNA for DRREDDY: moved +4.0% with zero DNA coverage"
        }
        self.assertEqual(_extract_direction(record), "UP")

    def test_ex002_direction_extraction_down(self):
        """Negative percentage → direction DOWN."""
        from cle_learning_executor.cle_executor import _extract_direction
        record = {
            "description": "Create candidate DNA for VEDL: moved -3.5% with zero DNA coverage"
        }
        self.assertEqual(_extract_direction(record), "DOWN")

    def test_ex003_direction_extraction_empty_on_unknown(self):
        """Unknown description → empty string (will be skipped by executor)."""
        from cle_learning_executor.cle_executor import _extract_direction
        record = {"description": "No percentage information here"}
        self.assertEqual(_extract_direction(record), "")

    def test_ex004_return_pct_extraction(self):
        """Return percentage extracted correctly from description."""
        from cle_learning_executor.cle_executor import _extract_return_pct
        record = {
            "description": "Create candidate DNA for DIVISLAB: moved +3.2% with zero DNA coverage"
        }
        pct = _extract_return_pct(record)
        self.assertAlmostEqual(pct, 3.2, places=1)

    def test_ex005_return_pct_default_on_missing(self):
        """Missing return percentage defaults to 1.0 (minimum threshold)."""
        from cle_learning_executor.cle_executor import _extract_return_pct
        record = {"description": "No percentage here"}
        self.assertEqual(_extract_return_pct(record), 1.0)

    def test_ex006_already_executed_candidate_created(self):
        """Record with CANDIDATE_CREATED outcome is already complete."""
        from cle_learning_executor.cle_executor import _already_executed_by_cle
        record = {"executed": True, "outcome": "CANDIDATE_CREATED"}
        self.assertTrue(_already_executed_by_cle(record))

    def test_ex007_already_executed_no_actionable_dna(self):
        """Record with NO_ACTIONABLE_DNA outcome is already complete."""
        from cle_learning_executor.cle_executor import _already_executed_by_cle
        record = {"executed": True, "outcome": "NO_ACTIONABLE_DNA"}
        self.assertTrue(_already_executed_by_cle(record))

    def test_ex008_not_executed_logged_for_review(self):
        """Record with LOGGED_FOR_REVIEW outcome is NOT yet executed by CLE."""
        from cle_learning_executor.cle_executor import _already_executed_by_cle
        record = {"executed": False, "outcome": "LOGGED_FOR_REVIEW"}
        self.assertFalse(_already_executed_by_cle(record))

    def test_ex009_not_executed_cle_scheduled(self):
        """Record with CLE_SCHEDULED outcome is NOT yet executed by CLE."""
        from cle_learning_executor.cle_executor import _already_executed_by_cle
        record = {"executed": True, "outcome": "CLE_SCHEDULED"}
        self.assertFalse(_already_executed_by_cle(record))

    def test_ex010_run_returns_valid_summary(self):
        """run_cat_e_learning() always returns a dict with required keys."""
        with patch("cle_learning_executor.cle_executor._load_registry",
                   return_value=[]):
            from cle_learning_executor.cle_executor import run_cat_e_learning
            summary = run_cat_e_learning(dry_run=True)

        required_keys = {"n_found", "n_processed", "n_candidates",
                         "n_no_dna", "n_skipped", "n_failed", "dry_run"}
        self.assertTrue(required_keys.issubset(summary.keys()))

    def test_ex011_empty_registry_returns_zero_counts(self):
        """Empty registry → all counts zero."""
        with patch("cle_learning_executor.cle_executor._load_registry",
                   return_value=[]):
            from cle_learning_executor.cle_executor import run_cat_e_learning
            summary = run_cat_e_learning(dry_run=True)

        self.assertEqual(summary["n_found"], 0)
        self.assertEqual(summary["n_processed"], 0)
        self.assertEqual(summary["n_candidates"], 0)

    def test_ex012_non_cat_e_records_ignored(self):
        """Records with category != 'E' must not be processed."""
        registry = [
            {"category": "B", "learning_id": "PGA-001", "symbol": "TEST",
             "outcome": "LOGGED_FOR_REVIEW", "description": "Cat-B record"},
            {"category": "C", "learning_id": "PGA-002", "symbol": "TEST2",
             "outcome": "LOGGED_FOR_REVIEW", "description": "Cat-C record"},
        ]
        with patch("cle_learning_executor.cle_executor._load_registry",
                   return_value=registry):
            from cle_learning_executor.cle_executor import run_cat_e_learning
            summary = run_cat_e_learning(dry_run=True)

        self.assertEqual(summary["n_found"], 0)
        self.assertEqual(summary["n_processed"], 0)

    def test_ex013_capital_constraint_record_skipped(self):
        """Capital constraint records counted as skipped, not processed for DNA."""
        registry = [
            {
                "category": "E",
                "learning_id": "PGA-CAPITAL1",
                "symbol": "HDFC",
                "outcome": "CLE_SCHEDULED",
                "description": "DNA gap for HDFC — portfolioconstraint blocked",
            }
        ]
        with patch("cle_learning_executor.cle_executor._load_registry",
                   return_value=registry), \
             patch("cle_learning_executor.cle_executor._save_registry"), \
             patch("cle_learning_executor.cle_executor._save_cle_log"):
            from cle_learning_executor.cle_executor import run_cat_e_learning
            summary = run_cat_e_learning(dry_run=True)

        self.assertEqual(summary["n_skipped"], 1)
        self.assertEqual(summary["n_candidates"], 0)

    def test_ex014_dry_run_does_not_save_registry(self):
        """dry_run=True must not call _save_registry."""
        registry = [
            {
                "category": "E",
                "learning_id": "PGA-DRY1",
                "symbol": "DRREDDY",
                "outcome": "CLE_SCHEDULED",
                "description": "Create candidate DNA for DRREDDY: moved +4.0% with zero DNA coverage",
            }
        ]
        mock_research = MagicMock()
        mock_research.status    = "CANDIDATE_CREATED"
        mock_research.dna_id    = "CLE-DRREDDY-UP-20260811"
        mock_research.sample_count = 20
        mock_research.win_rate  = 0.65
        mock_research.lift      = 2.1
        mock_research.reason    = "dry_run=True"

        with patch("cle_learning_executor.cle_executor._load_registry",
                   return_value=registry), \
             patch("cle_learning_executor.cle_executor._save_registry") as mock_save, \
             patch("cle_learning_executor.cle_executor._save_cle_log"), \
             patch("cle_learning_executor.cle_research.run_historical_research",
                   return_value=mock_research):
            from cle_learning_executor.cle_executor import run_cat_e_learning
            run_cat_e_learning(dry_run=True)

        mock_save.assert_not_called()


# ── RS (Research) Tests ────────────────────────────────────────────────────

class TestResearch(unittest.TestCase):
    """Unit tests for cle_research.py logic."""

    def test_rs001_fetch_failure_returns_none(self):
        """OHLCV fetch failure must return None gracefully."""
        import cle_learning_executor.cle_research as _res
        from cle_learning_executor.cle_research import _fetch_ohlcv

        mock_yf = MagicMock()
        mock_yf.download.side_effect = Exception("Network error")
        original_yf = _res.yf
        try:
            _res.yf = mock_yf
            result = _fetch_ohlcv("TESTSTOCK")
        finally:
            _res.yf = original_yf
        self.assertIsNone(result)

    def test_rs002_insufficient_data_status(self):
        """When OHLCV fetch returns None, research result status is FAILED."""
        with patch("cle_learning_executor.cle_research._fetch_ohlcv",
                   return_value=None):
            from cle_learning_executor.cle_research import run_historical_research
            result = run_historical_research(
                action_id="PGA-TEST",
                symbol="NODATA",
                direction="UP",
                return_pct=2.0,
                today="2026-08-11",
                dry_run=True,
            )
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.symbol, "NODATA")

    def test_rs003_low_sample_count_returns_insufficient(self):
        """Sample count below MIN_SAMPLE returns count < MIN_SAMPLE."""
        from cle_learning_executor.cle_research import _assess_evidence, MIN_SAMPLE
        try:
            import pandas as pd
            import numpy as np
        except ImportError:
            self.skipTest("pandas/numpy not available")

        # Create a tiny DataFrame where volume never spikes (no trigger conditions)
        dates = pd.date_range("2025-01-01", periods=50, freq="B")
        df = pd.DataFrame({
            "daily_return": np.random.normal(0, 1.0, 50),
            "momentum_5d":  np.random.normal(0, 2.0, 50),
            "vol_ratio_20": np.ones(50) * 0.8,  # always below 1.5 → zero triggers
            "high_low_pct": np.ones(50) * 1.0,
        }, index=dates)

        count, base, wr, lift = _assess_evidence(df, "UP", 2.0)
        self.assertLess(count, MIN_SAMPLE,
                        "Low vol_ratio should produce < MIN_SAMPLE trigger hits")

    def test_rs004_evidence_below_threshold_returns_no_actionable_dna(self):
        """Evidence below win_rate / lift thresholds → NO_ACTIONABLE_DNA."""
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")

        mock_df = pd.DataFrame({"Close": range(252)})  # real len() = 252

        with patch("cle_learning_executor.cle_research._fetch_ohlcv",
                   return_value=mock_df), \
             patch("cle_learning_executor.cle_research._compute_features",
                   return_value=mock_df), \
             patch("cle_learning_executor.cle_research._assess_evidence",
                   return_value=(15, 0.4, 0.40, 1.0)):  # lift=1.0 < MIN_LIFT

            from cle_learning_executor.cle_research import run_historical_research
            result = run_historical_research(
                action_id="PGA-WEAK",
                symbol="WEAKSTOCK",
                direction="UP",
                return_pct=2.0,
                today="2026-08-11",
                dry_run=False,
            )
        self.assertEqual(result.status, "NO_ACTIONABLE_DNA")

    def test_rs005_good_evidence_creates_candidate_in_dry_run(self):
        """Sufficient evidence in dry_run → CANDIDATE_CREATED without DB write."""
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")

        mock_df = pd.DataFrame({"Close": range(252)})  # real len() = 252

        with patch("cle_learning_executor.cle_research._fetch_ohlcv",
                   return_value=mock_df), \
             patch("cle_learning_executor.cle_research._compute_features",
                   return_value=mock_df), \
             patch("cle_learning_executor.cle_research._assess_evidence",
                   return_value=(20, 0.15, 0.70, 2.5)):  # good evidence

            from cle_learning_executor.cle_research import run_historical_research
            result = run_historical_research(
                action_id="PGA-GOOD",
                symbol="DRREDDY",
                direction="UP",
                return_pct=4.0,
                today="2026-08-11",
                dry_run=True,   # ← no DB write
            )
        self.assertEqual(result.status, "CANDIDATE_CREATED")
        self.assertIsNotNone(result.dna_id)
        self.assertIn("DRREDDY", result.dna_id)

    def test_rs006_idempotency_existing_dna_returns_same_id(self):
        """If DNA already exists in IDR, return existing id without creating duplicate."""
        import cle_learning_executor.cle_research as _res
        from cle_learning_executor.cle_research import _create_dna_candidate

        existing_dna = MagicMock()
        existing_dna.lifecycle = "DISCOVERED"

        class MockRepo:
            def get(self, dna_id):
                return existing_dna  # found — no create needed

        class _nfe(Exception):
            pass

        original_repo = _res.IDRRepository
        original_nfe  = _res.IDRNotFoundError
        try:
            _res.IDRRepository    = MockRepo
            _res.IDRNotFoundError = _nfe
            result = _create_dna_candidate(
                symbol="DRREDDY", direction="UP",
                feature_name="vol_momentum_up", sample_count=20,
                win_rate=0.65, effect_size=0.20, lift=2.1,
                action_id="PGA-IDEM", today="2026-08-11",
            )
        finally:
            _res.IDRRepository    = original_repo
            _res.IDRNotFoundError = original_nfe

        expected_id = "CLE-DRREDDY-UP-20260811"
        self.assertEqual(result, expected_id)

    def test_rs007_confidence_is_capped_at_0_60(self):
        """DNA confidence must be capped at 0.60 (well below institutional gate)."""
        import cle_learning_executor.cle_research as _res
        from cle_learning_executor.cle_research import _create_dna_candidate

        created_dna = {}

        class MockRepo:
            def get(self, dna_id):
                raise _nfe()
            def save(self, dna, study_id="", operator="system"):
                created_dna["confidence"] = dna.confidence
                return MagicMock()

        class _nfe(Exception):
            pass

        class MockDNA:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        original_repo = _res.IDRRepository
        original_nfe  = _res.IDRNotFoundError
        original_dna  = _res.InstitutionalDNA
        try:
            _res.IDRRepository    = MockRepo
            _res.IDRNotFoundError = _nfe
            _res.InstitutionalDNA = MockDNA
            _create_dna_candidate(
                symbol="HIGHWIN", direction="UP", feature_name="test",
                sample_count=100, win_rate=0.99, effect_size=0.50, lift=5.0,
                action_id="PGA-HIGHWIN", today="2026-08-11",
            )
        finally:
            _res.IDRRepository    = original_repo
            _res.IDRNotFoundError = original_nfe
            _res.InstitutionalDNA = original_dna

        self.assertLessEqual(created_dna.get("confidence", 1.0), 0.60,
                             "Confidence must be capped at 0.60")


# ── IT (Integration) Tests ─────────────────────────────────────────────────

class TestIntegration(unittest.TestCase):
    """Integration tests for pga_learning.py hook."""

    def test_it001_pga_learning_cat_e_hook_exists(self):
        """execute_actions() must have an explicit elif for Cat-E."""
        pga_path = os.path.join(ROOT, "predictive_gap", "pga_learning.py")
        with open(pga_path, encoding="utf-8") as f:
            source = f.read()
        self.assertIn('action.category == "E"', source,
                      "pga_learning.execute_actions() must have a Cat-E elif branch")

    def test_it002_cat_e_hook_outcome_is_cle_scheduled(self):
        """The Cat-E hook must set outcome='CLE_SCHEDULED'."""
        pga_path = os.path.join(ROOT, "predictive_gap", "pga_learning.py")
        with open(pga_path, encoding="utf-8") as f:
            source = f.read()
        self.assertIn("CLE_SCHEDULED", source,
                      "Cat-E branch must assign outcome='CLE_SCHEDULED'")

    def test_it003_orchestrator_wiring_exists(self):
        """master_orchestrator.py must import and call run_cat_e_learning."""
        orc_path = os.path.join(ROOT, "orchestrator", "master_orchestrator.py")
        with open(orc_path, encoding="utf-8") as f:
            source = f.read()
        self.assertIn("run_cat_e_learning", source,
                      "master_orchestrator.py must call run_cat_e_learning()")
        self.assertIn("cle_learning_executor", source,
                      "master_orchestrator.py must import from cle_learning_executor")

    def test_it004_orchestrator_cle_after_ilc(self):
        """CLE must be wired after ILC in _do_eod_learning()."""
        orc_path = os.path.join(ROOT, "orchestrator", "master_orchestrator.py")
        with open(orc_path, encoding="utf-8") as f:
            source = f.read()
        ilc_pos = source.find("run_ilc")
        cle_pos = source.find("run_cat_e_learning")
        prr_pos = source.find("run_prr")
        self.assertGreater(cle_pos, ilc_pos, "CLE must appear after ILC in source")
        self.assertLess(cle_pos, prr_pos,    "CLE must appear before PRR in source")

    def test_it005_cle_exception_does_not_propagate(self):
        """CLE failure in _do_eod_learning() must not stop the pipeline (PRR still runs)."""
        orc_path = os.path.join(ROOT, "orchestrator", "master_orchestrator.py")
        with open(orc_path, encoding="utf-8") as f:
            source = f.read()
        # Find the CLE-001 block and check for try/except within a 1500-char window
        cle_block_marker = "CLE-001: Cat-E Automatic DNA Learning Executor"
        block_start = source.find(cle_block_marker)
        self.assertGreater(block_start, 0,
                           "CLE-001 block comment not found in orchestrator")
        region = source[block_start: block_start + 1500]
        self.assertIn("except Exception", region,
                      "CLE block must be wrapped in try/except")


# ── E2E (End-to-End) Tests ─────────────────────────────────────────────────

class TestEndToEnd(unittest.TestCase):
    """End-to-end dry-run pass using a synthetic registry."""

    def _make_cat_e_record(self, action_id, symbol, pct):
        sign = "+" if pct >= 0 else ""
        return {
            "learning_id":     action_id,
            "created_date":    "2026-08-11",
            "action_type":     "create_dna_candidate",
            "category":        "E",
            "symbol":          symbol,
            "description":     f"Create candidate DNA for {symbol}: moved {sign}{pct:.1f}% with zero DNA coverage",
            "target_system":   "IDR",
            "expected_benefit": "Improve dna_count",
            "prediction_metric": "dna_count",
            "measurement_windows": [30, 60, 90],
            "baseline_metrics": {"dna_count": 0.0},
            "verification_results": [],
            "status":          "PENDING",
            "confidence":      "LOW",
            "eig_score":       0.0,
            "roi":             None,
            "executed":        True,         # CLE_SCHEDULED sets executed=True
            "outcome":         "CLE_SCHEDULED",
        }

    def test_e2e001_dry_run_all_symbols(self):
        """Dry-run pass over 15 Cat-E symbols from 2026-08-11 produces valid summary."""
        symbols = [
            ("DRREDDY", 4.0), ("DIVISLAB", 3.2), ("CANBK", 1.0),
            ("VEDL", -3.5), ("GODREJPROP", -3.3), ("MAXHEALTH", -2.4),
            ("HINDZINC", -2.1), ("METROPOLIS", -1.9), ("EMAMILTD", -1.5),
            ("SRF", -1.5), ("CROMPTON", -1.3), ("AAVAS", -1.2),
            ("DLF", -1.2), ("TORNTPHARM", -1.1), ("FORTIS", -1.0),
        ]
        registry = [
            self._make_cat_e_record(f"PGA-{sym[:8]:8s}".replace(" ", "0"), sym, pct)
            for sym, pct in symbols
        ]

        # Research mock: half get CANDIDATE_CREATED, half get NO_ACTIONABLE_DNA
        call_count = [0]

        def fake_research(**kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] % 2 == 0:
                r.status, r.dna_id     = "CANDIDATE_CREATED", f"CLE-{kwargs['symbol']}-UP-20260811"
                r.sample_count         = 20
                r.win_rate, r.lift     = 0.65, 2.1
            else:
                r.status, r.dna_id     = "NO_ACTIONABLE_DNA", None
                r.sample_count         = 8
                r.win_rate, r.lift     = 0.42, 1.1
            r.reason = "test"
            return r

        with patch("cle_learning_executor.cle_executor._load_registry",
                   return_value=registry), \
             patch("cle_learning_executor.cle_executor._save_registry"), \
             patch("cle_learning_executor.cle_executor._save_cle_log"), \
             patch("cle_learning_executor.cle_research.run_historical_research",
                   side_effect=fake_research):
            from cle_learning_executor.cle_executor import run_cat_e_learning
            summary = run_cat_e_learning(dry_run=True)

        self.assertEqual(summary["n_found"], 15)
        self.assertEqual(summary["n_processed"], 15)
        self.assertEqual(summary["n_skipped"], 0)
        self.assertGreater(summary["n_candidates"] + summary["n_no_dna"], 0)

    def test_e2e002_idempotency_on_second_run(self):
        """Running CLE twice on the same registry must not re-process completed records."""
        registry = [
            {
                "learning_id": "PGA-ALREADY1",
                "category":    "E",
                "symbol":      "DRREDDY",
                "outcome":     "CANDIDATE_CREATED",
                "executed":    True,
                "description": "Create candidate DNA for DRREDDY: moved +4.0% with zero DNA coverage",
            }
        ]
        research_called = [False]

        def fake_research(**_):
            research_called[0] = True
            return MagicMock(status="CANDIDATE_CREATED", dna_id="X", sample_count=20,
                             win_rate=0.65, lift=2.1, reason="")

        with patch("cle_learning_executor.cle_executor._load_registry",
                   return_value=registry), \
             patch("cle_learning_executor.cle_executor._save_registry"), \
             patch("cle_learning_executor.cle_executor._save_cle_log"), \
             patch("cle_learning_executor.cle_research.run_historical_research",
                   side_effect=fake_research):
            from cle_learning_executor.cle_executor import run_cat_e_learning
            summary = run_cat_e_learning(dry_run=True)

        self.assertEqual(summary["n_found"], 0,
                         "Already-completed record must not be found for re-processing")
        self.assertFalse(research_called[0],
                         "run_historical_research must not be called for completed records")


if __name__ == "__main__":
    unittest.main()
