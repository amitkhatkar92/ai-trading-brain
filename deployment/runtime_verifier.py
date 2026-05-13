"""
deployment/runtime_verifier.py
================================
Runtime verification of build integrity.

At startup this module:
  1. Reads /app/build_manifest.json (baked into the Docker image at build time).
  2. Computes live SHA-256 of every tracked file inside the container.
  3. Compares live hashes against the manifest.
  4. Logs [RuntimeVerifier] status lines.
  5. If any file differs → logs [DeploymentDrift] and sends a Telegram alert.

Called from main.py during --schedule startup.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("deployment.runtime_verifier")

# ── Files whose hashes are recorded in the build manifest ─────────────────
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

# Project root is one level above this file (deployment/)
_ROOT = Path(__file__).parent.parent
_MANIFEST_PATH   = _ROOT / "build_manifest.json"
_DEPLOY_REC_PATH = _ROOT / "data" / "deploy_record.json"


# ── Helpers ────────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    """Return hex SHA-256 of *path*, or empty string if file is missing."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return ""


def get_manifest() -> dict[str, Any]:
    """Load build_manifest.json, return empty dict if missing."""
    try:
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        log.warning("[RuntimeVerifier] Cannot read manifest: %s", exc)
        return {}


def get_deploy_record() -> dict[str, Any]:
    """Load data/deploy_record.json, return empty dict if missing."""
    try:
        return json.loads(_DEPLOY_REC_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        log.warning("[RuntimeVerifier] Cannot read deploy record: %s", exc)
        return {}


# ── Main verification ──────────────────────────────────────────────────────

def verify(send_alert: bool = True) -> dict[str, Any]:
    """
    Compare runtime file hashes against the build manifest.

    Returns:
        {
            "ok":          bool,          # True = no drift
            "drift_files": list[str],     # files that differ
            "verified":    int,           # files that matched
            "total":       int,           # files checked
            "manifest":    dict,          # raw manifest data
        }
    """
    manifest = get_manifest()
    recorded_hashes: dict[str, str] = manifest.get("file_hashes", {})

    if not manifest:
        log.warning(
            "[RuntimeVerifier] build_manifest.json not found — "
            "run scripts/generate_build_manifest.py before docker build."
        )
        return {"ok": False, "drift_files": [], "verified": 0, "total": 0, "manifest": {}}

    commit = manifest.get("commit", "unknown")
    built  = manifest.get("build_timestamp", "unknown")
    log.info("[RuntimeVerifier] Manifest loaded — commit=%s  built=%s", commit, built)

    drift_files: list[str] = []
    verified    = 0

    for rel_path in TRACKED_FILES:
        abs_path = _ROOT / rel_path
        live_hash = _sha256(abs_path)
        recorded  = recorded_hashes.get(rel_path, "")

        if not recorded:
            # File not in manifest (added after last build) — skip silently
            continue

        if live_hash == recorded:
            verified += 1
        else:
            drift_files.append(rel_path)
            log.error(
                "[DeploymentDrift] %s  recorded=%s  live=%s",
                rel_path, recorded[:12], live_hash[:12] if live_hash else "MISSING",
            )

    total = len([f for f in TRACKED_FILES if f in recorded_hashes])
    ok    = (len(drift_files) == 0)

    if ok:
        log.info(
            "[RuntimeVerifier] ✅ %d/%d files verified — no drift detected.",
            verified, total,
        )
    else:
        log.error(
            "[DeploymentDrift] ⚠️  %d/%d files drifted: %s",
            len(drift_files), total, ", ".join(drift_files),
        )
        if send_alert:
            _send_drift_alert(drift_files, manifest)

    return {
        "ok":          ok,
        "drift_files": drift_files,
        "verified":    verified,
        "total":       total,
        "manifest":    manifest,
    }


def _send_drift_alert(drift_files: list[str], manifest: dict) -> None:
    """Fire a Telegram alert for drift (best-effort, never raises)."""
    try:
        from notifications.notifier_manager import get_notifier
        notifier = get_notifier()
        commit   = manifest.get("commit", "?")
        lines    = "\n".join(f"  • {f}" for f in drift_files)
        msg = (
            "⚠️ <b>[DeploymentDrift] Runtime mismatch detected</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"COMMIT = <code>{commit}</code>\n\n"
            f"Files differ from build manifest:\n{lines}\n\n"
            "This usually means files were manually edited inside the container.\n"
            "<b>Deploy a fresh image via deploy.sh to restore integrity.</b>"
        )
        notifier.send_alert(msg)
    except Exception as exc:
        log.warning("[RuntimeVerifier] Could not send drift alert: %s", exc)
