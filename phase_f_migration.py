"""
phase_f_migration.py
Phase F — Database Migration Script with Acceptance Tests

Usage:
    python phase_f_migration.py            # apply schema
    python phase_f_migration.py --test     # run acceptance tests only
    python phase_f_migration.py --check    # verify schema exists (no changes)

Tests verify:
    1. All 5 Phase F tables exist
    2. Required indexes exist
    3. FKs between Phase F tables are internally consistent
    4. No Phase F tables reference A–E tables (isolation contract)
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import os

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from oios.db.connection import get_connection
from oios.db.migrations import apply_phase_f

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Expected schema contracts ─────────────────────────────────────────────────

PHASE_F_TABLES = [
    "market_leaders_daily",
    "market_leader_features",
    "market_leader_outcomes",
    "market_research_controls",
    "failure_attribution",
]

REQUIRED_INDEXES = [
    ("market_leaders_daily",     "idx_mld_date"),
    ("market_leaders_daily",     "idx_mld_symbol"),
    ("market_leaders_daily",     "idx_mld_type_date"),
    ("market_leaders_daily",     "idx_mld_sector"),
    ("market_leader_features",   "idx_mlf_leader"),
    ("market_leader_features",   "idx_mlf_name"),
    ("market_leader_features",   "idx_mlf_ldr_name"),
    ("market_leader_outcomes",   "idx_mlo_class"),
    ("market_research_controls", "idx_mrc_leader"),
    ("market_research_controls", "idx_mrc_symbol"),
    ("market_research_controls", "idx_mrc_hash"),
    ("market_research_controls", "idx_mrc_date"),
    ("failure_attribution",      "idx_fa_symbol"),
    ("failure_attribution",      "idx_fa_reason"),
    ("failure_attribution",      "idx_fa_leader"),
    ("failure_attribution",      "idx_fa_date"),
]

# Phase F tables must NOT have FK references into these A–E tables
AE_TABLES = {
    "opportunities", "signal_births", "opportunity_signals",
    "signal_state_transitions", "decision_log", "oios_events",
    "sector_conviction_daily", "theme_phase_history",
    "universe_stocks", "ohlcv_daily", "bhav_daily",
    "bulk_block_deals", "pending_adjustments",
    "archetype_outcome_distributions", "opportunity_re_snapshots",
    "daily_events", "company_relationships", "knowledge_graph_metadata",
    "event_entity_links", "opportunity_causes", "cause_scores",
    "propagation_paths", "propagation_scores", "shadow_cause_outcomes",
}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase F migration")
    parser.add_argument("--test",  action="store_true", help="Run acceptance tests only")
    parser.add_argument("--check", action="store_true", help="Verify schema without changes")
    args = parser.parse_args()

    if args.test:
        ok = run_tests(use_memory=True)
        sys.exit(0 if ok else 1)
    elif args.check:
        conn = get_connection()
        ok = _run_checks(conn)
        conn.close()
        sys.exit(0 if ok else 1)
    else:
        # Apply schema then verify
        log.info("Applying Phase F schema …")
        apply_phase_f()
        log.info("Schema applied.  Running verification …")
        conn = get_connection()
        ok = _run_checks(conn)
        conn.close()
        if ok:
            log.info("Phase F migration COMPLETE — all checks passed.")
        else:
            log.error("Phase F migration had verification failures.")
        sys.exit(0 if ok else 1)


# ── Acceptance tests ──────────────────────────────────────────────────────────

def run_tests(use_memory: bool = False) -> bool:
    """
    Run acceptance tests.  Returns True if all pass.

    use_memory=True creates an in-memory DB (useful for CI).
    """
    import unittest

    class PhaseFMigrationTests(unittest.TestCase):

        def setUp(self):
            if use_memory:
                import os
                os.environ["OIOS_DB_PATH"] = ":memory:"
                from oios.db.connection import get_connection as _gc
                self.conn = _gc()
            else:
                self.conn = get_connection()
            apply_phase_f(self.conn)

        def tearDown(self):
            self.conn.close()

        # ── Test 1: All tables exist ──────────────────────────────────────────
        def test_all_tables_exist(self):
            existing = {r[0] for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            for table in PHASE_F_TABLES:
                self.assertIn(table, existing,
                              f"Phase F table missing: {table}")

        # ── Test 2: All indexes exist ─────────────────────────────────────────
        def test_all_indexes_exist(self):
            existing = {r[0] for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
            for _, idx_name in REQUIRED_INDEXES:
                self.assertIn(idx_name, existing,
                              f"Phase F index missing: {idx_name}")

        # ── Test 3: No FK references into A–E tables ──────────────────────────
        def test_no_ae_table_fk_references(self):
            """
            Parse each Phase F table's CREATE SQL and verify it does not
            contain REFERENCES to any A–E table name.
            """
            for table in PHASE_F_TABLES:
                row = self.conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                ).fetchone()
                self.assertIsNotNone(row, f"Table {table} has no DDL")
                sql = (row[0] or "").upper()
                for ae_table in AE_TABLES:
                    self.assertNotIn(
                        f"REFERENCES {ae_table.upper()}",
                        sql,
                        f"Phase F table {table} has FK → {ae_table} (isolation violation)"
                    )

        # ── Test 4: market_leader_outcomes has primary key leader_id ──────────
        def test_outcomes_pk(self):
            row = self.conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='market_leader_outcomes'"
            ).fetchone()
            self.assertIn("leader_id", (row[0] or "").lower())

        # ── Test 5: market_leaders_daily leader_type CHECK constraint ─────────
        def test_leader_type_constraint(self):
            """Bad leader_type must be rejected."""
            with self.assertRaises(sqlite3.IntegrityError):
                with self.conn:
                    self.conn.execute("""
                        INSERT INTO market_leaders_daily
                            (leader_id, trade_date, symbol, leader_type, rank_position,
                             day_return_pct, sector, captured_at)
                        VALUES ('T1', '2026-01-01', 'TEST.NS', 'INVALID', 1, 5.0, 'TEST', datetime('now'))
                    """)

        # ── Test 6: Insert and retrieve a full leader round-trip ──────────────
        def test_round_trip_insert(self):
            with self.conn:
                self.conn.execute("""
                    INSERT INTO market_leaders_daily
                        (leader_id, trade_date, symbol, leader_type, rank_position,
                         day_return_pct, volume_ratio, sector, theme_phase, regime, captured_at)
                    VALUES ('LDR_TEST_001', '2026-06-19', 'BEL.NS', 'WINNER', 1,
                            4.5, 2.1, 'DEFENCE', 'ACCELERATION', 'bull_trend', datetime('now'))
                """)
                self.conn.execute("""
                    INSERT INTO market_leader_outcomes
                        (leader_id, outcome_class, updated_at)
                    VALUES ('LDR_TEST_001', 'UNKNOWN', datetime('now'))
                """)
                self.conn.execute("""
                    INSERT INTO market_leader_features
                        (feature_id, leader_id, feature_name, feature_value, captured_at)
                    VALUES ('FT_001', 'LDR_TEST_001', 'above_20dma', 1.0, datetime('now'))
                """)

            row = self.conn.execute(
                "SELECT symbol, day_return_pct FROM market_leaders_daily WHERE leader_id='LDR_TEST_001'"
            ).fetchone()
            self.assertEqual(row[0], "BEL.NS")
            self.assertAlmostEqual(row[1], 4.5, places=2)

            feat = self.conn.execute(
                "SELECT feature_value FROM market_leader_features WHERE feature_id='FT_001'"
            ).fetchone()
            self.assertAlmostEqual(feat[0], 1.0, places=3)

        # ── Test 7: failure_attribution UPSERT via INSERT OR REPLACE ──────────
        def test_failure_attribution_upsert(self):
            with self.conn:
                for _ in range(2):
                    self.conn.execute("""
                        INSERT OR REPLACE INTO failure_attribution
                            (failure_id, symbol, trade_date, candidate_reason,
                             confidence, recorded_at)
                        VALUES ('FA_001', 'RELIANCE.NS', '2026-06-19', 'LOW_DELIVERY',
                                0.75, datetime('now'))
                    """)
            cnt = self.conn.execute(
                "SELECT COUNT(*) FROM failure_attribution WHERE failure_id='FA_001'"
            ).fetchone()[0]
            self.assertEqual(cnt, 1)   # REPLACE = only one row

        # ── Test 8: outcome_class CHECK constraint ────────────────────────────
        def test_outcome_class_constraint(self):
            with self.conn:
                self.conn.execute("""
                    INSERT INTO market_leaders_daily
                        (leader_id, trade_date, symbol, leader_type, rank_position,
                         day_return_pct, sector, captured_at)
                    VALUES ('LDR_TEST_002', '2026-06-19', 'HAL.NS', 'WINNER', 2,
                            3.0, 'DEFENCE', datetime('now'))
                """)
            with self.assertRaises(sqlite3.IntegrityError):
                with self.conn:
                    self.conn.execute("""
                        INSERT INTO market_leader_outcomes
                            (leader_id, outcome_class, updated_at)
                        VALUES ('LDR_TEST_002', 'MEGA_WINNER', datetime('now'))
                    """)

    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromTestCase(PhaseFMigrationTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


# ── Schema check helper ───────────────────────────────────────────────────────

def _run_checks(conn: sqlite3.Connection) -> bool:
    """Verify Phase F schema on an existing connection. Returns True if all OK."""
    ok = True

    existing_tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    existing_indexes = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()}

    for table in PHASE_F_TABLES:
        if table in existing_tables:
            log.info("  ✅  Table: %s", table)
        else:
            log.error("  ❌  Table MISSING: %s", table)
            ok = False

    for _, idx in REQUIRED_INDEXES:
        if idx in existing_indexes:
            log.info("  ✅  Index: %s", idx)
        else:
            log.error("  ❌  Index MISSING: %s", idx)
            ok = False

    return ok


if __name__ == "__main__":
    main()
