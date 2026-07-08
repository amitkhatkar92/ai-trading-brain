"""
iios/ontology/reasoning/reasoning_registry.py
==============================================
Registry of reasoning modules (pluggable per-type reasoning strategies).

A "reasoning module" is any callable that implements the ReasoningModule
protocol: it accepts a ReasoningRequest and returns a ReasoningResult.

The built-in modules delegate to InferenceEngine (for FORWARD_CHAIN,
BACKWARD_CHAIN, FULL_INFERENCE) and to consistency checks (CONSISTENCY_CHECK).

Singleton: get_reasoning_registry() / reset_reasoning_registry()
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from .reasoning_constants  import ReasoningType
from .reasoning_exceptions import DuplicateRuleError, UnknownRuleError
from .reasoning_factory    import ReasoningRequest
from .reasoning_result     import ReasoningResult

__all__ = [
    "ReasoningModule",
    "ReasoningModuleRegistry",
    "get_reasoning_registry",
    "reset_reasoning_registry",
]

# A callable module: (request, registry_manager) -> ReasoningResult
ReasoningModuleFn = Callable[[ReasoningRequest, Any], ReasoningResult]


@runtime_checkable
class ReasoningModule(Protocol):
    """Protocol for pluggable reasoning modules."""
    module_id:      str
    reasoning_type: ReasoningType

    def execute(self, request: ReasoningRequest, mgr: Any) -> ReasoningResult: ...


@dataclass
class _FnModule:
    """Wraps a plain callable as a ReasoningModule."""
    module_id:      str
    reasoning_type: ReasoningType
    _fn:            ReasoningModuleFn

    def execute(self, request: ReasoningRequest, mgr: Any) -> ReasoningResult:
        return self._fn(request, mgr)


class ReasoningModuleRegistry:
    """
    Thread-safe registry of reasoning module implementations.

    Registration:
      registry.register(module_id, reasoning_type, fn)  # simple callable
      registry.register_module(my_module)               # full protocol object

    Execution:
      result = registry.execute_module(module_id, request, mgr)
    """

    def __init__(self) -> None:
        self._modules: dict[str, Any] = {}
        self._lock     = threading.RLock()

    def register(
        self,
        module_id:      str,
        reasoning_type: ReasoningType,
        fn:             ReasoningModuleFn,
        overwrite:      bool = False,
    ) -> None:
        with self._lock:
            if module_id in self._modules and not overwrite:
                raise DuplicateRuleError(module_id)
            self._modules[module_id] = _FnModule(module_id, reasoning_type, fn)

    def register_module(
        self,
        module:    "ReasoningModule",
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            if module.module_id in self._modules and not overwrite:
                raise DuplicateRuleError(module.module_id)
            self._modules[module.module_id] = module

    def unregister(self, module_id: str) -> bool:
        with self._lock:
            if module_id not in self._modules:
                return False
            del self._modules[module_id]
            return True

    def get(self, module_id: str) -> "ReasoningModule":
        with self._lock:
            m = self._modules.get(module_id)
            if m is None:
                raise UnknownRuleError(module_id)
            return m

    def has(self, module_id: str) -> bool:
        with self._lock:
            return module_id in self._modules

    def list_by_type(
        self,
        reasoning_type: ReasoningType,
    ) -> list["ReasoningModule"]:
        with self._lock:
            return [
                m for m in self._modules.values()
                if m.reasoning_type == reasoning_type
            ]

    def all_modules(self) -> list["ReasoningModule"]:
        with self._lock:
            return list(self._modules.values())

    def execute_module(
        self,
        module_id: str,
        request:   ReasoningRequest,
        mgr:       Any,
    ) -> ReasoningResult:
        module = self.get(module_id)
        return module.execute(request, mgr)

    def stats(self) -> dict:
        with self._lock:
            return {"total": len(self._modules)}


# ── Singleton ─────────────────────────────────────────────────────────────────

_mreg_lock = threading.Lock()
_mreg_inst: Optional[ReasoningModuleRegistry] = None


def get_reasoning_registry() -> ReasoningModuleRegistry:
    global _mreg_inst
    if _mreg_inst is None:
        with _mreg_lock:
            if _mreg_inst is None:
                _mreg_inst = ReasoningModuleRegistry()
    return _mreg_inst


def reset_reasoning_registry() -> None:
    global _mreg_inst
    with _mreg_lock:
        _mreg_inst = None
