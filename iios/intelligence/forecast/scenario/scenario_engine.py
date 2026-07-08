"""
iios/intelligence/forecast/scenario/scenario_engine.py
=======================================================
ScenarioEngine — create, store, and compare scenarios.
"""
from __future__ import annotations

import threading
from typing import Any

from .scenario_comparator import ScenarioComparator, ScenarioComparison
from .scenario_generator import Scenario, ScenarioGenerator
from .scenario_registry import ScenarioRegistry, get_scenario_registry
from ..hypothesis_constants import ScenarioType
from ..hypothesis_exceptions import InsufficientScenariosError


class ScenarioEngine:
    """Façade for scenario generation, storage, and comparison."""

    def __init__(self) -> None:
        self._generator: ScenarioGenerator = ScenarioGenerator()
        self._registry:  ScenarioRegistry   = get_scenario_registry()
        self._comparator: ScenarioComparator = ScenarioComparator()
        self._lock:      threading.RLock     = threading.RLock()

    # -- Generate ──────────────────────────────────────────────────────────────

    def generate_base_set(
        self,
        hypothesis_id:    str,
        base_probability: float = 0.50,
        bull_probability: float = 0.25,
        bear_probability: float = 0.25,
    ) -> list[Scenario]:
        scenarios = self._generator.generate_base_set(
            hypothesis_id, base_probability, bull_probability, bear_probability
        )
        self._registry.add_many(scenarios)
        return scenarios

    def generate_stress_set(self, hypothesis_id: str) -> list[Scenario]:
        scenarios = self._generator.generate_stress_set(hypothesis_id)
        self._registry.add_many(scenarios)
        return scenarios

    def create(
        self,
        hypothesis_id: str,
        name:          str,
        scenario_type: ScenarioType = ScenarioType.ALTERNATIVE,
        **kwargs: Any,
    ) -> Scenario:
        s = self._generator.create(hypothesis_id, name, scenario_type, **kwargs)
        self._registry.add(s)
        return s

    # -- Compare ───────────────────────────────────────────────────────────────

    def compare(self, scenario_ids: list[str]) -> ScenarioComparison:
        if len(scenario_ids) < 2:
            raise InsufficientScenariosError(2, len(scenario_ids))
        scenarios = [self._registry.get(sid) for sid in scenario_ids]
        return self._comparator.compare(scenarios)

    def compare_for_hypothesis(self, hypothesis_id: str) -> ScenarioComparison:
        scenarios = self._registry.for_hypothesis(hypothesis_id)
        if len(scenarios) < 2:
            raise InsufficientScenariosError(2, len(scenarios))
        return self._comparator.compare(scenarios)

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, scenario_id: str) -> Scenario:
        return self._registry.get(scenario_id)

    def for_hypothesis(self, hypothesis_id: str) -> list[Scenario]:
        return self._registry.for_hypothesis(hypothesis_id)

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return self._registry.stats()


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock          = threading.Lock()
_ENGINE: ScenarioEngine | None  = None


def get_scenario_engine() -> ScenarioEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = ScenarioEngine()
    return _ENGINE


def reset_scenario_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
