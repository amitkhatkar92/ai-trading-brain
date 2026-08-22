#!/usr/bin/env python3
"""
dev.py
======
IIOS Development Mode Entry Point

Starts IIOS with development defaults:
  - IIOS_ENV=development
  - IIOS_PAPER_TRADING=true
  - IIOS_LOG_LEVEL=DEBUG
  - Loads .env.development

Prints a startup diagnostic before delegating to main.py.

Usage:
    python dev.py

Architecture Reference: IIOS-BSS-001
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import os
import sys


def _print_diagnostic() -> None:
    """Print environment diagnostic for developer awareness."""
    print("=" * 56)
    print("  IIOS Development Mode")
    print("=" * 56)
    print(f"  Python  : {sys.version.split()[0]}")
    print(f"  CWD     : {os.getcwd()}")
    print(f"  ENV     : {os.environ.get('IIOS_ENV', 'development')}")
    print(f"  PAPER   : {os.environ.get('IIOS_PAPER_TRADING', 'true')}")
    print(f"  LOG     : {os.environ.get('IIOS_LOG_LEVEL', 'DEBUG')}")

    try:
        import iios

        print(f"  iios    : v{iios.__version__} [{iios.__status__}]")
    except ImportError:
        print("  iios    : not yet importable (Wave 1 pending)")

    print("=" * 56)


def main() -> int:
    """Development IIOS entry point."""
    # Force development defaults (do not override if already set)
    os.environ.setdefault("IIOS_ENV", "development")
    os.environ.setdefault("IIOS_PAPER_TRADING", "true")
    os.environ.setdefault("IIOS_LOG_LEVEL", "DEBUG")

    # Load .env.development
    try:
        from dotenv import load_dotenv

        if os.path.exists(".env.development"):
            load_dotenv(".env.development", override=False)
    except ImportError:
        print("WARNING: python-dotenv not installed. Run: pip install python-dotenv")

    _print_diagnostic()

    try:
        import main as _main  # noqa: F401 — side-effect import starts orchestrator

        return 0
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    except KeyboardInterrupt:
        print("\nDev session ended by user.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"IIOS dev startup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
