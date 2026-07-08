"""
iios/intelligence/forecast/scenario/scenario_generator.py
==========================================================
Scenario dataclass + generator logic.
The Scenario model lives here to mirror the Evidence→registry pattern.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..hypothesis_constants import ScenarioType, MAX_SCENARIOS
from ..hypothesis_exceptions import ScenarioValidationError


@dataclass
class Scenario:
    """
    A named, characterised forecast alternative.

    Attributes
    ----------
    scenario_id     : Unique identifier.
    hypothesis_id   : Parent hypothesis.
    name            : Short name (e.g. "Base Case").
    description     : Narrative explanation.
    scenario_type   : Semantic classification.
    probability     : Probability of this scenario [0, 1].
    impact          : Relative impact magnitude [0, 1].
    confidence      : Confidence in this characterisation [0, 1].
    drivers         : Causal factors (free-form strings).
    outcomes        : Expected measurable outcomes.
    forecast_id     : Attached forecast (if any).
    metadata        : Caller-supplied extras.
    created_at      : Unix timestamp.
    """

    scenario_id:   str            = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id: str            = ""
    name:          str            = ""
    description:   str            = ""
    scenario_type: ScenarioType   = ScenarioType.BASE_CASE
    probability:   float          = 0.34
    impact:        float          = 0.5
    confidence:    float          = 0.5
    drivers:       list[str]      = field(default_factory=list)
    outcomes:      dict[str, Any] = field(default_factory=dict)
    forecast_id:   str | None     = None
    metadata:      dict[str, Any] = field(default_factory=dict)
    created_at:    float          = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id":   self.scenario_id,
            "hypothesis_id": self.hypothesis_id,
            "name":          self.name,
            "description":   self.description,
            "scenario_type": self.scenario_type.value,
            "probability":   round(self.probability, 4),
            "impact":        round(self.impact, 4),
            "confidence":    round(self.confidence, 4),
            "drivers":       self.drivers,
            "outcomes":      self.outcomes,
            "forecast_id":   self.forecast_id,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }


class ScenarioGenerator:
    """
    Constructs scenario sets for a given hypothesis.
    Pluggable via override of ``generate_custom``.
    """

    # -- Standard scenario templates ──────────────────────────────────────────

    def generate_base_set(
        self,
        hypothesis_id: str,
        base_probability: float = 0.50,
        bull_probability: float = 0.25,
        bear_probability: float = 0.25,
    ) -> list[Scenario]:
        """Return (base, bull, bear) set with normalised probabilities."""
        total = base_probability + bull_probability + bear_probability
        if total <= 0:
            total = 1.0
        return [
            Scenario(
                hypothesis_id = hypothesis_id,
                name          = "Base Case",
                scenario_type = ScenarioType.BASE_CASE,
                probability   = base_probability / total,
                impact        = 0.5,
                confidence    = 0.7,
            ),
            Scenario(
                hypothesis_id = hypothesis_id,
                name          = "Bull Case",
                scenario_type = ScenarioType.BULL_CASE,
                probability   = bull_probability / total,
                impact        = 0.7,
                confidence    = 0.5,
            ),
            Scenario(
                hypothesis_id = hypothesis_id,
                name          = "Bear Case",
                scenario_type = ScenarioType.BEAR_CASE,
                probability   = bear_probability / total,
                impact        = 0.7,
                confidence    = 0.5,
            ),
        ]

    def generate_stress_set(
        self,
        hypothesis_id: str,
    ) -> list[Scenario]:
        """Return (stress, black-swan) scenarios."""
        return [
            Scenario(
                hypothesis_id = hypothesis_id,
                name          = "Stress Case",
                scenario_type = ScenarioType.STRESS_CASE,
                probability   = 0.10,
                impact        = 0.90,
                confidence    = 0.4,
            ),
            Scenario(
                hypothesis_id = hypothesis_id,
                name          = "Black Swan",
                scenario_type = ScenarioType.BLACK_SWAN,
                probability   = 0.01,
                impact        = 1.0,
                confidence    = 0.2,
            ),
        ]

    def create(
        self,
        hypothesis_id: str,
        name:          str,
        scenario_type: ScenarioType = ScenarioType.ALTERNATIVE,
        probability:   float         = 0.34,
        impact:        float         = 0.5,
        confidence:    float         = 0.5,
        description:   str           = "",
        drivers:       list[str] | None = None,
        outcomes:      dict[str, Any] | None = None,
        metadata:      dict[str, Any] | None = None,
    ) -> Scenario:
        # Validate raw inputs BEFORE creating the object so callers get
        # a clear error on out-of-range values (clamping happens after validation).
        _temp_id = str(uuid.uuid4())
        if probability < 0 or probability > 1:
            raise ScenarioValidationError(_temp_id, f"probability {probability} not in [0,1]")
        if impact < 0 or impact > 1:
            raise ScenarioValidationError(_temp_id, f"impact {impact} not in [0,1]")
        s = Scenario(
            hypothesis_id = hypothesis_id,
            name          = name,
            scenario_type = scenario_type,
            probability   = probability,
            impact        = impact,
            confidence    = max(0.0, min(1.0, confidence)),
            description   = description,
            drivers       = list(drivers) if drivers else [],
            outcomes      = dict(outcomes) if outcomes else {},
            metadata      = dict(metadata) if metadata else {},
        )
        return s

    def _validate(self, s: Scenario) -> None:
        if s.probability < 0 or s.probability > 1:
            raise ScenarioValidationError(
                s.scenario_id, f"probability {s.probability} not in [0,1]"
            )
        if s.impact < 0 or s.impact > 1:
            raise ScenarioValidationError(
                s.scenario_id, f"impact {s.impact} not in [0,1]"
            )
