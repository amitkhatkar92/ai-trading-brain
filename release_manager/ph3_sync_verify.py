"""
release_manager/ph3_sync_verify.py — Phase 3: Local → VPS Synchronization.

Verifies that Local / Git Remote / VPS / Container all contain the identical commit.
Deployment must fail if any layer differs.

Reuses SSH approach from scripts/_sync_check.py — no duplication.
"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from .frz_config import (
    CONTAINER_NAME,
    ROOT,
    SSH_KEY,
    SYNC_VERIFY_TIMEOUT_S,
    VPS_HOST,
    VPS_PROJECT_DIR,
)
from .frz_models import SyncVerification

log = logging.getLogger(__name__)


def _run(cmd: str, cwd=None) -> str:
    """Run a local shell command and return stdout stripped."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           cwd=cwd or ROOT, timeout=SYNC_VERIFY_TIMEOUT_S)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR:{e}"


def _ssh(cmd: str) -> str:
    """Run a command on VPS via SSH."""
    try:
        ssh_cmd = f'ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VPS_HOST} "{cmd}"'
        r = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True,
                           timeout=SYNC_VERIFY_TIMEOUT_S)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR:{e}"


def get_local_commit() -> str:
    return _run("git rev-parse HEAD")


def get_remote_commit() -> str:
    """Get the commit on origin/main (requires network)."""
    _run("git fetch origin --quiet")   # update remote refs
    return _run("git rev-parse origin/main")


def get_vps_commit() -> str:
    """Get the HEAD commit on the VPS."""
    return _ssh(f"cd {VPS_PROJECT_DIR} && git rev-parse HEAD")


def get_container_commit() -> str:
    """Read SYSTEM_VERSION.json inside the running container."""
    raw = _ssh(
        f"docker exec {CONTAINER_NAME} "
        f"cat /app/SYSTEM_VERSION.json 2>/dev/null || "
        f"docker exec {CONTAINER_NAME} "
        f"cat /app/build_manifest.json 2>/dev/null || echo '{{}}'"
    )
    try:
        d = json.loads(raw)
        return d.get("git_commit_full") or d.get("commit") or d.get("git_commit") or "unknown"
    except Exception:
        return raw[:40] if raw else "unknown"


def run_sync_verification(skip_container: bool = False) -> SyncVerification:
    """
    Run all four layer checks and return a SyncVerification result.
    If skip_container=True, container check is skipped (pre-deploy use).
    """
    ts = datetime.now(timezone.utc).isoformat()
    details: List[str] = []

    local     = get_local_commit()
    remote    = get_remote_commit()
    vps       = get_vps_commit()
    container = get_container_commit() if not skip_container else "SKIP"

    def _short(c: str) -> str:
        return c[:7] if len(c) >= 7 else c

    details.append(f"local={_short(local)}")
    details.append(f"remote={_short(remote)}")
    details.append(f"vps={_short(vps)}")
    if not skip_container:
        details.append(f"container={_short(container)}")

    # Normalise: compare short forms for container (may store 7-char)
    def _norm(c: str) -> str:
        return c[:7].lower() if c and not c.startswith("ERROR") and c != "SKIP" else c

    l_n, r_n, v_n = _norm(local), _norm(remote), _norm(vps)

    lr_ok = (l_n == r_n and l_n not in ("", "unknown") and not l_n.startswith("ERROR"))
    lv_ok = (l_n == v_n and l_n not in ("", "unknown") and not l_n.startswith("ERROR"))

    if skip_container:
        lc_ok  = True
        c_norm = "SKIP"
    else:
        c_norm = _norm(container)
        lc_ok  = (l_n == c_norm and l_n not in ("", "unknown") and not l_n.startswith("ERROR"))

    overall = "MATCH" if (lr_ok and lv_ok and lc_ok) else "MISMATCH"

    if not lr_ok:
        details.append(f"MISMATCH: local ({_short(local)}) ≠ remote ({_short(remote)})")
    if not lv_ok:
        details.append(f"MISMATCH: local ({_short(local)}) ≠ VPS ({_short(vps)})")
    if not lc_ok and not skip_container:
        details.append(f"MISMATCH: local ({_short(local)}) ≠ container ({_short(container)})")

    log.info(
        "[SyncVerify] local=%s remote=%s vps=%s container=%s → %s",
        _short(local), _short(remote), _short(vps),
        _short(container) if not skip_container else "SKIP",
        overall,
    )

    return SyncVerification(
        timestamp            = ts,
        local_commit         = local,
        remote_commit        = remote,
        vps_commit           = vps,
        container_commit     = container,
        local_remote_match   = lr_ok,
        local_vps_match      = lv_ok,
        local_container_match= lc_ok,
        overall_status       = overall,
        details              = details,
    )


def assert_in_sync(pre_deploy: bool = True) -> SyncVerification:
    """
    Run sync verification and raise RuntimeError if MISMATCH.
    Set pre_deploy=True to skip container check (container hasn't been rebuilt yet).
    """
    result = run_sync_verification(skip_container=pre_deploy)
    if result.overall_status == "MISMATCH":
        msg = "DEPLOYMENT BLOCKED — commit mismatch: " + " | ".join(result.details)
        log.error("[SyncVerify] %s", msg)
        raise RuntimeError(msg)
    return result
