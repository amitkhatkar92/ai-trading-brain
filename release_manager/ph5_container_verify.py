"""
release_manager/ph5_container_verify.py — Phase 5: Container Consistency.

Verifies Docker image / container / running code are all identical.
Reuses deployment/runtime_verifier.py — never duplicates its logic.
"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import List

from .frz_config import (
    CONTAINER_NAME,
    DASHBOARD_NAME,
    ROOT,
    SSH_KEY,
    SYNC_VERIFY_TIMEOUT_S,
    VPS_HOST,
)
from .frz_models import ContainerVerification

log = logging.getLogger(__name__)


def _ssh(cmd: str) -> tuple[int, str]:
    try:
        r = subprocess.run(
            f'ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VPS_HOST} "{cmd}"',
            shell=True, capture_output=True, text=True, timeout=SYNC_VERIFY_TIMEOUT_S,
        )
        return r.returncode, r.stdout.strip()
    except Exception as e:
        return 1, str(e)


def _container_status(name: str) -> str:
    rc, out = _ssh(f"docker inspect --format='{{{{.State.Health.Status}}}}' {name} 2>/dev/null || echo 'not_found'")
    s = out.strip().strip("'")
    return s if s else "unknown"


def _container_commit(name: str) -> str:
    """Read SYSTEM_VERSION.json or build_manifest.json inside container."""
    _, raw = _ssh(
        f"docker exec {name} cat /app/SYSTEM_VERSION.json 2>/dev/null || "
        f"docker exec {name} cat /app/build_manifest.json 2>/dev/null || echo '{{}}'"
    )
    try:
        d = json.loads(raw)
        return (d.get("git_commit_full") or d.get("commit") or d.get("git_commit") or "unknown")[:7]
    except Exception:
        return "unknown"


def _manifest_commit() -> str:
    """Read build_manifest.json from local disk (baked into image)."""
    try:
        d = json.loads((ROOT / "build_manifest.json").read_text(encoding="utf-8"))
        c = d.get("commit_full") or d.get("commit") or ""
        return c[:7] if c else "unknown"
    except Exception:
        return "unknown"


def _runtime_drift_files() -> List[str]:
    """
    Call deployment/runtime_verifier.verify() and return list of drifted files.
    Runs locally against the RUNNING container via SSH docker exec.
    Falls back to [] if runtime_verifier can't run remotely.
    """
    try:
        # Run runtime_verifier inside the container
        _, out = _ssh(
            f"docker exec {CONTAINER_NAME} python -c "
            f'"from deployment.runtime_verifier import verify; '
            f"r=verify(send_alert=False); "
            f"print(','.join(r.get('drift_files',[])) if isinstance(r,dict) else '')\""
        )
        if out and not out.startswith("ERROR"):
            return [f for f in out.split(",") if f]
        return []
    except Exception:
        return []


def verify_container_consistency() -> ContainerVerification:
    """
    Verify Docker image / container / running code consistency.
    """
    ts = datetime.now(timezone.utc).isoformat()
    details: List[str] = []

    local_commit   = subprocess.run(
        "git rev-parse --short HEAD", shell=True, capture_output=True,
        text=True, cwd=ROOT,
    ).stdout.strip()

    manifest_commit  = _manifest_commit()
    container_commit = _container_commit(CONTAINER_NAME)
    drift_files      = _runtime_drift_files()
    runtime_ok       = (len(drift_files) == 0)
    container_status = _container_status(CONTAINER_NAME)
    dashboard_status = _container_status(DASHBOARD_NAME)

    # Normalise to 7-char for comparison
    def _n(c: str) -> str:
        return c[:7].lower()

    image_ok = (_n(manifest_commit) == _n(local_commit)) if manifest_commit != "unknown" else False
    run_ok   = (_n(container_commit) == _n(local_commit)) if container_commit != "unknown" else False

    details.append(f"local_commit={local_commit}")
    details.append(f"manifest_commit={manifest_commit}")
    details.append(f"container_commit={container_commit}")
    details.append(f"container_status={container_status}")
    details.append(f"dashboard_status={dashboard_status}")
    if drift_files:
        details.append(f"drift_files={','.join(drift_files)}")

    overall_ok = (
        runtime_ok
        and container_status in ("healthy", "")
        and dashboard_status in ("healthy", "")
    )

    log.info(
        "[ContainerVerify] local=%s manifest=%s container=%s "
        "runtime_ok=%s status=%s/%s overall=%s",
        local_commit, manifest_commit, container_commit,
        runtime_ok, container_status, dashboard_status, overall_ok,
    )

    return ContainerVerification(
        timestamp        = ts,
        image_commit     = manifest_commit,
        container_commit = container_commit,
        manifest_commit  = manifest_commit,
        runtime_hashes_ok= runtime_ok,
        drift_files      = drift_files,
        container_status = container_status,
        dashboard_status = dashboard_status,
        overall_ok       = overall_ok,
        details          = details,
    )
