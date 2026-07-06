"""
iios/configuration/configuration_loader.py
============================================
Multi-source configuration loader.

Reads configuration from multiple file formats and returns a raw
``dict[str, Any]`` keyed by dotted path (e.g. ``"risk.vix_threshold"``).
Callers merge results in priority order using ``ConfigurationMerger``.

Supported source types:
  - ``EnvVarsSource``       — ``os.environ``
  - ``DotEnvFileSource``    — ``.env`` file (key=value format)
  - ``JSONFileSource``      — JSON (any depth)
  - ``TOMLFileSource``      — TOML (Python 3.11+ stdlib tomllib)
  - ``YAMLFileSource``      — YAML (requires PyYAML)
  - ``INIFileSource``       — INI (configparser)
  - ``PythonModuleSource``  — Python module public variables
  - ``DefaultsSource``      — Static in-memory dict
  - ``DictionarySource``    — Wraps any ``dict``

Missing or unreadable files → empty dict (not an error).
Syntax errors → ``ConfigurationLoadError`` raised.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import configparser
import importlib
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from .configuration_constants import ConfigSource, DEFAULT_ENCODING, ENV_VAR_MAP
from .configuration_exception import ConfigurationLoadError

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationSource",
    "EnvVarsSource",
    "DotEnvFileSource",
    "JSONFileSource",
    "TOMLFileSource",
    "YAMLFileSource",
    "INIFileSource",
    "PythonModuleSource",
    "DefaultsSource",
    "DictionarySource",
]


class ConfigurationSource(ABC):
    """Abstract base for configuration sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique source identifier (one of ``ConfigSource`` values)."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Merge priority — higher wins. Range 0–100."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Load and return raw configuration as ``{key: value}``."""


# ---------------------------------------------------------------------------
# Environment variables source
# ---------------------------------------------------------------------------


class EnvVarsSource(ConfigurationSource):
    """Reads configuration from ``os.environ``.

    Uses ``ENV_VAR_MAP`` to translate known environment variable names into
    dotted configuration keys. Unknown keys with the ``IIOS_`` prefix are
    also included under their lower-cased, prefix-stripped name.
    """

    def __init__(self, extra_env: Optional[dict[str, str]] = None) -> None:
        self._extra_env = extra_env or {}

    @property
    def name(self) -> str:
        return ConfigSource.ENV_VARS.value

    @property
    def priority(self) -> int:
        return 70

    def load(self) -> dict[str, Any]:
        env = dict(os.environ)
        env.update(self._extra_env)
        data: dict[str, Any] = {}

        for env_key, cfg_key in ENV_VAR_MAP.items():
            raw = env.get(env_key)
            if raw is not None:
                data[cfg_key] = _coerce_env_value(raw)

        return data


# ---------------------------------------------------------------------------
# .env file source
# ---------------------------------------------------------------------------


class DotEnvFileSource(ConfigurationSource):
    """Reads a ``.env`` file (KEY=value format, #comments, multiline unsupported)."""

    def __init__(self, path: str = ".env") -> None:
        self._path = Path(path)

    @property
    def name(self) -> str:
        return ConfigSource.ENV_FILE.value

    @property
    def priority(self) -> int:
        return 60

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            raw_vars = _parse_dotenv(self._path)
        except Exception as exc:
            raise ConfigurationLoadError(
                f"Failed to parse .env file: {self._path}",
                source=str(self._path),
                cause=exc,
            ) from exc

        # Translate env var names to dotted keys using the same map
        data: dict[str, Any] = {}
        for env_key, raw in raw_vars.items():
            cfg_key = ENV_VAR_MAP.get(env_key)
            if cfg_key:
                data[cfg_key] = _coerce_env_value(raw)
        return data


# ---------------------------------------------------------------------------
# JSON file source
# ---------------------------------------------------------------------------


class JSONFileSource(ConfigurationSource):
    """Reads a nested JSON file. Top-level keys become section names."""

    def __init__(self, path: str, priority: int = 40) -> None:
        self._path = Path(path)
        self._priority = priority

    @property
    def name(self) -> str:
        return ConfigSource.JSON.value

    @property
    def priority(self) -> int:
        return self._priority

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            with self._path.open(encoding=DEFAULT_ENCODING) as fh:
                return json.load(fh)
        except json.JSONDecodeError as exc:
            raise ConfigurationLoadError(
                f"JSON parse error in {self._path}: {exc}",
                source=str(self._path),
                cause=exc,
            ) from exc
        except OSError as exc:
            raise ConfigurationLoadError(
                f"Cannot read JSON file {self._path}: {exc}",
                source=str(self._path),
                cause=exc,
            ) from exc


# ---------------------------------------------------------------------------
# TOML file source
# ---------------------------------------------------------------------------


class TOMLFileSource(ConfigurationSource):
    """Reads a TOML file. Uses stdlib ``tomllib`` (Python 3.11+)."""

    def __init__(self, path: str, priority: int = 35) -> None:
        self._path = Path(path)
        self._priority = priority

    @property
    def name(self) -> str:
        return ConfigSource.TOML.value

    @property
    def priority(self) -> int:
        return self._priority

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            import tomllib  # stdlib Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                logger.warning("tomllib/tomli not available; skipping TOML source %s", self._path)
                return {}
        try:
            with self._path.open("rb") as fh:
                return tomllib.load(fh)
        except Exception as exc:
            raise ConfigurationLoadError(
                f"TOML parse error in {self._path}: {exc}",
                source=str(self._path),
                cause=exc,
            ) from exc


# ---------------------------------------------------------------------------
# YAML file source
# ---------------------------------------------------------------------------


class YAMLFileSource(ConfigurationSource):
    """Reads a YAML file. Requires PyYAML."""

    def __init__(self, path: str, priority: int = 45) -> None:
        self._path = Path(path)
        self._priority = priority

    @property
    def name(self) -> str:
        return ConfigSource.YAML.value

    @property
    def priority(self) -> int:
        return self._priority

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not available; skipping YAML source %s", self._path)
            return {}
        try:
            with self._path.open(encoding=DEFAULT_ENCODING) as fh:
                data = yaml.safe_load(fh)
                return data if isinstance(data, dict) else {}
        except Exception as exc:
            raise ConfigurationLoadError(
                f"YAML parse error in {self._path}: {exc}",
                source=str(self._path),
                cause=exc,
            ) from exc


# ---------------------------------------------------------------------------
# INI file source
# ---------------------------------------------------------------------------


class INIFileSource(ConfigurationSource):
    """Reads an INI file using ``configparser``.

    Sections map directly to configuration sections.
    The ``[DEFAULT]`` section (if present) is ignored.
    """

    def __init__(self, path: str, priority: int = 30) -> None:
        self._path = Path(path)
        self._priority = priority

    @property
    def name(self) -> str:
        return ConfigSource.INI.value

    @property
    def priority(self) -> int:
        return self._priority

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        cp = configparser.ConfigParser()
        try:
            cp.read(self._path, encoding=DEFAULT_ENCODING)
        except configparser.Error as exc:
            raise ConfigurationLoadError(
                f"INI parse error in {self._path}: {exc}",
                source=str(self._path),
                cause=exc,
            ) from exc

        data: dict[str, Any] = {}
        for section in cp.sections():
            data[section] = {}
            for key, val in cp.items(section):
                data[section][key] = _coerce_env_value(val)
        return data


# ---------------------------------------------------------------------------
# Python module source
# ---------------------------------------------------------------------------


class PythonModuleSource(ConfigurationSource):
    """Reads public variables from a Python module (e.g. ``config``)."""

    def __init__(self, module_name: str, priority: int = 20) -> None:
        self._module_name = module_name
        self._priority = priority

    @property
    def name(self) -> str:
        return ConfigSource.PYTHON.value

    @property
    def priority(self) -> int:
        return self._priority

    def load(self) -> dict[str, Any]:
        try:
            mod = importlib.import_module(self._module_name)
        except ImportError as exc:
            raise ConfigurationLoadError(
                f"Cannot import Python config module: {self._module_name!r}",
                source=self._module_name,
                cause=exc,
            ) from exc

        data: dict[str, Any] = {}
        for attr in dir(mod):
            if attr.startswith("_"):
                continue
            val = getattr(mod, attr)
            # Only include plain values, not functions/classes
            if not callable(val) and not isinstance(val, type):
                data[attr] = val
        return data


# ---------------------------------------------------------------------------
# Static sources
# ---------------------------------------------------------------------------


class DefaultsSource(ConfigurationSource):
    """Returns a fixed dictionary of defaults. Always the lowest priority."""

    def __init__(self, defaults: dict[str, Any]) -> None:
        self._defaults = defaults

    @property
    def name(self) -> str:
        return ConfigSource.DEFAULTS.value

    @property
    def priority(self) -> int:
        return 0

    def load(self) -> dict[str, Any]:
        return dict(self._defaults)


class DictionarySource(ConfigurationSource):
    """Wraps an in-memory dictionary. Useful for testing and runtime injection."""

    def __init__(self, data: dict[str, Any], name: str = "dict", priority: int = 80) -> None:
        self._data = data
        self._name = name
        self._priority = priority

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def load(self) -> dict[str, Any]:
        return dict(self._data)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_env_value(raw: str) -> Any:
    """Attempt to coerce a string env-var value to int, float, or bool."""
    stripped = raw.strip()
    if stripped.lower() in ("true", "yes", "1"):
        return True
    if stripped.lower() in ("false", "no", "0"):
        return False
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return stripped


_DOTENV_RE = re.compile(
    r"""^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:["']?(.*?)["']?)\s*$""",
    re.MULTILINE,
)


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser: KEY=value, strip quotes, skip comments/blank lines."""
    lines = path.read_text(encoding=DEFAULT_ENCODING, errors="replace")
    result: dict[str, str] = {}
    for line in lines.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _DOTENV_RE.match(line)
        if m:
            key, val = m.group(1), m.group(2)
            # Strip inline comments
            val = re.sub(r"\s+#.*$", "", val).strip()
            result[key] = val
    return result
