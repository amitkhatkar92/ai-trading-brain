#!/usr/bin/env python3
"""
healthcheck.py
==============
IIOS Docker Health Check Script

Used by docker-compose.yml:
  healthcheck:
    test: ["CMD", "python", "healthcheck.py"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s

Exit codes:
    0 — healthy (all critical checks pass)
    1 — unhealthy (one or more critical checks failed)

Architecture Reference: INFRA-HLT-001 (HealthService)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone


DB_PATH = os.environ.get("IIOS_DB_PATH", "data/iios.db")
LOG_DIR = os.path.dirname(os.environ.get("IIOS_LOG_FILE", "logs/iios.log")) or "logs"
DATA_DIR = os.path.dirname(DB_PATH) or "data"

StatusDict = dict[str, object]


def _check_database() -> StatusDict:
    """Verify SQLite database is accessible and not corrupted."""
    if not os.path.exists(DB_PATH):
        return {
            "status": "warning",
            "detail": "database not yet created (pre-first-run is normal)",
        }
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        row = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        ok = row is not None and row[0] == "ok"
        return {
            "status": "healthy" if ok else "unhealthy",
            "detail": str(row[0]) if row else "no result",
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "unhealthy", "detail": str(exc)}


def _check_log_dir() -> StatusDict:
    """Verify log directory is writable."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        probe = os.path.join(LOG_DIR, ".hc_probe")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.unlink(probe)
        return {"status": "healthy", "detail": f"{LOG_DIR} writable"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unhealthy", "detail": str(exc)}


def _check_data_dir() -> StatusDict:
    """Verify data directory is writable."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        probe = os.path.join(DATA_DIR, ".hc_probe")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.unlink(probe)
        return {"status": "healthy", "detail": f"{DATA_DIR} writable"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unhealthy", "detail": str(exc)}


def main() -> int:
    """Run health checks. Returns 0 if healthy, 1 if unhealthy."""
    results: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": _check_database(),
        "log_directory": _check_log_dir(),
        "data_directory": _check_data_dir(),
    }

    critical_checks = ["database", "log_directory", "data_directory"]
    all_ok = all(
        isinstance(results[k], dict)
        and results[k].get("status") in ("healthy", "warning")  # type: ignore[union-attr]
        for k in critical_checks
    )

    results["overall"] = "healthy" if all_ok else "unhealthy"

    print(json.dumps(results, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
