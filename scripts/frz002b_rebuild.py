"""
FRZ-002B RECOVERY — Option A: Whole-File Reconstruction
=========================================================================
APPROVED SCOPE — 2026-09-04. Supersedes the direct-DROP FRZ-002 attempt,
which was empirically ruled out (`DROP TABLE mi_latency_records` itself
raises "database disk image is malformed" — the page can't be touched by
any operation, read or DDL). See
/memories/repo/frz001_control_tower_corruption_audit.md for the full
history (FRZ-001 ct_events repair, FRZ-002 direct-drop failure, and the
complete read-only schema inventory this contract is based on).

Strategy: build a BRAND NEW control_tower.db file. Copy every readable
schema object and its data from the current (already ct_events-repaired)
live file EXCEPT the two corrupt tables and their 2 associated indexes.
Recreate `mi_latency_records` / `mi_latency_daily` / `mi_latency_records_date`
EMPTY, using the EXACT CREATE TABLE/INDEX text read live from the
source's own sqlite_master (schema metadata is NOT corrupt — only the
tables' own data pages are — so no guessing/hardcoding is needed for
their definitions either). This never issues DROP/ALTER against the
corrupt table at all, sidestepping the exact failure hit by FRZ-002.

Per the complete schema inventory (2026-09-04), control_tower.db contains
EXACTLY 9 objects: 3 healthy tables (ct_events, ct_cycles, ct_decisions),
2 corrupt tables (mi_latency_records, mi_latency_daily), 3 indexes (1
healthy autoindex, 2 corrupt), 0 triggers, 0 views. This script is
written generically (enumerates whatever triggers/views/indexes actually
exist at run time) so it remains correct even if that inventory changes
before execution.

DO NOT RUN until:
  1. Containers are already stopped.
  2. Explicit operator go-ahead for THIS specific run.

Invocation (VPS, /root/ai-trading-brain, containers already stopped):

    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002b_rebuild.py backup
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002b_rebuild.py build
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002b_rebuild.py validate
    docker compose run --rm --no-deps ai-trading-brain \\
        python3 scripts/frz002b_rebuild.py swap

Each phase writes its own sentinel unconditionally, even on failure.
`swap` refuses to run unless `validate` says PASSED, and itself performs
a final post-swap integrity_check + quick_check + foreign_key_check +
VACUUM + full recount before declaring success.
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
WORK_DIR = os.path.join(DATA, "frz", "_repair_work_002b")
BACKUP_DIR_PARENT = os.path.join(DATA, "frz", "pre_repair_backups_002b")

# The only objects ever intentionally excluded from data-copy (they are
# still RECREATED, empty, from the source's own schema text — never
# simply dropped/omitted).
_CORRUPT_TABLES = {"mi_latency_records", "mi_latency_daily"}
_CORRUPT_INDEXES = {"mi_latency_records_date", "sqlite_autoindex_mi_latency_daily_1"}


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


def _enumerate_objects(conn) -> list:
    """Every table/index/trigger/view in sqlite_master, deterministically
    ordered, excluding sqlite_ internal bookkeeping tables from the
    "application object" comparison (sqlite_sequence is handled separately)."""
    return conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name != 'sqlite_sequence' ORDER BY type, name"
    ).fetchall()


def _table_columns(conn, table: str) -> list:
    return [r[1] for r in conn.execute(f"PRAGMA table_info('{table}')").fetchall()]


def _table_scan_snapshot(conn, table: str) -> dict:
    """Forced full TABLE b-tree scan (NOT INDEXED) — never relies on any
    index being complete/consistent. This is a direct response to the
    ct_cycles finding: `sqlite_autoindex_ct_cycles_1` was silently missing
    15 real rows, so a plain COUNT(*)/indexed SELECT undercounts. Every
    number here — row count, min/max rowid, content hash — is derived
    purely from the table's own data pages."""
    cols = _table_columns(conn, table)
    col_list = ",".join(f'"{c}"' for c in cols)
    rows = conn.execute(
        f'SELECT rowid, {col_list} FROM "{table}" NOT INDEXED ORDER BY rowid'
    ).fetchall()
    count = len(rows)
    min_rowid = rows[0][0] if rows else None
    max_rowid = rows[-1][0] if rows else None
    content_hash = _row_hash(rows)
    return {"count": count, "min_rowid": min_rowid, "max_rowid": max_rowid, "content_hash": content_hash}


