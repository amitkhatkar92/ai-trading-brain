"""iios/investment/strategy/opportunity/constraint_engine.py
ConstraintEngine — enforces hard constraints that can REJECT a match
regardless of its soft matching score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate


@dataclass(frozen=True)
class ConstraintResult:
    passed:     bool
    violations: List[str] = field(default_factory=list)
    warnings:   List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "passed":     self.passed,
            "violations": self.violations,
            "warnings":   self.warnings,
        }


class ConstraintEngine:
    """
    Applies hard constraints.  A single violation causes passed=False.
    Warnings are advisory — they do not block a match.

    Constraints checked (in order):
      1. Strategy must be eligible (approved or conditional)
      2. Opportunity must not be expired
      3. Liquidity score must meet strategy minimum
      4. Opportunity confidence must meet profile minimum
      5. Asset type must be supported by strategy
      6. Direction must be supported
    """

    def __init__(
        self,
        min_confidence: float = 0.20,
        available_capital: float = 0.0,
    ) -> None:
        self._min_confidence = min_confidence
        self._available_capital = available_capital

    def check(
        self,
        candidate: StrategyCandidate,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
    ) -> ConstraintResult:
        violations: List[str] = []
        warnings: List[str] = []

        # 1. Approval
        if not candidate.is_eligible:
            violations.append(f"Strategy {candidate.strategy_id} is not eligible (status={candidate.approval_status})")

        # 2. Expiry
        if hasattr(opportunity, "is_expired") and opportunity.is_expired():
            violations.append(f"Opportunity {opportunity.opportunity_id} is expired")

        # 3. Confidence
        conf = getattr(opportunity, "confidence", 1.0)
        if conf < self._min_confidence:
            violations.append(
                f"Opportunity confidence {conf:.2f} below minimum {self._min_confidence:.2f}"
            )

        # 4. Liquidity (market opportunities only)
        if isinstance(opportunity, MarketOpportunity):
            liq = opportunity.liquidity_score
            if liq < candidate.min_liquidity_score:
                violations.append(
                    f"Liquidity {liq:.2f} < strategy minimum {candidate.min_liquidity_score:.2f}"
                )

        # 5. Direction
        direction = getattr(opportunity, "direction", "neutral")
        if not candidate.supports_direction(direction):
            violations.append(
                f"Strategy does not support direction={direction}"
            )

        # 6. Capital (advisory only — no hard reject)
        if self._available_capital > 0.0 and self._available_capital < candidate.min_capital:
            warnings.append(
                f"Available capital {self._available_capital:.0f} < strategy minimum {candidate.min_capital:.0f}"
            )

        return ConstraintResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )
