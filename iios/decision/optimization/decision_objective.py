"""
decision_objective.py — iios.decision.optimization
====================================================
DecisionObjective — a single optimization criterion.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from .constants import (
    MAXIMIZE_OBJECTIVES,
    MINIMIZE_OBJECTIVES,
    OBJECTIVE_FIELD_DEFAULTS,
    OptimizationObjectiveType,
)


@dataclass
class DecisionObjective:
    """
    A single optimization criterion evaluated against every candidate.

    The objective extracts a numeric value from a candidate's field dict
    via ``target_field`` (or the default mapping for ``objective_type``),
    then normalizes it across all candidates using min-max scaling.
    MAXIMIZE objectives score higher as the value increases; MINIMIZE
    objectives invert the scale.

    An optional ``custom_evaluator`` callable may override field extraction.

    Parameters
    ----------
    objective_id :        Unique identifier.
    name :                Human-readable name.
    objective_type :      The kind of value being optimized.
    weight :              Relative importance; used for weighted-sum scoring.
    target_field :        Dotted path into ``DecisionCandidate.to_dict()`` or
                          the optimization context data.  If empty the
                          type's default mapping is used.
    description :         Optional human-readable description.
    """

    objective_id:       str
    name:               str
    objective_type:     OptimizationObjectiveType
    weight:             float   = 1.0
    target_field:       str     = ""
    description:        str     = ""
    _custom_evaluator:  Optional[Callable[[dict], float]] = field(
        default=None, repr=False, compare=False
    )

    # ------------------------------------------------------------------
    # Field resolution
    # ------------------------------------------------------------------

    @property
    def resolved_field(self) -> str:
        """The field path that will be used to extract the raw value."""
        if self.target_field:
            return self.target_field
        return OBJECTIVE_FIELD_DEFAULTS.get(self.objective_type, "")

    @property
    def is_maximize(self) -> bool:
        return self.objective_type in MAXIMIZE_OBJECTIVES

    @property
    def is_minimize(self) -> bool:
        return self.objective_type in MINIMIZE_OBJECTIVES

    def extract_value(self, candidate_data: dict) -> float:
        """
        Extract the raw numeric value from *candidate_data*.

        Uses ``_custom_evaluator`` when set; otherwise navigates
        ``resolved_field`` as a dotted path.  Returns ``0.0`` on error.
        """
        if self._custom_evaluator is not None:
            try:
                return float(self._custom_evaluator(candidate_data))
            except Exception:
                return 0.0

        field = self.resolved_field
        if not field:
            return 0.0

        current: object = candidate_data
        for key in field.split("."):
            if not isinstance(current, dict):
                return 0.0
            current = current.get(key, 0.0)

        try:
            return float(current)
        except (TypeError, ValueError):
            return 0.0

    def normalize_score(self, value: float, min_val: float, max_val: float) -> float:
        """
        Return a [0.0, 1.0] score for *value* given the population range.

        MAXIMIZE objectives return higher scores for higher values.
        MINIMIZE objectives invert the scale.
        When min == max the score is 0.5 (no information).
        """
        if max_val == min_val:
            return 0.5
        raw = (value - min_val) / (max_val - min_val)
        raw = max(0.0, min(1.0, raw))
        return raw if self.is_maximize else (1.0 - raw)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:             str,
        objective_type:   OptimizationObjectiveType,
        *,
        objective_id:     Optional[str]                 = None,
        weight:           float                          = 1.0,
        target_field:     str                            = "",
        description:      str                            = "",
        custom_evaluator: Optional[Callable[[dict], float]] = None,
    ) -> "DecisionObjective":
        return cls(
            objective_id      = objective_id or str(uuid.uuid4()),
            name              = name,
            objective_type    = objective_type,
            weight            = weight,
            target_field      = target_field,
            description       = description,
            _custom_evaluator = custom_evaluator,
        )
