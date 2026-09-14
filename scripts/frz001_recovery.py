"""
FRZ-001 RECOVERY — Option 2: Surgical ct_events Replacement
=============================================================
APPROVED CONTRACT — 2026-09-04. See /memories/repo/frz001_control_tower_corruption_audit.md
for the full forensic audit this contract is based on.

DO NOT RUN until ALL of the following are true:
  1. Indian market is fully closed for the day (no live/pending orders).
  2. `docker compose stop ai-trading-brain trading-dashboard` has already
     been run on the VPS (both containers fully stopped, not just paused).
  3. Explicit operator go-ahead for THIS specific run, on THIS date.

Intended invocation (from the VPS, inside /root/ai-trading-brain, AFTER
both containers are stopped):

    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz001_recovery.py backup
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz001_recovery.py build
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz001_recovery.py validate
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz001_recovery.py swap
    docker compose start ai-trading-brain trading-dashboard

Each phase refuses to run unless the previous phase's sentinel file
shows SUCCESS. `swap` refuses to run unless `validate` produced a
PASSED verdict. Nothing here is fabricated: gaps are preserved and
recorded, never backfilled.

Repair boundary: ct_events ONLY. ct_cycles and ct_decisions are never
read, written, dropped, or modified by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
LIVE_DB = os.path.join(DATA, "control_tower.db")
WORK_DIR = os.path.join(DATA, "frz", "_repair_work")
BACKUP_DIR_PARENT = os.path.join(DATA, "frz", "pre_repair_backups")

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS ct_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    cycle_id      TEXT,
    event_type    TEXT    NOT NULL,
    source_agent  TEXT,
    payload       TEXT
);
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


# ─────────────────────────────────────────────────────────────────────────
# Phase: backup — copy the live (still corrupt) files, untouched, as the
# first, independent safety net. Read-only w.r.t. the live file.
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

    sentinel = {
        "phase": "backup",
        "status": "SUCCESS",
        "timestamp": ts,
        "dest_dir": dest_dir,
        "files_copied": copied,
    }
    _write_sentinel(os.path.join(WORK_DIR, "backup.json"), sentinel)
    print(f"[backup] OK — {dest_dir}")
    print(json.dumps(sentinel, indent=2, default=str))


# ─────────────────────────────────────────────────────────────────────────
# Phase: build — REQUIRES the app container to already be stopped (no
# concurrent writer). Makes one race-free copy of the live files, then
# extracts ONLY ct_events into a standalone rebuilt_events.db.
# ─────────────────────────────────────────────────────────────────────────
def phase_build() -> None:
    _read_sentinel(os.path.join(WORK_DIR, "backup.json"))  # must have run first

    if not os.path.exists(LIVE_DB):
        raise SystemExit(f"Live db not found: {LIVE_DB}")

    os.makedirs(WORK_DIR, exist_ok=True)
    quiesced = os.path.join(WORK_DIR, "source_quiesced.db")
    rebuilt = os.path.join(WORK_DIR, "rebuilt_events.db")

    for f in (quiesced, quiesced + "-wal", quiesced + "-shm", rebuilt):
        if os.path.exists(f):
            os.remove(f)

    # Container must be stopped before this runs — no concurrent writer,
    # so a plain multi-file copy is now race-free (this directly avoids
    # the snapshot-race artifact found during feasibility testing).
    shutil.copy2(LIVE_DB, quiesced)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(LIVE_DB + suffix):
            shutil.copy2(LIVE_DB + suffix, quiesced + suffix)

    src_conn = sqlite3.connect(quiesced)
    src_count, src_min, src_max = src_conn.execute(
        "SELECT COUNT(*), MIN(id), MAX(id) FROM ct_events"
    ).fetchone()

    out_conn = sqlite3.connect(rebuilt)
    out_conn.execute(_CREATE_EVENTS)
    out_conn.execute("ATTACH DATABASE ? AS src", (quiesced,))
    out_conn.execute(
        f"INSERT INTO main.ct_events ({','.join(_EVENT_COLUMNS)}) "
        f"SELECT {','.join(_EVENT_COLUMNS)} FROM src.ct_events ORDER BY id"
    )
    # sqlite_sequence row is created automatically by the AUTOINCREMENT
    # insert above; make sure it reflects the true max id explicitly.
    out_conn.execute(
        "UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM ct_events) WHERE name='ct_events'"
    )
    out_conn.commit()

    out_count, out_min, out_max = out_conn.execute(
        "SELECT COUNT(*), MIN(id), MAX(id) FROM ct_events"
    ).fetchone()
    out_conn.close()
    src_conn.close()

    sentinel = {
        "phase": "build",
        "status": "SUCCESS" if (out_count, out_min, out_max) == (src_count, src_min, src_max) else "MISMATCH",
        "timestamp": _now_ts(),
        "quiesced_copy": quiesced,
        "rebuilt_events_db": rebuilt,
        "source_ct_events": {"count": src_count, "min_id": src_min, "max_id": src_max},
        "rebuilt_ct_events": {"count": out_count, "min_id": out_min, "max_id": out_max},
    }
    _write_sentinel(os.path.join(WORK_DIR, "build.json"), sentinel)
    print(json.dumps(sentinel, indent=2, default=str))
    if sentinel["status"] != "SUCCESS":
        raise SystemExit("[build] MISMATCH between source and rebuilt counts — ABORT, do not validate/swap.")
    print("[build] OK")


# ─────────────────────────────────────────────────────────────────────────
# Phase: validate — independent process, closes/reopens the rebuilt file
# fresh, and runs the full structural + content validation gate. Writes
# validate.json with a PASSED/FAILED verdict. `swap` refuses to run
# unless this says PASSED.
# ─────────────────────────────────────────────────────────────────────────
def phase_validate() -> None:
    build_sentinel = _read_sentinel(os.path.join(WORK_DIR, "build.json"))
    if build_sentinel["status"] != "SUCCESS":
        raise SystemExit("[validate] build.json did not report SUCCESS — fix build phase first.")

    quiesced = build_sentinel["quiesced_copy"]
    rebuilt = build_sentinel["rebuilt_events_db"]

    checks: dict = {}
    failures: list = []

    def record(name: str, ok: bool, detail=None) -> None:
        checks[name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    # Fresh, independent connection — not the one that built the file.
    conn = sqlite3.connect(rebuilt)

    integrity = conn.execute("PRAGMA integrity_check").fetchall()
    record("integrity_check_ok", integrity == [("ok",)], integrity)

    quick = conn.execute("PRAGMA quick_check").fetchall()
    record("quick_check_ok", quick == [("ok",)], quick)

    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    record("foreign_key_check_empty", fk == [], fk)

    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='ct_events'"
    ).fetchone()
    record("schema_matches_expected", schema is not None and "ct_events" in schema[0], schema)

    src_conn = sqlite3.connect(quiesced)
    src_count, src_min, src_max = src_conn.execute(
        "SELECT COUNT(*), MIN(id), MAX(id) FROM ct_events"
    ).fetchone()
    out_count, out_min, out_max = conn.execute(
        "SELECT COUNT(*), MIN(id), MAX(id) FROM ct_events"
    ).fetchone()
    record("row_count_matches_source", out_count == src_count, {"source": src_count, "rebuilt": out_count})
    record("min_max_id_matches_source", (out_min, out_max) == (src_min, src_max),
           {"source": (src_min, src_max), "rebuilt": (out_min, out_max)})

    dup = conn.execute(
        "SELECT id, COUNT(*) c FROM ct_events GROUP BY id HAVING c > 1"
    ).fetchall()
    record("no_duplicate_ids", dup == [], dup)

    # Known-gap verification: the gap must be PRESENT (proves no
    # fabrication) — boundaries re-derived live from the source, not
    # hardcoded, in case new rows have been added since the audit.
    gap_rows = src_conn.execute(
        "SELECT id FROM ct_events ORDER BY id"
    ).fetchall()
    gap_ids = [r[0] for r in gap_rows]
    gaps = [(a, b) for a, b in zip(gap_ids, gap_ids[1:]) if b - a > 1]
    for gap_start, gap_end in gaps:
        missing_in_rebuilt = conn.execute(
            "SELECT COUNT(*) FROM ct_events WHERE id > ? AND id < ?", (gap_start, gap_end)
        ).fetchone()[0]
        record(f"gap_preserved_{gap_start}_{gap_end}", missing_in_rebuilt == 0,
               {"gap_start": gap_start, "gap_end": gap_end, "rows_found": missing_in_rebuilt})
        boundary_present = conn.execute(
            "SELECT COUNT(*) FROM ct_events WHERE id IN (?, ?)", (gap_start, gap_end)
        ).fetchone()[0]
        record(f"gap_boundaries_present_{gap_start}_{gap_end}", boundary_present == 2,
               {"gap_start": gap_start, "gap_end": gap_end})

    # Content-hash comparison over identical, ordered row sets (excludes
    # nothing — every source row must appear identically in rebuilt).
    src_rows = src_conn.execute(
        f"SELECT {','.join(_EVENT_COLUMNS)} FROM ct_events ORDER BY id"
    ).fetchall()
    out_rows = conn.execute(
        f"SELECT {','.join(_EVENT_COLUMNS)} FROM ct_events ORDER BY id"
    ).fetchall()
    src_hash = _row_hash(src_rows)
    out_hash = _row_hash(out_rows)
    record("content_hash_matches_source", src_hash == out_hash, {"source": src_hash, "rebuilt": out_hash})

    seq_row = conn.execute(
        "SELECT seq FROM sqlite_sequence WHERE name='ct_events'"
    ).fetchone()
    max_id_now = conn.execute("SELECT MAX(id) FROM ct_events").fetchone()[0]
    record("sqlite_sequence_matches_max_id", seq_row is not None and seq_row[0] == max_id_now,
           {"seq": seq_row, "max_id": max_id_now})

    triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
    record("no_unexpected_triggers", triggers == [], triggers)

    src_conn.close()
    conn.close()

    # Close/reopen cycle: prove the file is valid fresh, not just within
    # the connection that built/checked it.
    reopened = sqlite3.connect(rebuilt)
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
        "rebuilt_events_db": rebuilt,
        "quiesced_copy": quiesced,
    }
    _write_sentinel(os.path.join(WORK_DIR, "validate.json"), sentinel)
    print(json.dumps(sentinel, indent=2, default=str))
    if verdict == "PASSED":
        print("[validate] PASSED — safe to proceed to swap.")
    else:
        print(f"[validate] FAILED — {failures}. DO NOT SWAP. Investigate before retrying.")
        raise SystemExit(1)


# ─────────────────────────────────────────────────────────────────────────
# Phase: swap — ONLY runs if validate.json says PASSED. Preserves the
# live file as a rollback copy, then performs the surgical in-place
# ct_events replacement on the (already-quiesced) live file. Runs a
# final full-database validation before declaring success.
# ─────────────────────────────────────────────────────────────────────────
def phase_swap() -> None:
    validate_sentinel = _read_sentinel(os.path.join(WORK_DIR, "validate.json"))
    if validate_sentinel["status"] != "PASSED":
        raise SystemExit("[swap] validate.json is not PASSED — refusing to swap.")

    rebuilt = validate_sentinel["rebuilt_events_db"]
    ts = _now_ts()

    # Preserve the live (corrupt) file as a rollback copy BEFORE touching it.
    superseded_dir = os.path.join(WORK_DIR, f"superseded_{ts}")
    os.makedirs(superseded_dir, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        src = LIVE_DB + suffix
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(superseded_dir, os.path.basename(LIVE_DB) + suffix))

    # Snapshot ct_cycles/ct_decisions counts BEFORE, to prove they are
    # unaffected by the surgical repair (never dropped/read/written here
    # other than this read-only count check).
    pre_conn = sqlite3.connect(LIVE_DB)
    pre_cycles = pre_conn.execute("SELECT COUNT(*) FROM ct_cycles").fetchone()[0]
    pre_decisions = pre_conn.execute("SELECT COUNT(*) FROM ct_decisions").fetchone()[0]
    pre_conn.close()

    conn = sqlite3.connect(LIVE_DB)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DROP TABLE ct_events")
        conn.execute(_CREATE_EVENTS)
        conn.execute("ATTACH DATABASE ? AS fix", (rebuilt,))
        conn.execute(
            f"INSERT INTO main.ct_events ({','.join(_EVENT_COLUMNS)}) "
            f"SELECT {','.join(_EVENT_COLUMNS)} FROM fix.ct_events ORDER BY id"
        )
        conn.execute(
            "UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM ct_events) WHERE name='ct_events'"
        )
        conn.commit()
        # `fix` auto-detaches when the connection closes below — an explicit
        # DETACH here can raise "database is locked" while the INSERT's
        # statement handle is still cached by the sqlite3 module.
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Reclaim the freed (formerly corrupted) pages now that the dropped
    # table's b-tree is gone — run only after the swap transaction commits.
    vac_conn = sqlite3.connect(LIVE_DB)
    vac_conn.execute("VACUUM")
    vac_conn.close()

    # Final full-database validation — fresh connection.
    final = sqlite3.connect(LIVE_DB)
    integrity = final.execute("PRAGMA integrity_check").fetchall()
    post_cycles = final.execute("SELECT COUNT(*) FROM ct_cycles").fetchone()[0]
    post_decisions = final.execute("SELECT COUNT(*) FROM ct_decisions").fetchone()[0]
    post_events = final.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM ct_events").fetchone()
    final.close()

    ct_cycles_untouched = (pre_cycles == post_cycles)
    ct_decisions_untouched = (pre_decisions == post_decisions)
    db_clean = integrity == [("ok",)]

    sentinel = {
        "phase": "swap",
        "status": "SUCCESS" if (db_clean and ct_cycles_untouched and ct_decisions_untouched) else "FAILED",
        "timestamp": ts,
        "superseded_backup_dir": superseded_dir,
        "post_integrity_check": integrity,
        "ct_cycles": {"before": pre_cycles, "after": post_cycles, "untouched": ct_cycles_untouched},
        "ct_decisions": {"before": pre_decisions, "after": post_decisions, "untouched": ct_decisions_untouched},
        "ct_events_after": {"count": post_events[0], "min_id": post_events[1], "max_id": post_events[2]},
    }
    _write_sentinel(os.path.join(WORK_DIR, "swap.json"), sentinel)
    print(json.dumps(sentinel, indent=2, default=str))
    if sentinel["status"] != "SUCCESS":
        print("[swap] FAILED post-swap validation — RESTORE from superseded_backup_dir immediately.")
        raise SystemExit(1)
    print("[swap] OK — restart the containers and run post-restart verification next.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["backup", "build", "validate", "swap"])
    args = parser.parse_args()

    {
        "backup": phase_backup,
        "build": phase_build,
        "validate": phase_validate,
        "swap": phase_swap,
    }[args.phase]()


if __name__ == "__main__":
    main()
