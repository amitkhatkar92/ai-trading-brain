#!/usr/bin/env python3
"""
bootstrap.py
============
IIOS Bootstrap Verification Script

Pre-implementation readiness check. Verifies the repository is correctly
structured and the environment is configured before Wave 1 development begins.

This is NOT the production 45-stage bootstrap (see iios/bootstrap/).
This is a developer-facing verification tool.

Usage:
    python bootstrap.py               # Full verification table
    python bootstrap.py --quick       # Exit-code only (0=pass)

Architecture Reference: IIOS-BSS-001 — Pre-Condition checks
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import NamedTuple


class Check(NamedTuple):
    name: str
    passed: bool
    detail: str
    critical: bool = True


# =============================================================================
# Individual checks
# =============================================================================


def check_python_version() -> Check:
    ok = sys.version_info >= (3, 12)
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return Check("python_version", ok, ver)


def check_iios_package() -> Check:
    try:
        import iios

        return Check("iios_package", True, f"v{iios.__version__} status={iios.__status__}")
    except ImportError as exc:
        return Check(
            "iios_package",
            False,
            f"ImportError: {exc} — run: pip install -e .",
            critical=False,  # Expected before Wave 1 completes
        )


def check_required_packages() -> Check:
    probes = {
        "dotenv": "python-dotenv",
        "pandas": "pandas",
        "numpy": "numpy",
        "yfinance": "yfinance",
        "requests": "requests",
        "schedule": "schedule",
        "streamlit": "streamlit",
        "loguru": "loguru",
    }
    missing = [pip for mod, pip in probes.items() if _try_import(mod)]
    if missing:
        return Check(
            "dependencies",
            False,
            f"Missing: {', '.join(missing)} — run: pip install -r requirements.txt",
        )
    return Check("dependencies", True, f"{len(probes)} core packages installed")


def _try_import(module: str) -> str | None:
    """Return module name if import fails, else None."""
    try:
        importlib.import_module(module)
        return None
    except ImportError:
        return module


def check_directory_structure() -> Check:
    base = Path(__file__).parent
    required = [
        "iios",
        "iios/core",
        "iios/infrastructure",
        "iios/knowledge",
        "iios/reasoning",
        "iios/risk",
        "iios/execution",
        "tests",
        "tests/unit",
        "tests/integration",
        "scripts",
        "docs",
        "data",
    ]
    missing = [d for d in required if not (base / d).is_dir()]
    if missing:
        return Check("directory_structure", False, f"Missing dirs: {', '.join(missing)}")
    return Check("directory_structure", True, f"{len(required)} directories present")


def check_iios_packages_init() -> Check:
    """Spot-check that key iios sub-packages have __init__.py."""
    base = Path(__file__).parent
    packages = [
        "iios/__init__.py",
        "iios/core/__init__.py",
        "iios/infrastructure/__init__.py",
        "iios/knowledge/__init__.py",
    ]
    missing = [p for p in packages if not (base / p).exists()]
    if missing:
        return Check("iios_init_files", False, f"Missing: {', '.join(missing)}")
    return Check("iios_init_files", True, f"{len(packages)} __init__.py files present")


def check_config() -> Check:
    try:
        import config  # type: ignore[import]  # noqa: PLC0415

        attrs = ["PAPER_TRADING"]
        missing = [a for a in attrs if not hasattr(config, a)]
        if missing:
            return Check("config_module", False, f"Missing constants: {', '.join(missing)}")
        paper = getattr(config, "PAPER_TRADING", None)
        return Check("config_module", True, f"PAPER_TRADING={paper}")
    except ImportError as exc:
        return Check("config_module", False, f"Cannot import config.py: {exc}")


def check_env_file() -> Check:
    candidates = [".env.development", ".env", ".env.example"]
    found = [f for f in candidates if os.path.exists(f)]
    if found:
        return Check("env_file", True, f"Found: {', '.join(found)}")
    return Check(
        "env_file",
        False,
        "No .env file found — copy .env.example to .env.development",
    )


def check_data_dir_writable() -> Check:
    try:
        os.makedirs("data", exist_ok=True)
        probe = "data/.bootstrap_probe"
        with open(probe, "w") as fh:
            fh.write("ok")
        os.unlink(probe)
        return Check("data_dir_writable", True, "data/ is writable")
    except OSError as exc:
        return Check("data_dir_writable", False, str(exc))


def check_pyproject() -> Check:
    exists = os.path.exists("pyproject.toml")
    return Check("pyproject_toml", exists, "found" if exists else "missing — run git pull")


# =============================================================================
# Runner
# =============================================================================


def main() -> int:
    quick = "--quick" in sys.argv

    checks = [
        check_python_version(),
        check_iios_package(),
        check_required_packages(),
        check_directory_structure(),
        check_iios_packages_init(),
        check_config(),
        check_env_file(),
        check_data_dir_writable(),
        check_pyproject(),
    ]

    if quick:
        failures = [c for c in checks if not c.passed and c.critical]
        return 1 if failures else 0

    print("=" * 62)
    print("  IIOS Bootstrap Verification")
    print("  Foundation: IIOS-FCR-001 (CERTIFIED)")
    print("=" * 62)

    passed = 0
    failed = 0
    warned = 0

    for check in checks:
        if check.passed:
            tag = " OK "
            label = "PASS"
            passed += 1
        elif not check.critical:
            tag = "WARN"
            label = "SKIP"
            warned += 1
        else:
            tag = "FAIL"
            label = "FAIL"
            failed += 1

        print(f"  [{tag}] {label:<4}  {check.name:<30}  {check.detail}")

    print("=" * 62)
    print(f"  Results:  {passed} passed / {warned} warnings / {failed} failed")

    if failed == 0:
        print("  STATUS:   READY — Wave 1 implementation can begin.")
    else:
        print("  STATUS:   NOT READY — resolve FAIL items before proceeding.")

    print("=" * 62)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
