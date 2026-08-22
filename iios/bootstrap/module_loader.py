"""
iios/bootstrap/module_loader.py
==================================
Dynamic module loader with a registry and rich error reporting.

``ModuleLoader`` wraps ``importlib.import_module`` with:
  - Try-except with structured context on every load
  - A registry so callers can query what was loaded
  - Reload support for hot-patching in development
  - Lazy loading via ``load_lazy``

Architecture Reference: IIOS-BSS-001 §3.4 Module Loading
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import time
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Optional

__all__ = ["ModuleLoader", "ModuleRecord", "ModuleLoadError"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ModuleRecord:
    """Metadata about a loaded (or failed) module."""

    import_name: str
    module: Optional[ModuleType] = None
    loaded_at: float = field(default_factory=time.monotonic)
    load_time_ms: float = 0.0
    error: Optional[Exception] = None
    reloads: int = 0

    @property
    def available(self) -> bool:
        return self.module is not None

    @property
    def error_message(self) -> str:
        return str(self.error) if self.error else ""


class ModuleLoadError(ImportError):
    """Raised when a module cannot be loaded and it was declared critical."""

    def __init__(self, import_name: str, cause: Exception) -> None:
        super().__init__(f"Cannot load module {import_name!r}: {cause}")
        self.import_name = import_name
        self.cause = cause


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class ModuleLoader:
    """Safe dynamic module loader with registry and reload support.

    All load operations are non-raising by default: failures are recorded
    in the registry and returned as ``ModuleRecord`` with ``available=False``.
    Call ``load_strict`` when a missing module must abort startup.
    """

    def __init__(self) -> None:
        self._registry: dict[str, ModuleRecord] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def load(self, import_name: str) -> ModuleRecord:
        """Load ``import_name`` and record the result.

        Returns the cached record if already loaded.
        """
        if import_name in self._registry and self._registry[import_name].available:
            return self._registry[import_name]

        record = self._do_load(import_name)
        self._registry[import_name] = record

        if record.available:
            logger.debug(
                "Module loaded: %s (%.1f ms)", import_name, record.load_time_ms
            )
        else:
            logger.warning(
                "Module load FAILED: %s — %s", import_name, record.error_message
            )
        return record

    def load_strict(self, import_name: str) -> ModuleType:
        """Load ``import_name`` and raise ``ModuleLoadError`` on failure."""
        record = self.load(import_name)
        if not record.available:
            raise ModuleLoadError(import_name, record.error or ImportError(import_name))
        assert record.module is not None
        return record.module

    def load_many(self, import_names: list[str]) -> dict[str, ModuleRecord]:
        """Load multiple modules in order. Returns a dict of records."""
        return {name: self.load(name) for name in import_names}

    def reload(self, import_name: str) -> ModuleRecord:
        """Force-reload a previously loaded module."""
        existing = self._registry.get(import_name)
        old_module = existing.module if existing else None

        if import_name in sys.modules and old_module is not None:
            try:
                t0 = time.monotonic()
                module = importlib.reload(old_module)
                elapsed = (time.monotonic() - t0) * 1000.0
                record = ModuleRecord(
                    import_name=import_name,
                    module=module,
                    load_time_ms=elapsed,
                    reloads=(existing.reloads + 1) if existing else 1,
                )
                self._registry[import_name] = record
                logger.info("Module reloaded: %s (%.1f ms)", import_name, elapsed)
                return record
            except Exception as exc:  # noqa: BLE001
                logger.warning("Module reload FAILED: %s — %s", import_name, exc)
                if existing:
                    return existing

        return self.load(import_name)

    def is_available(self, import_name: str) -> bool:
        record = self._registry.get(import_name)
        if record is not None:
            return record.available
        # Not yet probed — check sys.modules
        return import_name in sys.modules

    def get(self, import_name: str) -> Optional[ModuleType]:
        """Return the loaded module or None."""
        record = self._registry.get(import_name)
        if record and record.available:
            return record.module
        if import_name in sys.modules:
            return sys.modules[import_name]
        return None

    def load_lazy(self, import_name: str) -> Any:
        """Return a lazy proxy. The module is imported on first attribute access."""
        return _LazyModule(import_name, self)

    @property
    def records(self) -> dict[str, ModuleRecord]:
        return dict(self._registry)

    def summary(self) -> dict[str, Any]:
        available = [n for n, r in self._registry.items() if r.available]
        failed = [n for n, r in self._registry.items() if not r.available]
        return {
            "loaded": len(available),
            "failed": len(failed),
            "available": available,
            "failed_modules": {n: self._registry[n].error_message for n in failed},
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _do_load(self, import_name: str) -> ModuleRecord:
        t0 = time.monotonic()
        try:
            # Already imported — use cached module
            if import_name in sys.modules:
                module = sys.modules[import_name]
                elapsed = (time.monotonic() - t0) * 1000.0
                return ModuleRecord(
                    import_name=import_name,
                    module=module,
                    load_time_ms=elapsed,
                )
            module = importlib.import_module(import_name)
            elapsed = (time.monotonic() - t0) * 1000.0
            return ModuleRecord(
                import_name=import_name,
                module=module,
                load_time_ms=elapsed,
            )
        except ImportError as exc:
            elapsed = (time.monotonic() - t0) * 1000.0
            return ModuleRecord(
                import_name=import_name,
                load_time_ms=elapsed,
                error=exc,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.monotonic() - t0) * 1000.0
            return ModuleRecord(
                import_name=import_name,
                load_time_ms=elapsed,
                error=exc,
            )


# ---------------------------------------------------------------------------
# Lazy proxy
# ---------------------------------------------------------------------------


class _LazyModule:
    """Proxy that defers actual import until first attribute access."""

    __slots__ = ("_name", "_loader", "_module")

    def __init__(self, name: str, loader: ModuleLoader) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_loader", loader)
        object.__setattr__(self, "_module", None)

    def _resolve(self) -> ModuleType:
        module = object.__getattribute__(self, "_module")
        if module is None:
            name = object.__getattribute__(self, "_name")
            loader = object.__getattribute__(self, "_loader")
            module = loader.load_strict(name)
            object.__setattr__(self, "_module", module)
        return module

    def __getattr__(self, item: str) -> Any:
        return getattr(self._resolve(), item)

    def __repr__(self) -> str:
        name = object.__getattribute__(self, "_name")
        return f"<LazyModule {name!r}>"