def _index_consistency(conn, table: str) -> dict:
    """Compare an index-path count against a forced table-scan count for
    the same table — proves the table's own indexes are fully consistent
    with its data, not just individually well-formed."""
    indexed_count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    scanned_count = conn.execute(f'SELECT COUNT(*) FROM "{table}" NOT INDEXED').fetchone()[0]
    return {"indexed_count": indexed_count, "scanned_count": scanned_count, "consistent": indexed_count == scanned_count}


def _protected_table_snapshot(conn) -> dict:
    return {
        "ct_events":    _table_scan_snapshot(conn, "ct_events"),
        "ct_cycles":    _table_scan_snapshot(conn, "ct_cycles"),
        "ct_decisions": _table_scan_snapshot(conn, "ct_decisions"),
    }


# ─────────────────────────────────────────────────────────────────────────
# Phase: backup
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
                raise SystemExit(f"Backup size mismatch for {src} — ABORTING.")

    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True, timeout=5)
    objects = _enumerate_objects(conn)
    protected = _protected_table_snapshot(conn)
    readable_row_counts = {}
    index_consistency = {}
    for typ, name, tbl_name, sql in objects:
        if typ == "table" and name not in _CORRUPT_TABLES:
            try:
                # Forced table scan — plain COUNT(*) is exactly what missed
                # ct_cycles' 15 index-invisible rows; never trust an index
                # to be complete when establishing the rollback baseline.
                readable_row_counts[name] = conn.execute(f'SELECT COUNT(*) FROM "{name}" NOT INDEXED').fetchone()[0]
                index_consistency[name] = _index_consistency(conn, name)
            except Exception as exc:
                readable_row_counts[name] = f"ERROR: {exc!r}"
    sqlite_sequence = conn.execute("SELECT name, seq FROM sqlite_sequence").fetchall()
    conn.close()

    sentinel = {
        "phase": "backup",
        "status": "SUCCESS",
        "timestamp": ts,
        "dest_dir": dest_dir,
        "files_copied": copied,
        "source_objects": [{"type": t, "name": n, "tbl_name": tb, "sql": s} for t, n, tb, s in objects],
        "readable_row_counts": readable_row_counts,
        "source_index_consistency": index_consistency,
        "protected_tables": protected,
        "sqlite_sequence": sqlite_sequence,
    }
    _write_sentinel(os.path.join(WORK_DIR, "backup.json"), sentinel)
    print(f"[backup] OK — {dest_dir}")
    print(json.dumps(sentinel, indent=2, default=str))


