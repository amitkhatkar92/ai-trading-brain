"""
iios/intelligence/forecast/scenario/scenario_registry.py
=========================================================
Thread-safe store for Scenario objects.
"""
from __future__ import annotations

import threading
from typing import Any

from .scenario_generator import Scenario
from ..hypothesis_constants import ScenarioType, MAX_SCENARIOS
from ..hypothesis_exceptions import ScenarioNotFoundError


class ScenarioRegistry:
    """Thread-safe in-memory store for Scenario instances."""

    def __init__(self) -> None:
        self._store:  dict[str, Scenario]     = {}
        self._by_hyp: dict[str, list[str]]    = {}
        self._lock:   threading.RLock          = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def add(self, scenario: Scenario) -> None:
        with self._lock:
            if len(self._store) >= MAX_SCENARIOS and scenario.scenario_id not in self._store:
                raise OverflowError(f"ScenarioRegistry full (max {MAX_SCENARIOS})")
            self._store[scenario.scenario_id] = scenario
            ids = self._by_hyp.setdefault(scenario.hypothesis_id, [])
            if scenario.scenario_id not in ids:
                ids.append(scenario.scenario_id)

    def add_many(self, scenarios: list[Scenario]) -> None:
        for s in scenarios:
            self.add(s)

    def remove(self, scenario_id: str) -> None:
        with self._lock:
            s = self._store.pop(scenario_id, None)
            if s and s.hypothesis_id in self._by_hyp:
                try:
                    self._by_hyp[s.hypothesis_id].remove(scenario_id)
                except ValueError:
                    pass

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, scenario_id: str) -> Scenario:
        with self._lock:
            s = self._store.get(scenario_id)
        if s is None:
            raise ScenarioNotFoundError(scenario_id)
        return s

    def has(self, scenario_id: str) -> bool:
        with self._lock:
            return scenario_id in self._store

    def for_hypothesis(self, hypothesis_id: str) -> list[Scenario]:
        with self._lock:
            ids = list(self._by_hyp.get(hypothesis_id, []))
            return [self._store[i] for i in ids if i in self._store]

    def all(self) -> list[Scenario]:
        with self._lock:
            return list(self._store.values())

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total": len(self._store),
                "hypotheses": len(self._by_hyp),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock              = threading.Lock()
_REGISTRY: ScenarioRegistry | None    = None


def get_scenario_registry() -> ScenarioRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = ScenarioRegistry()
    return _REGISTRY


def reset_scenario_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
