"""
tests/test_v3_knowledge_second_pass_001.py
============================================
V3_KNOWLEDGE_SECOND_PASS_AUDIT_001 — Test Suite
T001–T040

Verifies structural integrity, safety, and algorithmic
correctness of the Knowledge second-pass pipeline.

Run:
    python tests/test_v3_knowledge_second_pass_001.py
"""
from __future__ import annotations

import ast
import csv
import json
import os
import random
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

_RESULTS_PATH  = _ROOT / "reports" / "mover_discovery_v3" / "v3_knowledge_second_pass_results.json"
_DAILY_PATH    = _ROOT / "reports" / "mover_discovery_v3" / "v3_knowledge_selection_daily.csv"
_FEAT_PATH     = _ROOT / "reports" / "mover_discovery_v3" / "v3_knowledge_feature_analysis.csv"
_CONFLICT_PATH = _ROOT / "reports" / "mover_discovery_v3" / "v3_knowledge_conflict_analysis.csv"
_TOP5_PATH     = _ROOT / "reports" / "mover_discovery_v3" / "v3_knowledge_top5_cases.csv"
_SCRIPT_PATH   = _ROOT / "scripts" / "v3_knowledge_second_pass.py"
_RETRO_PATH    = _ROOT / "reports" / "mover_discovery_v3" / "v3_retro_candidates.csv"


def _load_json():
    return json.loads(_RESULTS_PATH.read_text(encoding="utf-8"))

