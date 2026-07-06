"""
iios/configuration/configuration_constants.py
===============================================
Constants for the IIOS Configuration Management System.

Includes:
  - Source priority ordering
  - IIOS architecture-invariant values (FC-RULE-017, FC-RULE-018)
  - Section names
  - Environment variable prefixes
  - Encryption markers

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Final

__all__ = [
    "ConfigSource",
    "ConfigSection",
    "IIOS_ARCHITECTURE_CONSTANTS",
    "ENV_PREFIX",
    "ENCRYPTED_MARKER",
    "REFERENCE_PREFIX",
    "DEFAULT_ENCODING",
    "DEFAULT_CACHE_TTL_SECONDS",
    "DEFAULT_RELOAD_INTERVAL_SECONDS",
    "MAX_HISTORY_VERSIONS",
    "SOURCE_PRIORITY",
]


# ---------------------------------------------------------------------------
# Configuration source identifiers
# ---------------------------------------------------------------------------


class ConfigSource(Enum):
    """Identifies the origin of a configuration value.

    Priority order: DEFAULTS (lowest) → PYTHON → INI → TOML → JSON → YAML
    → ENV_FILE → ENV_VARS → CLI → SECRETS (highest).
    """

    DEFAULTS     = "defaults"
    PYTHON       = "python"
    INI          = "ini"
    TOML         = "toml"
    JSON         = "json"
    YAML         = "yaml"
    ENV_FILE     = "env_file"
    ENV_VARS     = "env_vars"
    CLI          = "cli"
    SECRETS      = "secrets"
    RUNTIME      = "runtime"     # Set programmatically at runtime


# Source priority (ascending — later sources override earlier)
SOURCE_PRIORITY: list[ConfigSource] = [
    ConfigSource.DEFAULTS,
    ConfigSource.PYTHON,
    ConfigSource.INI,
    ConfigSource.TOML,
    ConfigSource.JSON,
    ConfigSource.YAML,
    ConfigSource.ENV_FILE,
    ConfigSource.ENV_VARS,
    ConfigSource.CLI,
    ConfigSource.SECRETS,
    ConfigSource.RUNTIME,
]


# ---------------------------------------------------------------------------
# Configuration sections (one per IIOS subsystem)
# ---------------------------------------------------------------------------


class ConfigSection(str, Enum):
    """Named configuration sections, one per IIOS subsystem."""

    SYSTEM          = "system"
    INFRASTRUCTURE  = "infrastructure"
    DATABASE        = "database"
    KNOWLEDGE       = "knowledge"
    ONTOLOGY        = "ontology"
    AI              = "ai"
    OBSERVATION     = "observation"
    REASONING       = "reasoning"
    DECISION        = "decision"
    STRATEGY        = "strategy"
    PORTFOLIO       = "portfolio"
    RISK            = "risk"
    EXECUTION       = "execution"
    MONITORING      = "monitoring"
    LOGGING         = "logging"
    NOTIFICATION    = "notification"
    SECURITY        = "security"
    PLUGIN          = "plugin"


# ---------------------------------------------------------------------------
# IIOS Architecture-Invariant Constants
# These are the certified values. Any deviation triggers a WARNING.
# FC-RULE-017, FC-RULE-018
# ---------------------------------------------------------------------------


IIOS_ARCHITECTURE_CONSTANTS: Final[dict[str, object]] = {
    "decision.decision_threshold":   6.5,
    "risk.vix_threshold":            45.0,
    "risk.daily_loss_pct":           0.02,
    "decision.debate_agents":        5,
    "system.layers":                 17,
    "system.paper_trading":          True,   # default; must be True until SYSTEM_CERTIFIED
}

# Certified minimum win rate for SYSTEM_CERTIFIED (Layer 15 ResearchLab)
CERTIFIED_WIN_RATE_MIN:   Final[float] = 0.50
CERTIFIED_SHARPE_MIN:     Final[float] = 0.80
CERTIFIED_MAX_DRAWDOWN:   Final[float] = 0.15

# Layer SLA (ms)
LAYER_WARN_MS:            Final[int]   = 2_000
LAYER_CRIT_MS:            Final[int]   = 5_000
GLOBAL_INTELLIGENCE_WARN: Final[int]   = 5_000
GLOBAL_INTELLIGENCE_CRIT: Final[int]   = 12_000
FULL_CYCLE_SLA_MS:        Final[int]   = 200


# ---------------------------------------------------------------------------
# Environment variable prefixes and naming
# ---------------------------------------------------------------------------

ENV_PREFIX: Final[str] = "IIOS_"

# Map from env var name → dotted config key
ENV_VAR_MAP: Final[dict[str, str]] = {
    "IIOS_ENV":                      "system.env",
    "IIOS_PAPER_TRADING":            "system.paper_trading",
    "IIOS_LOG_LEVEL":                "logging.level",
    "IIOS_LOG_FILE":                 "logging.file",
    "IIOS_DB_PATH":                  "database.path",
    "IIOS_PAPER_TRADES_PATH":        "execution.paper_trades_path",
    "IIOS_DECISION_THRESHOLD":       "decision.decision_threshold",
    "IIOS_VIX_THRESHOLD":            "risk.vix_threshold",
    "IIOS_DAILY_LOSS_PCT":           "risk.daily_loss_pct",
    "DHAN_CLIENT_ID":                "execution.dhan_client_id",
    "DHAN_ACCESS_TOKEN":             "execution.dhan_access_token",
    "TELEGRAM_BOT_TOKEN":            "notification.telegram_bot_token",
    "TELEGRAM_CHAT_ID":              "notification.telegram_chat_id",
    "TELEGRAM_WHITELIST_IDS":        "notification.telegram_whitelist_ids",
    "STREAMLIT_PORT":                "monitoring.streamlit_port",
    "IIOS_ENABLE_TELEGRAM":          "notification.enabled",
    "IIOS_ENABLE_DASHBOARD":         "monitoring.dashboard_enabled",
    "IIOS_ENABLE_LIVE_TRADING":      "execution.live_trading_enabled",
    "IIOS_CONTINUOUS_SCAN":          "strategy.continuous_scan",
    "BROKER_PRIMARY":                "execution.broker_primary",
    "BROKER_FALLBACK":               "execution.broker_fallback",
}


# ---------------------------------------------------------------------------
# Encryption and reference markers
# ---------------------------------------------------------------------------

ENCRYPTED_MARKER: Final[str]  = "ENC:"     # Value prefix for encrypted strings
REFERENCE_PREFIX: Final[str]  = "${{"       # Variable reference: ${{section.key}}
REFERENCE_SUFFIX: Final[str]  = "}}"


# ---------------------------------------------------------------------------
# Sensitive key patterns (values are redacted in logs)
# ---------------------------------------------------------------------------

SENSITIVE_KEY_PATTERNS: Final[frozenset[str]] = frozenset({
    "access_token",
    "secret",
    "password",
    "api_key",
    "token",
    "private_key",
    "certificate",
})


# ---------------------------------------------------------------------------
# Cache, reload, and history settings
# ---------------------------------------------------------------------------

DEFAULT_ENCODING: Final[str]                 = "utf-8"
DEFAULT_CACHE_TTL_SECONDS: Final[int]        = 300        # 5 minutes
DEFAULT_RELOAD_INTERVAL_SECONDS: Final[int]  = 30
MAX_HISTORY_VERSIONS: Final[int]             = 10
