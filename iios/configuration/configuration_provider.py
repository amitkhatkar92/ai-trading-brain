"""
iios/configuration/configuration_provider.py
==============================================
Provider abstraction — each provider wraps one configuration source and
returns a ``dict[str, Any]`` on ``load()``.

Providers are registered in ``ConfigurationRegistry`` and called by
``ConfigurationManager``. Priority determines override order.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from .configuration_loader import (
    ConfigurationSource,
    DefaultsSource,
    DictionarySource,
    DotEnvFileSource,
    EnvVarsSource,
    INIFileSource,
    JSONFileSource,
    PythonModuleSource,
    TOMLFileSource,
    YAMLFileSource,
)
from .configuration_exception import ConfigurationProviderError

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationProvider",
    "EnvironmentVariableProvider",
    "DotEnvFileProvider",
    "JSONFileProvider",
    "TOMLFileProvider",
    "YAMLFileProvider",
    "INIFileProvider",
    "PythonModuleProvider",
    "DefaultsProvider",
    "DictionaryProvider",
]


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class ConfigurationProvider(ABC):
    """Abstract base for all configuration providers.

    Each provider wraps one ``ConfigurationSource`` and adds:
      - ``enabled`` flag (can be toggled at runtime)
      - ``load()`` with standardised error handling
      - A human-readable ``description`` for diagnostics
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Merge priority — 0 (lowest) to 100 (highest)."""

    @property
    def description(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, priority={self.priority})"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @abstractmethod
    def _source(self) -> ConfigurationSource:
        """Return the underlying ``ConfigurationSource`` instance."""

    def load(self) -> dict[str, Any]:
        """Load configuration. Returns empty dict if disabled or on error."""
        if not self._enabled:
            return {}
        try:
            data = self._source().load()
            logger.debug("Provider %r loaded %d key(s)", self.name, _count_keys(data))
            return data
        except Exception as exc:
            raise ConfigurationProviderError(
                f"Provider {self.name!r} failed: {exc}",
                provider=self.name,
            ) from exc


# ---------------------------------------------------------------------------
# Concrete providers
# ---------------------------------------------------------------------------


class EnvironmentVariableProvider(ConfigurationProvider):
    """Reads from ``os.environ`` using the IIOS env-var map."""

    def __init__(self, extra_env: Optional[dict[str, str]] = None) -> None:
        super().__init__()
        self._extra_env = extra_env or {}

    @property
    def name(self) -> str:
        return "env_vars"

    @property
    def priority(self) -> int:
        return 70

    def _source(self) -> ConfigurationSource:
        return EnvVarsSource(self._extra_env)


class DotEnvFileProvider(ConfigurationProvider):
    """Reads a ``.env`` file."""

    def __init__(self, path: str = ".env") -> None:
        super().__init__()
        self._path = path

    @property
    def name(self) -> str:
        return "dotenv"

    @property
    def priority(self) -> int:
        return 60

    @property
    def description(self) -> str:
        return f"DotEnvFileProvider(path={self._path!r})"

    def _source(self) -> ConfigurationSource:
        return DotEnvFileSource(self._path)


class JSONFileProvider(ConfigurationProvider):
    """Reads a JSON configuration file."""

    def __init__(self, path: str, priority: int = 40) -> None:
        super().__init__()
        self._path = path
        self._priority = priority

    @property
    def name(self) -> str:
        return f"json:{self._path}"

    @property
    def priority(self) -> int:
        return self._priority

    def _source(self) -> ConfigurationSource:
        return JSONFileSource(self._path, self._priority)


class TOMLFileProvider(ConfigurationProvider):
    """Reads a TOML configuration file."""

    def __init__(self, path: str, priority: int = 35) -> None:
        super().__init__()
        self._path = path
        self._priority = priority

    @property
    def name(self) -> str:
        return f"toml:{self._path}"

    @property
    def priority(self) -> int:
        return self._priority

    def _source(self) -> ConfigurationSource:
        return TOMLFileSource(self._path, self._priority)


class YAMLFileProvider(ConfigurationProvider):
    """Reads a YAML configuration file."""

    def __init__(self, path: str, priority: int = 45) -> None:
        super().__init__()
        self._path = path
        self._priority = priority

    @property
    def name(self) -> str:
        return f"yaml:{self._path}"

    @property
    def priority(self) -> int:
        return self._priority

    def _source(self) -> ConfigurationSource:
        return YAMLFileSource(self._path, self._priority)


class INIFileProvider(ConfigurationProvider):
    """Reads an INI configuration file."""

    def __init__(self, path: str, priority: int = 30) -> None:
        super().__init__()
        self._path = path
        self._priority = priority

    @property
    def name(self) -> str:
        return f"ini:{self._path}"

    @property
    def priority(self) -> int:
        return self._priority

    def _source(self) -> ConfigurationSource:
        return INIFileSource(self._path, self._priority)


class PythonModuleProvider(ConfigurationProvider):
    """Reads public variables from a Python module (e.g. ``config``)."""

    def __init__(self, module_name: str, priority: int = 20) -> None:
        super().__init__()
        self._module = module_name
        self._priority = priority

    @property
    def name(self) -> str:
        return f"python:{self._module}"

    @property
    def priority(self) -> int:
        return self._priority

    def _source(self) -> ConfigurationSource:
        return PythonModuleSource(self._module, self._priority)


class DefaultsProvider(ConfigurationProvider):
    """Returns a fixed set of default values. Always lowest priority."""

    def __init__(self, defaults: dict[str, Any]) -> None:
        super().__init__()
        self._defaults = defaults

    @property
    def name(self) -> str:
        return "defaults"

    @property
    def priority(self) -> int:
        return 0

    def _source(self) -> ConfigurationSource:
        return DefaultsSource(self._defaults)


class DictionaryProvider(ConfigurationProvider):
    """Wraps an in-memory dictionary. Useful for tests and runtime overrides."""

    def __init__(
        self,
        data: dict[str, Any],
        name: str = "dict",
        priority: int = 80,
    ) -> None:
        super().__init__()
        self._data = data
        self._name = name
        self._priority = priority

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def _source(self) -> ConfigurationSource:
        return DictionarySource(self._data, self._name, self._priority)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_keys(data: dict[str, Any], depth: int = 2) -> int:
    """Shallow key count for debug logging."""
    count = len(data)
    if depth > 0:
        for v in data.values():
            if isinstance(v, dict):
                count += _count_keys(v, depth - 1)
    return count
