"""
decision_candidate.py — iios.decision.optimization
====================================================
DecisionCandidate — a policy-approved decision option.
CandidateScore    — scored result from the scoring engine.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------

@dataclass
class DecisionCandidate:
    """
    A single policy-approved candidate decision awaiting optimization.

    All numeric scores are in [0.0, 1.0] unless noted otherwise.

    Parameters
    ----------
    candidate_id :       Unique identifier.
    decision_id :        Parent decision ID.
    symbol :             Financial instrument identifier.
    direction :          Trade direction (``"buy"``, ``"sell"``, ``"hold"``).
    quantity :           Proposed quantity (units / lots).
    price :              Proposed price.
    expected_return :    Expected P&L fraction, [-1.0, 1.0].
    risk_score :         Risk level, [0.0, 1.0].  0 = minimal, 1 = extreme.
    confidence :         Model confidence, [0.0, 1.0].
    liquidity_score :    Liquidity quality, [0.0, 1.0].  1 = highly liquid.
    execution_cost :     Estimated execution cost fraction, [0.0, 1.0].
    portfolio_exposure : Proposed portfolio weight change, [0.0, 1.0].
    source :             Originating strategy / policy label.
    metadata :           Arbitrary supplementary data.
    created_at :         Creation timestamp (UTC).
    """

    candidate_id:       str
    decision_id:        str
    symbol:             str
    direction:          str
    quantity:           float
    price:              float
    expected_return:    float
    risk_score:         float
    confidence:         float
    liquidity_score:    float    = 0.5
    execution_cost:     float    = 0.0
    portfolio_exposure: float    = 0.0
    source:             str      = ""
    metadata:           Dict[str, Any] = field(default_factory=dict)
    created_at:         datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ------------------------------------------------------------------
    # Computed properties (used by scoring engine)
    # ------------------------------------------------------------------

    @property
    def risk_adjusted_return(self) -> float:
        """Expected return divided by risk score (Sharpe-like proxy)."""
        return self.expected_return / max(self.risk_score, 0.001)

    @property
    def drawdown_estimate(self) -> float:
        """Simplified drawdown estimate from risk_score."""
        return self.risk_score * 0.5

    @property
    def capital_efficiency(self) -> float:
        """Return per unit of combined cost & exposure."""
        cost = max(self.execution_cost + self.portfolio_exposure, 0.001)
        return max(self.expected_return, 0.0) / cost

    @property
    def operational_stability(self) -> float:
        """Proxy for operational stability (equals confidence)."""
        return self.confidence

    @property
    def policy_compliance_score(self) -> float:
        """All candidates are policy-approved; compliance score = 1.0."""
        return 1.0

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a flat dict including computed properties."""
        return {
            "candidate_id":        self.candidate_id,
            "decision_id":         self.decision_id,
            "symbol":              self.symbol,
            "direction":           self.direction,
            "quantity":            self.quantity,
            "price":               self.price,
            "expected_return":     self.expected_return,
            "risk_score":          self.risk_score,
            "confidence":          self.confidence,
            "liquidity_score":     self.liquidity_score,
            "execution_cost":      self.execution_cost,
            "portfolio_exposure":  self.portfolio_exposure,
            "source":              self.source,
            # computed
            "risk_adjusted_return":   self.risk_adjusted_return,
            "drawdown_estimate":      self.drawdown_estimate,
            "capital_efficiency":     self.capital_efficiency,
            "operational_stability":  self.operational_stability,
            "policy_compliance_score": self.policy_compliance_score,
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        symbol:             str,
        direction:          str,
        quantity:           float,
        price:              float,
        expected_return:    float,
        risk_score:         float,
        confidence:         float,
        *,
        candidate_id:       Optional[str]  = None,
        decision_id:        str            = "",
        liquidity_score:    float          = 0.5,
        execution_cost:     float          = 0.0,
        portfolio_exposure: float          = 0.0,
        source:             str            = "",
        metadata:           Optional[Dict] = None,
    ) -> "DecisionCandidate":
        return cls(
            candidate_id       = candidate_id or str(uuid.uuid4()),
            decision_id        = decision_id,
            symbol             = symbol,
            direction          = direction,
            quantity           = quantity,
            price              = price,
            expected_return    = expected_return,
            risk_score         = risk_score,
            confidence         = confidence,
            liquidity_score    = liquidity_score,
            execution_cost     = execution_cost,
            portfolio_exposure = portfolio_exposure,
            source             = source,
            metadata           = metadata or {},
        )


# ---------------------------------------------------------------------------
# CandidateScore — produced by DecisionScoringEngine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CandidateScore:
    """
    Scoring result for a single candidate produced by
    :class:`DecisionScoringEngine`.

    Parameters
    ----------
    candidate_id :             Candidate this score belongs to.
    total_score :              Weighted sum of all objective scores.
    objective_scores :         Per-objective score dict (id → score).
    constraint_penalty :       Penalty deducted for soft constraint violations.
    final_score :              ``total_score - constraint_penalty``.
    is_feasible :              ``True`` if no hard constraints are violated.
    confidence_adjusted_score: ``final_score × candidate.confidence``.
    """

    candidate_id:               str
    total_score:                float
    objective_scores:           Dict[str, float]
    constraint_penalty:         float
    final_score:                float
    is_feasible:                bool
    confidence_adjusted_score:  float
