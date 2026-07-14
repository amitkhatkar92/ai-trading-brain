"""iios/investment/decision/risk/scenario_registry.py
ScenarioRegistry — thread-safe store for StressScenarios.
Supports custom scenario registration alongside defaults.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.decision.risk.risk_constants import ScenarioType
from iios.investment.decision.risk.stress_scenarios import DEFAULT_SCENARIOS, StressScenario


class ScenarioRegistry:
    """Thread-safe registry for StressScenarios."""

    def __init__(self, load_defaults: bool = True) -> None:
        self._lock      = threading.RLock()
        self._scenarios: Dict[str, StressScenario] = {}
        if load_defaults:
            for s in DEFAULT_SCENARIOS:
                self._scenarios[s.scenario_type.value] = s

    def register(self, scenario: StressScenario) -> None:
        with self._lock:
            self._scenarios[scenario.scenario_type.value] = scenario

    def get(self, scenario_type: ScenarioType) -> Optional[StressScenario]:
        with self._lock:
            return self._scenarios.get(scenario_type.value)

    def all_scenarios(self) -> List[StressScenario]:
        with self._lock:
            return list(self._scenarios.values())

    def count(self) -> int:
        with self._lock:
            return len(self._scenarios)

    def remove(self, scenario_type: ScenarioType) -> None:
        with self._lock:
            self._scenarios.pop(scenario_type.value, None)
