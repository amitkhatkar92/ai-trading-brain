"""
tests/test_mover_discovery_v3_shadow_001.py
============================================
MOVER_DISCOVERY_V3_SHADOW_AUDIT_001 — 2026-08-17
Programmatic verification of shadow pipeline health.

These tests run against the LIVE shadow JSONL produced on the VPS.
They assert technical health only — NO performance thresholds.

Run (local, with env SHADOW_JSONL_PATH set, or defaults to VPS download):
    python tests/test_mover_discovery_v3_shadow_001.py [path_to_shadow.jsonl]
"""
from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Locate JSONL — accept path as first CLI arg or fall back to local copy
_JSONL_PATH = Path(
    sys.argv[1] if len(sys.argv) > 1 else
    os.environ.get("SHADOW_JSONL_PATH", str(_ROOT / "data" / "mover_discovery_v3_shadow_raw.jsonl"))
)
_RUNNER_PATH = _ROOT / "opportunity_engine" / "mover_discovery_v3_shadow_runner.py"
_ORCH_PATH   = _ROOT / "orchestrator" / "master_orchestrator.py"

EXPECTED_POOL_SIZE  = 20
FORBIDDEN_FUTURE_KEYS = {
    "ret_1d","ret_3d","ret_5d","mfe_5d","mae_5d","future_close","future_high",
    "future_low","future_volume","future_ret","future_label","forward_return",
    "actual_move_pct","final_state","MFE","MAE",
}


