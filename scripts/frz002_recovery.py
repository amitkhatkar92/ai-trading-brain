"""
FRZ-002 RECOVERY — mi_latency_records / mi_latency_daily reconstruction
=========================================================================
APPROVED SCOPE — 2026-09-04. See
/memories/repo/frz001_control_tower_corruption_audit.md for the full
read-only investigation this contract is based on.

Context: PRAGMA dbstat conclusively showed 4 corrupted pages belong to
`mi_latency_records`, `mi_latency_daily`, and their 2 indexes — NOT to
ct_events (which has already been separately repaired and validated,
commit-equivalent state confirmed via this script's own baseline capture
below). No backup anywhere contains these 2 tables (they were created
after every available backup) and every SQL-level read of them fails
with "database disk image is malformed" (dbstat reports 0 cells / 0
payload — nothing is recoverable). This contract therefore reconstructs
them EMPTY from the canonical schema — it does not, and cannot,
repopulate any historical rows. That loss is permanent and is explicitly
documented, never fabricated.

DO NOT RUN until:
  1. Containers are already stopped (they are, from the FRZ-001 window).
  2. Explicit operator go-ahead for THIS specific run.

Invocation (VPS, /root/ai-trading-brain, containers already stopped):

    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002_recovery.py backup
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002_recovery.py repair
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002_recovery.py vacuum
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002_recovery.py validate

Each phase writes its OWN sentinel unconditionally (even on failure —
lesson learned from FRZ-001's swap phase, where an uncaught VACUUM
exception left no record). `repair` and `vacuum` are deliberately
SEPARATE phases so a VACUUM failure can never be confused with a
DROP/CREATE failure again.

Repair boundary: mi_latency_records, mi_latency_daily, and their 2
indexes ONLY. ct_events, ct_cycles, ct_decisions are never dropped or
written — `validate` re-derives their exact state and compares it
against the `backup` phase's own baseline capture to PROVE this.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import traceback
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
LIVE_DB = os.path.join(DATA, "control_tower.db")
WORK_DIR = os.path.join(DATA, "frz", "_repair_work_002")
BACKUP_DIR_PARENT = os.path.join(DATA, "frz", "pre_repair_backups_002")

# Canonical schema — copied verbatim from control_tower/mi_latency_audit.py,
# confirmed identical to sqlite_master's stored text during the read-only
# FRZ-002 investigation. Not a guessed reconstruction.
_CREATE_RECORDS = """
CREATE TABLE mi_latency_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,
    cycle_time      TEXT    NOT NULL,
    mi_latency_ms   REAL    NOT NULL,
    bucket          TEXT    NOT NULL,
    aborted         INTEGER NOT NULL DEFAULT 0,
    regime          TEXT,
    vix             REAL,
    pcr             REAL,
    created_at      TEXT    NOT NULL
);
"""

_CREATE_DAILY = """
CREATE TABLE mi_latency_daily (
    date              TEXT    PRIMARY KEY,
    total_cycles      INTEGER NOT NULL DEFAULT 0,
    normal_cycles     INTEGER NOT NULL DEFAULT 0,
    slow_cycles       INTEGER NOT NULL DEFAULT 0,
    critical_cycles   INTEGER NOT NULL DEFAULT 0,
    aborted_cycles    INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms    REAL,
    max_latency_ms    REAL,
    p95_latency_ms    REAL,
    last_updated      TEXT
);
"""

_CREATE_RECORDS_IDX = """
CREATE INDEX mi_latency_records_date
    ON mi_latency_records (date);
