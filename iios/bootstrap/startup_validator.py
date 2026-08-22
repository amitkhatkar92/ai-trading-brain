"""
iios/bootstrap/startup_validator.py
======================================
Orchestrates all pre-startup validation checks and produces a single
``ValidationReport`` that the bootstrap engine uses to decide whether
to proceed.

Runs in order:
  1. Repository structure (RepositoryValidator)
  2. Environment variables (EnvironmentLoader)
  3. Configuration constants (ConfigurationLoader)
  4. Package dependencies (DependencyLoader)
  5. Security guard checks

Architecture Reference: IIOS-BSS-001 Stages 1-10 (Pre-Validation)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .configuration_loader import ConfigurationLoader, ConfigurationSnapshot
from .dependency_loader import DependencyLoader, DependencyReport
from .environment_loader import EnvironmentLoader, EnvironmentSnapshot
from .repository_validator import RepositoryReport, RepositoryValidator
from .startup_state import ValidationFinding, ValidationSeverity

__all__ = ["StartupValidator", "ValidationReport"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Aggregated Report
# ---------------------------------------------------------------------------


@dataclass
class ValidationReport:
    """Consolidated pre-startup validation report.

    All blocking findings must be resolved before the bootstrap engine
    proceeds to Stage 11 (Configuration Init).
    """

    started_at: float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None

    repository: Optional[RepositoryReport] = None
    environment: Optional[EnvironmentSnapshot] = None
    configuration: Optional[ConfigurationSnapshot] = None
    dependencies: Optional[DependencyReport] = None

    extra_findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def all_findings(self) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if self.repository:
            findings.extend(self.repository.findings)
        if self.environment:
            findings.extend(self.environment.findings)
        if self.configuration:
            findings.extend(self.configuration.findings)
        if self.dependencies:
            findings.extend(self.dependencies.findings)
        findings.extend(self.extra_findings)
        return findings

    @property
    def blocking_findings(self) -> list[ValidationFinding]:
        return [f for f in self.all_findings if f.blocks_startup]

    @property
    def warning_findings(self) -> list[ValidationFinding]:
        return [
            f for f in self.all_findings
            if f.severity == ValidationSeverity.WARNING
        ]

    @property
    def passed(self) -> bool:
        return len(self.blocking_findings) == 0

    @property
    def duration_ms(self) -> float:
        end = self.completed_at if self.completed_at is not None else time.monotonic()
        return (end - self.started_at) * 1000.0

    def print_summary(self) -> None:
        """Print a human-readable validation summary to the logger."""
        level = "PASS" if self.passed else "FAIL"
        logger.info(
            "Validation %s: %d blocking, %d warnings, %.1f ms",
            level,
            len(self.blocking_findings),
            len(self.warning_findings),
            self.duration_ms,
        )
        for finding in self.blocking_findings:
            logger.error("  BLOCKING: %s", finding)
        for finding in self.warning_findings:
            logger.warning("  WARNING:  %s", finding)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class StartupValidator:
    """Orchestrates all pre-startup validation checks.

    Designed to be called once by ``BootstrapEngine`` before any
    infrastructure is initialized.
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self._root = repo_root or Path(".").resolve()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def validate(self) -> ValidationReport:
        """Run all validation checks and return the aggregated report."""
        report = ValidationReport()
        logger.info("StartupValidator: running pre-startup checks (root=%s)", self._root)

        # Stage 1-5: Repository
        logger.debug("StartupValidator: [1/5] repository structure")
        repo_validator = RepositoryValidator(repo_root=self._root)
        report.repository = repo_validator.validate()

        # Stage 6-10: Environment
        logger.debug("StartupValidator: [2/5] environment variables")
        env_loader = EnvironmentLoader(repo_root=self._root)
        report.environment = env_loader.load()

        # Stage 11-15: Configuration
        logger.debug("StartupValidator: [3/5] configuration constants")
        config_loader = ConfigurationLoader()
        report.configuration = config_loader.load()

        # Stage 6-10 (continued): Dependencies
        logger.debug("StartupValidator: [4/5] package dependencies")
        dep_loader = DependencyLoader()
        report.dependencies = dep_loader.load()

        # Stage: Security guard checks
        logger.debug("StartupValidator: [5/5] security guards")
        self._check_security_guards(report)

        report.completed_at = time.monotonic()
        report.print_summary()
        return report

    def validate_repository_only(self) -> RepositoryReport:
        """Run only repository structure validation (fast pre-check)."""
        return RepositoryValidator(repo_root=self._root).validate()

    # ─────────────────────────────────────────────────────────────────────────
    # Security guards
    # ─────────────────────────────────────────────────────────────────────────

    def _check_security_guards(self, report: ValidationReport) -> None:
        """Apply IIOS security rules that cut across multiple validators."""
        env = report.environment
        config = report.configuration

        if env is None or config is None:
            return

        # Guard 1: live trading requires paper_trading=false AND env=production
        live_trading = env.typed.get("IIOS_ENABLE_LIVE_TRADING", False)
        if live_trading:
            if env.env_name != "production":
                report.extra_findings.append(ValidationFinding(
                    check_name="security_live_trading",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        "IIOS_ENABLE_LIVE_TRADING=true is only permitted in IIOS_ENV=production. "
                        f"Current env: {env.env_name!r}"
                    ),
                    detail="Live order routing from a non-production environment is unsafe",
                    remediation="Set IIOS_ENV=production or IIOS_ENABLE_LIVE_TRADING=false",
                ))
            if config.paper_trading:
                report.extra_findings.append(ValidationFinding(
                    check_name="security_live_trading",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        "IIOS_ENABLE_LIVE_TRADING=true but PAPER_TRADING=True in config.py. "
                        "config.py takes precedence — orders will be simulated."
                    ),
                    detail="Both flags must agree for live trading to activate",
                    remediation="Set PAPER_TRADING=False in config.py to enable live orders",
                ))

        # Guard 2: Dhan token present for live mode
        if live_trading and not env.raw.get("DHAN_ACCESS_TOKEN", ""):
            report.extra_findings.append(ValidationFinding(
                check_name="security_broker_credentials",
                severity=ValidationSeverity.ERROR,
                message="DHAN_ACCESS_TOKEN not set but live trading is enabled",
                detail="All live order routing requires valid broker credentials",
                remediation="Set DHAN_ACCESS_TOKEN in .env.production",
            ))

        # Guard 3: Architecture constants sanity (belt-and-suspenders after config check)
        if config.module_loaded:
            if config.vix_threshold > 100.0 or config.vix_threshold < 10.0:
                report.extra_findings.append(ValidationFinding(
                    check_name="security_vix_threshold",
                    severity=ValidationSeverity.WARNING,
                    message=f"VIX_THRESHOLD={config.vix_threshold} is outside sane range [10, 100]",
                    detail="This may disable the RiskGuardian kill switch under normal conditions",
                    remediation="Restore VIX_THRESHOLD=45.0 in config.py",
                ))
            if config.daily_loss_pct > 0.10:
                report.extra_findings.append(ValidationFinding(
                    check_name="security_daily_loss",
                    severity=ValidationSeverity.WARNING,
                    message=f"DAILY_LOSS_PCT={config.daily_loss_pct:.1%} exceeds 10% — unusually high",
                    detail="This weakens the portfolio drawdown protection",
                    remediation="Restore DAILY_LOSS_PCT=0.02 in config.py",
                ))
