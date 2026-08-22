"""
iios/bootstrap/configuration_loader.py
=========================================
Loads and validates the IIOS configuration module (config.py).

Validates that all architecture-invariant constants are present and within
acceptable bounds. Constants that deviate from their certified values trigger
a WARNING (not an ERROR) so that deliberate overrides via environment variables
are possible — but must be acknowledged explicitly.

Architecture Invariants (FC-RULE-017, FC-RULE-018):
    DECISION_THRESHOLD  = 6.5   (Layer 10 DebateAndDecision)
    VIX_THRESHOLD       = 45.0  (Layer 9 RiskGuardian kill switch)
    DAILY_LOSS_PCT      = 0.02  (Daily loss limit 2%)
    DEBATE_AGENTS       = 5     (Exactly 5 debate agents)
    LAYERS              = 17    (Pipeline layer count)

Architecture Reference: IIOS-BSS-001 Stages 11-15 (Configuration Init)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

from .startup_state import ValidationFinding, ValidationSeverity

__all__ = ["ConfigurationLoader", "ConfigurationSnapshot"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Certified architecture constants (FC-RULE-017, FC-RULE-018)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _ConstantSpec:
    name: str
    certified_value: Any
    tolerance: float = 0.0      # Fractional tolerance for float comparisons
    required: bool = True
    description: str = ""


_CERTIFIED_CONSTANTS: list[_ConstantSpec] = [
    _ConstantSpec(
        "DECISION_THRESHOLD", 6.5, tolerance=0.0,
        description="Layer 10 DebateAndDecision decision gate (FC-RULE-017)",
    ),
    _ConstantSpec(
        "VIX_THRESHOLD", 45.0, tolerance=0.0,
        description="Layer 9 RiskGuardian VIX kill switch (FC-RULE-018)",
    ),
    _ConstantSpec(
        "DAILY_LOSS_PCT", 0.02, tolerance=0.001,
        description="Daily portfolio loss limit 2% (FC-RULE-018)",
    ),
    _ConstantSpec(
        "PAPER_TRADING", None, required=False,
        description="Paper trading mode flag",
    ),
]

_INFORMATIONAL_CONSTANTS: list[str] = [
    "SCHEDULE",
    "CONTINUOUS_SCAN_INTERVAL",
    "BROKER",
    "SYMBOLS",
]


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass
class ConfigurationSnapshot:
    """Resolved snapshot of config.py attributes."""

    module_loaded: bool = False
    module_name: str = "config"
    attributes: dict[str, Any] = field(default_factory=dict)
    findings: list[ValidationFinding] = field(default_factory=list)
    paper_trading: bool = True
    decision_threshold: float = 6.5
    vix_threshold: float = 45.0
    daily_loss_pct: float = 0.02

    @property
    def passed(self) -> bool:
        return self.module_loaded and not any(f.blocks_startup for f in self.findings)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class ConfigurationLoader:
    """Loads config.py and validates architecture-invariant constants.

    If config.py cannot be imported, a CRITICAL finding is added and the
    snapshot is returned with ``module_loaded=False``.
    """

    def __init__(self, module_name: str = "config") -> None:
        self._module_name = module_name

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def load(self) -> ConfigurationSnapshot:
        """Import config module and return a validated snapshot."""
        snap = ConfigurationSnapshot(module_name=self._module_name)

        module = self._import_module(snap)
        if module is None:
            return snap

        snap.module_loaded = True
        snap.attributes = self._read_attributes(module)

        # Extract key constants with defaults
        snap.paper_trading       = snap.attributes.get("PAPER_TRADING", True)
        snap.decision_threshold  = float(snap.attributes.get("DECISION_THRESHOLD", 6.5))
        snap.vix_threshold       = float(snap.attributes.get("VIX_THRESHOLD", 45.0))
        snap.daily_loss_pct      = float(snap.attributes.get("DAILY_LOSS_PCT", 0.02))

        self._validate_certified_constants(snap, module)
        self._validate_paper_trading(snap)
        self._log_summary(snap)

        return snap

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _import_module(self, snap: ConfigurationSnapshot) -> Optional[Any]:
        try:
            if self._module_name in sys.modules:
                module = sys.modules[self._module_name]
                logger.debug("config module already loaded (from sys.modules)")
            else:
                module = importlib.import_module(self._module_name)
            return module
        except ImportError as exc:
            snap.findings.append(ValidationFinding(
                check_name="config_import",
                severity=ValidationSeverity.CRITICAL,
                message=f"Cannot import configuration module: {self._module_name}",
                detail=str(exc),
                remediation=f"Ensure {self._module_name}.py exists in the repository root",
            ))
            return None
        except Exception as exc:  # noqa: BLE001
            snap.findings.append(ValidationFinding(
                check_name="config_import",
                severity=ValidationSeverity.CRITICAL,
                message=f"Exception while loading {self._module_name}.py",
                detail=str(exc),
                remediation="Check config.py for syntax errors",
            ))
            return None

    def _read_attributes(self, module: Any) -> dict[str, Any]:
        """Return all public (non-dunder) module attributes."""
        attrs: dict[str, Any] = {}
        for name in dir(module):
            if name.startswith("__"):
                continue
            try:
                attrs[name] = getattr(module, name)
            except AttributeError:
                pass
        return attrs

    def _validate_certified_constants(
        self, snap: ConfigurationSnapshot, module: Any
    ) -> None:
        for spec in _CERTIFIED_CONSTANTS:
            if spec.certified_value is None:
                continue  # informational only

            actual = getattr(module, spec.name, None)
            if actual is None:
                if spec.required:
                    snap.findings.append(ValidationFinding(
                        check_name="config_constant",
                        severity=ValidationSeverity.WARNING,
                        message=f"Architecture constant not defined: {spec.name}",
                        detail=f"Expected certified value: {spec.certified_value}",
                        remediation=f"Add {spec.name} = {spec.certified_value} to config.py",
                    ))
                continue

            # Check value matches within tolerance
            try:
                if isinstance(spec.certified_value, float):
                    deviation = abs(float(actual) - spec.certified_value)
                    matches = deviation <= spec.tolerance
                else:
                    matches = actual == spec.certified_value
            except (TypeError, ValueError):
                matches = False

            if not matches:
                snap.findings.append(ValidationFinding(
                    check_name="config_constant",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Architecture constant {spec.name} deviates from certified value. "
                        f"Got {actual!r}, expected {spec.certified_value!r}."
                    ),
                    detail=spec.description,
                    remediation=(
                        "Revert to certified value or obtain Architecture Council approval. "
                        "FC-RULE-017 / FC-RULE-018"
                    ),
                ))
            else:
                logger.debug("Constant OK: %s = %r", spec.name, actual)

    def _validate_paper_trading(self, snap: ConfigurationSnapshot) -> None:
        if not snap.paper_trading:
            snap.findings.append(ValidationFinding(
                check_name="paper_trading_mode",
                severity=ValidationSeverity.WARNING,
                message="PAPER_TRADING=False detected in config.py",
                detail=(
                    "Live trading mode. Ensure SYSTEM_CERTIFIED criteria are satisfied: "
                    "WinRate>=50%, Sharpe>0.8, MaxDD<15% over 90+ day paper run."
                ),
                remediation="Set PAPER_TRADING=True until SYSTEM_CERTIFIED is confirmed",
            ))

    def _log_summary(self, snap: ConfigurationSnapshot) -> None:
        logger.info(
            "Configuration loaded: paper_trading=%s, decision_threshold=%.1f, "
            "vix_threshold=%.1f, daily_loss_pct=%.3f",
            snap.paper_trading,
            snap.decision_threshold,
            snap.vix_threshold,
            snap.daily_loss_pct,
        )
        for finding in snap.findings:
            if finding.blocks_startup:
                logger.error("Config finding: %s", finding)
            else:
                logger.warning("Config finding: %s", finding)