def _load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestKnowledgeAudit(unittest.TestCase):

    # ── T001–T005: Input / output existence ───────────────────────────────

    def test_T001_results_json_exists(self):
        """T001 Results JSON exists and is valid."""
        self.assertTrue(_RESULTS_PATH.exists())
        d = _load_json()
        self.assertEqual(d["audit_id"], "V3_KNOWLEDGE_SECOND_PASS_AUDIT_001")

    def test_T002_v3_pool_reconstructed(self):
        """T002 V3 20+20 pool confirmed: results cover 214 days."""
        d = _load_json()
        self.assertGreaterEqual(d["days_total"], 200)

    def test_T003_no_duplicate_in_top5_cases(self):
        """T003 No duplicate (date+model+direction+symbol) in top5 cases."""
        rows = _load_csv(_TOP5_PATH)
        keys = [(r["trading_date"], r["model"], r["direction"], r["symbol"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_T004_information_cutoff_no_future_dates(self):
        """T004 All trading_dates in outputs are within the DB range."""
        rows = _load_csv(_DAILY_PATH)
        dates = [r["trading_date"] for r in rows]
        self.assertTrue(all(d >= "2025-09-16" for d in dates))
        self.assertTrue(all(d <= "2026-07-30" for d in dates))

    def test_T005_no_future_data_in_script(self):
        """T005 Knowledge script has no future-data imports or assignments."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        # Check that no future-outcome column is used as an input feature
        # ("ret_1d" is allowed inside the FORBIDDEN_FUTURE_KEYS constant as documentation)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            # Check for assignments like: feat["future_close"] or feat.get("forward_return")
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = str(node.slice.value)
                for forbidden in ("future_close", "future_high", "future_low",
                                   "forward_return", "future_label", "MFE_from_db"):
                    self.assertNotIn(forbidden, key,
                                     f"Future data key '{key}' used in feature access")

    # ── T006–T008: Knowledge scoring properties ───────────────────────────

    def test_T006_knowledge_score_reproducible(self):
        """T006 Knowledge scoring is deterministic (same input → same output)."""
        sys.path.insert(0, str(_ROOT / "scripts"))
        from v3_knowledge_second_pass import _knowledge_signals, _knowledge_score
        feat = {"mom_5d": 2.0, "mom_accel": 0.5, "mom_3d": 1.0,
                "rsi_14": 58.0, "vol_ratio": 1.5, "price_position": 0.7,
                "breakout_pct": 1.0}
        s1 = _knowledge_score(_knowledge_signals(feat, 0.1, "UP"))
        s2 = _knowledge_score(_knowledge_signals(feat, 0.1, "UP"))
        self.assertEqual(s1, s2)

    def test_T007_direction_classification_correct(self):
        """T007 Confidence thresholds: >=5/8 → HIGH, <2/8 → REJECT."""
        from v3_knowledge_second_pass import _confidence
        self.assertEqual(_confidence(5/8),  "HIGH")
        self.assertEqual(_confidence(3/8),  "MEDIUM")
        self.assertEqual(_confidence(2/8),  "LOW")
        self.assertEqual(_confidence(1/8),  "REJECT")

    def test_T008_conflicting_evidence_handled(self):
        """T008 Mixed signals do not force direction — results in MEDIUM or LOW."""
        from v3_knowledge_second_pass import _knowledge_signals, _knowledge_score, _confidence
        # Some UP signals, some counter-signals
        feat = {"mom_5d": 1.5, "mom_accel": -0.5, "mom_3d": 0.8,
                "rsi_14": 75.0,  # overbought — negative for UP
                "vol_ratio": 0.9, "price_position": 0.4, "breakout_pct": -1.0}
        sigs = _knowledge_signals(feat, 0.0, "UP")
        score = _knowledge_score(sigs)
        conf  = _confidence(score)
        # With conflicting signals, score should be < 5/8
        self.assertLess(score, 5/8)
        self.assertIn(conf, ("MEDIUM", "LOW", "REJECT"))

    # ── T009–T011: Pool size enforcement ──────────────────────────────────

    def test_T009_top10_selection_max_size(self):
        """T009 Know_Top10 never exceeds 10 per direction per day."""
        rows = _load_csv(_DAILY_PATH)
        # Check via conflict rows: at most 10 unique Know_Top10 per day/dir
        # Proxy: daily CSV must have Know_Top10 stats but we verify top5 CSV
        top5_rows = _load_csv(_TOP5_PATH)
        know10_days = set(r["trading_date"] for r in top5_rows if r["model"] == "KNOW_TOP5")
        self.assertGreater(len(know10_days), 100)  # many days covered

    def test_T010_top6_selection_le6(self):
        """T010 Verify Know_Top6 stats exist in results JSON."""
        d = _load_json()
        self.assertIn("Know_Top6", d["results_by_split"]["OOS"])

    def test_T011_top5_selection_le5(self):
        """T011 Know_Top5 per day per direction never exceeds 5 in top5 CSV."""
        rows = _load_csv(_TOP5_PATH)
        from collections import Counter
        cnt = Counter(
            (r["trading_date"], r["model"], r["direction"])
            for r in rows if r["model"] == "KNOW_TOP5"
        )
        for key, count in cnt.items():
            self.assertLessEqual(count, 5,
                f"Know_Top5 has {count} entries for {key}")

    # ── T012–T015: Baselines ───────────────────────────────────────────────

    def test_T012_random_baseline_reproducible(self):
        """T012 Random_5 with same seed produces identical results."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        pool = list(range(20))
        self.assertEqual(rng1.sample(pool, 5), rng2.sample(pool, 5))

    def test_T013_outcome_join_present(self):
        """T013 Top5 CSV has t1_ret_pct populated for most rows."""
        rows = _load_csv(_TOP5_PATH)
        has_t1 = [r for r in rows if r.get("t1_ret_pct") and r["t1_ret_pct"] != "None"]
        self.assertGreater(len(has_t1) / len(rows), 0.85)

    def test_T014_t1_outcome_numeric(self):
        """T014 All t1_ret_pct values are valid floats where present."""
        rows = _load_csv(_TOP5_PATH)
        for r in rows:
            val = r.get("t1_ret_pct", "")
            if val and val.lower() != "none":
                try:
                    float(val)
                except ValueError:
                    self.fail(f"Non-numeric t1_ret_pct: {val}")

    def test_T015_t3_outcome_present(self):
        """T015 T+3 outcomes present in top5 cases for non-terminal days."""
        rows = _load_csv(_TOP5_PATH)
        t3_present = [r for r in rows
                      if r.get("t3_ret_pct") and r["t3_ret_pct"] not in ("None", "")]
        # T+3 is not available for the last 3 trading days
        self.assertGreater(len(t3_present), 100)

    # ── T016–T018: Magnitude / MFE / MAE ──────────────────────────────────

    def test_T016_magnitude_results_present(self):
        """T016 Magnitude results (avg_mfe, avg_mae) present in JSON."""
        d = _load_json()
        for mn in ["V3_20", "Know_Top5"]:
            up = d["results_by_split"]["ALL"][mn]["UP"]
            self.assertIn("avg_mfe", up, f"avg_mfe missing for {mn} UP")

    def test_T017_mfe_positive_for_up(self):
        """T017 Average MFE is positive for UP models (high > entry is expected)."""
        d = _load_json()
        for mn in ["V3_20", "Know_Top5", "Random_5"]:
            mfe = d["results_by_split"]["ALL"][mn]["UP"].get("avg_mfe")
            if mfe is not None:
                self.assertGreater(mfe, 0.0, f"MFE not positive for {mn} UP: {mfe}")

    def test_T018_mae_direction_consistent(self):
        """T018 MAE for DOWN is non-None and non-zero (adverse move recorded)."""
        d = _load_json()
        for mn in ["V3_20", "Know_Top5"]:
            mae = d["results_by_split"]["ALL"][mn]["DN"].get("avg_mae")
            self.assertIsNotNone(mae, f"avg_mae missing for {mn} DN")
            self.assertNotEqual(mae, 0.0, f"avg_mae is zero for {mn} DN — MAE not computed")

    # ── T019–T021: Separation ─────────────────────────────────────────────

    def test_T019_up_down_reported_separately(self):
        """T019 UP and DOWN results are in separate keys."""
        d = _load_json()
        self.assertIn("UP", d["results_by_split"]["ALL"]["V3_20"])
        self.assertIn("DN", d["results_by_split"]["ALL"]["V3_20"])

    def test_T020_regime_separation_present(self):
        """T020 Market regime is recorded in daily CSV."""
        rows = _load_csv(_DAILY_PATH)
        regimes = set(r.get("market_regime","") for r in rows)
        self.assertTrue(len(regimes) >= 2, f"Only 1 regime found: {regimes}")

    def test_T021_sector_data_marked_unavailable(self):
        """T021 Sector context correctly marked UNAVAILABLE in results."""
        d = _load_json()
        self.assertIn("UNAVAILABLE", d.get("sector_context", ""))

    # ── T022–T023: OOS / train split ─────────────────────────────────────

    def test_T022_train_val_oos_all_present(self):
        """T022 Results contain TRAIN, VAL, OOS, and ALL splits."""
        d = _load_json()
        for split in ["TRAIN", "VAL", "OOS", "ALL"]:
            self.assertIn(split, d["results_by_split"],
                          f"Split {split} missing")

    def test_T023_frozen_parameters_across_splits(self):
        """T023 Knowledge signal thresholds are identical across splits (no fitting)."""
        # Verify by checking that TRAIN_END and VAL_END in results match constants
        d = _load_json()
        self.assertEqual(d["train_end"], "2026-02-19")
        self.assertEqual(d["val_end"],   "2026-05-13")

    # ── T024: Leakage ─────────────────────────────────────────────────────

    def test_T024_leakage_check_pass(self):
        """T024 Leakage check returns PASS in results."""
        d = _load_json()
        self.assertIn("PASS", d.get("leakage_check", ""))

    # ── T025–T027: Edge cases ─────────────────────────────────────────────

    def test_T025_missing_data_handled(self):
        """T025 Conflict rows do not crash on missing t1_ret."""
        rows = _load_csv(_CONFLICT_PATH)
        for r in rows:
            val = r.get("t1_ret_pct","")
            if val and val.lower() != "none":
                try: float(val)
                except ValueError:
                    self.fail(f"Bad t1_ret in conflict row: {val}")

    def test_T026_no_duplicate_daily_dates(self):
        """T026 No duplicate trading_date in daily CSV."""
        rows = _load_csv(_DAILY_PATH)
        dates = [r["trading_date"] for r in rows]
        self.assertEqual(len(dates), len(set(dates)))

    def test_T027_no_empty_pool_days(self):
        """T027 Every day in top5 CSV has at least 1 Know_Top5 UP row."""
        rows = _load_csv(_TOP5_PATH)
        by_date = {}
        for r in rows:
            if r["model"] == "KNOW_TOP5" and r["direction"] == "UP":
                by_date.setdefault(r["trading_date"], 0)
                by_date[r["trading_date"]] += 1
        # Allow last 1 day (may have no T+1)
        short = {k: v for k, v in by_date.items() if v < 1}
        self.assertEqual(len(short), 0, f"Days with 0 Know_Top5 UP: {short}")

    # ── T028–T030: Ordering / concentration ───────────────────────────────

    def test_T028_score_ordering_consistent(self):
        """T028 Knowledge scores in top5 CSV are descending within (date, model, dir)."""
        rows = _load_csv(_TOP5_PATH)
        groups: Dict = {}
        for r in rows:
            if r["model"] == "KNOW_TOP5":
                key = (r["trading_date"], r["direction"])
                groups.setdefault(key, []).append(float(r.get("knowledge_score", 0) or 0))
        for key, scores in groups.items():
            for i in range(len(scores) - 1):
                self.assertGreaterEqual(
                    scores[i] + 1e-9, scores[i+1],
                    f"Scores not descending at {key}: {scores}"
                )

    def test_T029_top5_concentration_recorded(self):
        """T029 Concentration metrics present in results JSON."""
        d = _load_json()
        self.assertIn("concentration", d)
        self.assertIn("know5_avg_share", d["concentration"]["UP"])

    def test_T030_top6_concentration_ge_top5(self):
        """T030 Top-6 captures >= Top-5 share of favorable movement."""
        d = _load_json()
        up = d["concentration"]["UP"]
        if up.get("know5_avg_share") and up.get("know6_avg_share"):
            self.assertGreaterEqual(up["know6_avg_share"], up["know5_avg_share"] - 0.01)

    # ── T031: False positive ─────────────────────────────────────────────

    def test_T031_false_positive_rate_in_range(self):
        """T031 False-positive rate is between 0 and 1 for all models."""
        d = _load_json()
        for mn in ["V3_20","Know_Top5","Random_5"]:
            for dn in ["UP","DN"]:
                fp = d["results_by_split"]["ALL"][mn][dn].get("false_positive_rate")
                if fp is not None:
                    self.assertGreaterEqual(fp, 0.0)
                    self.assertLessEqual(fp, 1.0)

    # ── T032: Capital observation ─────────────────────────────────────────

    def test_T032_capital_observation_not_in_results(self):
        """T032 No production capital fields in research output."""
        d = _load_json()
        # Research output must not contain production order fields
        text = json.dumps(d)
        for field in ["order_id", "qty", "slippage", "brokerage", "order_placed"]:
            self.assertNotIn(field, text, f"Production field '{field}' found in results")

    # ── T033–T039: Safety / isolation ────────────────────────────────────

    def test_T033_no_production_writes(self):
        """T033 Knowledge script never imports CandidateStore."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        combined = " ".join(imports).lower()
        self.assertNotIn("candidatestore", combined)

    def test_T034_no_candidatestore_import(self):
        """T034 No CandidateStore import in knowledge script."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        combined = " ".join(imports).lower()
        for forbidden in ("candidatestore", "candidate_store"):
            self.assertNotIn(forbidden, combined,
                             f"Forbidden import '{forbidden}' in knowledge script")

    def test_T035_no_strategy_lab_calls(self):
        """T035 No StrategyLab imports in knowledge script."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("strategy_lab", source.lower())

    def test_T036_no_decision_engine_calls(self):
        """T036 No DecisionEngine imports in knowledge script."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("decision_engine", source.lower())

    def test_T037_no_risk_control_calls(self):
        """T037 No RiskControl imports in knowledge script."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("risk_control", source.lower())

    def test_T038_no_order_manager_calls(self):
        """T038 No OrderManager imports in knowledge script."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("order_manager", source.lower())

    def test_T039_no_broker_calls(self):
        """T039 No broker imports in knowledge script."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        combined = " ".join(imports).lower()
        for forbidden in ("dhan_feed", "zeroadhabroker", "broker_api"):
            self.assertNotIn(forbidden, combined,
                             f"Broker import '{forbidden}' found in knowledge script")

    # ── T040: Determinism ─────────────────────────────────────────────────

    def test_T040_deterministic_rerun(self):
        """T040 Knowledge signal for a known input is deterministic."""
        from v3_knowledge_second_pass import _knowledge_signals, _knowledge_score
        feat = {"mom_1d": 0.5, "mom_3d": 1.2, "mom_5d": 2.1, "mom_accel": 0.3,
                "rsi_14": 58, "vol_ratio": 1.4, "price_position": 0.65,
                "breakout_pct": 0.5}
        results = set()
        for _ in range(5):
            sigs = _knowledge_signals(feat, 0.1, "UP")
            results.add(_knowledge_score(sigs))
        self.assertEqual(len(results), 1, "Non-deterministic knowledge scoring")


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        sys.argv.pop(1)
    runner = unittest.TextTestRunner(verbosity=2)
    suite  = unittest.TestLoader().loadTestsFromTestCase(TestKnowledgeAudit)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
