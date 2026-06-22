"""
tests/oios/test_phase_f_migration.py
Phase F — Acceptance tests for schema, migration, and service isolation.

Tests:
  schema       — 5 tables + 16 indexes created correctly
  isolation    — no FK references into A–E tables
  constraints  — CHECK constraints enforced
  round-trip   — insert/retrieve for each table
  services     — leader_capture, feature_extractor, outcome_tracker,
                 control_population, failure_analyzer, weekly_market_research,
                 phase_f_shadow all importable with no side-effects
"""

from __future__ import annotations

import os
import sqlite3
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.db.connection import get_connection
from oios.db.migrations import apply_phase_f


# ── Shared fixture ────────────────────────────────────────────────────────────

def _fresh_db() -> sqlite3.Connection:
    """Each test gets its own in-memory DB with Phase F schema applied."""
    conn = get_connection()
    apply_phase_f(conn)
    return conn


PHASE_F_TABLES = [
    "market_leaders_daily",
    "market_leader_features",
    "market_leader_outcomes",
    "market_research_controls",
    "failure_attribution",
    "feature_differentials",
]

REQUIRED_INDEXES = [
    "idx_mld_date", "idx_mld_symbol", "idx_mld_type_date", "idx_mld_sector",
    "idx_mlf_leader", "idx_mlf_name", "idx_mlf_ldr_name",
    "idx_mlo_class",
    "idx_mrc_leader", "idx_mrc_symbol", "idx_mrc_hash", "idx_mrc_date",
    "idx_fa_symbol", "idx_fa_reason", "idx_fa_leader", "idx_fa_date",
    # Phase F2.5
    "idx_fd_date", "idx_fd_winner", "idx_fd_control", "idx_fd_similarity", "idx_fd_leader",
]

AE_TABLES = {
    "opportunities", "signal_births", "decision_log",
    "sector_conviction_daily", "theme_phase_history",
    "universe_stocks", "ohlcv_daily", "bhav_daily", "bulk_block_deals",
    "pending_adjustments", "opportunity_causes", "cause_scores",
}


