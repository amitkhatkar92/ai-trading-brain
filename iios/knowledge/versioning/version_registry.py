"""
iios/knowledge/versioning/version_registry.py
=============================================
VersionRegistry — lazy-initialising component registry for the
versioning engine.  All subsystem singletons are registered under
canonical names and can be retrieved, replaced, or inspected via this
registry.

Usage::

    from iios.knowledge.versioning.version_registry import get_version_registry

    reg = get_version_registry()
    engine = reg.get("version_engine")          # → VersionEngine
    reg.register("my_engine", custom_engine)    # override for testing
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

__all__ = ["VersionRegistry", "get_version_registry", "reset_version_registry"]

_LOG = logging.getLogger("iios.knowledge.versioning.registry")
_lock = threading.Lock()
_registry: Optional["VersionRegistry"] = None


class VersionRegistry:
    """Thread-safe component registry for versioning subsystems."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._components: dict[str, Any] = {}
        self._initialised = False

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, name: str, component: Any) -> None:
        with self._lock:
            self._components[name] = component
        _LOG.debug("VersionRegistry: registered '%s'", name)

    def get(self, name: str) -> Any:
        with self._lock:
            if not self._initialised:
                self._auto_register()
            component = self._components.get(name)
        if component is None:
            raise KeyError(f"Component '{name}' not found in VersionRegistry.")
        return component

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._components

    def names(self) -> list[str]:
        with self._lock:
            if not self._initialised:
                self._auto_register()
            return sorted(self._components.keys())

    # ── Auto-registration ─────────────────────────────────────────────────────

    def _auto_register(self) -> None:
        """Lazily register all default versioning components.

        Local imports prevent circular dependencies at module load time.
        """
        from .version_manager     import get_version_manager
        from .branch_manager      import get_branch_manager
        from .diff_engine         import get_diff_engine
        from .audit_log           import get_audit_log
        from .provenance_tracker  import get_provenance_tracker
        from .lineage_manager     import get_lineage_manager, get_dependency_tracker
        from .version_context     import get_version_context
        from .version_factory     import get_version_factory
        from .version_engine      import get_version_engine

        self._components.setdefault("version_manager",    get_version_manager())
        self._components.setdefault("branch_manager",     get_branch_manager())
        self._components.setdefault("diff_engine",        get_diff_engine())
        self._components.setdefault("audit_log",          get_audit_log())
        self._components.setdefault("provenance_tracker", get_provenance_tracker())
        self._components.setdefault("lineage_manager",    get_lineage_manager())
        self._components.setdefault("dependency_tracker", get_dependency_tracker())
        self._components.setdefault("version_context",    get_version_context())
        self._components.setdefault("version_factory",    get_version_factory())
        self._components.setdefault("version_engine",     get_version_engine())

        self._initialised = True
        _LOG.debug("VersionRegistry: auto-registered %d components",
                   len(self._components))

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered":  self.names(),
                "count":       len(self._components),
                "initialised": self._initialised,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_version_registry() -> VersionRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = VersionRegistry()
    return _registry


def reset_version_registry() -> None:
    global _registry
    with _lock:
        _registry = None
