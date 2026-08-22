#!/usr/bin/env python3
"""
run.py
======
IIOS Production Entry Point

Validates runtime prerequisites, loads the correct .env file,
then delegates execution to main.py.

Usage:
    python run.py                     # Production mode
    python run.py --paper             # Paper trading mode
    python run.py --telegram          # With Telegram bot
    python run.py --status            # System status

Architecture Reference: IIOS-BSS-001 (System Bootstrap Specification)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import os
import sys


def _load_environment() -> None:
    """Load the .env file matching IIOS_ENV (default: development)."""
    env_name = os.environ.get("IIOS_ENV", "development")
    candidates = [
        f".env.{env_name}",
        ".env",
        ".env.example",
    ]
    try:
        from dotenv import load_dotenv

        for candidate in candidates:
            if os.path.exists(candidate):
                load_dotenv(candidate, override=False)
                break
    except ImportError:
        pass  # dotenv optional; env vars may already be set externally


def _check_python() -> bool:
    """Verify Python >= 3.12."""
    if sys.version_info < (3, 12):
        print(
            f"ERROR: IIOS requires Python >= 3.12. Got: {sys.version_info.major}"
            f".{sys.version_info.minor}",
            file=sys.stderr,
        )
        return False
    return True


def main() -> int:
    """IIOS production entry point."""
    if not _check_python():
        return 1

    _load_environment()

    try:
        import main as _main  # noqa: F401 — side-effect import starts orchestrator

        return 0
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"IIOS startup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