# ─────────────────────────────────────────────────────────────────────────────
# Group 1: Schema Correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestPhaseFSchema(unittest.TestCase):

    def setUp(self):
        self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()

    def _tables(self):
        return {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

    def _indexes(self):
        return {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}

    def test_all_5_tables_exist(self):
        tables = self._tables()
        for t in PHASE_F_TABLES:
            self.assertIn(t, tables, f"Missing table: {t}")

    def test_all_16_indexes_exist(self):
        indexes = self._indexes()
        for idx in REQUIRED_INDEXES:
            self.assertIn(idx, indexes, f"Missing index: {idx}")

    def test_no_ae_fk_references(self):
        """Phase F tables must not REFERENCES any A–E table."""
        for table in PHASE_F_TABLES:
            row = self.conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            self.assertIsNotNone(row)
            sql = (row[0] or "").upper()
            for ae in AE_TABLES:
                self.assertNotIn(
                    f"REFERENCES {ae.upper()}", sql,
                    f"Phase F table {table} has FK → {ae}"
                )

    def test_schema_is_idempotent(self):
        """apply_phase_f() called twice must not raise."""
        apply_phase_f(self.conn)

    def test_exactly_5_phase_f_tables(self):
        """Updated to 6 tables now that F2.5 (feature_differentials) is included."""
        tables = self._tables()
        pf_found = [t for t in PHASE_F_TABLES if t in tables]
        self.assertEqual(len(pf_found), 6)


# ─────────────────────────────────────────────────────────────────────────────
# Group 2: Constraints
# ─────────────────────────────────────────────────────────────────────────────

class TestPhaseFConstraints(unittest.TestCase):

    def setUp(self):
        self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()

    def test_leader_type_check(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute("""
                    INSERT INTO market_leaders_daily
                        (leader_id, trade_date, symbol, leader_type, rank_position,
                         day_return_pct, sector, captured_at)
                    VALUES ('X1','2026-06-19','TST.NS','NEUTRAL',1,3.0,'IT',datetime('now'))
                """)

    def test_outcome_class_check(self):
        with self.conn:
            self.conn.execute("""
                INSERT INTO market_leaders_daily
                    (leader_id, trade_date, symbol, leader_type, rank_position,
                     day_return_pct, sector, captured_at)
                VALUES ('X2','2026-06-19','TST.NS','WINNER',1,3.0,'IT',datetime('now'))
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute("""
                    INSERT INTO market_leader_outcomes
                        (leader_id, outcome_class, updated_at)
                    VALUES ('X2', 'MEGA_BULL', datetime('now'))
                """)

    def test_control_outcome_class_check(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute("""
                    INSERT INTO market_research_controls
                        (control_id, trade_date, symbol, fingerprint_hash,
                         matched_leader_id, outcome_class, captured_at)
                    VALUES ('C1','2026-06-19','HAL.NS','abc123','LDR_X',
                            'SUPER_WINNER',datetime('now'))
                """)

    def test_unique_outcome_per_leader(self):
        """market_leader_outcomes PK=leader_id → duplicate must fail."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO market_leaders_daily
                    (leader_id,trade_date,symbol,leader_type,rank_position,
                     day_return_pct,sector,captured_at)
                VALUES ('U1','2026-06-19','BEL.NS','WINNER',1,5.0,'DEFENCE',datetime('now'))
            """)
            self.conn.execute("""
                INSERT INTO market_leader_outcomes (leader_id,outcome_class,updated_at)
                VALUES ('U1','UNKNOWN',datetime('now'))
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute("""
                    INSERT INTO market_leader_outcomes (leader_id,outcome_class,updated_at)
                    VALUES ('U1','UNKNOWN',datetime('now'))
                """)


# ─────────────────────────────────────────────────────────────────────────────
# Group 3: Round-trip Data
# ─────────────────────────────────────────────────────────────────────────────

class TestPhaseFRoundTrip(unittest.TestCase):

    def setUp(self):
        self.conn = _fresh_db()
        # Seed a standard leader row used by multiple tests
        with self.conn:
            self.conn.execute("""
                INSERT INTO market_leaders_daily
                    (leader_id,trade_date,symbol,leader_type,rank_position,
                     day_return_pct,volume_ratio,sector,theme_phase,regime,captured_at)
                VALUES ('LDR_001','2026-06-19','BEL.NS','WINNER',1,
                        4.5,2.1,'DEFENCE','ACCELERATION','bull_trend',datetime('now'))
            """)

    def tearDown(self):
        self.conn.close()

    def test_leader_retrieval(self):
        row = self.conn.execute(
            "SELECT symbol,day_return_pct,leader_type FROM market_leaders_daily WHERE leader_id='LDR_001'"
        ).fetchone()
        self.assertEqual(row[0], "BEL.NS")
        self.assertAlmostEqual(row[1], 4.5, places=2)
        self.assertEqual(row[2], "WINNER")

    def test_feature_round_trip(self):
        with self.conn:
            self.conn.execute("""
                INSERT INTO market_leader_features
                    (feature_id,leader_id,feature_name,feature_value,captured_at)
                VALUES ('FT_001','LDR_001','above_20dma',1.0,datetime('now'))
            """)
        val = self.conn.execute(
            "SELECT feature_value FROM market_leader_features WHERE feature_id='FT_001'"
        ).fetchone()[0]
        self.assertAlmostEqual(val, 1.0, places=3)

    def test_outcome_upsert(self):
        with self.conn:
            self.conn.execute("""
                INSERT INTO market_leader_outcomes
                    (leader_id,return_1d,return_3d,outcome_class,updated_at)
                VALUES ('LDR_001',4.2,3.1,'SHORT_RUNNER',datetime('now'))
            """)
        row = self.conn.execute(
            "SELECT return_1d,outcome_class FROM market_leader_outcomes WHERE leader_id='LDR_001'"
        ).fetchone()
        self.assertAlmostEqual(row[0], 4.2, places=2)
        self.assertEqual(row[1], "SHORT_RUNNER")

    def test_control_round_trip(self):
        with self.conn:
            self.conn.execute("""
                INSERT INTO market_research_controls
                    (control_id,trade_date,symbol,fingerprint_hash,
                     matched_leader_id,outcome_class,captured_at)
                VALUES ('CTRL_001','2026-06-19','HAL.NS','abc123',
                        'LDR_001','UNKNOWN',datetime('now'))
            """)
        row = self.conn.execute(
            "SELECT symbol FROM market_research_controls WHERE control_id='CTRL_001'"
        ).fetchone()
        self.assertEqual(row[0], "HAL.NS")

    def test_failure_attribution_round_trip(self):
        with self.conn:
            self.conn.execute("""
                INSERT INTO failure_attribution
                    (failure_id,symbol,trade_date,candidate_reason,confidence,recorded_at)
                VALUES ('FA_001','HAL.NS','2026-06-19','LOW_DELIVERY',0.75,datetime('now'))
            """)
        row = self.conn.execute(
            "SELECT candidate_reason,confidence FROM failure_attribution WHERE failure_id='FA_001'"
        ).fetchone()
        self.assertEqual(row[0], "LOW_DELIVERY")
        self.assertAlmostEqual(row[1], 0.75, places=3)


# ─────────────────────────────────────────────────────────────────────────────
# Group 4: Service Import Smoke Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPhaseFServiceImports(unittest.TestCase):
    """All Phase F modules must import cleanly with no side-effects."""

    def test_leader_capture_importable(self):
        from oios.phase_f import leader_capture  # noqa
        self.assertTrue(hasattr(leader_capture, "capture_daily_leaders"))

    def test_feature_extractor_importable(self):
        from oios.phase_f import feature_extractor  # noqa
        self.assertTrue(hasattr(feature_extractor, "extract_features"))

    def test_outcome_tracker_importable(self):
        from oios.phase_f import outcome_tracker  # noqa
        self.assertTrue(hasattr(outcome_tracker, "update_outcomes"))

    def test_control_population_importable(self):
        from oios.phase_f import control_population  # noqa
        self.assertTrue(hasattr(control_population, "build_controls_for_date"))

    def test_failure_analyzer_importable(self):
        from oios.phase_f import failure_analyzer  # noqa
        self.assertTrue(hasattr(failure_analyzer, "analyze_failures"))

    def test_weekly_research_importable(self):
        from oios.phase_f import weekly_market_research  # noqa
        self.assertTrue(hasattr(weekly_market_research, "generate_weekly_report"))

    def test_phase_f_shadow_importable(self):
        from oios.phase_f import phase_f_shadow  # noqa
        self.assertTrue(hasattr(phase_f_shadow, "run_shadow"))
        self.assertTrue(hasattr(phase_f_shadow, "format_shadow_report"))

    def test_shadow_has_no_write_calls(self):
        """Phase F shadow module source must contain no INSERT/UPDATE/DELETE SQL."""
        import inspect
        from oios.phase_f import phase_f_shadow
        source = inspect.getsource(phase_f_shadow)
        for verb in ("INSERT ", "UPDATE ", "DELETE ", "executemany"):
            self.assertNotIn(verb, source,
                             f"phase_f_shadow.py contains '{verb}' — isolation violation")

    def test_differential_engine_importable(self):
        from oios.phase_f import differential_engine  # noqa
        self.assertTrue(hasattr(differential_engine, "compute_differentials"))
        self.assertTrue(hasattr(differential_engine, "aggregate_top_differentiators"))
        self.assertTrue(hasattr(differential_engine, "same_setup_different_outcome"))
        self.assertTrue(hasattr(differential_engine, "format_differential_report"))


# ─────────────────────────────────────────────────────────────────────────────
# Group 5b: feature_differentials table
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureDifferentials(unittest.TestCase):
    """Schema, isolation, and round-trip tests for the F2.5 table."""

    def test_differentials_table_exists(self):
        conn = _fresh_db()
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        self.assertIn("feature_differentials", tables)

    def test_differentials_indexes_exist(self):
        conn = _fresh_db()
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        for idx in ("idx_fd_date", "idx_fd_winner", "idx_fd_control",
                    "idx_fd_similarity", "idx_fd_leader"):
            self.assertIn(idx, indexes, f"Missing index: {idx}")

    def test_differentials_round_trip(self):
        conn = _fresh_db()
        import json
        conn.execute("""
            INSERT INTO feature_differentials
                (differential_id, trade_date, winner_symbol, control_symbol,
                 matched_leader_id, control_id, similarity_score,
                 differing_features, outcome_gap_1d, outcome_gap_3d,
                 outcome_gap_5d, outcome_gap_20d)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "DIFF_20260101_BEL_HAL", "2026-01-01", "BEL", "HAL",
            "LDR_20260101_abc", "CTRL_HAL_20260101",
            0.82,
            json.dumps([{"feature": "volume_ratio", "winner_val": 2.8,
                         "control_val": 2.4, "delta": 0.4, "abs_delta": 0.4}]),
            11.7, 9.2, 6.1, 3.5,
        ))
        conn.commit()
        row = conn.execute(
            "SELECT winner_symbol, control_symbol, similarity_score, outcome_gap_1d "
            "FROM feature_differentials WHERE differential_id = ?",
            ("DIFF_20260101_BEL_HAL",)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "BEL")
        self.assertEqual(row[1], "HAL")
        self.assertAlmostEqual(row[2], 0.82)
        self.assertAlmostEqual(row[3], 11.7)

    def test_outcome_gap_nullable(self):
        """Gaps can be NULL before return data is available."""
        conn = _fresh_db()
        conn.execute("""
            INSERT INTO feature_differentials
                (differential_id, trade_date, winner_symbol, control_symbol,
                 matched_leader_id, control_id, similarity_score)
            VALUES (?,?,?,?,?,?,?)
        """, (
            "DIFF_NULL_GAP", "2026-01-02", "TCS", "INFY",
            "LDR_20260102_xyz", "CTRL_INFY_20260102", 0.75,
        ))
        conn.commit()
        row = conn.execute(
            "SELECT outcome_gap_1d FROM feature_differentials WHERE differential_id='DIFF_NULL_GAP'"
        ).fetchone()
        self.assertIsNone(row[0])

    def test_no_ae_fk_in_differentials(self):
        """feature_differentials must not reference any A-E table via FK."""
        conn = _fresh_db()
        fk_info = conn.execute(
            "PRAGMA foreign_key_list(feature_differentials)"
        ).fetchall()
        ae_tables = AE_TABLES
        for fk in fk_info:
            referenced = fk[2]  # table column
            self.assertNotIn(referenced, ae_tables,
                             f"FK to A-E table detected: {referenced}")

    def test_aggregate_differentiators_empty_returns_list(self):
        """aggregate_top_differentiators returns [] when no data is present."""
        conn = _fresh_db()
        from oios.phase_f.differential_engine import aggregate_top_differentiators
        result = aggregate_top_differentiators("2026-01-31", conn, lookback_days=30)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_aggregate_differentiators_with_data(self):
        """aggregate_top_differentiators correctly scores features across pairs."""
        conn = _fresh_db()
        import json
        from oios.phase_f.differential_engine import aggregate_top_differentiators

        # Insert 5 pairs where volume_ratio always favours winner
        for i in range(5):
            diff = [
                {"feature": "volume_ratio", "winner_val": 2.8 + i * 0.1,
                 "control_val": 1.5, "delta": 1.3, "abs_delta": 1.3},
                {"feature": "above_20dma", "winner_val": 1.0,
                 "control_val": 0.0, "delta": 1.0, "abs_delta": 1.0},
            ]
            conn.execute("""
                INSERT INTO feature_differentials
                    (differential_id, trade_date, winner_symbol, control_symbol,
                     matched_leader_id, control_id, similarity_score,
                     differing_features, outcome_gap_1d)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                f"DIFF_TEST_{i}", f"2026-01-{i+10:02d}",
                "BEL", "HAL", f"LDR_{i}", f"CTRL_{i}",
                0.80, json.dumps(diff), 5.0 + i,
            ))
        conn.commit()

        result = aggregate_top_differentiators("2026-01-31", conn, lookback_days=30,
                                               min_pairs=3)
        self.assertGreater(len(result), 0)
        # volume_ratio should rank highly (always winner > control)
        top_features = [r["feature"] for r in result]
        self.assertIn("volume_ratio", top_features)
        top = result[0]
        self.assertIn("feature", top)
        self.assertIn("winner_higher_pct", top)
        self.assertIn("avg_delta", top)
        self.assertIn("separation_power", top)

    def test_same_setup_empty_returns_list(self):
        conn = _fresh_db()
        from oios.phase_f.differential_engine import same_setup_different_outcome
        result = same_setup_different_outcome("2026-01-31", conn)
        self.assertIsInstance(result, list)

    def test_format_differential_report_returns_markdown(self):
        conn = _fresh_db()
        from oios.phase_f.differential_engine import format_differential_report
        report = format_differential_report("2026-01-31", conn, lookback_days=30)
        self.assertIsInstance(report, str)
        self.assertIn("# Phase F2.5", report)
        self.assertIn("## Top Separating Features", report)
        self.assertIn("## Same Setup", report)


# ─────────────────────────────────────────────────────────────────────────────
# Group 5: outcome_tracker unit logic
# ─────────────────────────────────────────────────────────────────────────────

class TestOutcomeClassification(unittest.TestCase):

    def _classify(self, r1=None, r3=None, r5=None, r10=None, r20=None):
        from oios.phase_f.outcome_tracker import _classify
        # _classify takes {horizon_int: value_or_None}
        return _classify({1: r1, 3: r3, 5: r5, 10: r10, 20: r20})

    def test_unknown_when_r20_missing(self):
        self.assertEqual(self._classify(r1=5.0, r3=4.0, r5=3.0, r10=2.0), "UNKNOWN")

    def test_long_trend_winner(self):
        self.assertEqual(
            self._classify(r1=5, r3=7, r5=9, r10=12, r20=8),
            "LONG_TREND_WINNER"
        )

    def test_multi_week_winner(self):
        self.assertEqual(
            self._classify(r1=5, r3=6, r5=7, r10=4, r20=3),
            "MULTI_WEEK_WINNER"
        )

    def test_short_runner(self):
        self.assertEqual(
            self._classify(r1=5, r3=4, r5=2, r10=-1, r20=0.5),
            "SHORT_RUNNER"
        )

    def test_one_day_spike(self):
        # r3 ≤ 0.5 × r1 → reversal
        self.assertEqual(
            self._classify(r1=6, r3=2, r5=1, r10=-1, r20=-2),
            "ONE_DAY_SPIKE"
        )


if __name__ == "__main__":
    unittest.main()
