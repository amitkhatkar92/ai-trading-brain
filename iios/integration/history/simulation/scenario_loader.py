"""iios/integration/history/simulation/scenario_loader.py

Loads scenario definitions for simulation runs.

A scenario is a named configuration that specifies:
- which datasets to use
- the time range
- the speed
- overrides for any simulation parameters
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import (
    HistoricalDataType,
    SimulationMode,
    SimulationStatus,
)
from iios.integration.history.history_exceptions import ScenarioNotFoundError


@dataclass
class Scenario:
    """One simulation scenario definition."""
    scenario_id:      str               = field(default_factory=lambda: str(uuid.uuid4()))
    name:             str               = ""
    description:      str               = ""
    mode:             SimulationMode    = SimulationMode.SCENARIO
    dataset_ids:      list[str]         = field(default_factory=list)
    data_types:       list[HistoricalDataType] = field(default_factory=list)
    symbols:          list[str]         = field(default_factory=list)
    start_ts:         float             = 0.0
    end_ts:           float             = 0.0
    speed_multiplier: float             = 0.0   # 0 = as-fast-as-possible
    seed:             int               = 42     # for deterministic RNG
    parameters:       dict[str, Any]    = field(default_factory=dict)
    tags:             list[str]         = field(default_factory=list)
    created_at:       float             = field(default_factory=time.time)
    metadata:         dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id":      self.scenario_id,
            "name":             self.name,
            "mode":             self.mode.value,
            "start_ts":         self.start_ts,
            "end_ts":           self.end_ts,
            "speed_multiplier": self.speed_multiplier,
            "seed":             self.seed,
        }


class ScenarioLoader:
    """
    In-memory scenario registry.

    Scenarios can be registered programmatically or loaded from
    external configuration (extension point).
    """

    def __init__(self) -> None:
        self._scenarios: dict[str, Scenario] = {}

    def register(self, scenario: Scenario) -> None:
        self._scenarios[scenario.scenario_id] = scenario

    def register_by_name(self, scenario: Scenario) -> None:
        """Also index by name for human-friendly lookup."""
        self._scenarios[scenario.scenario_id] = scenario
        self._scenarios[scenario.name]         = scenario

    def get(self, scenario_id_or_name: str) -> Scenario:
        s = self._scenarios.get(scenario_id_or_name)
        if s is None:
            raise ScenarioNotFoundError(
                f"Scenario '{scenario_id_or_name}' not found."
            )
        return s

    def has(self, scenario_id_or_name: str) -> bool:
        return scenario_id_or_name in self._scenarios

    def list_all(self) -> list[Scenario]:
        seen: set[str] = set()
        result = []
        for s in self._scenarios.values():
            if s.scenario_id not in seen:
                seen.add(s.scenario_id)
                result.append(s)
        return result

    def count(self) -> int:
        return len({s.scenario_id for s in self._scenarios.values()})
