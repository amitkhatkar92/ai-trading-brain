"""
benchmark_scenario.py -- iios.ai.learning_evaluation.core
===========================================================
:class:`ScenarioType`     — scenario classification.
:class:`BenchmarkScenario` — immutable scenario specification.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class ScenarioType(str, Enum):
    """Classification of a benchmark scenario."""
    CORRECTNESS     = "correctness"
    EDGE_CASE       = "edge_case"
    STRESS          = "stress"
    REGRESSION      = "regression"
    PERFORMANCE     = "performance"
    ADVERSARIAL     = "adversarial"
    HALLUCINATION   = "hallucination"


@dataclass(frozen=True)
class BenchmarkScenario:
    """
    Immutable specification for one benchmark scenario.

    ``input_data``   — data provided to the system under benchmark.
    ``expected``     — optional ground-truth for correctness scenarios.
    ``weight``       — relative contribution to aggregate benchmark score (default 1.0).
    ``parameters``   — scenario-specific key→value settings.
    ``pass_threshold`` — minimum score to consider this scenario passing.
    """

    scenario_id:     str
    name:            str
    scenario_type:   ScenarioType
    input_data:      Any
    expected:        Optional[Any]
    weight:          float
    pass_threshold:  float
    parameters:      FrozenSet[Tuple[str, Any]]
    description:     str

    @classmethod
    def create(
        cls,
        name:           str,
        scenario_type:  ScenarioType,
        input_data:     Any,
        expected:       Optional[Any]          = None,
        weight:         float                  = 1.0,
        pass_threshold: float                  = 0.6,
        description:    str                    = "",
        **parameters: Any,
    ) -> "BenchmarkScenario":
        return cls(
            scenario_id    = str(uuid.uuid4()),
            name           = name,
            scenario_type  = scenario_type,
            input_data     = input_data,
            expected       = expected,
            weight         = max(0.0, weight),
            pass_threshold = max(0.0, min(1.0, pass_threshold)),
            parameters     = frozenset(parameters.items()),
            description    = description,
        )

    def get_param(self, key: str, default: Any = None) -> Any:
        for k, v in self.parameters:
            if k == key:
                return v
        return default
