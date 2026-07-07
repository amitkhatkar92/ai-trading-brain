"""
iios/knowledge/governance/governance_registry.py
================================================
GovernanceRegistry — lazy auto-registering component registry for all
governance-side services (and a reference to the quality registry).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

__all__ = [
    "GovernanceRegistry",
    "get_governance_registry",
    "reset_governance_registry",
]

_LOG = logging.getLogger("iios.knowledge.governance.governance_registry")
_lock = threading.Lock()
_reg: Optional["GovernanceRegistry"] = None


class GovernanceRegistry:
    """Thread-safe registry for governance subsystem components."""

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._components: dict[str, Any] = {}
        self._registered  = False

    def _auto_register(self) -> None:
        if self._registered:
            return
        from .governance_engine     import get_governance_engine
        from .policy_manager        import get_policy_manager
        from .certification_manager import get_certification_manager
        from .governance_audit      import get_governance_audit_log
        from .knowledge_governor    import get_knowledge_governor
        from .governance_context    import get_governance_context
        from .quality_registry      import get_quality_registry

        self._components = {
            "governance_engine":     get_governance_engine(),
            "policy_manager":        get_policy_manager(),
            "certification_manager": get_certification_manager(),
            "governance_audit":      get_governance_audit_log(),
            "knowledge_governor":    get_knowledge_governor(),
            "governance_context":    get_governance_context(),
            "quality_registry":      get_quality_registry(),
        }
        self._registered = True

    def register(self, name: str, component: Any) -> None:
        with self._lock:
            self._auto_register()
            self._components[name] = component

    def get(self, name: str) -> Any:
        with self._lock:
            self._auto_register()
            if name not in self._components:
                raise KeyError(f"GovernanceRegistry: component '{name}' not found.")
            return self._components[name]

    def has(self, name: str) -> bool:
        with self._lock:
            self._auto_register()
            return name in self._components

    def names(self) -> list[str]:
        with self._lock:
            self._auto_register()
            return list(self._components)

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._auto_register()
            return {name: type(c).__name__ for name, c in self._components.items()}


def get_governance_registry() -> GovernanceRegistry:
    global _reg
    if _reg is None:
        with _lock:
            if _reg is None:
                _reg = GovernanceRegistry()
    return _reg


def reset_governance_registry() -> None:
    global _reg
    with _lock:
        _reg = None
