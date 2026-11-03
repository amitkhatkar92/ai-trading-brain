"""
Tests for DTA-UNIVERSE-FRESHNESS-001 refinement items 2-4:
  predictive_gap/universe_refresh_engine.py

  - run_bounded_broad_refresh(): rotating batch, once/day guard, cursor
    persistence/wraparound, fail-open
  - reconcile_universe_stocks(): activates file members, deactivates
    stale/legacy rows (never deletes), inserts missing rows with required
    NOT NULL columns populated, fail-open
"""
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from predictive_gap import universe_refresh_engine as ure


def _make_universe_stocks_db(tmp_path, rows):
    """rows: list of (symbol, company_name, sector, is_active)"""
    db_path = tmp_path / "test_market_behavior.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE universe_stocks ("
        "symbol TEXT NOT NULL PRIMARY KEY, company_name TEXT NOT NULL, "
        "sector TEXT NOT NULL, sector_purity_score REAL NOT NULL DEFAULT 1.0, "
        "is_active INTEGER NOT NULL DEFAULT 1, added_date TEXT NOT NULL, "
        "removed_date TEXT, removal_reason TEXT)"
    )
    conn.executemany(
        "INSERT INTO universe_stocks (symbol, company_name, sector, is_active, added_date) "
        "VALUES (?, ?, ?, ?, '2026-01-01')",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


class TestReconcileUniverseStocks(unittest.TestCase):

    def _run(self, tmp_path, db_rows, file_entries):
        db_path = _make_universe_stocks_db(tmp_path, db_rows)
        universe_file = tmp_path / "nifty500_universe.json"
        universe_file.write_text(json.dumps(file_entries), encoding="utf-8")

        # reconcile_universe_stocks() closes the connection it's given (same
        # convention as every other get_connection() consumer in this repo),
        # so verification re-opens a fresh connection against the same file.
        with patch("oios.db.connection.get_connection",
                   side_effect=lambda: sqlite3.connect(str(db_path))):
            result = ure.reconcile_universe_stocks(universe_json_path=universe_file)
        return result, sqlite3.connect(str(db_path))

    def test_t01_deactivates_row_not_in_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            result, conn = self._run(
                tmp_path,
                db_rows=[("GOLDBEES.NS", "Gold BeES", "UNKNOWN", 1)],
                file_entries=[{"symbol": "RELIANCE", "sector": "Energy"}],
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["deactivated"], 1)
            row = conn.execute(
                "SELECT is_active, removal_reason FROM universe_stocks WHERE symbol='GOLDBEES.NS'"
            ).fetchone()
            self.assertEqual(row[0], 0)
            self.assertEqual(row[1], "UNIVERSE_RECONCILE_NOT_IN_LATEST_FILE")
            conn.close()

    def test_t02_inserts_new_row_with_required_columns(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            result, conn = self._run(
                tmp_path,
                db_rows=[],
                file_entries=[{"symbol": "NEWCO", "sector": "IT"}],
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["activated"], 1)
            row = conn.execute(
                "SELECT company_name, sector, is_active FROM universe_stocks WHERE symbol='NEWCO.NS'"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], "IT")
            self.assertEqual(row[2], 1)
            conn.close()

    def test_t03_reactivates_previously_deactivated_row(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            result, conn = self._run(
                tmp_path,
                db_rows=[("OLDCO.NS", "Old Co", "IT", 0)],
                file_entries=[{"symbol": "OLDCO", "sector": "IT"}],
            )
            self.assertEqual(result["activated"], 1)
            row = conn.execute(
                "SELECT is_active FROM universe_stocks WHERE symbol='OLDCO.NS'"
            ).fetchone()
            self.assertEqual(row[0], 1)
            conn.close()

    def test_t04_already_active_and_in_file_is_untouched(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            result, conn = self._run(
                tmp_path,
                db_rows=[("SAME.NS", "Same Co", "IT", 1)],
                file_entries=[{"symbol": "SAME", "sector": "IT"}],
            )
            self.assertEqual(result["activated"], 0)
            self.assertEqual(result["deactivated"], 0)
            conn.close()

    def test_t05_missing_universe_file_fails_open(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            result = ure.reconcile_universe_stocks(universe_json_path=tmp_path / "missing.json")
            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "universe_json_missing")

    def test_t06_never_deletes_a_row(self):
        """Deactivation only flips is_active -- the row must still exist."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            result, conn = self._run(
                tmp_path,
                db_rows=[("REMOVED.NS", "Removed Co", "IT", 1)],
                file_entries=[{"symbol": "OTHER", "sector": "IT"}],
            )
            count = conn.execute(
                "SELECT COUNT(*) FROM universe_stocks WHERE symbol='REMOVED.NS'"
            ).fetchone()[0]
            self.assertEqual(count, 1)
            conn.close()


class TestBoundedBroadRefresh(unittest.TestCase):

    def test_t07_skips_if_already_ran_today(self):
        with patch.object(ure, "_load_state", return_value={"last_broad_refresh_date": "2026-01-01"}):
            result = ure.run_bounded_broad_refresh(trading_date="2026-01-01")
            self.assertTrue(result["ok"])
            self.assertEqual(result.get("skipped"), "already_ran_today")

    def test_t08_fails_open_on_exception(self):
        with patch.object(ure, "_load_state", return_value={}), \
             patch("predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
                   side_effect=RuntimeError("boom")):
            result = ure.run_bounded_broad_refresh(trading_date="2026-01-02")
            self.assertFalse(result["ok"])

    def test_t09_rotates_cursor_and_wraps_around(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("A.NS",)]  # only A active
        fake_result = MagicMock(symbols_ok=["B.NS"], symbols_failed=[], rows_inserted=5)

        with patch.object(ure, "_load_state", return_value={"cursor": 0}), \
             patch.object(ure, "_save_state") as mock_save, \
             patch("predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
                   return_value=["A", "B", "C"]), \
             patch("oios.db.connection.get_connection", return_value=mock_conn), \
             patch("oios.data.ohlcv_fetcher.run_daily_fetch", return_value=fake_result):
            result = ure.run_bounded_broad_refresh(batch_size=2, trading_date="2026-01-03")

        self.assertTrue(result["ok"])
        self.assertEqual(result["excluded_pool_size"], 2)  # B, C excluded (A is active)
        saved_state = mock_save.call_args[0][0]
        self.assertEqual(saved_state["cursor"], 0)  # wraps back to 0 after a 2-size batch of a 2-pool

    def test_t10_nothing_excluded_is_a_safe_noop(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("A.NS",), ("B.NS",)]
        with patch.object(ure, "_load_state", return_value={}), \
             patch("predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
                   return_value=["A", "B"]), \
             patch("oios.db.connection.get_connection", return_value=mock_conn):
            result = ure.run_bounded_broad_refresh(trading_date="2026-01-04")
        self.assertTrue(result["ok"])
        self.assertEqual(result["attempted"], 0)


class TestCombinedCycle(unittest.TestCase):

    def test_t11_runs_both_steps_in_order(self):
        calls = []
        with patch.object(ure, "run_bounded_broad_refresh",
                          side_effect=lambda **kw: calls.append("refresh") or {"ok": True}), \
             patch.object(ure, "reconcile_universe_stocks",
                          side_effect=lambda **kw: calls.append("reconcile") or {"ok": True}):
            result = ure.run_daily_universe_refresh_cycle()
        self.assertEqual(calls, ["refresh", "reconcile"])
        self.assertIn("broad_refresh", result)
        self.assertIn("reconciliation", result)


class TestHistoryPersistence(unittest.TestCase):

    def test_t12_record_and_read_back(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            history_path = Path(td) / "universe_refresh_history.jsonl"
            with patch.object(ure, "_HISTORY_PATH", history_path):
                ure.record_refresh_cycle_result("2026-11-03", {"broad_refresh": {"ok": True}})
                ure.record_refresh_cycle_result("2026-11-04", {"broad_refresh": {"ok": True}})
                records = ure.get_refresh_cycle_history(n=10)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["trading_date"], "2026-11-03")
        self.assertEqual(records[1]["trading_date"], "2026-11-04")

    def test_t13_read_missing_file_returns_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            history_path = Path(td) / "does_not_exist.jsonl"
            with patch.object(ure, "_HISTORY_PATH", history_path):
                records = ure.get_refresh_cycle_history()
        self.assertEqual(records, [])

    def test_t14_record_never_raises_on_write_failure(self):
        with patch.object(ure, "_HISTORY_PATH", Path("/nonexistent_root/x/y.jsonl")):
            ure.record_refresh_cycle_result("2026-11-03", {"ok": True})  # must not raise

    def test_t15_daily_cycle_calls_record(self):
        with patch.object(ure, "run_bounded_broad_refresh", return_value={"ok": True}), \
             patch.object(ure, "reconcile_universe_stocks", return_value={"ok": True}), \
             patch.object(ure, "record_refresh_cycle_result") as mock_record:
            ure.run_daily_universe_refresh_cycle()
        mock_record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