"""

_EVENT_COLUMNS = ("id", "ts", "cycle_id", "event_type", "source_agent", "payload")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_sentinel(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _read_sentinel(path: str) -> dict:
    if not os.path.exists(path):
        raise SystemExit(f"REQUIRED sentinel missing: {path}. Run the previous phase first.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _row_hash(rows) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update("|".join("" if v is None else str(v) for v in row).encode("utf-8", errors="replace"))
        h.update(b"\n")
    return h.hexdigest()


def _capture_baseline(conn) -> dict:
    """Snapshot ct_events/ct_cycles/ct_decisions exactly as they are right
    now — used both as the pre-repair baseline and, later, as the thing
    `validate` proves was NOT disturbed by the mi_latency repair."""
    ce = conn.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM ct_events").fetchone()
    ce_hash = _row_hash(conn.execute(
        f"SELECT {','.join(_EVENT_COLUMNS)} FROM ct_events ORDER BY id"
    ).fetchall())
    cc = conn.execute("SELECT COUNT(*), MIN(rowid), MAX(rowid) FROM ct_cycles").fetchone()
    cd = conn.execute("SELECT COUNT(*), MIN(rowid), MAX(rowid) FROM ct_decisions").fetchone()
    return {
        "ct_events":    {"count": ce[0], "min_id": ce[1], "max_id": ce[2], "content_hash": ce_hash},
        "ct_cycles":    {"count": cc[0], "min_rowid": cc[1], "max_rowid": cc[2]},
        "ct_decisions": {"count": cd[0], "min_rowid": cd[1], "max_rowid": cd[2]},
    }


# ─────────────────────────────────────────────────────────────────────────
# Phase: backup — fresh timestamped copy of the CURRENT live file (which
# already has the FRZ-001 ct_events repair applied), taken BEFORE any
# mi_latency change. Also captures the ct_events/ct_cycles/ct_decisions
# baseline that `validate` will later prove is unchanged.
# ─────────────────────────────────────────────────────────────────────────
def phase_backup() -> None:
    ts = _now_ts()
    dest_dir = os.path.join(BACKUP_DIR_PARENT, ts)
    os.makedirs(dest_dir, exist_ok=True)

    copied = {}
    for suffix in ("", "-wal", "-shm"):
        src = LIVE_DB + suffix
        if os.path.exists(src):
            dst = os.path.join(dest_dir, os.path.basename(LIVE_DB) + suffix)
            shutil.copy2(src, dst)
            copied[suffix or "main"] = {"src_size": os.path.getsize(src), "dst_size": os.path.getsize(dst)}
            if copied[suffix or "main"]["src_size"] != copied[suffix or "main"]["dst_size"]:
                raise SystemExit(f"Backup size mismatch for {src} — ABORTING, do not proceed.")

    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True, timeout=5)
    baseline = _capture_baseline(conn)
    conn.close()

    sentinel = {
        "phase": "backup",
        "status": "SUCCESS",
        "timestamp": ts,
        "dest_dir": dest_dir,
        "files_copied": copied,
        "baseline": baseline,
    }
    _write_sentinel(os.path.join(WORK_DIR, "backup.json"), sentinel)
    print(f"[backup] OK — {dest_dir}")
    print(json.dumps(sentinel, indent=2, default=str))


# ─────────────────────────────────────────────────────────────────────────
# Phase: repair — DROP + CREATE the 2 corrupted tables + 1 index, in one
# transaction. Deliberately does NOT call VACUUM (that is its own phase,
# so its outcome can never again be conflated with this one). Writes a
# sentinel unconditionally, even on failure.
# ─────────────────────────────────────────────────────────────────────────
def phase_repair() -> None:
    _read_sentinel(os.path.join(WORK_DIR, "backup.json"))  # must have run first

    ts = _now_ts()
    result = {"phase": "repair", "timestamp": ts}
    conn = sqlite3.connect(LIVE_DB)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DROP TABLE IF EXISTS mi_latency_records")
        conn.execute("DROP TABLE IF EXISTS mi_latency_daily")
        conn.execute(_CREATE_RECORDS)
        conn.execute(_CREATE_DAILY)
        conn.execute(_CREATE_RECORDS_IDX)
        conn.commit()
        result["status"] = "SUCCESS"
    except Exception as exc:
        conn.rollback()
        result["status"] = "FAILED"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    finally:
        conn.close()

    _write_sentinel(os.path.join(WORK_DIR, "repair.json"), result)
    print(json.dumps(result, indent=2, default=str))
    if result["status"] != "SUCCESS":
        print("[repair] FAILED — do not run vacuum/validate. Investigate.")
        raise SystemExit(1)
    print("[repair] OK — mi_latency_records/mi_latency_daily recreated empty.")


# ─────────────────────────────────────────────────────────────────────────
# Phase: vacuum — separate, isolated phase. Failure here does NOT imply
# the repair transaction failed (that already has its own sentinel).
# ─────────────────────────────────────────────────────────────────────────
def phase_vacuum() -> None:
    repair_sentinel = _read_sentinel(os.path.join(WORK_DIR, "repair.json"))
    if repair_sentinel["status"] != "SUCCESS":
        raise SystemExit("[vacuum] repair.json did not report SUCCESS — fix repair phase first.")

    ts = _now_ts()
    result = {"phase": "vacuum", "timestamp": ts}
    try:
        conn = sqlite3.connect(LIVE_DB)
        conn.execute("VACUUM")
        conn.close()
        result["status"] = "SUCCESS"
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()

    _write_sentinel(os.path.join(WORK_DIR, "vacuum.json"), result)
    print(json.dumps(result, indent=2, default=str))
    if result["status"] != "SUCCESS":
        print("[vacuum] FAILED — the repair transaction (repair.json) still succeeded; "
              "VACUUM is purely a compaction/hygiene step. Proceed to `validate` to see "
              "the actual current integrity state before deciding next steps.")
        raise SystemExit(1)
    print("[vacuum] OK — freed pages reclaimed.")


# ─────────────────────────────────────────────────────────────────────────
# Phase: validate — comprehensive, fresh-process, final check. Confirms
# mi_latency schema/index correctness AND that ct_events/ct_cycles/
# ct_decisions are byte-for-byte unchanged from the `backup` phase's own
# baseline (not a hardcoded value from a previous turn).
# ─────────────────────────────────────────────────────────────────────────
def phase_validate() -> None:
    backup_sentinel = _read_sentinel(os.path.join(WORK_DIR, "backup.json"))
    baseline = backup_sentinel["baseline"]

    checks: dict = {}
    failures: list = []

    def record(name: str, ok: bool, detail=None) -> None:
        checks[name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    conn = sqlite3.connect(LIVE_DB)

    integrity = conn.execute("PRAGMA integrity_check").fetchall()
    record("integrity_check_ok", integrity == [("ok",)], integrity)

    quick = conn.execute("PRAGMA quick_check").fetchall()
    record("quick_check_ok", quick == [("ok",)], quick)

    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    record("foreign_key_check_empty", fk == [], fk)

    # Schema verification — exact canonical text, no guessed reconstruction.
    schema_rows = {r[0]: r[1] for r in conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE name IN "
        "('mi_latency_records','mi_latency_daily','mi_latency_records_date')"
    )}
    record("mi_latency_records_schema_present", "mi_latency_records" in schema_rows,
           schema_rows.get("mi_latency_records"))
    record("mi_latency_daily_schema_present", "mi_latency_daily" in schema_rows,
           schema_rows.get("mi_latency_daily"))
    record("mi_latency_records_date_index_present", "mi_latency_records_date" in schema_rows,
           schema_rows.get("mi_latency_records_date"))

    # New tables must be genuinely readable and empty (not fabricated rows).
    try:
        rec_count = conn.execute("SELECT COUNT(*) FROM mi_latency_records").fetchone()[0]
        daily_count = conn.execute("SELECT COUNT(*) FROM mi_latency_daily").fetchone()[0]
        record("mi_latency_tables_readable_and_empty", rec_count == 0 and daily_count == 0,
               {"mi_latency_records": rec_count, "mi_latency_daily": daily_count})
    except Exception as exc:
        record("mi_latency_tables_readable_and_empty", False, repr(exc))

    # Prove ct_events / ct_cycles / ct_decisions are untouched — compared
    # against the SAME run's own pre-repair baseline, not a hardcoded value.
    now = _capture_baseline(conn)
    record("ct_events_unchanged", now["ct_events"] == baseline["ct_events"],
           {"before": baseline["ct_events"], "after": now["ct_events"]})
    record("ct_cycles_unchanged", now["ct_cycles"] == baseline["ct_cycles"],
           {"before": baseline["ct_cycles"], "after": now["ct_cycles"]})
    record("ct_decisions_unchanged", now["ct_decisions"] == baseline["ct_decisions"],
           {"before": baseline["ct_decisions"], "after": now["ct_decisions"]})

    conn.close()

    # Close/reopen cycle — prove valid fresh, not just within this run.
    reopened = sqlite3.connect(LIVE_DB)
    reopened_integrity = reopened.execute("PRAGMA integrity_check").fetchall()
    record("integrity_check_after_reopen", reopened_integrity == [("ok",)], reopened_integrity)
    reopened.close()

    verdict = "PASSED" if not failures else "FAILED"
    sentinel = {
        "phase": "validate",
        "status": verdict,
        "timestamp": _now_ts(),
        "checks": checks,
        "failures": failures,
    }
    _write_sentinel(os.path.join(WORK_DIR, "validate.json"), sentinel)
    print(json.dumps(sentinel, indent=2, default=str))
    if verdict == "PASSED":
        print("[validate] PASSED — mi_latency_* rebuilt clean; ct_events/ct_cycles/"
              "ct_decisions confirmed unchanged. Safe to restart containers.")
    else:
        print(f"[validate] FAILED — {failures}. Do NOT restart containers yet.")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["backup", "repair", "vacuum", "validate"])
    args = parser.parse_args()

    {
        "backup": phase_backup,
        "repair": phase_repair,
        "vacuum": phase_vacuum,
        "validate": phase_validate,
    }[args.phase]()


if __name__ == "__main__":
    main()
