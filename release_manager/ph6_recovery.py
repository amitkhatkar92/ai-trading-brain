"""
release_manager/ph6_recovery.py — Phase 6: One-Command Recovery System.

Provides recovery to:
  - Latest stable version (most recent backup)
  - Previous stable version (second-most-recent)
  - Specific version (by backup_id or git commit)

Recovery restores: Code (git reset) + Databases + Configuration + Containers.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from .frz_config import (
    BACKUP_DIR,
    ROOT,
    SSH_KEY,
    VPS_BACKUP_DIR,
    VPS_HOST,
    VPS_PROJECT_DIR,
)
from .frz_models import RecoveryPoint
from .ph4_backup import list_local_backups

log = logging.getLogger(__name__)


def _ssh(cmd: str, timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(
            f'ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=15 {VPS_HOST} "{cmd}"',
            shell=True, capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, r.stdout.strip()
    except Exception as e:
        return 1, str(e)


def list_recovery_points() -> List[RecoveryPoint]:
    """Return all available recovery points (local backups + git tags)."""
    points: List[RecoveryPoint] = []

    # From local backups
    for bkp in list_local_backups():
        try:
            from .ph1_system_version import load_version
            sv = load_version()
            ver = sv.platform_version if sv else "unknown"
        except Exception:
            ver = "unknown"
        points.append(RecoveryPoint(
            backup_id    = bkp.backup_id,
            timestamp    = bkp.timestamp,
            git_commit   = bkp.git_commit,
            version      = ver,
            local_path   = bkp.local_path,
            vps_path     = "",
            is_certified = "IIOS-V" in bkp.backup_id,
        ))

    # From git tags (IIOS-V*)
    try:
        r = subprocess.run(
            "git tag -l 'IIOS-V*' --sort=-version:refname",
            shell=True, capture_output=True, text=True, cwd=ROOT
        )
        for tag in r.stdout.strip().splitlines()[:10]:
            commit_r = subprocess.run(
                f"git rev-list -n 1 {tag}",
                shell=True, capture_output=True, text=True, cwd=ROOT
            )
            commit = commit_r.stdout.strip()[:7]
            points.append(RecoveryPoint(
                backup_id    = tag,
                timestamp    = "",
                git_commit   = commit,
                version      = tag.replace("IIOS-V", ""),
                local_path   = "",
                vps_path     = "",
                is_certified = True,
            ))
    except Exception:
        pass

    return points


def recover(
    backup_id: Optional[str] = None,
    target: str = "latest",      # latest | previous | specific
    dry_run: bool = False,
) -> dict:
    """
    Recover to a specific backup or git tag.

    target='latest'   → most recent backup
    target='previous' → second-most-recent backup
    target='specific' → use backup_id

    Returns dict with recovery result.
    """
    points = list_recovery_points()
    if not points:
        return {"ok": False, "error": "No recovery points available"}

    # Select recovery point
    if target == "latest":
        point = points[0]
    elif target == "previous" and len(points) >= 2:
        point = points[1]
    elif backup_id:
        matched = [p for p in points if p.backup_id == backup_id or p.git_commit.startswith(backup_id)]
        if not matched:
            return {"ok": False, "error": f"Backup '{backup_id}' not found"}
        point = matched[0]
    else:
        return {"ok": False, "error": "No recovery target specified"}

    log.info(
        "[Recovery] %sRecovering to %s (commit=%s)",
        "[DRY-RUN] " if dry_run else "", point.backup_id, point.git_commit,
    )

    steps = []

    # Step 1: Restore local files from backup
    if point.local_path and Path(point.local_path).exists():
        if not dry_run:
            _restore_local_files(Path(point.local_path))
        steps.append(f"Local files restored from {point.local_path}")
    else:
        steps.append("No local backup path — skipping file restore")

    # Step 2: Git reset to target commit (if it's a tag/commit, not just files)
    if point.git_commit and point.git_commit != "unknown":
        if not dry_run:
            _git_reset(point.git_commit)
        steps.append(f"Git reset to {point.git_commit}")

    # Step 3: VPS recovery — git reset + docker rebuild
    if not dry_run:
        vps_ok = _vps_recover(point.git_commit)
        steps.append(f"VPS recovery: {'OK' if vps_ok else 'FAILED'}")
    else:
        steps.append("[DRY-RUN] VPS recovery would run git reset + docker rebuild")

    return {"ok": True, "recovery_point": point.backup_id, "steps": steps}


def _restore_local_files(backup_path: Path) -> None:
    """Restore backed-up files to their original locations."""
    for item in backup_path.rglob("*"):
        if item.is_file() and item.name != "backup_manifest.json":
            rel = item.relative_to(backup_path)
            dest = ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
            log.debug("[Recovery] Restored: %s", rel)


def _git_reset(commit: str) -> bool:
    """Reset local git to a specific commit."""
    try:
        subprocess.run(f"git reset --hard {commit}", shell=True, check=True, cwd=ROOT)
        return True
    except Exception as e:
        log.error("[Recovery] Git reset failed: %s", e)
        return False


def _vps_recover(commit: str) -> bool:
    """Reset VPS git and rebuild containers."""
    cmds = [
        f"cd {VPS_PROJECT_DIR} && git fetch origin",
        f"cd {VPS_PROJECT_DIR} && git reset --hard {commit}",
        f"cd {VPS_PROJECT_DIR} && docker compose build --no-cache",
        f"cd {VPS_PROJECT_DIR} && docker compose down",
        f"cd {VPS_PROJECT_DIR} && docker compose up -d",
    ]
    for cmd in cmds:
        rc, out = _ssh(cmd, timeout=300)
        if rc != 0:
            log.error("[Recovery] VPS step failed: %s → %s", cmd, out)
            return False
        log.info("[Recovery] VPS: %s → OK", cmd.split("&&")[-1].strip())
    return True
