"""
scripts/generate_build_manifest.py
=====================================
Generates build_manifest.json in the project root.

Run this BEFORE docker compose build:
    python scripts/generate_build_manifest.py

The deploy.sh script runs this automatically.
build_manifest.json is excluded from git (.gitignore) but included
in the Docker image via COPY . .
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Project root ───────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent

# Must match deployment/runtime_verifier.TRACKED_FILES exactly
TRACKED_FILES: list[str] = [
    "main.py",
    "config.py",
    "orchestrator/master_orchestrator.py",
    "execution_engine/order_manager.py",
    "risk_guardian/risk_guardian.py",
    "learning_system/strategy_performance_tracker.py",
    "notifications/telegram_bot.py",
    "notifications/notifier_manager.py",
    "data_feeds/data_feed_manager.py",
    "data_feeds/yahoo_feed.py",
    "global_intelligence/global_data_ai.py",
    "deployment/runtime_verifier.py",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(args: list[str], default: str = "unknown") -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else default
    except Exception:
        return default


def generate() -> dict:
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)

    commit      = _git(["rev-parse", "--short", "HEAD"])
    commit_full = _git(["rev-parse", "HEAD"])
    branch      = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    message     = _git(["log", "-1", "--pretty=%s"])

    file_hashes: dict[str, str] = {}
    missing: list[str] = []
    for rel in TRACKED_FILES:
        p = ROOT / rel
        if p.exists():
            file_hashes[rel] = _sha256(p)
        else:
            missing.append(rel)
            print(f"  WARNING: tracked file missing: {rel}", file=sys.stderr)

    manifest = {
        "schema_version":  1,
        "commit":          commit,
        "commit_full":     commit_full,
        "branch":          branch,
        "commit_message":  message,
        "build_timestamp": now.isoformat(),
        "python_version":  platform.python_version(),
        "platform":        platform.system(),
        "file_hashes":     file_hashes,
        "tracked_files":   TRACKED_FILES,
        "missing_files":   missing,
    }
    return manifest


def main() -> None:
    print("Generating build_manifest.json...")
    manifest = generate()
    out_path = ROOT / "build_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  commit  = {manifest['commit']}")
    print(f"  branch  = {manifest['branch']}")
    print(f"  message = {manifest['commit_message']}")
    print(f"  files   = {len(manifest['file_hashes'])} hashed")
    if manifest["missing_files"]:
        print(f"  MISSING = {manifest['missing_files']}")
    print(f"  written → {out_path}")


if __name__ == "__main__":
    main()
