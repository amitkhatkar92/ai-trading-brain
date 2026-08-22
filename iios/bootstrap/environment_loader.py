"""
iios/bootstrap/environment_loader.py
=======================================
Discovers and loads environment variables for the IIOS platform.

Precedence order (first wins):
  1. Already-set OS environment variables
  2. .env.<IIOS_ENV>   (e.g. .env.development, .env.production)
  3. .env              (generic fallback)
  4. .env.example      (documentation only — warns if used as source)

After loading, validates that all required variables are present and
coerces typed variables (bool, int, float) to their correct Python types.

Architecture Reference: IIOS-BSS-001 Stages 6-10 (Environment Init)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .startup_state import ValidationFinding, ValidationSeverity

__all__ = ["EnvironmentLoader", "EnvironmentSnapshot"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Variable definitions
# ---------------------------------------------------------------------------

@dataclass
class _EnvVar:
    name: str
    required: bool
    default: str
    description: str
    coerce_to: str = "str"    # str | bool | int | float


_KNOWN_VARS: list[_EnvVar] = [
    _EnvVar("IIOS_ENV",              False, "development", "Runtime environment",   "str"),
    _EnvVar("IIOS_PAPER_TRADING",    False, "true",        "Enable paper trading",  "bool"),
    _EnvVar("IIOS_LOG_LEVEL",        False, "INFO",        "Log verbosity",         "str"),
    _EnvVar("IIOS_LOG_FILE",         False, "logs/iios.log", "Log file path",       "str"),
    _EnvVar("IIOS_DB_PATH",          False, "data/iios.db",  "SQLite database path","str"),
    _EnvVar("IIOS_PAPER_TRADES_PATH",False, "data/paper_trades.csv", "Paper trades journal", "str"),
    _EnvVar("DHAN_CLIENT_ID",        False, "",  "Dhan broker client ID",   "str"),
    _EnvVar("DHAN_ACCESS_TOKEN",     False, "",  "Dhan daily access token", "str"),
    _EnvVar("TELEGRAM_BOT_TOKEN",    False, "",  "Telegram bot token",      "str"),
    _EnvVar("TELEGRAM_CHAT_ID",      False, "",  "Telegram operator chat ID","str"),
    _EnvVar("TELEGRAM_WHITELIST_IDS",False, "",  "Comma-separated allowed chat IDs","str"),
    _EnvVar("STREAMLIT_PORT",        False, "8501","Streamlit dashboard port","int"),
    _EnvVar("BROKER_PRIMARY",        False, "dhan",  "Primary broker",    "str"),
    _EnvVar("BROKER_FALLBACK",       False, "yahoo", "Fallback data feed","str"),
    _EnvVar("IIOS_ENABLE_TELEGRAM",  False, "false", "Start Telegram bot","bool"),
    _EnvVar("IIOS_ENABLE_DASHBOARD", False, "true",  "Start Streamlit dashboard","bool"),
    _EnvVar("IIOS_ENABLE_LIVE_TRADING", False, "false", "Enable live order routing","bool"),
    _EnvVar("IIOS_CONTINUOUS_SCAN",  False, "false", "Enable 30s continuous scan","bool"),
    # Architecture constants can be overridden via env (optional)
    _EnvVar("IIOS_DECISION_THRESHOLD", False, "", "Override DECISION_THRESHOLD (6.5)", "float"),
    _EnvVar("IIOS_VIX_THRESHOLD",      False, "", "Override VIX_THRESHOLD (45.0)",     "float"),
    _EnvVar("IIOS_DAILY_LOSS_PCT",     False, "", "Override DAILY_LOSS_PCT (0.02)",     "float"),
]

_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "DHAN_ACCESS_TOKEN",
    "TELEGRAM_BOT_TOKEN",
})


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass
class EnvironmentSnapshot:
    """Resolved environment after loading and validation."""

    env_name: str = "development"
    source_file: str = ""           # Which .env file was loaded
    raw: dict[str, str] = field(default_factory=dict)
    typed: dict[str, Any] = field(default_factory=dict)
    missing_required: list[str] = field(default_factory=list)
    findings: list[ValidationFinding] = field(default_factory=list)

    # Typed convenience properties
    @property
    def paper_trading(self) -> bool:
        return bool(self.typed.get("IIOS_PAPER_TRADING", True))

    @property
    def log_level(self) -> str:
        return str(self.typed.get("IIOS_LOG_LEVEL", "INFO"))

    @property
    def log_file(self) -> str:
        return str(self.typed.get("IIOS_LOG_FILE", "logs/iios.log"))

    @property
    def db_path(self) -> str:
        return str(self.typed.get("IIOS_DB_PATH", "data/iios.db"))

    @property
    def enable_telegram(self) -> bool:
        return bool(self.typed.get("IIOS_ENABLE_TELEGRAM", False))

    @property
    def enable_dashboard(self) -> bool:
        return bool(self.typed.get("IIOS_ENABLE_DASHBOARD", True))

    @property
    def enable_live_trading(self) -> bool:
        return bool(self.typed.get("IIOS_ENABLE_LIVE_TRADING", False))

    @property
    def passed(self) -> bool:
        return not any(f.blocks_startup for f in self.findings)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class EnvironmentLoader:
    """Discovers, loads, and validates environment variables.

    Resolution order:
      1. OS environment (already set, highest priority)
      2. .env.<iios_env>  (e.g. .env.development)
      3. .env
      4. .env.example (triggers a warning)
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self._root = repo_root or Path(".").resolve()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def load(self) -> EnvironmentSnapshot:
        """Load environment and return a snapshot."""
        snap = EnvironmentSnapshot()

        # Determine which .env file to load
        env_name = os.environ.get("IIOS_ENV", "development")
        snap.env_name = env_name
        source_file = self._find_env_file(env_name)

        if source_file:
            loaded = self._load_dotenv_file(source_file)
            snap.source_file = source_file
            snap.raw.update(loaded)
            if source_file.endswith(".env.example"):
                snap.findings.append(ValidationFinding(
                    check_name="env_file",
                    severity=ValidationSeverity.WARNING,
                    message="Loading .env.example as fallback — no real .env file found",
                    detail="Copy .env.example to .env.development and fill in credentials",
                    remediation="cp .env.example .env.development",
                ))
            logger.info("Environment loaded from: %s", source_file)
        else:
            snap.findings.append(ValidationFinding(
                check_name="env_file",
                severity=ValidationSeverity.WARNING,
                message="No .env file found — using OS environment variables only",
                detail="Create .env.development from .env.example",
                remediation="cp .env.example .env.development",
            ))

        # Overlay OS env vars on top (OS wins)
        snap.raw.update({k: v for k, v in os.environ.items() if k in {v.name for v in _KNOWN_VARS}})

        # Coerce types
        snap.typed = self._coerce(snap.raw)

        # Validate
        self._validate(snap)

        logger.debug(
            "Environment snapshot: env=%s, paper=%s, telegram=%s",
            snap.env_name,
            snap.paper_trading,
            snap.enable_telegram,
        )
        return snap

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _find_env_file(self, env_name: str) -> str:
        candidates = [
            str(self._root / f".env.{env_name}"),
            str(self._root / ".env"),
            str(self._root / ".env.example"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return ""

    def _load_dotenv_file(self, filepath: str) -> dict[str, str]:
        """Parse a .env file into a dict (key=value pairs, skip comments)."""
        result: dict[str, str] = {}
        try:
            with open(filepath, encoding="utf-8") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # Strip inline comments
                    if "  #" in value:
                        value = value[:value.index("  #")].strip()
                    # Strip surrounding quotes
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    if key:
                        result[key] = value
        except OSError as exc:
            logger.warning("Cannot read env file %s: %s", filepath, exc)
        return result

    def _coerce(self, raw: dict[str, str]) -> dict[str, Any]:
        """Coerce raw string values to typed Python objects."""
        typed: dict[str, Any] = {}
        for var in _KNOWN_VARS:
            raw_val = raw.get(var.name, var.default)
            if raw_val == "" and not var.required:
                # Optional empty value — keep as empty string or skip
                typed[var.name] = raw_val
                continue
            try:
                if var.coerce_to == "bool":
                    typed[var.name] = raw_val.lower() in ("true", "1", "yes", "on")
                elif var.coerce_to == "int":
                    typed[var.name] = int(raw_val) if raw_val else 0
                elif var.coerce_to == "float":
                    typed[var.name] = float(raw_val) if raw_val else 0.0
                else:
                    typed[var.name] = raw_val
            except (ValueError, TypeError) as exc:
                logger.warning("Cannot coerce %s=%r to %s: %s", var.name, raw_val, var.coerce_to, exc)
                typed[var.name] = raw_val
        return typed

    def _validate(self, snap: EnvironmentSnapshot) -> None:
        """Validate required variables and security rules."""
        for var in _KNOWN_VARS:
            if not var.required:
                continue
            val = snap.raw.get(var.name, "")
            if not val:
                snap.missing_required.append(var.name)
                snap.findings.append(ValidationFinding(
                    check_name="env_required",
                    severity=ValidationSeverity.ERROR,
                    message=f"Required environment variable not set: {var.name}",
                    detail=var.description,
                    remediation=f"Set {var.name} in .env.development",
                ))

        # Security: live trading guard
        live = snap.typed.get("IIOS_ENABLE_LIVE_TRADING", False)
        paper = snap.typed.get("IIOS_PAPER_TRADING", True)
        if live and not paper:
            snap.findings.append(ValidationFinding(
                check_name="live_trading_guard",
                severity=ValidationSeverity.WARNING,
                message="Live trading is enabled (IIOS_ENABLE_LIVE_TRADING=true, IIOS_PAPER_TRADING=false)",
                detail="Ensure SYSTEM_CERTIFIED criteria are met before authorizing",
                remediation="Set IIOS_PAPER_TRADING=true until certified",
            ))

        # Redact sensitive keys from raw snapshot for safety
        for key in _SENSITIVE_KEYS:
            if key in snap.raw and snap.raw[key]:
                snap.raw[key] = "***REDACTED***"
            if key in snap.typed and snap.typed[key]:
                snap.typed[key] = "***REDACTED***"
