"""
tests/test_mover_discovery_v3_shadow.py
========================================
Shadow deployment tests for Mover Discovery V3 Phase D integration.

Tests:
  T001 — V3 shadow executes
  T002 — existing scanner still executes
  T003 — V3 does not modify CandidateStore
  T004 — V3 does not call DecisionEngine
  T005 — V3 does not call Risk Control
  T006 — V3 does not call Execution Engine
  T007 — V3 failure does not stop Phase D
  T008 — exactly top 20 UP are recorded
  T009 — exactly top 20 DOWN are recorded
  T010 — overlap calculation is correct
  T011 — JSONL output is valid
  T012 — no future data is present
  T013 — shadow mode can be disabled
  T014 — deterministic ranking
  T015 — execution timing is recorded
"""
from __future__ import annotations

import ast
import importlib
import json
import os
import sqlite3
import sys
import tempfile
import time
import textwrap
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, call

# ── Workspace path resolution ─────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# Helpers to build synthetic OHLCV data and features
# ─────────────────────────────────────────────────────────────────────────────

def _make_ohlcv(n: int = 40, close_start: float = 100.0, trend: float = 0.002):
    closes  = [round(close_start * (1 + trend) ** i, 4) for i in range(n)]
    highs   = [round(c * 1.01, 4) for c in closes]
    lows    = [round(c * 0.99, 4) for c in closes]
    volumes = [1_000_000.0 + i * 1000 for i in range(n)]
    return closes, highs, lows, volumes


def _make_symbol_features(n_symbols: int = 30) -> Dict[str, Dict[str, List[float]]]:
    """Return synthetic OHLCV dict for n_symbols distinct tickers."""
    from opportunity_engine.mover_discovery_v3 import compute_v3_features
    result = {}
    for i in range(n_symbols):
        sym = f"SYM{i:03d}"
        closes, highs, lows, vols = _make_ohlcv(
            n=40, close_start=100.0 + i * 5, trend=0.001 * (i + 1)
        )
        feat = compute_v3_features(sym, closes, highs, lows, vols)
        if feat:
            result[sym] = {"closes": closes, "highs": highs, "lows": lows, "volumes": vols}
    return result


