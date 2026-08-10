#!/usr/bin/env python3
"""
scripts/sync_env_from_vps.py — Pull VPS .env token fields to local .env.

Run this after sending /token via Telegram to keep the local dev machine in sync.
Only syncs DHAN_ACCESS_TOKEN (and optionally DHAN_CLIENT_ID).
Never touches secrets that are local-only (e.g. ZERODHA_*).

Usage:
    python scripts/sync_env_from_vps.py
    python scripts/sync_env_from_vps.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

VPS_HOST    = "root@178.18.252.24"
SSH_KEY     = str(Path.home() / ".ssh" / "trading_vps")
VPS_ENV     = "/root/ai-trading-brain/.env"
LOCAL_ENV   = Path(__file__).parent.parent / ".env"

# Fields pulled from VPS → local (order matters for display)
SYNC_FIELDS = ["DHAN_ACCESS_TOKEN", "DHAN_CLIENT_ID", "ACTIVE_BROKER"]


def _vps_field(field: str) -> str | None:
    """SSH-read a single field from VPS .env without exposing the value in shell."""
    cmd = ["ssh", "-i", SSH_KEY, VPS_HOST,
           f"grep '^{field}' {VPS_ENV} | head -1"]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=15)
        line = out.decode().strip()
        if "=" not in line:
            return None
        return line.split("=", 1)[1].strip()
    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        print(f"  SSH error reading {field}: {e}", file=sys.stderr)
        return None


def _update_local(field: str, value: str, dry_run: bool) -> bool:
    """Update or insert `field = value` in local .env."""
    if not LOCAL_ENV.exists():
        print(f"  LOCAL .env not found at {LOCAL_ENV}", file=sys.stderr)
        return False
    lines = LOCAL_ENV.read_text(encoding="utf-8").splitlines(keepends=True)
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(field):
            old_val = line.split("=", 1)[1].strip() if "=" in line else ""
            if old_val == value:
                print(f"  {field}: already up-to-date (suffix=...{value[-8:]})")
                return True
            if not dry_run:
                lines[i] = f"{field} = {value}\n"
            updated = True
            print(f"  {field}: updated (suffix=...{value[-8:]})")
            break
    if not updated:
        if not dry_run:
            lines.append(f"{field} = {value}\n")
        print(f"  {field}: inserted (suffix=...{value[-8:]})")
    if not dry_run:
        LOCAL_ENV.write_text("".join(lines), encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="Sync VPS .env token to local .env")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing")
    args = parser.parse_args()

    print(f"Syncing from VPS ({VPS_HOST}:{VPS_ENV}) → local ({LOCAL_ENV})")
    if args.dry_run:
        print("[DRY RUN]")

    any_change = False
    for field in SYNC_FIELDS:
        value = _vps_field(field)
        if value is None:
            print(f"  {field}: not found on VPS — skipped")
            continue
        changed = _update_local(field, value, dry_run=args.dry_run)
        any_change = any_change or changed

    if any_change and not args.dry_run:
        print("\nLocal .env updated. Reload dotenv in any running local process to apply.")
    elif not args.dry_run:
        print("\nNothing to update.")


if __name__ == "__main__":
    main()