def _load_jsonl() -> List[Dict[str, Any]]:
    if not _JSONL_PATH.exists():
        raise FileNotFoundError(f"Shadow JSONL not found: {_JSONL_PATH}")
    return [json.loads(line) for line in _JSONL_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _summaries(records):
    return [r for r in records if r.get("record_type") == "SHADOW_SUMMARY"]

def _candidates(records):
    return [r for r in records if r.get("record_type") == "SHADOW_CANDIDATE"]

def _up(records, trading_date=None):
    c = [r for r in records if r.get("direction") == "UP" and r.get("record_type") == "SHADOW_CANDIDATE"]
    if trading_date:
        c = [r for r in c if r.get("trading_date") == trading_date]
    return c

def _dn(records, trading_date=None):
    c = [r for r in records if r.get("direction") == "DOWN" and r.get("record_type") == "SHADOW_CANDIDATE"]
    if trading_date:
        c = [r for r in c if r.get("trading_date") == trading_date]
    return c


class TestAudit001TechnicalHealth(unittest.TestCase):
    """Pipeline integrity checks — pass/fail independently of market outcomes."""

    @classmethod
    def setUpClass(cls):
        cls.records  = _load_jsonl()
        cls.summaries = _summaries(cls.records)
        cls.cands    = _candidates(cls.records)
        cls.trading_dates = sorted({s["trading_date"] for s in cls.summaries})

    # ── A01: File health ──────────────────────────────────────────────────────

    def test_A01_file_exists_and_nonempty(self):
        """Shadow JSONL exists and has records."""
        self.assertTrue(_JSONL_PATH.exists())
        self.assertGreater(len(self.records), 0)

    def test_A02_at_least_one_run_present(self):
        """At least one shadow run recorded."""
        self.assertGreaterEqual(len(self.summaries), 1)

    def test_A03_line_count_consistent(self):
        """Total lines = (runs × 41) or (runs × 41) for 20+20+1 per run."""
        n_runs = len(self.summaries)
        expected = n_runs * 41   # 20 UP + 20 DOWN + 1 summary per run
        self.assertEqual(len(self.records), expected,
                         f"Expected {expected} records for {n_runs} runs, got {len(self.records)}")

    # ── A04: Pool completeness ────────────────────────────────────────────────

    def test_A04_every_run_has_20_up(self):
        """Every shadow run produced exactly 20 UP candidates."""
        for td in self.trading_dates:
            up = _up(self.records, td)
            self.assertEqual(len(up), EXPECTED_POOL_SIZE,
                             f"trading_date={td}: expected 20 UP, got {len(up)}")

    def test_A05_every_run_has_20_down(self):
        """Every shadow run produced exactly 20 DOWN candidates."""
        for td in self.trading_dates:
            dn = _dn(self.records, td)
            self.assertEqual(len(dn), EXPECTED_POOL_SIZE,
                             f"trading_date={td}: expected 20 DOWN, got {len(dn)}")

    # ── A06: Structural validity ──────────────────────────────────────────────

    def test_A06_no_duplicate_up_symbols_within_run(self):
        """No symbol appears twice in the same UP pool."""
        for td in self.trading_dates:
            syms = [r["symbol"] for r in _up(self.records, td)]
            self.assertEqual(len(syms), len(set(syms)),
                             f"Duplicate UP symbols on {td}: {[s for s in syms if syms.count(s)>1]}")

    def test_A07_no_duplicate_down_symbols_within_run(self):
        """No symbol appears twice in the same DOWN pool."""
        for td in self.trading_dates:
            syms = [r["symbol"] for r in _dn(self.records, td)]
            self.assertEqual(len(syms), len(set(syms)),
                             f"Duplicate DOWN symbols on {td}")

    def test_A08_no_up_down_overlap_within_run(self):
        """No symbol appears in both UP and DOWN on the same day."""
        for td in self.trading_dates:
            up_syms = {r["symbol"] for r in _up(self.records, td)}
            dn_syms = {r["symbol"] for r in _dn(self.records, td)}
            overlap = up_syms & dn_syms
            self.assertEqual(len(overlap), 0,
                             f"UP/DOWN overlap on {td}: {overlap}")

    def test_A09_ranks_unique_and_complete(self):
        """Ranks 1-20 are present exactly once in each directional pool."""
        for td in self.trading_dates:
            for direction, pool in [("UP", _up(self.records, td)), ("DOWN", _dn(self.records, td))]:
                ranks = sorted(r["v3_rank"] for r in pool)
                self.assertEqual(ranks, list(range(1, 21)),
                                 f"Ranks for {direction} on {td}: {ranks}")

    def test_A10_scores_descending(self):
        """Scores are in descending order within each pool (rank 1 = highest score)."""
        for td in self.trading_dates:
            for direction, pool_fn in [("UP", _up), ("DOWN", _dn)]:
                pool = sorted(pool_fn(self.records, td), key=lambda x: x["v3_rank"])
                scores = [r["v3_score"] for r in pool]
                self.assertTrue(
                    all(scores[i] >= scores[i+1] for i in range(len(scores)-1)),
                    f"Scores not descending for {direction} on {td}: {scores[:5]}"
                )

    def test_A11_no_nan_or_none_scores(self):
        """No candidate has a NaN or None v3_score."""
        bad = [r for r in self.cands
               if r.get("v3_score") is None or str(r.get("v3_score")).lower() in ("nan", "none", "")]
        self.assertEqual(len(bad), 0, f"NaN/None scores: {[r['symbol'] for r in bad]}")

    # ── A12: Safety / leakage ─────────────────────────────────────────────────

    def test_A12_no_future_data_leakage(self):
        """No forbidden future-data keys appear in any candidate record."""
        violations = [
            (r.get("symbol"), k)
            for r in self.cands
            for k in FORBIDDEN_FUTURE_KEYS
            if k in r
        ]
        self.assertEqual(violations, [], f"Leakage detected: {violations}")

    def test_A13_no_trades_generated_all_records(self):
        """Every record carries no_trades_generated=True."""
        bad = [i for i, r in enumerate(self.records, 1) if not r.get("no_trades_generated")]
        self.assertEqual(bad, [], f"Lines missing no_trades_generated: {bad}")

    def test_A14_no_candidatestore_write_in_summaries(self):
        """Every summary record confirms no_candidatestore_write=True."""
        bad = [s.get("trading_date") for s in self.summaries if not s.get("no_candidatestore_write")]
        self.assertEqual(bad, [], f"Summaries missing no_candidatestore_write: {bad}")

    # ── A15: Isolation (static analysis) ─────────────────────────────────────

    def test_A15_runner_imports_clean(self):
        """Shadow runner has no imports from forbidden production modules."""
        source = _RUNNER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        combined = " ".join(imports).lower()
        for forbidden in ("decision_engine", "risk_control", "execution_engine",
                          "order_manager", "dhan_feed", "zeroadhabroker"):
            self.assertNotIn(forbidden, combined,
                             f"Forbidden import {forbidden!r} found in shadow runner")

    # ── A16: Orchestrator integration ─────────────────────────────────────────

    def test_A16_orchestrator_has_shadow_hook(self):
        """Orchestrator has the V3 shadow hook with try/except isolation."""
        source = _ORCH_PATH.read_text(encoding="utf-8")
        self.assertIn("MOVER_DISCOVERY_V3_SHADOW_MODE", source)
        self.assertIn("run_phase_d_v3_shadow", source)
        self.assertIn("Phase D shadow failed — production unaffected", source)

    # ── A17: Data freshness ───────────────────────────────────────────────────

    def test_A17_trading_date_not_future(self):
        """No shadow run uses a trading_date in the future."""
        from datetime import date
        today = date.today().isoformat()
        for s in self.summaries:
            self.assertLessEqual(s["trading_date"], today,
                                 f"trading_date {s['trading_date']} is in the future")

    def test_A18_trading_dates_unique(self):
        """No trading_date appears in more than one summary (no duplicate runs)."""
        dates = [s["trading_date"] for s in self.summaries]
        self.assertEqual(len(dates), len(set(dates)),
                         f"Duplicate trading dates: {[d for d in dates if dates.count(d)>1]}")

    # ── A19: Required fields ──────────────────────────────────────────────────

    def test_A19_all_required_candidate_fields_present(self):
        """Every candidate record has the required audit fields."""
        required = {
            "timestamp", "trading_date", "phase", "record_type", "symbol",
            "direction", "v3_rank", "v3_score", "atr_pct", "mom_5d",
            "rs_pct_5d", "vol_ratio", "mom_accel", "discovery_pool_size",
            "data_timestamp", "no_trades_generated",
        }
        for r in self.cands:
            missing = required - set(r.keys())
            self.assertEqual(missing, set(),
                             f"symbol={r.get('symbol')}: missing fields {missing}")

    # ── A20: Duration recorded ────────────────────────────────────────────────

    def test_A20_duration_recorded_and_positive(self):
        """Every summary records v3_shadow_duration_ms > 0."""
        for s in self.summaries:
            self.assertIn("v3_shadow_duration_ms", s,
                          f"trading_date={s['trading_date']}: missing duration")
            self.assertGreater(s["v3_shadow_duration_ms"], 0,
                               f"trading_date={s['trading_date']}: duration not positive")


if __name__ == "__main__":
    # Strip the optional path arg so unittest doesn't try to parse it
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        sys.argv.pop(1)
    runner = unittest.TextTestRunner(verbosity=2)
    suite  = unittest.TestLoader().loadTestsFromTestCase(TestAudit001TechnicalHealth)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