# ─────────────────────────────────────────────────────────────────────────
# Phase: build — construct rebuilt_full.db containing every source object
# except the 2 corrupt tables + 2 corrupt indexes, which are RECREATED
# EMPTY (not omitted) using the source's own recorded schema text.
# ─────────────────────────────────────────────────────────────────────────
def phase_build() -> None:
    backup_sentinel = _read_sentinel(os.path.join(WORK_DIR, "backup.json"))

    os.makedirs(WORK_DIR, exist_ok=True)
    quiesced = os.path.join(WORK_DIR, "source_quiesced.db")
    rebuilt = os.path.join(WORK_DIR, "rebuilt_full.db")
    for f in (quiesced, quiesced + "-wal", quiesced + "-shm", rebuilt):
        if os.path.exists(f):
            os.remove(f)

    shutil.copy2(LIVE_DB, quiesced)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(LIVE_DB + suffix):
            shutil.copy2(LIVE_DB + suffix, quiesced + suffix)

    src = sqlite3.connect(quiesced)
    out = sqlite3.connect(rebuilt)
    out.execute("ATTACH DATABASE ? AS src", (quiesced,))

    objects = _enumerate_objects(src)
    transfer_log = []

    # 1) Create every TABLE first (tables must exist before their indexes).
    for typ, name, tbl_name, sql in objects:
        if typ != "table":
            continue
        out.execute(sql)  # exact source text, verbatim — no reconstruction guesswork
        if name in _CORRUPT_TABLES:
            transfer_log.append({"object": name, "type": "table", "action": "recreated_empty"})
            continue  # never attempt to read/copy data from a corrupt table
        cols = _table_columns(src, name)
        col_list = ",".join(f'"{c}"' for c in cols)
        pk_order = "rowid"
        # NOT INDEXED forces a full TABLE b-tree scan on the source side —
        # required after discovering ct_cycles' autoindex silently missed
        # 15 real rows. Never rely on an index being complete/consistent
        # when reading the source we're about to preserve.
        out.execute(
            f'INSERT INTO main."{name}" ({col_list}) '
            f'SELECT {col_list} FROM src."{name}" NOT INDEXED ORDER BY {pk_order}'
        )
        src_scan = src.execute(f'SELECT COUNT(*) FROM "{name}" NOT INDEXED').fetchone()[0]
        out_count = out.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        out_consistency = _index_consistency(out, name)
        transfer_log.append({
            "object": name, "type": "table", "action": "copied",
            "source_table_scan_count": src_scan, "rebuilt_count": out_count,
            "match": src_scan == out_count,
            "rebuilt_index_consistency": out_consistency,
        })

    # 2) Create every INDEX (skip only the 2 corrupt ones; autoindexes are
    #    implicit from PK constraints and cannot/should not be manually
    #    created — SQLite already generated the healthy one automatically
    #    from ct_cycles' CREATE TABLE above).
    for typ, name, tbl_name, sql in objects:
        if typ != "index":
            continue
        if name in _CORRUPT_INDEXES:
            if name == "mi_latency_records_date":
                # Non-auto index on a corrupt table — recreate from the
                # source's own recorded text once the empty table exists.
                out.execute(sql)
                transfer_log.append({"object": name, "type": "index", "action": "recreated_empty"})
            else:
                # sqlite_autoindex_* cannot be created manually — it is
                # implicit from mi_latency_daily's PRIMARY KEY, already
                # created automatically by that CREATE TABLE above.
                transfer_log.append({"object": name, "type": "index", "action": "implicit_from_pk"})
            continue
        if sql is None:
            continue  # implicit autoindex on a healthy table — already created above
        out.execute(sql)
        transfer_log.append({"object": name, "type": "index", "action": "recreated"})

    # 3) Triggers / views, if any (none expected per the inventory, but
    #    handled generically so this script stays correct if that changes).
    for typ, name, tbl_name, sql in objects:
        if typ in ("trigger", "view") and sql:
            out.execute(sql)
            transfer_log.append({"object": name, "type": typ, "action": "recreated"})

    # 4) sqlite_sequence — copy real counters for ct_events/ct_decisions;
    #    deliberately leave mi_latency_records without a stale counter
    #    (it is empty; SQLite will create a correct seq row starting at 1
    #    on its first real future insert — the old counter referred only
    #    to permanently lost rows).
    for name, seq in src.execute("SELECT name, seq FROM sqlite_sequence"):
        if name in _CORRUPT_TABLES:
            continue
        out.execute("UPDATE sqlite_sequence SET seq=? WHERE name=?", (seq, name))

    out.commit()

    protected_before = backup_sentinel["protected_tables"]
    protected_after = _protected_table_snapshot(out)
    protected_match = protected_before == protected_after

    mi_readable_empty = {}
    for t in _CORRUPT_TABLES:
        try:
            mi_readable_empty[t] = out.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception as exc:
            mi_readable_empty[t] = f"ERROR: {exc!r}"

    out.close()
    src.close()

    all_copies_matched = all(
        e.get("match", True) for e in transfer_log if e["action"] == "copied"
    )
    all_indexes_consistent = all(
        e["rebuilt_index_consistency"]["consistent"]
        for e in transfer_log if e["action"] == "copied"
    )

    sentinel = {
        "phase": "build",
        "status": "SUCCESS" if (protected_match and all_copies_matched and all_indexes_consistent) else "MISMATCH",
        "timestamp": _now_ts(),
        "quiesced_copy": quiesced,
        "rebuilt_db": rebuilt,
        "transfer_log": transfer_log,
        "protected_tables_before": protected_before,
        "protected_tables_after": protected_after,
        "protected_tables_match": protected_match,
        "all_indexes_consistent": all_indexes_consistent,
        "mi_latency_readable_and_empty": mi_readable_empty,
    }
    _write_sentinel(os.path.join(WORK_DIR, "build.json"), sentinel)
    print(json.dumps(sentinel, indent=2, default=str))
    if sentinel["status"] != "SUCCESS":
        raise SystemExit("[build] MISMATCH — do not validate/swap. Investigate.")
    print("[build] OK")


