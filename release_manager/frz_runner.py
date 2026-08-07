"""
release_manager/frz_runner.py — FRZ-001 Main Runner.

CLI entry point for all FRZ-001 operations.

Usage:
    python -m release_manager.frz_runner init          # Phase 1: create SYSTEM_VERSION.json
    python -m release_manager.frz_runner snapshot      # Phase 2: config snapshot
    python -m release_manager.frz_runner sync          # Phase 3: sync verification
    python -m release_manager.frz_runner backup        # Phase 4: backup
    python -m release_manager.frz_runner container     # Phase 5: container verify
    python -m release_manager.frz_runner recover       # Phase 6: recovery menu
    python -m release_manager.frz_runner tag           # Phase 7: release tag
    python -m release_manager.frz_runner lock          # Phase 8: production lock check
    python -m release_manager.frz_runner startup       # Phase 9: startup self-check
    python -m release_manager.frz_runner cert          # Phase 10: release certificate
    python -m release_manager.frz_runner deploy        # Full pre-deploy checklist
    python -m release_manager.frz_runner status        # Quick status overview
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


def cmd_init(args) -> int:
    """Phase 1: Create / update SYSTEM_VERSION.json."""
    from .ph1_system_version import create_or_update_version
    bump  = getattr(args, "bump", "patch")
    notes = getattr(args, "notes", "")
    sv = create_or_update_version(bump=bump, release_notes=notes)
    print(f"✅ {sv.release_name} (build {sv.build_number}) — commit {sv.git_commit}")
    return 0


def cmd_snapshot(args) -> int:
    """Phase 2: Config snapshot."""
    from .ph2_config_snapshot import take_config_snapshot
    from .ph1_system_version import load_version
    sv = load_version()
    snap = take_config_snapshot(commit=sv.git_commit if sv else "")
    print(f"✅ Config snapshot: {len(snap.config_params)} params, {len(snap.env_keys)} env keys")
    return 0


def cmd_sync(args) -> int:
    """Phase 3: Sync verification."""
    from .ph3_sync_verify import run_sync_verification
    skip = getattr(args, "skip_container", False)
    result = run_sync_verification(skip_container=skip)
    icon = "✅" if result.overall_status == "MATCH" else "❌"
    print(f"{icon} Sync: {result.overall_status}")
    for d in result.details:
        print(f"  {d}")
    return 0 if result.overall_status == "MATCH" else 1


def cmd_backup(args) -> int:
    """Phase 4: Create backup."""
    from .ph4_backup import create_backup
    record = create_backup()
    icon = "✅" if record.success else "❌"
    print(f"{icon} Backup: {record.backup_id} ({record.files_backed_up} files, {record.size_bytes//1024} KB)")
    return 0 if record.success else 1


def cmd_container(args) -> int:
    """Phase 5: Container verification."""
    from .ph5_container_verify import verify_container_consistency
    cv = verify_container_consistency()
    icon = "✅" if cv.overall_ok else "❌"
    print(f"{icon} Container: {'CONSISTENT' if cv.overall_ok else 'DRIFT DETECTED'}")
    for d in cv.details:
        print(f"  {d}")
    return 0 if cv.overall_ok else 1


def cmd_recover(args) -> int:
    """Phase 6: Recovery."""
    from .ph6_recovery import list_recovery_points, recover
    points = list_recovery_points()
    if not points:
        print("❌ No recovery points available")
        return 1

    target = getattr(args, "target", "latest")
    bkp_id = getattr(args, "backup_id", None)
    dry    = getattr(args, "dry_run", False)

    if target == "list":
        print(f"\nAvailable recovery points ({len(points)}):")
        for i, p in enumerate(points[:10]):
            cert = "✅" if p.is_certified else "  "
            print(f"  {cert} [{i}] {p.backup_id}  commit={p.git_commit}  version={p.version}")
        return 0

    result = recover(backup_id=bkp_id, target=target, dry_run=dry)
    icon = "✅" if result.get("ok") else "❌"
    print(f"{icon} Recovery: {result.get('recovery_point', '?')}")
    for s in result.get("steps", []):
        print(f"  {s}")
    return 0 if result.get("ok") else 1


def cmd_tag(args) -> int:
    """Phase 7: Release tagging."""
    from .ph7_release_tagging import create_release_tag, list_release_tags
    if getattr(args, "list", False):
        tags = list_release_tags()
        for t in tags:
            print(f"  {t.tag_name}  commit={t.git_commit}")
        return 0
    version = getattr(args, "version", None)
    notes   = getattr(args, "notes", "")
    no_push = getattr(args, "no_push", False)
    tag = create_release_tag(version=version, release_notes=notes, push=not no_push)
    print(f"✅ Tagged: {tag.tag_name} at {tag.git_commit}")
    return 0


def cmd_lock(args) -> int:
    """Phase 8: Production lock check."""
    from .ph8_production_lock import check_production_lock, confirm_production_changes
    confirm = getattr(args, "confirm", False)
    reason  = getattr(args, "reason", "")

    if confirm:
        ok = confirm_production_changes(reason or "Acknowledged via CLI")
        print(f"{'✅' if ok else '❌'} Lock hashes updated")
        return 0 if ok else 1

    status = check_production_lock()
    if status.requires_confirmation:
        print("⚠️  PRODUCTION LOCK: Architecture is FROZEN")
        print(f"    {len(status.changed_protected_modules)} protected module(s) changed:")
        for m in status.changed_protected_modules:
            print(f"    - {m}")
        print("\n  Run with --confirm --reason '<reason>' to acknowledge changes.")
        return 1
    elif status.changed_protected_modules:
        print(f"⚠️  {len(status.changed_protected_modules)} module(s) changed (system not locked)")
        return 0
    else:
        print("✅ Production lock: all protected modules unchanged")
        return 0


def cmd_startup(args) -> int:
    """Phase 9: Startup self-check."""
    from .ph9_startup_check import run_startup_check, write_startup_health_report
    today = getattr(args, "date", None) or datetime.now().date().isoformat()
    result = run_startup_check(today=today)
    report = write_startup_health_report(result, today=today)
    icon = "✅" if result.overall_ok else "❌"
    print(f"{icon} Startup check: {'HEALTHY' if result.overall_ok else 'ISSUES FOUND'}")
    print(f"  Disk: {result.disk_free_gb:.1f}GB free | Mem: {result.memory_free_mb:.0f}MB | CPU: {result.cpu_pct:.0f}%")
    print(f"  Broker: {result.broker_connection} | Report: {report}")
    if result.failed_checks:
        print(f"  ❌ Failed: {', '.join(result.failed_checks)}")
    if result.warnings:
        print(f"  ⚠️  Warnings: {', '.join(result.warnings)}")
    return 0 if result.overall_ok else 1


def cmd_cert(args) -> int:
    """Phase 10: Release certificate."""
    today = getattr(args, "date", None) or datetime.now().date().isoformat()
    data  = _collect_frz_data(today, quick=True)
    cert  = data.get("release_cert")
    if cert:
        from .ph10_release_cert import write_release_certificate
        path = write_release_certificate(cert, today=today)
        print(f"✅ Release certificate: {path}")
        print(f"  Readiness: {cert.production_readiness}")
        print(f"  SD: {cert.scientific_director_approval} | MA: {cert.methodology_auditor_approval}")
        return 0
    print("❌ Certificate generation failed")
    return 1


def cmd_deploy(args) -> int:
    """Full pre-deploy checklist (Phases 1-4 + 8)."""
    print("\n" + "="*55)
    print("  FRZ-001 Pre-Deployment Checklist")
    print("="*55)
    today = datetime.now().date().isoformat()
    rc = 0

    # Phase 8: production lock
    from .ph8_production_lock import check_production_lock
    lock = check_production_lock()
    if lock.requires_confirmation:
        print("❌ BLOCKED: Protected modules changed. Run 'lock --confirm' first.")
        return 1
    print("✅ Phase 8: Production lock — no protected changes")

    # Phase 2: config snapshot
    try:
        from .ph2_config_snapshot import take_config_snapshot
        from .ph1_system_version import load_version
        sv = load_version()
        take_config_snapshot(commit=sv.git_commit if sv else "")
        print("✅ Phase 2: Config snapshot taken")
    except Exception as e:
        print(f"⚠️  Phase 2: Config snapshot failed ({e})")

    # Phase 4: backup
    from .ph4_backup import create_backup
    bkp = create_backup()
    if bkp.success:
        print(f"✅ Phase 4: Backup created ({bkp.backup_id})")
    else:
        print(f"⚠️  Phase 4: Local backup failed — {bkp.error}")

    # Phase 3: sync verify (pre-deploy: skip container)
    from .ph3_sync_verify import run_sync_verification
    sync = run_sync_verification(skip_container=True)
    if sync.overall_status == "MATCH":
        print(f"✅ Phase 3: Sync verified — {sync.local_commit[:7]}")
    else:
        print("❌ BLOCKED: Sync MISMATCH — push your changes before deploying")
        for d in sync.details:
            print(f"   {d}")
        return 1

    print("\n✅ Pre-deploy checklist PASSED — proceed with deployment\n")
    return 0


def cmd_status(args) -> int:
    """Quick status overview."""
    today = datetime.now().date().isoformat()
    print(f"\n{'='*50}")
    print(f"  IIOS FRZ-001 Status — {today}")
    print(f"{'='*50}")

    try:
        from .ph1_system_version import load_version
        sv = load_version()
        if sv:
            print(f"  Version:    {sv.release_name}")
            print(f"  Commit:     {sv.git_commit}")
            print(f"  FRZ Status: {sv.frz_status}")
            print(f"  PRR Status: {sv.certification_status}")
        else:
            print("  Version:    ⚠️  SYSTEM_VERSION.json not found — run 'init'")
    except Exception as e:
        print(f"  Version:    ERROR — {e}")

    try:
        from .ph8_production_lock import check_production_lock
        lock = check_production_lock()
        changed = len(lock.changed_protected_modules)
        print(f"  Lock:       {'✅ LOCKED' if lock.is_locked else 'DEVELOPMENT'} ({changed} modules changed)")
    except Exception as e:
        print(f"  Lock:       ERROR — {e}")

    try:
        from .ph4_backup import list_local_backups
        bkps = list_local_backups()
        print(f"  Backups:    {len(bkps)} local backups available")
    except Exception:
        print("  Backups:    Unknown")

    print(f"{'='*50}\n")
    return 0


def run_startup_checks(today: Optional[str] = None) -> Dict[str, Any]:
    """Callable from main.py during --schedule startup. Non-blocking."""
    from .ph9_startup_check import run_startup_check, write_startup_health_report
    today = today or datetime.now().date().isoformat()
    result = run_startup_check(today=today)
    write_startup_health_report(result, today=today)
    return {
        "ok":            result.overall_ok,
        "failed_checks": result.failed_checks,
        "warnings":      result.warnings,
        "broker_mode":   result.broker_connection,
    }


def _collect_frz_data(today: str, quick: bool = False) -> Dict[str, Any]:
    """Collect all FRZ phase outputs for reporting."""
    data: Dict[str, Any] = {"date": today}

    try:
        from .ph1_system_version import load_version
        data["system_version"] = load_version()
    except Exception:
        data["system_version"] = None

    try:
        from .ph9_startup_check import run_startup_check
        data["startup"] = run_startup_check(today=today)
    except Exception as e:
        log.debug("[FRZRunner] Startup check failed: %s", e)
        data["startup"] = None

    try:
        from .ph8_production_lock import check_production_lock
        data["lock_status"] = check_production_lock()
    except Exception:
        data["lock_status"] = None

    # PRR-001 integration
    prr_verdict = "UNKNOWN"
    ils_score   = 0.0
    gva_score   = 0.0
    try:
        from production_readiness.prr_runner import run_prr
        prr = run_prr(report_date=today, dry_run=True)
        prr_verdict = prr.get("certification_status", "UNKNOWN")
        ils_score   = prr.get("ils_score", 0.0)
        gva_score   = prr.get("gva_score", 0.0)
    except Exception as e:
        log.debug("[FRZRunner] PRR check failed: %s", e)

    # Build release cert
    try:
        from .ph10_release_cert import build_release_certificate
        data["release_cert"] = build_release_certificate(
            sv          = data.get("system_version"),
            sync        = data.get("sync"),
            container   = data.get("container"),
            backup      = data.get("backup"),
            startup     = data.get("startup"),
            lock_status = data.get("lock_status"),
            prr_verdict = prr_verdict,
            ils_score   = ils_score,
            gva_score   = gva_score,
            today       = today,
        )
    except Exception as e:
        log.debug("[FRZRunner] Cert build failed: %s", e)
        data["release_cert"] = None

    return data


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _main():
    import sys, io
    # Force UTF-8 on Windows consoles that default to cp1252
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-8s %(message)s")

    parser = argparse.ArgumentParser(
        description="FRZ-001 Architecture Freeze & Release Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # init
    p_init = sub.add_parser("init", help="Create/update SYSTEM_VERSION.json")
    p_init.add_argument("--bump", choices=["major","minor","patch","none"], default="patch")
    p_init.add_argument("--notes", default="")

    # snapshot
    sub.add_parser("snapshot", help="Take config snapshot")

    # sync
    p_sync = sub.add_parser("sync", help="Sync verification")
    p_sync.add_argument("--skip-container", action="store_true")

    # backup
    sub.add_parser("backup", help="Create backup")

    # container
    sub.add_parser("container", help="Container consistency check")

    # recover
    p_rec = sub.add_parser("recover", help="Recovery")
    p_rec.add_argument("--target", choices=["latest","previous","specific","list"], default="list")
    p_rec.add_argument("--backup-id", default=None)
    p_rec.add_argument("--dry-run", action="store_true")

    # tag
    p_tag = sub.add_parser("tag", help="Release tagging")
    p_tag.add_argument("--version", default=None)
    p_tag.add_argument("--notes", default="")
    p_tag.add_argument("--no-push", action="store_true")
    p_tag.add_argument("--list", action="store_true")

    # lock
    p_lock = sub.add_parser("lock", help="Production lock check")
    p_lock.add_argument("--confirm", action="store_true")
    p_lock.add_argument("--reason", default="")

    # startup
    p_startup = sub.add_parser("startup", help="Startup self-check")
    p_startup.add_argument("--date", default=None)

    # cert
    p_cert = sub.add_parser("cert", help="Release certificate")
    p_cert.add_argument("--date", default=None)

    # deploy (pre-deploy checklist)
    sub.add_parser("deploy", help="Pre-deploy checklist")

    # status
    sub.add_parser("status", help="Quick status overview")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    cmd_map = {
        "init":      cmd_init,
        "snapshot":  cmd_snapshot,
        "sync":      cmd_sync,
        "backup":    cmd_backup,
        "container": cmd_container,
        "recover":   cmd_recover,
        "tag":       cmd_tag,
        "lock":      cmd_lock,
        "startup":   cmd_startup,
        "cert":      cmd_cert,
        "deploy":    cmd_deploy,
        "status":    cmd_status,
    }
    fn = cmd_map.get(args.command)
    if fn:
        sys.exit(fn(args))
    parser.print_help()


if __name__ == "__main__":
    _main()
