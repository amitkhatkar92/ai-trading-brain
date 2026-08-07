"""
release_manager/frz_reporter.py — FRZ-001 Report Writer.

Generates all FRZ-001 reports into data/frz/reports/YYYY-MM-DD/.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .frz_config import REPORT_DIR
from .frz_models import (
    BackupRecord,
    ConfigSnapshot,
    ContainerVerification,
    ProductionLockStatus,
    StartupCheckResult,
    SyncVerification,
    SystemVersion,
)

log = logging.getLogger(__name__)


def _dir(today: str) -> Path:
    d = REPORT_DIR / today
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_deployment_verification(
    sync: Optional[SyncVerification],
    container: Optional[ContainerVerification],
    today: str,
) -> Path:
    d = _dir(today)
    path = d / "DEPLOYMENT_VERIFICATION.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if sync is None:
        path.write_text(f"# DEPLOYMENT_VERIFICATION — {today}\n\n_Not run._\n", encoding="utf-8")
        return path

    def _s(c: str) -> str:
        return c[:7] if len(c) >= 7 else c

    icon  = "✅ MATCH" if sync.overall_status == "MATCH" else "❌ MISMATCH"
    icon2 = "✅ OK" if (container and container.overall_ok) else "⚠️ CHECK REQUIRED"
    lr    = "✅" if sync.local_remote_match else "❌"
    lv    = "✅" if sync.local_vps_match else "❌"
    lc    = "✅" if sync.local_container_match else "❌"

    drift_rows = ""
    if container and container.drift_files:
        drift_rows = "\n".join(f"- `{f}`" for f in container.drift_files)

    path.write_text(f"""# DEPLOYMENT_VERIFICATION — {today}
_Generated: {ts} | FRZ-001 Phase 3 + 5_

## Synchronization Status: {icon}

| Layer | Commit | Match |
|-------|--------|-------|
| Local | `{_s(sync.local_commit)}` | — |
| Git Remote | `{_s(sync.remote_commit)}` | {lr} |
| VPS | `{_s(sync.vps_commit)}` | {lv} |
| Container | `{_s(sync.container_commit)}` | {lc} |

## Container Consistency: {icon2}

| Check | Status |
|-------|--------|
| Runtime file hashes OK | {'✅' if (container and container.runtime_hashes_ok) else '⚠️'} |
| Main container status | {container.container_status if container else 'UNKNOWN'} |
| Dashboard status | {container.dashboard_status if container else 'UNKNOWN'} |

{('### Drifted Files\\n' + drift_rows) if drift_rows else ''}

## Details

{chr(10).join(f'- {d}' for d in (sync.details + (container.details if container else []))) or '_None_'}

## Governance Rule

> **Deployment is BLOCKED if any layer shows MISMATCH.**
> All four layers (Local → Git → VPS → Container) must be identical.
""", encoding="utf-8")
    return path


def write_container_verification(cv: Optional[ContainerVerification], today: str) -> Path:
    d = _dir(today)
    path = d / "CONTAINER_VERIFICATION.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if cv is None:
        path.write_text(f"# CONTAINER_VERIFICATION — {today}\n\n_Not run._\n", encoding="utf-8")
        return path

    drift_list = "\n".join(f"- `{f}`" for f in cv.drift_files) or "_None_"
    path.write_text(f"""# CONTAINER_VERIFICATION — {today}
_Generated: {ts} | FRZ-001 Phase 5_

## Status: {"✅ CONSISTENT" if cv.overall_ok else "❌ DRIFT DETECTED"}

| Layer | Commit |
|-------|--------|
| Build manifest | `{cv.manifest_commit}` |
| Container | `{cv.container_commit}` |
| Runtime hashes | {'✅ All match' if cv.runtime_hashes_ok else '❌ Drift detected'} |
| Main container | {cv.container_status} |
| Dashboard | {cv.dashboard_status} |

## Drifted Files

{drift_list}
""", encoding="utf-8")
    return path


def write_config_snapshot_report(snap: Optional[ConfigSnapshot], today: str) -> Path:
    d = _dir(today)
    path = d / "CONFIGURATION_SNAPSHOT.md"
    if snap is None:
        path.write_text(f"# CONFIGURATION_SNAPSHOT — {today}\n\n_Not taken._\n", encoding="utf-8")
        return path
    try:
        from .ph2_config_snapshot import build_config_snapshot_md
        path.write_text(build_config_snapshot_md(snap), encoding="utf-8")
    except Exception as e:
        path.write_text(f"# CONFIGURATION_SNAPSHOT\n\n_Error: {e}_\n", encoding="utf-8")
    return path


def write_all_frz_reports(data: Dict[str, Any], today: Optional[str] = None) -> None:
    today = today or datetime.now().date().isoformat()

    write_deployment_verification(
        sync      = data.get("sync"),
        container = data.get("container"),
        today     = today,
    )
    write_container_verification(data.get("container"), today)
    write_config_snapshot_report(data.get("config_snapshot"), today)

    # Startup health report is written by ph9 directly
    # Release certificate is written by ph10 directly
    log.info("[FRZReporter] Reports written to %s", REPORT_DIR / today)
