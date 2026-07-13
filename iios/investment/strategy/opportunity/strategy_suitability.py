"""iios/investment/strategy/opportunity/strategy_suitability.py
SuitabilityEngine — combines ConstraintEngine + CompatibilityEngine
into a single suitability verdict per strategy–opportunity pair.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.constraint_engine import (
    ConstraintEngine, ConstraintResult
)
from iios.investment.strategy.opportunity.compatibility_engine import (
    CompatibilityEngine, CompatibilityScores
)
from iios.investment.strategy.opportunity.suitability_statistics import clamp


@dataclass(frozen=True)
class SuitabilityResult:
    """
    Full suitability assessment for one strategy–opportunity pair.
    score is in [0, 100]; suitable=True only when all constraints pass.
    """
    strategy_id:    str
    opportunity_id: str
    suitable:       bool
    score:          float         # 0–100
    constraints:    ConstraintResult
    compatibility:  CompatibilityScores
    rationale:      str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":    self.strategy_id,
            "opportunity_id": self.opportunity_id,
            "suitable":       self.suitable,
            "score":          self.score,
            "constraints":    self.constraints.to_dict(),
            "compatibility":  self.compatibility.to_dict(),
            "rationale":      self.rationale,
        }


class SuitabilityEngine:
    """
    Evaluates whether a strategy is suitable for an opportunity.

    Constraints are checked first (hard gates).  If all pass, compatibility
    scores are computed and aggregated into a single suitability score.
    """

    def __init__(
        self,
        available_capital: float = 0.0,
        min_confidence: float = 0.20,
        min_suitability_score: float = 40.0,
    ) -> None:
        self._constraints   = ConstraintEngine(
            min_confidence=min_confidence,
            available_capital=available_capital,
        )
        self._compatibility = CompatibilityEngine(
            available_capital=available_capital
        )
        self._min_score     = min_suitability_score

    def evaluate(
        self,
        candidate: StrategyCandidate,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
    ) -> SuitabilityResult:
        oid = opportunity.opportunity_id

        # ── hard constraints ──────────────────────────────────────────────────
        cr = self._constraints.check(candidate, opportunity)
        if not cr.passed:
            rationale = "Hard constraint violations: " + "; ".join(cr.violations)
            return SuitabilityResult(
                strategy_id=candidate.strategy_id,
                opportunity_id=oid,
                suitable=False,
                score=0.0,
                constraints=cr,
                compatibility=CompatibilityScores(),
                rationale=rationale,
            )

        # ── soft compatibility ────────────────────────────────────────────────
        compat = self._compatibility.score(candidate, opportunity)

        # Blend evaluation quality into the suitability score
        eval_boost = candidate.evaluation_score * 0.15
        raw = compat.overall * 0.85 + eval_boost
        score = round(clamp(raw), 2)
        suitable = score >= self._min_score

        rationale = self._build_rationale(candidate, opportunity, compat, suitable)

        return SuitabilityResult(
            strategy_id=candidate.strategy_id,
            opportunity_id=oid,
            suitable=suitable,
            score=score,
            constraints=cr,
            compatibility=compat,
            rationale=rationale,
        )

    def _build_rationale(
        self,
        c: StrategyCandidate,
        opp: Union[MarketOpportunity, CompanyOpportunity],
        compat: CompatibilityScores,
        suitable: bool,
    ) -> str:
        verdict = "SUITABLE" if suitable else "MARGINAL"
        parts = [f"{verdict}: overall_compat={compat.overall:.1f}"]
        if compat.risk_compatibility < 50.0:
            parts.append("risk-compatibility low")
        if compat.timeframe_compatibility < 50.0:
            parts.append("timeframe mismatch")
        if compat.execution_readiness < 60.0:
            parts.append("execution not ready")
        return " | ".join(parts)
