"""
iios/bootstrap/repository_validator.py
=========================================
Validates the IIOS repository structure before any other stage runs.

Checks:
  - Python runtime version >= 3.12
  - Required top-level directories exist
  - Required iios sub-packages have __init__.py
  - Required files (config.py, main.py, pyproject.toml, etc.) are present
  - data/ and logs/ directories are writable

Architecture Reference: IIOS-BSS-001 Stage 1-5 (Pre-Validation)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .startup_state import ValidationFinding, ValidationSeverity

__all__ = ["RepositoryValidator", "RepositoryReport"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Required structure declarations
# ---------------------------------------------------------------------------

_REQUIRED_DIRS: list[str] = [
    "iios",
    "iios/core",
    "iios/infrastructure",
    "iios/knowledge",
    "iios/reasoning",
    "iios/market",
    "iios/risk",
    "iios/execution",
    "iios/decisions",
    "iios/learning",
    "iios/monitoring",
    "iios/bootstrap",
    "iios/agents",
    "iios/models",
    "iios/integrations",
    "tests",
    "tests/unit",
    "tests/integration",
    "data",
    "logs",
]

_REQUIRED_FILES: list[str] = [
    "config.py",
    "main.py",
    "pyproject.toml",
    "requirements.txt",
]

_REQUIRED_INIT_PACKAGES: list[str] = [
    "iios",
    "iios/core",
    "iios/infrastructure",
    "iios/knowledge",
    "iios/bootstrap",
]

_WRITABLE_DIRS: list[str] = [
    "data",
    "logs",
]

MIN_PYTHON = (3, 12)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class RepositoryReport:
    """Aggregated result of repository validation."""

    python_version: str = ""
    python_ok: bool = False
    repo_root: Path = field(default_factory=lambda: Path(".").resolve())
    directories_ok: bool = False
    files_ok: bool = False
    packages_ok: bool = False
    write_access_ok: bool = False
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.blocks_startup for f in self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.blocks_startup)

    @property
    def warning_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.severity == ValidationSeverity.WARNING
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class RepositoryValidator:
    """Validates the IIOS repository structure and runtime prerequisites.

    All checks produce ``ValidationFinding`` objects at appropriate severity
    levels. Critical and error findings block startup; warnings are logged
    but do not prevent startup.
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self._root = repo_root or Path(".").resolve()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def validate(self) -> RepositoryReport:
        """Run all repository validation checks and return a report."""
        report = RepositoryReport(repo_root=self._root)
        logger.debug("RepositoryValidator: root=%s", self._root)

        self._check_python_version(report)
        self._check_directories(report)
        self._check_files(report)
        self._check_init_packages(report)
        self._check_write_access(report)

        level = "PASS" if report.passed else "FAIL"
        logger.info(
            "RepositoryValidator: %s (%d errors, %d warnings)",
            level,
            report.error_count,
            report.warning_count,
        )
        return report

    # ─────────────────────────────────────────────────────────────────────────
    # Internal checks
    # ─────────────────────────────────────────────────────────────────────────

    def _check_python_version(self, report: RepositoryReport) -> None:
        vi = sys.version_info
        report.python_version = f"{vi.major}.{vi.minor}.{vi.micro}"
        report.python_ok = vi >= MIN_PYTHON

        if report.python_ok:
            logger.debug("Python version: %s OK", report.python_version)
        else:
            report.findings.append(ValidationFinding(
                check_name="python_version",
                severity=ValidationSeverity.CRITICAL,
                message=f"Python {report.python_version} is below the required minimum {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
                detail=f"Detected: {sys.version}",
                remediation=f"Upgrade to Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
            ))

    def _check_directories(self, report: RepositoryReport) -> None:
        missing: list[str] = []
        created: list[str] = []

        for rel_path in _REQUIRED_DIRS:
            full = self._root / rel_path
            if full.is_dir():
                continue
            # Auto-create data/ and logs/ if they don't exist
            if rel_path in _WRITABLE_DIRS:
                try:
                    full.mkdir(parents=True, exist_ok=True)
                    created.append(rel_path)
                    logger.debug("Auto-created directory: %s", rel_path)
                    continue
                except OSError as exc:
                    report.findings.append(ValidationFinding(
                        check_name="directory_create",
                        severity=ValidationSeverity.ERROR,
                        message=f"Cannot create required directory: {rel_path}",
                        detail=str(exc),
                        remediation=f"Manually create {full}",
                    ))
                    missing.append(rel_path)
            else:
                missing.append(rel_path)

        if missing:
            for d in missing:
                report.findings.append(ValidationFinding(
                    check_name="directory_structure",
                    severity=ValidationSeverity.ERROR,
                    message=f"Required directory missing: {d}",
                    detail=str(self._root / d),
                    remediation="Run: git checkout main && git pull",
                ))
            report.directories_ok = False
        else:
            report.directories_ok = True
            if created:
                logger.info("Auto-created directories: %s", ", ".join(created))

    def _check_files(self, report: RepositoryReport) -> None:
        missing: list[str] = []
        for rel_path in _REQUIRED_FILES:
            if not (self._root / rel_path).is_file():
                missing.append(rel_path)

        if missing:
            for f in missing:
                report.findings.append(ValidationFinding(
                    check_name="required_files",
                    severity=ValidationSeverity.ERROR,
                    message=f"Required file missing: {f}",
                    detail=str(self._root / f),
                    remediation="Run: git checkout main && git pull",
                ))
            report.files_ok = False
        else:
            report.files_ok = True

    def _check_init_packages(self, report: RepositoryReport) -> None:
        missing: list[str] = []
        for pkg_rel in _REQUIRED_INIT_PACKAGES:
            init_file = self._root / pkg_rel / "__init__.py"
            if not init_file.is_file():
                missing.append(f"{pkg_rel}/__init__.py")

        if missing:
            for m in missing:
                report.findings.append(ValidationFinding(
                    check_name="package_init",
                    severity=ValidationSeverity.ERROR,
                    message=f"Package __init__.py missing: {m}",
                    detail=str(self._root / m),
                    remediation="Run: git checkout main && git pull",
                ))
            report.packages_ok = False
        else:
            report.packages_ok = True

    def _check_write_access(self, report: RepositoryReport) -> None:
        failures: list[str] = []
        for rel_path in _WRITABLE_DIRS:
            full = self._root / rel_path
            probe = full / ".write_probe"
            try:
                full.mkdir(parents=True, exist_ok=True)
                probe.write_text("ok")
                probe.unlink()
            except OSError as exc:
                failures.append(rel_path)
                report.findings.append(ValidationFinding(
                    check_name="write_access",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Directory not writable: {rel_path}",
                    detail=str(exc),
                    remediation=f"Fix permissions on {full}",
                ))

        report.write_access_ok = len(failures) == 0
