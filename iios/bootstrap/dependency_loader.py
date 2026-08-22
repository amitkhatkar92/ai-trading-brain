"""
iios/bootstrap/dependency_loader.py
======================================
Discovers and validates Python package dependencies.

Separates packages into three tiers:
  1. CRITICAL — missing = startup blocked
  2. REQUIRED — missing = degraded mode with warning
  3. OPTIONAL — missing = feature unavailable

Also exposes ``load_package`` for safe runtime importing with rich
error context, and ``PackageRegistry`` for querying what is available.

Architecture Reference: IIOS-BSS-001 Stages 6-10 (Environment Init)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .startup_state import ValidationFinding, ValidationSeverity

__all__ = [
    "DependencyLoader",
    "DependencyTier",
    "PackageSpec",
    "PackageRegistry",
    "DependencyReport",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Package tiers
# ---------------------------------------------------------------------------


class DependencyTier(Enum):
    CRITICAL = "critical"   # Startup fails without this
    REQUIRED = "required"   # Degraded mode without this
    OPTIONAL = "optional"   # Feature unavailable without this


@dataclass(frozen=True)
class PackageSpec:
    """Specification of a required Python package."""

    import_name: str            # Name used in `import <import_name>`
    pip_name: str               # Name used in `pip install <pip_name>`
    tier: DependencyTier
    min_version: str = ""
    feature: str = ""           # Human-readable feature description
    alternatives: tuple[str, ...] = ()  # Alternative import names to try


# ---------------------------------------------------------------------------
# Known package declarations
# ---------------------------------------------------------------------------

_PACKAGES: list[PackageSpec] = [
    # Critical — must import successfully
    PackageSpec("pandas",      "pandas",         DependencyTier.CRITICAL,  feature="Data processing"),
    PackageSpec("numpy",       "numpy",          DependencyTier.CRITICAL,  feature="Numerical computing"),
    PackageSpec("requests",    "requests",       DependencyTier.CRITICAL,  feature="HTTP client"),
    PackageSpec("schedule",    "schedule",       DependencyTier.CRITICAL,  feature="Intraday scheduler"),
    PackageSpec("loguru",      "loguru",         DependencyTier.CRITICAL,  feature="Structured logging"),

    # Required — degraded mode without
    PackageSpec("yfinance",    "yfinance",       DependencyTier.REQUIRED,  feature="Yahoo Finance fallback feed"),
    PackageSpec("sklearn",     "scikit-learn",   DependencyTier.REQUIRED,  feature="MetaLearning k-NN predictor"),
    PackageSpec("dotenv",      "python-dotenv",  DependencyTier.REQUIRED,  feature="Environment variable loading"),
    PackageSpec("streamlit",   "streamlit",      DependencyTier.REQUIRED,  feature="Layer 17 ControlTower dashboard"),
    PackageSpec("scipy",       "scipy",          DependencyTier.REQUIRED,  feature="Statistical analysis"),

    # Optional — feature disabled if missing
    PackageSpec("dhanhq",      "dhanhq",         DependencyTier.OPTIONAL,  feature="Dhan primary broker"),
    PackageSpec("kiteconnect", "kiteconnect",    DependencyTier.OPTIONAL,  feature="Zerodha broker"),
    PackageSpec("telegram",    "python-telegram-bot", DependencyTier.OPTIONAL, feature="13 operator Telegram commands"),
    PackageSpec("plotly",      "plotly",         DependencyTier.OPTIONAL,  feature="Dashboard interactive charts"),
    PackageSpec("ta",          "ta",             DependencyTier.OPTIONAL,  feature="Technical indicators (RSI, MACD, ATR)"),
    PackageSpec("cryptography","cryptography",   DependencyTier.OPTIONAL,  feature="INFRA-ENC-001 EncryptionService"),
    PackageSpec("tqdm",        "tqdm",           DependencyTier.OPTIONAL,  feature="Progress bars"),
    PackageSpec("pytz",        "pytz",           DependencyTier.OPTIONAL,  feature="Timezone handling"),
]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class PackageRegistry:
    """Thread-safe registry of import availability results."""

    def __init__(self) -> None:
        self._available: dict[str, bool] = {}
        self._versions: dict[str, str] = {}

    def register(self, import_name: str, available: bool, version: str = "") -> None:
        self._available[import_name] = available
        self._versions[import_name] = version

    def is_available(self, import_name: str) -> bool:
        return self._available.get(import_name, False)

    def get_version(self, import_name: str) -> str:
        return self._versions.get(import_name, "")

    def available_packages(self) -> list[str]:
        return [k for k, v in self._available.items() if v]

    def unavailable_packages(self) -> list[str]:
        return [k for k, v in self._available.items() if not v]

    def to_dict(self) -> dict[str, Any]:
        return {
            k: {"available": v, "version": self._versions.get(k, "")}
            for k, v in self._available.items()
        }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class DependencyReport:
    """Aggregated result of dependency validation."""

    checked: int = 0
    available: int = 0
    missing_critical: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    registry: PackageRegistry = field(default_factory=PackageRegistry)
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.missing_critical) == 0

    @property
    def summary(self) -> str:
        return (
            f"{self.available}/{self.checked} packages available, "
            f"{len(self.missing_critical)} critical missing, "
            f"{len(self.missing_required)} required missing, "
            f"{len(self.missing_optional)} optional missing"
        )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class DependencyLoader:
    """Probes all declared packages and builds a ``DependencyReport``.

    Import probes are attempted without side effects — no initialization
    code in probed modules is invoked beyond the import itself.
    """

    def __init__(self, extra_packages: Optional[list[PackageSpec]] = None) -> None:
        self._packages = list(_PACKAGES)
        if extra_packages:
            self._packages.extend(extra_packages)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def load(self) -> DependencyReport:
        """Probe all declared packages and return a report."""
        report = DependencyReport()

        for spec in self._packages:
            report.checked += 1
            available, version = self._probe(spec)
            report.registry.register(spec.import_name, available, version)

            if available:
                report.available += 1
                logger.debug("Package OK: %s (%s)", spec.import_name, version or "?")
            else:
                self._handle_missing(spec, report)

        logger.info("DependencyLoader: %s", report.summary)
        return report

    def load_package(self, import_name: str) -> Optional[Any]:
        """Safely import a package by name. Returns module or None."""
        try:
            return importlib.import_module(import_name)
        except ImportError as exc:
            logger.debug("Cannot import %s: %s", import_name, exc)
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _probe(self, spec: PackageSpec) -> tuple[bool, str]:
        """Attempt to import ``spec.import_name``. Returns (available, version)."""
        names_to_try = [spec.import_name, *spec.alternatives]
        for name in names_to_try:
            if name in sys.modules:
                return True, self._get_version(spec.pip_name)
            try:
                importlib.import_module(name)
                return True, self._get_version(spec.pip_name)
            except ImportError:
                continue
            except Exception:  # noqa: BLE001
                continue
        return False, ""

    @staticmethod
    def _get_version(pip_name: str) -> str:
        try:
            return importlib.metadata.version(pip_name)
        except importlib.metadata.PackageNotFoundError:
            return ""
        except Exception:  # noqa: BLE001
            return ""

    def _handle_missing(self, spec: PackageSpec, report: DependencyReport) -> None:
        severity_map = {
            DependencyTier.CRITICAL: ValidationSeverity.CRITICAL,
            DependencyTier.REQUIRED: ValidationSeverity.WARNING,
            DependencyTier.OPTIONAL: ValidationSeverity.INFO,
        }
        severity = severity_map[spec.tier]
        message = f"Package not available: {spec.import_name} ({spec.feature})"

        report.findings.append(ValidationFinding(
            check_name="dependency",
            severity=severity,
            message=message,
            detail=f"pip install {spec.pip_name}",
            remediation=f"pip install -r requirements.txt",
        ))

        if spec.tier == DependencyTier.CRITICAL:
            report.missing_critical.append(spec.import_name)
            logger.error("CRITICAL package missing: %s — install: pip install %s", spec.import_name, spec.pip_name)
        elif spec.tier == DependencyTier.REQUIRED:
            report.missing_required.append(spec.import_name)
            logger.warning("Required package missing: %s (degraded mode)", spec.import_name)
        else:
            report.missing_optional.append(spec.import_name)
            logger.debug("Optional package missing: %s (%s unavailable)", spec.import_name, spec.feature)
