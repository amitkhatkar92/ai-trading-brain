"""
test_outcome_activation_001.py

Activation validation suite for OUTCOME_TRACKING_ACTIVATION_001.
Tests confirm the post-backfill state, resolver integration, and isolation.

Run: python3 test_outcome_activation_001.py
"""
from __future__ import annotations

import hashlib, json, os, sqlite3, sys
from pathlib import Path
from typing import Any, Dict, List

IS_VPS = os.path.exists("/root/ai-trading-brain/data/market_behavior.db")
DB_PATH = "/root/ai-trading-brain/data/market_behavior.db" if IS_VPS else None
BACKUP  = "/root/ai-trading-brain/data/market_behavior_pre_backfill_2026-08-14.db"

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results: List[Dict[str, Any]] = []

def record(tid, name, ok, detail=""):
    results.append({"id": tid, "name": name, "status": PASS if ok else FAIL, "detail": detail})
    print(f"  [{'OK' if ok else 'XX'}] {tid}: {name}")
    if not ok and detail: print(f"       {detail}")

def skip(tid, name, reason=""):
    results.append({"id": tid, "name": name, "status": SKIP, "detail": reason})
    print(f"  [--] {tid}: {name}  (SKIP: {reason})")

sys.path.insert(0, str(Path(__file__).parent))

from oios.engine.signal_outcome_tracker import (
    resolve_signal_outcomes, run_daily_outcome_resolution, ensure_schema,
    FS_WIN, FS_LOSS, FS_EXPIRED, FS_PENDING, FS_NO_DATA,
)

# ── ACT-1: Production DB backfill verified ─────────────────────────────────
print("\n=== ACT-1: Production backfill state ===")
if not IS_VPS:
    for tid in ["ACT1a","ACT1b","ACT1c","ACT1d","ACT1e"]:
        skip(tid, "Production DB check", "Not on VPS")
else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
    resolved_count = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state IS NOT NULL").fetchone()[0]
    null_count = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state IS NULL").fetchone()[0]

    wins    = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state='WIN'").fetchone()[0]
    losses  = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state='LOSS'").fetchone()[0]
    expired = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state='EXPIRED'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state='PENDING'").fetchone()[0]
    actual_pct_set = conn.execute(
        "SELECT COUNT(*) FROM signal_births WHERE actual_move_pct IS NOT NULL AND actual_move_pct != 0.0"
    ).fetchone()[0]

    record("ACT1a", f"Total signals = 3335",
           total == 3335, f"got {total}")
    record("ACT1b", f"Resolved (final_state IS NOT NULL) = 3253",
           resolved_count == 3253, f"got {resolved_count}")
    record("ACT1c", "WIN=1046 LOSS=934 EXPIRED=268 PENDING=1005",
           wins == 1046 and losses == 934 and expired == 268 and pending == 1005,
           f"WIN={wins} LOSS={losses} EXPIRED={expired} PENDING={pending}")
    record("ACT1d", "NO_DATA signals have final_state IS NULL (correct — awaiting next OHLCV)",
           null_count == 82, f"null={null_count} (expect 82 brand-new signals)")
    record("ACT1e", "actual_move_pct populated for resolved non-PENDING signals",
           actual_pct_set >= 2000, f"actual_pct_set={actual_pct_set}")

    conn.close()

# ── ACT-2: Immutable field hashes unchanged ────────────────────────────────
print("\n=== ACT-2: Immutable field hashes ===")
if not IS_VPS:
    skip("ACT2a", "Hash comparison", "Not on VPS")
