"""
release_manager/ph4_backup.py — Phase 4: Automatic Backup.

Creates timestamped backups before every deployment:
  - LOCAL: copies key files to data/frz/backups/<timestamp>/
  - VPS:   tars /root/ai-trading-brain/data/ to /root/ai-trading-brain/backups/<timestamp>.tar.gz
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .frz_config import (
    BACKUP_DIR,
    LOCAL_BACKUP_ITEMS,
    ROOT,
    SSH_KEY,
    SYNC_VERIFY_TIMEOUT_S,
    VPS_BACKUP_DIR,
    VPS_HOST,
    VPS_PROJECT_DIR,
)
from .frz_models import BackupRecord

log = logging.getLogger(__name__)


def _ssh(cmd: str) -> tuple[int, str]:
    try:
        r = subprocess.run(
            f'ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=15 {VPS_HOST} "{cmd}"',
            shell=True, capture_output=True, text=True, timeout=120,
        )
        return r.returncode, r.stdout.strip()
    except Exception as e:
        return 1, str(e)


def _git_commit() -> str:
    try:
        r = subprocess.run("git rev-parse HEAD", shell=True, capture_output=True, text=True, cwd=ROOT)
        return r.stdout.strip()[:7]
    except Exception:
        return "unknown"


def run_local_backup(backup_id: str, dest: Path) -> tuple[int, int]:
    """
    Copy LOCAL_BACKUP_ITEMS to dest/.
    Returns (files_backed_up, total_size_bytes).
    """
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    total_bytes = 0
    for rel_path in LOCAL_BACKUP_ITEMS:
        src = ROOT / rel_path
        if not src.exists():
            log.debug("[Backup] Skip missing: %s", rel_path)
            continue
        dst = dest / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        total_bytes += dst.stat().st_size
        count += 1
    log.info("[Backup] Local: %d files, %d bytes → %s", count, total_bytes, dest)
    return count, total_bytes


def run_vps_backup(backup_id: str) -> tuple[bool, str]:
    """
    Create a tarball of /root/ai-trading-brain/data/ on the VPS.
    Returns (success, vps_path).
    """
    vps_path = f"{VPS_BACKUP_DIR}/{backup_id}.tar.gz"
    rc, _ = _ssh(f"mkdir -p {VPS_BACKUP_DIR}")
    if rc != 0:
        log.warning("[Backup] VPS: cannot create backup dir")
        return False, ""
    rc, out = _ssh(
        f"tar -czf {vps_path} -C {VPS_PROJECT_DIR} data/ --exclude=data/frz/backups/ 2>&1"
    )
    if rc != 0:
        log.warning("[Backup] VPS tar failed (rc=%d): %s", rc, out)
        return False, ""
    log.info("[Backup] VPS: backup created at %s", vps_path)
    return True, vps_path


def create_backup(commit: Optional[str] = None) -> BackupRecord:
    """
    Create timestamped backup (local + VPS).
    Returns BackupRecord with details.
    """
    commit   = commit or _git_commit()
    ts_str   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bkp_id   = f"backup_{ts_str}_{commit}"
    local_dir = BACKUP_DIR / bkp_id

    # Local backup
    try:
        count, size = run_local_backup(bkp_id, local_dir)
        local_ok = True
    except Exception as e:
        log.warning("[Backup] Local backup failed: %s", e)
        count, size = 0, 0
        local_ok = False

    # VPS backup
    try:
        vps_ok, vps_path = run_vps_backup(bkp_id)
    except Exception as e:
        log.warning("[Backup] VPS backup failed: %s", e)
        vps_ok, vps_path = False, ""

    record = BackupRecord(
        timestamp       = datetime.now(timezone.utc).isoformat(),
        backup_id       = bkp_id,
        git_commit      = commit,
        local_path      = str(local_dir) if local_ok else "",
        vps_path        = vps_path,
        files_backed_up = count,
        size_bytes      = size,
        success         = local_ok,
        error           = "" if (local_ok or vps_ok) else "Both local and VPS backup failed",
    )

    # Write backup manifest
    if local_dir.exists():
        manifest = {
            "backup_id":  bkp_id,
            "timestamp":  record.timestamp,
            "git_commit": commit,
            "files":      count,
        }
        (local_dir / "backup_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    log.info("[Backup] Complete: id=%s local=%s vps=%s", bkp_id, local_ok, vps_ok)
    return record


def list_local_backups() -> list[BackupRecord]:
    """Return all local backup records sorted by timestamp (newest first)."""
    if not BACKUP_DIR.exists():
        return []
    records = []
    for d in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        manifest_file = d / "backup_manifest.json"
        if not manifest_file.exists():
            continue
        try:
            m = json.loads(manifest_file.read_text(encoding="utf-8"))
            records.append(BackupRecord(
                timestamp       = m.get("timestamp", ""),
                backup_id       = m.get("backup_id", d.name),
                git_commit      = m.get("git_commit", ""),
                local_path      = str(d),
                vps_path        = "",
                files_backed_up = m.get("files", 0),
                size_bytes      = 0,
                success         = True,
            ))
        except Exception:
            continue
    return records