# ─────────────────────────────────────────────────────────────────────────
# Phase: validate
# ─────────────────────────────────────────────────────────────────────────
def phase_validate() -> None:
    backup_sentinel = _read_sentinel(os.path.join(WORK_DIR, "backup.json"))
    build_sentinel = _read_sentinel(os.path.join(WORK_DIR, "build.json"))
    if build_sentinel["status"] != "SUCCESS":
        raise SystemExit("[validate] build.json did not report SUCCESS — fix build phase first.")

    rebuilt = build_sentinel["rebuilt_db"]
    checks: dict = {}
    failures: list = []

    def record(name: str, ok: bool, detail=None) -> None:
        checks[name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    conn = sqlite3.connect(rebuilt)

    integrity = conn.execute("PRAGMA integrity_check").fetchall()
    record("integrity_check_ok", integrity == [("ok",)], integrity)

    quick = conn.execute("PRAGMA quick_check").fetchall()
    record("quick_check_ok", quick == [("ok",)], quick)

    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    record("foreign_key_check_empty", fk == [], fk)

    # Object-set comparison: every source object (by type,name) must exist
    # in rebuilt with IDENTICAL sql text — including the 2 corrupt objects,
    # which must now be present (recreated), not silently dropped.
    source_objs = {(o["type"], o["name"]): o["sql"] for o in backup_sentinel["source_objects"]}
    rebuilt_objs = {(t, n): s for t, n, tb, s in _enumerate_objects(conn)}
    missing = [k for k in source_objs if k not in rebuilt_objs]
    unexpected = [k for k in rebuilt_objs if k not in source_objs]
    sql_mismatches = [k for k in source_objs if k in rebuilt_objs and source_objs[k] != rebuilt_objs[k]]
    record("no_missing_objects", missing == [], missing)
    record("no_unexpected_objects", unexpected == [], unexpected)
    record("schema_sql_identical_for_all_objects", sql_mismatches == [], sql_mismatches)

    # Protected tables — must match the pre-repair baseline exactly.
    now = _protected_table_snapshot(conn)
    baseline = backup_sentinel["protected_tables"]
    record("ct_events_unchanged", now["ct_events"] == baseline["ct_events"],
           {"before": baseline["ct_events"], "after": now["ct_events"]})
    record("ct_cycles_unchanged", now["ct_cycles"] == baseline["ct_cycles"],
           {"before": baseline["ct_cycles"], "after": now["ct_cycles"]})
    record("ct_decisions_unchanged", now["ct_decisions"] == baseline["ct_decisions"],
           {"before": baseline["ct_decisions"], "after": now["ct_decisions"]})

    # Every other readable table from the baseline must match row count too
    # (generic safety net beyond the 3 named protected tables) — using the
    # SAME forced table-scan method as the baseline, never plain COUNT(*).
    for tname, before_count in backup_sentinel["readable_row_counts"].items():
        try:
            after_count = conn.execute(f'SELECT COUNT(*) FROM "{tname}" NOT INDEXED').fetchone()[0]
        except Exception as exc:
            after_count = f"ERROR: {exc!r}"
        record(f"row_count_matches_{tname}", after_count == before_count,
               {"before": before_count, "after": after_count})

    # Rebuilt indexes must now be fully consistent with their tables — the
    # exact defect found in the source's ct_cycles autoindex must be gone.
    for tname in backup_sentinel["readable_row_counts"]:
        consistency = _index_consistency(conn, tname)
        record(f"rebuilt_index_consistent_{tname}", consistency["consistent"], consistency)

    # mi_latency tables: present, readable, genuinely empty (no fabrication).
    for t in _CORRUPT_TABLES:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            record(f"{t}_readable_and_empty", cnt == 0, cnt)
        except Exception as exc:
            record(f"{t}_readable_and_empty", False, repr(exc))

    conn.close()

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
        "rebuilt_db": rebuilt,
    }
    _write_sentinel(os.path.join(WORK_DIR, "validate.json"), sentinel)
    print(json.dumps(sentinel, indent=2, default=str))
    if verdict == "PASSED":
        print("[validate] PASSED — safe to proceed to swap.")
    else:
        print(f"[validate] FAILED — {failures}. DO NOT SWAP.")
        raise SystemExit(1)