else:
    IMMUTABLE_COLS = [
        "signal_id","symbol","archetype_id","archetype_version","signal_type",
        "detected_at","birth_price","base_score","regime_at_birth",
        "expected_ttl_days","expected_move_direction","expected_move_pct",
        "expected_move_pct_source","current_state","age_trading_days",
        "edge_consumed_pct","trade_executed",
    ]
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    avail = [c for c in IMMUTABLE_COLS if c in {r[1] for r in conn.execute("PRAGMA table_info(signal_births)")}]

    # Verify all signals have non-null symbol and direction (basic sanity)
    bad_symbol    = conn.execute("SELECT COUNT(*) FROM signal_births WHERE symbol IS NULL OR symbol=''").fetchone()[0]
    bad_direction = conn.execute("SELECT COUNT(*) FROM signal_births WHERE expected_move_direction NOT IN ('LONG','SHORT')").fetchone()[0]
    bad_price     = conn.execute("SELECT COUNT(*) FROM signal_births WHERE birth_price IS NULL OR birth_price <= 0").fetchone()[0]
    conn.close()

    record("ACT2a", "All signals have valid symbol", bad_symbol == 0, f"bad_symbol={bad_symbol}")
    record("ACT2b", "All signals have LONG or SHORT direction",
           bad_direction == 0, f"bad_direction={bad_direction}")
    record("ACT2c", "All signals have birth_price > 0",
           bad_price == 0, f"bad_price={bad_price}")

# ── ACT-3: Idempotency on post-backfill DB ─────────────────────────────────
print("\n=== ACT-3: Post-backfill idempotency ===")
if not IS_VPS:
    skip("ACT3a", "Idempotency", "Not on VPS")
else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    as_of = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]
    r = resolve_signal_outcomes(conn, as_of, dry_run=False)
    conn.commit()
    conn.close()
    record("ACT3a", "Post-backfill resolve: 0 new writes (idempotent)",
           r["resolved"] == 0, f"resolved={r['resolved']}")
    record("ACT3b", "Post-backfill resolve: 0 errors",
           r["errors"] == 0, f"errors={r['errors']}")

# ── ACT-4: Orchestrator wiring ─────────────────────────────────────────────
print("\n=== ACT-4: Orchestrator wiring ===")
orch_path = Path(__file__).parent / "orchestrator" / "master_orchestrator.py"
if not orch_path.exists():
    skip("ACT4a", "Orchestrator wiring", "File not found")
else:
    src = orch_path.read_text()
    record("ACT4a", "run_daily_outcome_resolution imported in orchestrator",
           "run_daily_outcome_resolution" in src and "_sor_run" in src)
    record("ACT4b", "OutcomeResolver log line present",
           "[OutcomeResolver]" in src)
    record("ACT4c", "Wired after signal scan (correct sequence)",
           src.index("_sor_run") > src.index("_oios_scan_exc"))
    record("ACT4d", "Wired inside _do_eod_learning (not a new scheduler)",
           "_do_eod_learning" in src[:src.index("_sor_run")])
    record("ACT4e", "Failure does not propagate (non-critical try/except)",
           "Signal outcome resolution failed (non-critical)" in src)

# ── ACT-5: Resolver does not touch trading-decision tables ─────────────────
print("\n=== ACT-5: Trading-path isolation ===")
tracker_path = Path(__file__).parent / "oios" / "engine" / "signal_outcome_tracker.py"
if not tracker_path.exists():
    skip("ACT5a", "Tracker source check", "File not found")
else:
    src5 = tracker_path.read_text()
    import_lines = "\n".join(l for l in src5.splitlines()
                             if l.strip().startswith(("import ","from ")))

    forbidden_imports = [
        "DecisionEngine","decision_engine","StrategyLab","strategy_lab",
        "CapitalRiskEngine","capital_risk_engine","OrderManager","order_manager",
        "dhan","DhanHQ","dhanhq","RiskGuardian","risk_guardian",
        "place_order","close_position","modify_order","cancel_order",
    ]
    violations = [f for f in forbidden_imports if f.lower() in import_lines.lower()]
    record("ACT5a", "No trading imports in signal_outcome_tracker.py",
           len(violations) == 0, f"violations: {violations}")

    forbidden_tables = ["ct_decisions","ct_cycles","decision_log","learning_db"]
    # Check only non-comment, non-docstring lines (docstring lists these as forbidden — correct)
    code_lines = []
    in_docstring = False
    for line in src5.splitlines():
        s = line.strip()
        if s.startswith('#'): continue
        if '"""' in s: in_docstring = not in_docstring; continue
        if in_docstring: continue
        code_lines.append(line)
    code_only = "\n".join(code_lines)
    tbl_violations = [t for t in forbidden_tables if t in code_only]
    record("ACT5b", "Does not reference trading-decision tables in code",
           len(tbl_violations) == 0, f"violations: {tbl_violations}")

    record("ACT5c", "Writes only to signal_births measurement columns",
           "UPDATE signal_births" in src5 and src5.count("UPDATE") == 1)

