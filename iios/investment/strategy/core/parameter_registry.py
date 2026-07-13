"""iios/investment/strategy/core/parameter_registry.py
Central registry for strategy parameter specifications.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .strategy_configuration import ParameterSpec


class ParameterRegistry:
    """
    Global registry of ParameterSpec objects, namespaced by strategy_id.
    Enables centralised discovery and documentation of all known parameters.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # strategy_id → {param_name → ParameterSpec}
        self._specs: Dict[str, Dict[str, ParameterSpec]] = {}

    def register(self, strategy_id: str, spec: ParameterSpec) -> None:
        with self._lock:
            self._specs.setdefault(strategy_id, {})[spec.name] = spec

    def register_all(
        self, strategy_id: str, specs: List[ParameterSpec]
    ) -> None:
        for spec in specs:
            self.register(strategy_id, spec)

    def get(
        self, strategy_id: str, name: str
    ) -> Optional[ParameterSpec]:
        with self._lock:
            return self._specs.get(strategy_id, {}).get(name)

    def specs_for(self, strategy_id: str) -> Dict[str, ParameterSpec]:
        with self._lock:
            return dict(self._specs.get(strategy_id, {}))

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._specs.keys())

    def required_parameters(self, strategy_id: str) -> List[ParameterSpec]:
        with self._lock:
            return [
                s for s in self._specs.get(strategy_id, {}).values()
                if s.required
            ]

    def optional_parameters(self, strategy_id: str) -> List[ParameterSpec]:
        with self._lock:
            return [
                s for s in self._specs.get(strategy_id, {}).values()
                if not s.required
            ]

    def parameter_count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._specs.get(strategy_id, {}))