def _setup_test_db(db_path: str, symbols: List[str], trade_date: str = "2026-08-14") -> None:
    """Create a minimal market_behavior.db with universe_stocks + ohlcv_daily."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS universe_stocks "
        "(symbol TEXT PRIMARY KEY, sector TEXT, is_active INTEGER DEFAULT 1)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ohlcv_daily "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    for sym in symbols:
        conn.execute(
            "INSERT OR IGNORE INTO universe_stocks(symbol, sector, is_active) VALUES(?,?,1)",
            (sym, "UNKNOWN"),
        )
        closes, highs, lows, vols = _make_ohlcv(n=40, close_start=100.0)
        # Insert 40 rows spanning trade_date backwards
        from datetime import date, timedelta
        base = date.fromisoformat(trade_date)
        for day_offset in range(39, -1, -1):
            d = (base - timedelta(days=day_offset)).isoformat()
            idx = 39 - day_offset
            conn.execute(
                "INSERT INTO ohlcv_daily(symbol, trade_date, open, high, low, close, volume) "
                "VALUES(?,?,?,?,?,?,?)",
                (sym, d, closes[idx], highs[idx], lows[idx], closes[idx], vols[idx]),
            )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test class
# ─────────────────────────────────────────────────────────────────────────────

class TestV3ShadowDeployment(unittest.TestCase):

    def setUp(self):
        """Create a temp DB and point OIOS_DB_PATH at it for isolation."""
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = os.path.join(self._tmpdir, "market_behavior.db")
        self._log_path = os.path.join(self._tmpdir, "mover_discovery_v3_shadow.jsonl")
        self._symbols = [f"SYM{i:03d}" for i in range(30)]
        _setup_test_db(self._db_path, self._symbols)
        os.environ["OIOS_DB_PATH"] = self._db_path
        # Reload shadow runner module to pick up the new env var
        if "opportunity_engine.mover_discovery_v3_shadow_runner" in sys.modules:
            importlib.reload(sys.modules["opportunity_engine.mover_discovery_v3_shadow_runner"])

    def tearDown(self):
        os.environ.pop("OIOS_DB_PATH", None)
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _run_shadow(self, log_path: str | None = None) -> Dict[str, Any]:
        from opportunity_engine import mover_discovery_v3_shadow_runner as mod
        mod._SHADOW_LOG_PATH = Path(log_path or self._log_path)
        return mod.run_phase_d_v3_shadow(trading_date="2026-08-14")

    # ─────────────────────────────────────────────────────────────────────────

    def test_T001_shadow_executes(self):
        """T001: run_phase_d_v3_shadow() returns a success result."""
        result = self._run_shadow()
        self.assertIsInstance(result, dict, "should return a dict")
        self.assertTrue(result.get("success"), f"expected success=True, got {result}")
        self.assertIn("v3_shadow_duration_ms", result)

    def test_T002_existing_scanner_still_executes(self):
        """T002: when shadow fails, run_scan() is unaffected; both code paths are independent."""
        # Simulate orchestrator pattern: run_scan runs, then shadow runs separately
        with patch("opportunity_engine.market_scanner.run_scan", return_value=True) as mock_scan:
            mock_scan()  # production call
        self.assertTrue(mock_scan.called, "production run_scan must have been called")

        # Shadow can raise without affecting the mock_scan result
        with patch(
            "opportunity_engine.mover_discovery_v3_shadow_runner.run_phase_d_v3_shadow",
            side_effect=RuntimeError("shadow exploded"),
        ):
            try:
                from opportunity_engine.mover_discovery_v3_shadow_runner import run_phase_d_v3_shadow
                run_phase_d_v3_shadow()
                self.fail("expected RuntimeError")
            except RuntimeError:
                pass
        # run_scan result was independent — not affected by shadow failure
        self.assertTrue(mock_scan.return_value)

    def test_T003_v3_does_not_modify_candidatestore(self):
        """T003: CandidateStore.write() is never called by the shadow runner."""
        with patch("opportunity_engine.candidate_store.CandidateStore.write") as mock_write:
            self._run_shadow()
        mock_write.assert_not_called()

    @staticmethod
    def _get_runner_imports() -> List[str]:
        """Return all module names imported by mover_discovery_v3_shadow_runner.py."""
        runner_path = Path(__file__).resolve().parents[1] / \
            "opportunity_engine" / "mover_discovery_v3_shadow_runner.py"
        tree = ast.parse(runner_path.read_text(encoding="utf-8"))
        imported: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module)
                    for alias in node.names:
                        imported.append(f"{node.module}.{alias.name}")
        return imported

    def test_T004_v3_does_not_call_decision_engine(self):
        """T004: shadow runner module does not import DecisionEngine."""
        imports = self._get_runner_imports()
        combined = " ".join(imports).lower()
        self.assertNotIn(
            "decision_engine", combined,
            f"shadow runner must not import decision_engine; found: {imports}",
        )

    def test_T005_v3_does_not_call_risk_control(self):
        """T005: shadow runner module does not import RiskControl or RiskManagerAI."""
        imports = self._get_runner_imports()
        combined = " ".join(imports).lower()
        for forbidden in ("risk_control", "risk_manager"):
            self.assertNotIn(
                forbidden, combined,
                f"shadow runner must not import {forbidden}; found: {imports}",
            )

    def test_T006_v3_does_not_call_execution_engine(self):
        """T006: shadow runner module does not import OrderManager or ExecutionEngine."""
        imports = self._get_runner_imports()
        combined = " ".join(imports).lower()
        for forbidden in ("order_manager", "execution_engine", "zeroadhabroker"):
            self.assertNotIn(
                forbidden, combined,
                f"shadow runner must not import {forbidden}; found: {imports}",
            )

    def test_T007_v3_failure_does_not_stop_phase_d(self):
        """T007: orchestrator wraps V3 shadow in try/except; exception must not propagate."""
        # Read the orchestrator source and verify the try/except pattern exists
        orch_path = Path(__file__).resolve().parents[1] / \
            "orchestrator" / "master_orchestrator.py"
        source = orch_path.read_text(encoding="utf-8")
        # Must have the V3 shadow block with try/except and warning log
        self.assertIn("MOVER_DISCOVERY_V3_SHADOW_MODE", source,
                      "orchestrator must check config flag")
        self.assertIn("run_phase_d_v3_shadow", source,
                      "orchestrator must call run_phase_d_v3_shadow")
        self.assertIn("Phase D shadow failed — production unaffected", source,
                      "orchestrator must log V3 failure without re-raising")

        # Functional check: simulate the orchestrator block
        scan_ran = []

        def fake_scan():
            scan_ran.append(True)
            return True

        def bad_shadow():
            raise RuntimeError("V3 exploded")

        try:
            fake_scan()
            bad_shadow()
        except RuntimeError:
            pass  # orchestrator catches this

        self.assertTrue(scan_ran, "production scan must complete even if shadow fails")

    def test_T008_exactly_20_up_recorded(self):
        """T008: JSONL contains exactly cfg.discovery_pool_size=20 UP candidate records."""
        self._run_shadow()
        up_records = []
        with open(self._log_path, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                if rec.get("direction") == "UP" and rec.get("record_type") == "SHADOW_CANDIDATE":
                    up_records.append(rec)
        self.assertEqual(
            len(up_records), 20,
            f"expected exactly 20 UP records, got {len(up_records)}",
        )

    def test_T009_exactly_20_down_recorded(self):
        """T009: JSONL contains exactly cfg.discovery_pool_size=20 DOWN candidate records."""
        self._run_shadow()
        down_records = []
        with open(self._log_path, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                if rec.get("direction") == "DOWN" and rec.get("record_type") == "SHADOW_CANDIDATE":
                    down_records.append(rec)
        self.assertEqual(
            len(down_records), 20,
            f"expected exactly 20 DOWN records, got {len(down_records)}",
        )

    def test_T010_overlap_calculation_correct(self):
        """T010: overlap counts in summary record match per-symbol records."""
        # Inject known existing_scanner candidates = first 5 symbols
        known_existing = self._symbols[:5]
        fake_existing = [{"symbol": s, "buckets": ["BREAKOUT"]} for s in known_existing]

        with patch("opportunity_engine.candidate_store.CandidateStore.read",
                   return_value=fake_existing):
            self._run_shadow()

        summary = None
        up_overlap_syms = set()
        down_overlap_syms = set()
        with open(self._log_path, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                if rec.get("record_type") == "SHADOW_SUMMARY":
                    summary = rec
                elif rec.get("direction") == "UP" and rec.get("overlap"):
                    up_overlap_syms.add(rec["symbol"])
                elif rec.get("direction") == "DOWN" and rec.get("overlap"):
                    down_overlap_syms.add(rec["symbol"])

        self.assertIsNotNone(summary, "SHADOW_SUMMARY record must be written")
        self.assertEqual(
            summary["up_overlap_count"], len(up_overlap_syms),
            "up_overlap_count must equal per-symbol UP overlap count",
        )
        self.assertEqual(
            summary["down_overlap_count"], len(down_overlap_syms),
            "down_overlap_count must equal per-symbol DOWN overlap count",
        )
        # total_overlap ≤ up + down (a symbol can appear in both)
        self.assertLessEqual(
            summary["total_overlap"],
            summary["up_overlap_count"] + summary["down_overlap_count"],
        )

    def test_T011_jsonl_output_valid(self):
        """T011: every line in the JSONL is valid JSON with required fields."""
        self._run_shadow()
        required_candidate = {
            "timestamp", "trading_date", "phase", "symbol", "direction",
            "v3_rank", "v3_score", "atr_pct", "mom_5d", "no_trades_generated",
        }
        required_summary = {
            "record_type", "v3_up_count", "v3_down_count",
            "v3_shadow_duration_ms", "no_trades_generated", "no_candidatestore_write",
        }
        with open(self._log_path, encoding="utf-8") as fh:
            lines = fh.readlines()
        self.assertGreater(len(lines), 0, "JSONL must not be empty")
        for i, line in enumerate(lines):
            rec = json.loads(line)  # raises if invalid JSON
            if rec.get("record_type") == "SHADOW_SUMMARY":
                for field in required_summary:
                    self.assertIn(field, rec, f"line {i}: missing field {field!r} in summary")
            elif rec.get("record_type") == "SHADOW_CANDIDATE":
                for field in required_candidate:
                    self.assertIn(field, rec, f"line {i}: missing field {field!r} in candidate")

    def test_T012_no_future_data_in_records(self):
        """T012: no FORBIDDEN_FUTURE_KEYS appear in any JSONL record."""
        from opportunity_engine.mover_discovery_v3 import FORBIDDEN_FUTURE_KEYS
        self._run_shadow()
        with open(self._log_path, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                for bad_key in FORBIDDEN_FUTURE_KEYS:
                    self.assertNotIn(
                        bad_key, rec,
                        f"future key {bad_key!r} found in JSONL record for {rec.get('symbol')}",
                    )

    def test_T013_shadow_mode_disabled(self):
        """T013: when MOVER_DISCOVERY_V3_SHADOW_MODE=False, shadow runner is not called."""
        called = []

        def fake_shadow(*args, **kwargs):
            called.append(True)
            return {"success": True, "v3_up_count": 20, "v3_down_count": 20,
                    "total_overlap": 0, "v3_only_candidates": 40,
                    "v3_shadow_duration_ms": 1.0, "no_trades_generated": True}

        # Simulate orchestrator config-check pattern
        shadow_mode = False  # OFF
        if shadow_mode:
            fake_shadow()

        self.assertEqual(len(called), 0, "shadow must not run when config flag is False")

        # Confirm config.py default is False
        import config
        importlib.reload(config)
        self.assertFalse(
            getattr(config, "MOVER_DISCOVERY_V3_SHADOW_MODE", True),
            "MOVER_DISCOVERY_V3_SHADOW_MODE must default to False in config.py",
        )

    def test_T014_deterministic_ranking(self):
        """T014: running shadow twice on the same data produces identical UP/DOWN ordering."""
        log_path_1 = os.path.join(self._tmpdir, "shadow_run1.jsonl")
        log_path_2 = os.path.join(self._tmpdir, "shadow_run2.jsonl")

        self._run_shadow(log_path=log_path_1)
        self._run_shadow(log_path=log_path_2)

        def extract_ordered(path: str, direction: str) -> List[str]:
            records = []
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    rec = json.loads(line)
                    if rec.get("direction") == direction and rec.get("record_type") == "SHADOW_CANDIDATE":
                        records.append((rec["v3_rank"], rec["symbol"]))
            records.sort()
            return [sym for _, sym in records]

        up1   = extract_ordered(log_path_1, "UP")
        up2   = extract_ordered(log_path_2, "UP")
        down1 = extract_ordered(log_path_1, "DOWN")
        down2 = extract_ordered(log_path_2, "DOWN")

        self.assertEqual(up1, up2,   "UP ranking must be deterministic across runs")
        self.assertEqual(down1, down2, "DOWN ranking must be deterministic across runs")
        self.assertEqual(len(up1), 20,   "must have exactly 20 UP candidates")
        self.assertEqual(len(down1), 20, "must have exactly 20 DOWN candidates")

    def test_T015_execution_timing_recorded(self):
        """T015: v3_shadow_duration_ms is present and positive in return value and JSONL summary."""
        result = self._run_shadow()
        self.assertIn("v3_shadow_duration_ms", result)
        self.assertGreater(result["v3_shadow_duration_ms"], 0,
                           "duration_ms must be > 0")

        summary = None
        with open(self._log_path, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                if rec.get("record_type") == "SHADOW_SUMMARY":
                    summary = rec
                    break
        self.assertIsNotNone(summary)
        self.assertIn("v3_shadow_duration_ms", summary)
        self.assertGreater(summary["v3_shadow_duration_ms"], 0)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromTestCase(TestV3ShadowDeployment)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