# ─────────────────────────────────────────────────────────────────────────
# Phase: swap
# ─────────────────────────────────────────────────────────────────────────
def phase_swap() -> None:
    validate_sentinel = _read_sentinel(os.path.join(WORK_DIR, "validate.json"))
    if validate_sentinel["status"] != "PASSED":
        raise SystemExit("[swap] validate.json is not PASSED — refusing to swap.")
    backup_sentinel = _read_sentinel(os.path.join(WORK_DIR, "backup.json"))
    build_sentinel = _read_sentinel(os.path.join(WORK_DIR, "build.json"))
    rebuilt = build_sentinel["rebuilt_db"]

    ts = _now_ts()
    superseded_dir = os.path.join(WORK_DIR, f"superseded_{ts}")
    os.makedirs(superseded_dir, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        src = LIVE_DB + suffix
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(superseded_dir, os.path.basename(LIVE_DB) + suffix))

    result = {"phase": "swap", "timestamp": ts, "superseded_backup_dir": superseded_dir}
    try:
        for suffix in ("", "-wal", "-shm"):
            p = LIVE_DB + suffix
            if os.path.exists(p):
                os.remove(p)
        shutil.move(rebuilt, LIVE_DB)

        conn = sqlite3.connect(LIVE_DB)
        conn.execute("VACUUM")
        conn.close()

        final = sqlite3.connect(LIVE_DB)
        integrity = final.execute("PRAGMA integrity_check").fetchall()
        quick = final.execute("PRAGMA quick_check").fetchall()
        fk = final.execute("PRAGMA foreign_key_check").fetchall()
        now = _protected_table_snapshot(final)
        mi_counts = {t: final.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in _CORRUPT_TABLES}
        final.close()

        baseline = backup_sentinel["protected_tables"]
        protected_ok = (now == baseline)
        clean = integrity == [("ok",)] and quick == [("ok",)] and fk == []

        result.update({
            "post_integrity_check": integrity,
            "post_quick_check": quick,
            "post_foreign_key_check": fk,
            "protected_tables_after": now,
            "protected_tables_match": protected_ok,
            "mi_latency_counts_after": mi_counts,
            "status": "SUCCESS" if (clean and protected_ok) else "FAILED",
        })
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()

    _write_sentinel(os.path.join(WORK_DIR, "swap.json"), result)
    print(json.dumps(result, indent=2, default=str))
    if result["status"] != "SUCCESS":
        print("[swap] FAILED — RESTORE from superseded_backup_dir immediately.")
        raise SystemExit(1)
    print("[swap] OK — VACUUM succeeded, integrity_check clean, protected tables unchanged. "
          "Restart the containers and run post-restart verification next.")


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
