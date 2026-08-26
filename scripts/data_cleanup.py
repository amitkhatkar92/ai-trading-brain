"""
Data Cleanup Manager — GAP-008, GAP-018, GAP-021, GAP-025
==========================================================
Runs nightly at EOD (wired into _do_eod_learning) to prune unbounded runtime
data directories while preserving the research value of older records.

Cleanup policy per path:

  data/klp/kda/kda_vs_stratlab_YYYY-MM-DD.jsonl
    • Keep last 30 days raw.
    • Files older than 30 days: extract per-day summary (decision counts,
      accuracy stats) into data/klp/kda/summary_archive.json, then delete raw.
    • Prevents the directory from growing to millions of rows over months.

  data/predictive_gap/scan_attrition_*.jsonl
    • Keep last 30 days raw.
    • Older files deleted (summary stats written to predictive_gap/archive_summary.json).

  data/lol/LOL_*.jsonl
    • Keep last 60 days raw.
    • Older files deleted (counts preserved in lol/archive_summary.json).

  data/frz/backups/
    • Keep the 7 most recent timestamped snapshots.
    • Older snapshot directories deleted.

  data/rejection_audit.db
    • Rows older than 90 days deleted via SQLite DELETE (shrinks the file).
    • VACUUM run after deletion to reclaim space.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from utils import get_logger

log = get_logger(__name__)

# Root data directory
_DATA = Path(__file__).resolve().parents[1] / "data"

# Retention windows
KDA_RETAIN_DAYS        = 30
ATTRITION_RETAIN_DAYS  = 30
LOL_RETAIN_DAYS        = 60
FRZ_RETAIN_SNAPSHOTS   = 7
REJECTION_DB_DAYS      = 90


# ─────────────────────────────────────────────────────────────────────────────
# KDA comparison files (GAP-008)
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_kda_files() -> dict:
    kda_dir = _DATA / "klp" / "kda"
    if not kda_dir.exists():
        return {"skipped": True, "reason": "directory not found"}

    cutoff = date.today() - timedelta(days=KDA_RETAIN_DAYS)
    archive_path = kda_dir / "summary_archive.json"

    # Load existing archive
    archive: Dict[str, Any] = {}
    if archive_path.exists():
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
        except Exception:
            archive = {}

    deleted = 0
    summarised = 0
    for fpath in sorted(kda_dir.glob("kda_vs_stratlab_*.jsonl")):
        # Parse date from filename
        stem = fpath.stem  # kda_vs_stratlab_YYYY-MM-DD
        try:
            file_date = date.fromisoformat(stem.replace("kda_vs_stratlab_", ""))
        except ValueError:
            continue
        if file_date >= cutoff:
            continue  # within retention window — keep

        # Summarise before deleting
        date_key = file_date.isoformat()
        if date_key not in archive:
            counts: Dict[str, int] = {
                "total": 0, "kda_authorized": 0, "stratlab_approved": 0,
                "both": 0, "kda_hold_blocked": 0,
            }
            try:
                with open(fpath, encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            row = json.loads(line)
                            counts["total"] += 1
                            if row.get("kda_authorized"):
                                counts["kda_authorized"] += 1
                            if row.get("strategylab_approved"):
                                counts["stratlab_approved"] += 1
                            if row.get("authorization_source") == "BOTH":
                                counts["both"] += 1
                            if row.get("kda_hold_blocked"):
                                counts["kda_hold_blocked"] += 1
                        except Exception:
                            pass
            except Exception as exc:
                log.warning("[DataCleanup] KDA summary failed for %s: %s", fpath.name, exc)
            archive[date_key] = counts
            summarised += 1

        try:
            fpath.unlink()
            deleted += 1
        except Exception as exc:
            log.warning("[DataCleanup] Could not delete %s: %s", fpath, exc)

    # Save updated archive
    if summarised > 0:
        try:
            archive_path.write_text(json.dumps(archive, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("[DataCleanup] Could not write KDA archive: %s", exc)

    return {"deleted": deleted, "summarised": summarised, "retained_archive_days": len(archive)}


# ─────────────────────────────────────────────────────────────────────────────
# Scan attrition files (GAP-008 / predictive_gap)
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_attrition_files() -> dict:
    att_dir = _DATA / "predictive_gap"
    if not att_dir.exists():
        return {"skipped": True, "reason": "directory not found"}

    cutoff = date.today() - timedelta(days=ATTRITION_RETAIN_DAYS)
    archive_path = att_dir / "archive_summary.json"

    archive: Dict[str, Any] = {}
    if archive_path.exists():
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
        except Exception:
            archive = {}

    deleted = 0
    summarised = 0
    for fpath in sorted(att_dir.glob("*.jsonl")):
        if fpath.name == "archive_summary.jsonl":
            continue
        try:
            # Attempt to extract a date from the filename
            for part in fpath.stem.split("_"):
                try:
                    file_date = date.fromisoformat(part)
                    break
                except ValueError:
                    continue
            else:
                # No date found — skip
                continue
        except Exception:
            continue
        if file_date >= cutoff:
            continue

        date_key = file_date.isoformat()
        if date_key not in archive:
            try:
                lines = fpath.read_text(encoding="utf-8").splitlines()
                archive[date_key] = {"rows": len(lines)}
                summarised += 1
            except Exception:
                pass

        try:
            fpath.unlink()
            deleted += 1
        except Exception as exc:
            log.warning("[DataCleanup] Could not delete attrition file %s: %s", fpath, exc)

    if summarised > 0:
        try:
            archive_path.write_text(json.dumps(archive, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("[DataCleanup] Could not write attrition archive: %s", exc)

    return {"deleted": deleted, "summarised": summarised}


# ─────────────────────────────────────────────────────────────────────────────
# LOL (Learning Observation Ledger) files (GAP-025)
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_lol_files() -> dict:
    lol_dir = _DATA / "lol"
    if not lol_dir.exists():
        return {"skipped": True, "reason": "directory not found"}

    cutoff = date.today() - timedelta(days=LOL_RETAIN_DAYS)
    archive_path = lol_dir / "archive_summary.json"

    archive: Dict[str, Any] = {}
    if archive_path.exists():
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
        except Exception:
            archive = {}

    deleted = 0
    for fpath in sorted(lol_dir.glob("LOL_*.jsonl")):
        # Filename: LOL_YYYY-MM-DD.jsonl or LOL_YYYY_MM_DD.jsonl
        try:
            date_str = fpath.stem.replace("LOL_", "").replace("_", "-")
            file_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        if file_date >= cutoff:
            continue

        date_key = file_date.isoformat()
        if date_key not in archive:
            try:
                lines = fpath.read_text(encoding="utf-8").splitlines()
                archive[date_key] = {"rows": len(lines)}
            except Exception:
                pass

        try:
            fpath.unlink()
            deleted += 1
        except Exception as exc:
            log.warning("[DataCleanup] Could not delete LOL file %s: %s", fpath, exc)

    if deleted > 0 or archive:
        try:
            archive_path.write_text(json.dumps(archive, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("[DataCleanup] Could not write LOL archive: %s", exc)

    return {"deleted": deleted}


# ─────────────────────────────────────────────────────────────────────────────
# FRZ backup snapshots (GAP-018)
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_frz_backups() -> dict:
    frz_dir = _DATA / "frz" / "backups"
    if not frz_dir.exists():
        return {"skipped": True, "reason": "directory not found"}

    # Each snapshot is a directory named backup_YYYYMMDD_HHMMSS_hash
    snapshots: List[Path] = sorted(
        [p for p in frz_dir.iterdir() if p.is_dir() and p.name.startswith("backup_")],
        key=lambda p: p.name,
    )

    to_delete = snapshots[:-FRZ_RETAIN_SNAPSHOTS] if len(snapshots) > FRZ_RETAIN_SNAPSHOTS else []
    deleted = 0
    for snap in to_delete:
        try:
            shutil.rmtree(snap)
            deleted += 1
            log.info("[DataCleanup] Deleted old FRZ snapshot: %s", snap.name)
        except Exception as exc:
            log.warning("[DataCleanup] Could not delete FRZ snapshot %s: %s", snap, exc)

    return {"deleted": deleted, "retained": len(snapshots) - deleted}


# ─────────────────────────────────────────────────────────────────────────────
# rejection_audit.db row pruning (GAP-027 companion)
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_rejection_db() -> dict:
    db_path = _DATA / "rejection_audit.db"
    if not db_path.exists():
        return {"skipped": True, "reason": "db not found"}

    cutoff_str = (date.today() - timedelta(days=REJECTION_DB_DAYS)).isoformat()
    deleted = 0
    try:
        with sqlite3.connect(str(db_path)) as conn:
            # Try common column names; gracefully skip if schema differs
            for table, col in [("rejections", "trade_date"), ("rejection_log", "date"),
                                ("rejections", "date")]:
                try:
                    cur = conn.execute(f"DELETE FROM {table} WHERE {col} < ?", (cutoff_str,))
                    deleted += cur.rowcount
                    conn.commit()
                    break
                except sqlite3.OperationalError:
                    continue
            conn.execute("VACUUM")
    except Exception as exc:
        log.warning("[DataCleanup] rejection_audit.db cleanup failed: %s", exc)
        return {"error": str(exc)}

    return {"rows_deleted": deleted, "cutoff": cutoff_str}


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_cleanup() -> dict:
    """
    Run all cleanup tasks.  Called from orchestrator._do_eod_learning.
    Never raises — failures are logged and included in the result.
    """
    results: Dict[str, Any] = {"run_at": datetime.now().isoformat()}
    try:
        results["kda"]          = _cleanup_kda_files()
    except Exception as exc:
        results["kda"]          = {"error": str(exc)}

    try:
        results["attrition"]    = _cleanup_attrition_files()
    except Exception as exc:
        results["attrition"]    = {"error": str(exc)}

    try:
        results["lol"]          = _cleanup_lol_files()
    except Exception as exc:
        results["lol"]          = {"error": str(exc)}

    try:
        results["frz_backups"]  = _cleanup_frz_backups()
    except Exception as exc:
        results["frz_backups"]  = {"error": str(exc)}

    try:
        results["rejection_db"] = _cleanup_rejection_db()
    except Exception as exc:
        results["rejection_db"] = {"error": str(exc)}

    log.info("[DataCleanup] Daily cleanup complete: %s", results)
    return results


if __name__ == "__main__":
    # Can be run manually: python scripts/data_cleanup.py
    import sys
    _root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_root))
    result = run_daily_cleanup()
    print(json.dumps(result, indent=2))