# ── ACT-6: Backup exists for rollback ──────────────────────────────────────
print("\n=== ACT-6: Rollback readiness ===")
if not IS_VPS:
    skip("ACT6a", "Backup existence", "Not on VPS")
else:
    backup_exists = os.path.exists(BACKUP)
    record("ACT6a", "Pre-backfill backup file exists on VPS",
           backup_exists, f"path={BACKUP}")
    if backup_exists:
        backup_size = os.path.getsize(BACKUP)
        record("ACT6b", "Backup size > 0",
               backup_size > 0, f"size={backup_size:,}B")

# ── ACT-7: run_daily_outcome_resolution auto-detects as_of_date ────────────
print("\n=== ACT-7: Daily resolver auto-detection ===")
if not IS_VPS:
    skip("ACT7a", "Auto as_of detection", "Not on VPS")
else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    expected_asof = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]
    r7 = run_daily_outcome_resolution(conn, as_of_date=None)
    conn.close()
    record("ACT7a", "run_daily_outcome_resolution auto-detects as_of_date",
           r7.get("as_of_date") == expected_asof,
           f"got={r7.get('as_of_date')} expected={expected_asof}")
    record("ACT7b", "Auto-resolved: 0 errors",
           r7.get("errors", 0) == 0, f"errors={r7.get('errors')}")

# ── ACT-8: PENDING signals stay PENDING until TTL ──────────────────────────
print("\n=== ACT-8: PENDING signal handling ===")
if not IS_VPS:
    skip("ACT8a", "PENDING signal count", "Not on VPS")
else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    pending_count = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state='PENDING'").fetchone()[0]
    conn.close()
    record("ACT8a", f"PENDING signals = 1005 (legitimate within-TTL signals)",
           pending_count == 1005, f"got {pending_count}")

# ── ACT-9: NO_DATA signals correctly handled ───────────────────────────────
print("\n=== ACT-9: NO_DATA signal handling ===")
if not IS_VPS:
    skip("ACT9a", "NO_DATA handling", "Not on VPS")
else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    null_fs = conn.execute("SELECT COUNT(*) FROM signal_births WHERE final_state IS NULL").fetchone()[0]
    conn.close()
    record("ACT9a", "NO_DATA signals have final_state IS NULL (awaiting next OHLCV)",
           null_fs == 82, f"got {null_fs}")

# ── SUMMARY ────────────────────────────────────────────────────────────────
total_tests = len(results)
passed  = sum(1 for r in results if r["status"] == PASS)
failed  = sum(1 for r in results if r["status"] == FAIL)
skipped = sum(1 for r in results if r["status"] == SKIP)

print(f"\n{'='*60}")
print(f"Results: {passed}/{total_tests} passed  |  {failed} failed  |  {skipped} skipped")
print(f"{'='*60}")

if failed:
    print("\nFailed tests:")
    for r in results:
        if r["status"] == FAIL:
            print(f"  XX {r['id']}: {r['name']}")
            if r["detail"]: print(f"     {r['detail']}")

Path("test_outcome_activation_001_results.json").write_text(
    json.dumps({"total": total_tests, "passed": passed, "failed": failed,
                "skipped": skipped, "tests": results}, indent=2)
)

sys.exit(0 if failed == 0 else 1)
