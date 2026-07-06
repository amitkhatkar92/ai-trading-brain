"""
iios/configuration/configuration_manager.py
=============================================
Main orchestrator for the IIOS Configuration Management System.

``ConfigurationManager`` coordinates all other configuration components:
  1. Loads raw dicts from ``ConfigurationRegistry`` (all providers)
  2. Resolves ``${VAR}`` references via ``ConfigurationResolver``
  3. Decrypts ``ENC:`` values via ``ConfigurationEncryption``
  4. Validates against the IIOS schema via ``ConfigurationValidator``
  5. Caches the result in ``ConfigurationCache``
  6. Populates typed ``IIOSConfiguration`` model

Thread safety: all public methods are safe to call concurrently.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import dataclasses
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Type, TypeVar

from .configuration_cache import ConfigurationCache
from .configuration_constants import (
    DEFAULT_CACHE_TTL_SECONDS,
    IIOS_ARCHITECTURE_CONSTANTS,
)
from .configuration_encryption import ConfigurationEncryption
from .configuration_exception import (
    ConfigurationError,
    ConfigurationNotFoundError,
    ConfigurationReloadError,
)
from .configuration_merger import ConfigurationMerger
from .configuration_models import IIOSConfiguration
from .configuration_provider import (
    DefaultsProvider,
    DotEnvFileProvider,
    EnvironmentVariableProvider,
    PythonModuleProvider,
)
from .configuration_registry import ConfigurationRegistry
from .configuration_resolver import ConfigurationResolver
from .configuration_validator import ConfigurationValidator
from .configuration_watcher import ConfigurationWatcher

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationManager",
    "get_configuration_manager",
]

T = TypeVar("T")


class ConfigurationManager:
    """Manages the full configuration lifecycle for IIOS.

    Usage::

        manager = ConfigurationManager(repo_root="/path/to/project")
        config  = manager.initialize()   # Returns IIOSConfiguration

        vix = manager.get("risk.vix_threshold")  # 45.0
        risk_cfg = manager.get_typed("risk", RiskConfiguration)

    Args:
        repo_root: Root directory of the IIOS project. Used to locate
                   ``.env``, ``config.py``, and config files.
        encryption_key: Fernet key for decrypting ``ENC:`` values. If None,
                        reads from ``IIOS_ENCRYPTION_KEY`` env var.
        cache_ttl_seconds: How long before the cache is considered stale.
        auto_watch: If True, start file watcher for hot-reload on ``.env``
                    and YAML/JSON config files.
        validate_invariants: If True, warn when arch constants deviate from
                             certified values.
    """

    def __init__(
        self,
        repo_root: Optional[str] = None,
        encryption_key: Optional[str] = None,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        auto_watch: bool = False,
        validate_invariants: bool = True,
    ) -> None:
        self._repo_root = Path(repo_root) if repo_root else Path.cwd()
        self._lock = threading.RLock()
        self._initialized = False

        # Components
        self._registry = ConfigurationRegistry(merger=ConfigurationMerger())
        self._resolver = ConfigurationResolver()
        self._encryption = ConfigurationEncryption(key=encryption_key)
        self._validator = ConfigurationValidator(enforce_invariants=validate_invariants)
        self._cache = ConfigurationCache(ttl_seconds=cache_ttl_seconds)
        self._watcher = ConfigurationWatcher() if auto_watch else None

        # Typed model
        self._iios_config: Optional[IIOSConfiguration] = None

        # Subscribe callbacks: key → list of callables
        self._subscriptions: dict[str, list[Callable[[str, Any, Any], None]]] = {}

        self._setup_default_providers()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> IIOSConfiguration:
        """Bootstrap the configuration system and return a typed config.

        Steps:
            1. Load from all registered providers
            2. Resolve variable references
            3. Decrypt ENC: values
            4. Validate against IIOS schema
            5. Cache the merged dict
            6. Build and return ``IIOSConfiguration``

        This method is idempotent — calling it again forces a full reload.
        """
        with self._lock:
            logger.info("Initialising IIOS configuration from %s", self._repo_root)

            raw = self._registry.load_all(skip_errors=True)
            resolved = self._resolver.resolve(raw)
            decrypted = self._encryption.scan_and_decrypt(resolved)

            report = self._validator.validate(decrypted)
            if report.warnings:
                for warn in report.warnings:
                    logger.warning("Configuration: %s", warn)
            report.raise_if_invalid()

            self._cache.put(decrypted, sources=self._registry.provider_names)
            self._iios_config = self._build_typed(decrypted)
            self._initialized = True

            logger.info(
                "Configuration ready — env=%r paper_trading=%r",
                self._iios_config.system.env,
                self._iios_config.system.paper_trading,
            )
            return self._iios_config

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dotted key (e.g. ``"risk.vix_threshold"``)."""
        return self._cache.get(key, default)

    def require(self, key: str) -> Any:
        """Like ``get()`` but raises ``ConfigurationNotFoundError`` if missing."""
        val = self._cache.get(key)
        if val is None:
            parts = key.split(".", 1)
            section = parts[0] if len(parts) > 1 else None
            field_name = parts[1] if len(parts) > 1 else key
            raise ConfigurationNotFoundError(field_name, section)
        return val

    def get_section(self, section: str) -> dict[str, Any]:
        """Return all values for a configuration section."""
        val = self._cache.get(section)
        if not isinstance(val, dict):
            return {}
        return dict(val)

    def get_typed(self, section: str, cls: Type[T]) -> T:
        """Return the configuration for *section* as a typed dataclass.

        The section dict values are passed as keyword arguments to ``cls()``.
        Unknown fields are silently dropped.

        Args:
            section: Section name (e.g. ``"risk"``).
            cls:     Dataclass type (e.g. ``RiskConfiguration``).

        Returns:
            Instance of *cls* populated with section values.
        """
        data = self.get_section(section)
        field_names = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)

    @property
    def config(self) -> Optional[IIOSConfiguration]:
        """The currently active typed configuration, or None before ``initialize()``."""
        return self._iios_config

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def version(self) -> int:
        return self._cache.version

    # ------------------------------------------------------------------
    # Reload
    # ------------------------------------------------------------------

    def reload(self) -> IIOSConfiguration:
        """Hot-reload all providers and update the cached configuration.

        Fires change subscriptions for any keys whose values changed.

        Returns the new ``IIOSConfiguration``.
        """
        with self._lock:
            old_data = self._cache.get_all()
            try:
                new_config = self.initialize()
            except Exception as exc:
                raise ConfigurationReloadError(
                    f"Configuration reload failed: {exc}", cause=exc
                ) from exc

            # Detect and broadcast changes
            new_data = self._cache.get_all()
            self._broadcast_changes(old_data, new_data)
            return new_config

    # ------------------------------------------------------------------
    # Change subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """Register a callback invoked when *key* changes on reload.

        Args:
            key:      Dotted key (e.g. ``"risk.vix_threshold"``). Use ``"*"``
                      for all changes.
            callback: ``Callable[[key, old_value, new_value], None]``
        """
        with self._lock:
            self._subscriptions.setdefault(key, []).append(callback)

    def unsubscribe(self, key: str, callback: Callable) -> None:
        with self._lock:
            if key in self._subscriptions:
                self._subscriptions[key] = [
                    c for c in self._subscriptions[key] if c is not callback
                ]

    # ------------------------------------------------------------------
    # Rollback & diff
    # ------------------------------------------------------------------

    def rollback(self, version: int) -> IIOSConfiguration:
        """Restore a previous configuration version.

        Args:
            version: Version number from ``cache.history``.
        """
        with self._lock:
            snap = self._cache.rollback(version)
            self._iios_config = self._build_typed(snap.data)
            return self._iios_config

    def diff(self, version_a: int, version_b: int) -> dict[str, tuple[Any, Any]]:
        """Return keys that differ between two cached versions."""
        return self._cache.diff(version_a, version_b)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self, fmt: str = "json") -> str:
        """Export current configuration as JSON, YAML, or TOML string.

        Args:
            fmt: ``"json"`` | ``"yaml"`` | ``"toml"``

        Returns:
            String representation of the full configuration.
        """
        data = self._cache.get_all()
        fmt = fmt.lower()
        if fmt == "json":
            return json.dumps(data, indent=2, default=str)
        if fmt == "yaml":
            try:
                import yaml  # type: ignore
                return yaml.dump(data, default_flow_style=False)
            except ImportError:
                raise ConfigurationError(
                    "PyYAML required for YAML export", code="CFG-EXP-001"
                )
        if fmt == "toml":
            try:
                import tomllib  # stdlib Python 3.11+ (read only)
                # tomli_w for writing
                import tomli_w  # type: ignore
                return tomli_w.dumps(data)
            except ImportError:
                raise ConfigurationError(
                    "tomli_w required for TOML export", code="CFG-EXP-002"
                )
        raise ConfigurationError(f"Unknown export format: {fmt!r}", code="CFG-EXP-003")

    # ------------------------------------------------------------------
    # Provider registration helpers
    # ------------------------------------------------------------------

    def add_provider(self, provider: Any) -> "ConfigurationManager":
        """Add a provider to the registry. Fluent."""
        self._registry.register(provider)
        return self

    def describe_providers(self) -> list[dict]:
        """Return diagnostic info for all registered providers."""
        return self._registry.describe()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _setup_default_providers(self) -> None:
        """Register the default IIOS provider stack."""
        # Defaults (lowest priority)
        self._registry.register(DefaultsProvider(self._get_certified_defaults()))
        # Python config module
        self._registry.register(PythonModuleProvider("config", priority=20))
        # .env file
        self._registry.register(DotEnvFileProvider(str(self._repo_root / ".env")))
        # Environment variables (highest priority, besides runtime overrides)
        self._registry.register(EnvironmentVariableProvider())

    def _get_certified_defaults(self) -> dict[str, Any]:
        """Build defaults dict from architecture constants."""
        defaults: dict[str, Any] = {}
        for dotted, value in IIOS_ARCHITECTURE_CONSTANTS.items():
            parts = dotted.split(".", 1)
            if len(parts) == 2:
                section, field = parts
                defaults.setdefault(section, {})[field] = value
        # Paper trading default
        defaults.setdefault("system", {})["paper_trading"] = True
        defaults.setdefault("system", {})["layers"] = 17
        return defaults

    def _build_typed(self, data: dict[str, Any]) -> IIOSConfiguration:
        """Populate an ``IIOSConfiguration`` from a nested dict."""
        cfg = IIOSConfiguration()

        # For each section dataclass, pull matching keys from data
        for section_name in cfg.sections():
            section_data = data.get(section_name)
            if not isinstance(section_data, dict):
                continue
            section_obj = getattr(cfg, section_name)
            section_fields = {f.name for f in dataclasses.fields(section_obj)}
            for field_name, value in section_data.items():
                if field_name in section_fields:
                    try:
                        setattr(section_obj, field_name, value)
                    except (TypeError, AttributeError):
                        pass  # Wrong type — keep default

        cfg.metadata.loaded_at_wall = datetime.now(timezone.utc).isoformat()
        cfg.metadata.version = self._cache.version
        cfg.metadata.sources = self._registry.provider_names
        return cfg

    def _broadcast_changes(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> None:
        """Fire subscriptions for any keys that changed between old and new."""
        from .configuration_cache import _diff_dicts
        diffs = _diff_dicts(old, new)
        all_callbacks = list(self._subscriptions.get("*", []))
        for changed_key, (old_val, new_val) in diffs.items():
            callbacks = self._subscriptions.get(changed_key, [])
            for cb in callbacks + all_callbacks:
                try:
                    cb(changed_key, old_val, new_val)
                except Exception as exc:
                    logger.warning("Subscription callback error for %r: %s", changed_key, exc)


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_singleton: Optional[ConfigurationManager] = None
_singleton_lock = threading.Lock()


def get_configuration_manager(
    repo_root: Optional[str] = None,
    **kwargs: Any,
) -> ConfigurationManager:
    """Return (or create) the global ``ConfigurationManager`` singleton.

    The first call creates the singleton with the provided arguments.
    Subsequent calls ignore all arguments and return the existing instance.
    """
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = ConfigurationManager(repo_root=repo_root, **kwargs)
    return _singleton


def _reset_singleton() -> None:
    """Reset the global singleton — for tests only."""
    global _singleton
    with _singleton_lock:
        _singleton = None
