"""iios/investment/portfolio/integration/portfolio_confidence.py

Calculates overall confidence in the integrated portfolio intelligence,
applying penalties for missing engines and unresolved conflicts.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.integration.integration_types import (
    EngineId, IntegrationParameters, REQUIRED_ENGINES, now_utc,
)


@dataclass(frozen=True)
class PortfolioConfidenceScore:
    score_id:        str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str   = ""
    calculated_at:   str   = field(default_factory=now_utc)
    raw_confidence:  float = 0.0
    penalized_score: float = 0.0
    n_engines:       int   = 0
    completeness:    float = 0.0
    n_conflicts:     int   = 0
    penalty_applied: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_confidence":  round(self.raw_confidence, 4),
            "penalized_score": round(self.penalized_score, 4),
            "n_engines":       self.n_engines,
            "completeness":    round(self.completeness, 4),
            "n_conflicts":     self.n_conflicts,
        }


class PortfolioConfidenceCalculator:
    """
    Calculates overall confidence in the integrated portfolio intelligence.
    Confidence is penalized for incompleteness and unresolved conflicts.
    """

    CONFLICT_PENALTY_PER_UNRESOLVED = 0.05
    MAX_CONFLICT_PENALTY            = 0.40
    INCOMPLETENESS_PENALTY          = 0.20

    def __init__(self, params: Optional[IntegrationParameters] = None) -> None:
        self._params = params or IntegrationParameters()

    def calculate(
        self,
        present_engines:        List[EngineId],
        completeness:           float,
        n_unresolved_conflicts: int,
        portfolio_id:           str = "",
    ) -> PortfolioConfidenceScore:
        n_required = len(REQUIRED_ENGINES)
        n_present  = len(present_engines)

        # Base: fraction of required engines present × completeness
        base = (n_present / n_required) if n_required > 0 else 0.0
        raw  = base * max(completeness, 0.0)

        # Penalties
        conflict_penalty = min(
            self.MAX_CONFLICT_PENALTY,
            n_unresolved_conflicts * self.CONFLICT_PENALTY_PER_UNRESOLVED,
        )
        incompleteness_penalty = (
            self.INCOMPLETENESS_PENALTY
            if completeness < self._params.min_completeness
            else 0.0
        )
        total_penalty = conflict_penalty + incompleteness_penalty
        penalized     = max(0.0, min(1.0, raw - total_penalty))

        return PortfolioConfidenceScore(
            portfolio_id    = portfolio_id,
            raw_confidence  = round(raw, 4),
            penalized_score = round(penalized, 4),
            n_engines       = n_present,
            completeness    = round(completeness, 4),
            n_conflicts     = n_unresolved_conflicts,
            penalty_applied = round(total_penalty, 4),
        )
