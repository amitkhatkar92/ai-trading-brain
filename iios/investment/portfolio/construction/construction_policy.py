"""iios/investment/portfolio/construction/construction_policy.py

Construction policy definitions.  Policies govern HOW a portfolio is
constructed — they encode institutional mandates, governance rules, and
investment philosophy.  They are checked BEFORE and AFTER weight assignment.

Policies are pure data + checker functions.  They do not modify the blueprint.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    ConstructionDirection,
    ConstructionType,
    MarketCapCategory,
    WeightingMethod,
)


@dataclass(frozen=True)
class PolicyViolation:
    """A single policy violation finding."""

    violation_id:  str   = field(default_factory=lambda: str(uuid.uuid4()))
    policy_name:   str   = ""
    rule:          str   = ""
    message:       str   = ""
    is_blocking:   bool  = True
    details:       Dict[str, Any] = field(default_factory=dict)
    detected_at:   float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "policy_name":  self.policy_name,
            "rule":         self.rule,
            "message":      self.message,
            "is_blocking":  self.is_blocking,
            "details":      dict(self.details),
            "detected_at":  self.detected_at,
        }


@dataclass(frozen=True)
class InvestmentUniversePolicy:
    """
    Controls which securities are eligible for the portfolio.

    All non-empty frozensets are allowlists; empty = unconstrained.
    Excluded sets override allowed sets.
    """

    policy_name:            str                       = "investment_universe"
    allowed_asset_classes:  FrozenSet[AssetClass]     = field(default_factory=frozenset)
    excluded_asset_classes: FrozenSet[AssetClass]     = field(default_factory=frozenset)
    allowed_sectors:        FrozenSet[str]            = field(default_factory=frozenset)
    excluded_sectors:       FrozenSet[str]            = field(default_factory=frozenset)
    allowed_directions:     FrozenSet[ConstructionDirection] = field(
        default_factory=lambda: frozenset({ConstructionDirection.LONG})
    )
    allowed_market_caps:    FrozenSet[MarketCapCategory] = field(default_factory=frozenset)
    allow_expired_recs:     bool                      = False

    def check_recommendation(self, rec) -> List[PolicyViolation]:
        """Check a single InvestmentRecommendation against this policy."""
        violations: List[PolicyViolation] = []

        if not self.allow_expired_recs and rec.is_expired:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="no_expired_recommendations",
                message=f"{rec.symbol} recommendation is expired",
            ))

        if self.allowed_asset_classes and rec.asset_class not in self.allowed_asset_classes:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="asset_class_allowed",
                message=f"{rec.symbol}: asset_class {rec.asset_class.value} not in allowed set",
                details={"asset_class": rec.asset_class.value},
            ))

        if rec.asset_class in self.excluded_asset_classes:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="asset_class_excluded",
                message=f"{rec.symbol}: asset_class {rec.asset_class.value} is excluded",
                details={"asset_class": rec.asset_class.value},
            ))

        if self.allowed_sectors and rec.sector not in self.allowed_sectors:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="sector_allowed",
                message=f"{rec.symbol}: sector '{rec.sector}' not in allowed set",
                details={"sector": rec.sector},
            ))

        if rec.sector in self.excluded_sectors:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="sector_excluded",
                message=f"{rec.symbol}: sector '{rec.sector}' is excluded",
                details={"sector": rec.sector},
            ))

        if self.allowed_directions and rec.direction not in self.allowed_directions:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="direction_allowed",
                message=f"{rec.symbol}: direction {rec.direction.value} not allowed",
                details={"direction": rec.direction.value},
            ))

        if self.allowed_market_caps and rec.market_cap_category not in self.allowed_market_caps:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="market_cap_allowed",
                message=f"{rec.symbol}: market_cap {rec.market_cap_category.value} not in allowed set",
                details={"market_cap": rec.market_cap_category.value},
            ))

        return violations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":            self.policy_name,
            "allowed_asset_classes":  [v.value for v in sorted(self.allowed_asset_classes)],
            "excluded_asset_classes": [v.value for v in sorted(self.excluded_asset_classes)],
            "allowed_sectors":        sorted(self.allowed_sectors),
            "excluded_sectors":       sorted(self.excluded_sectors),
            "allowed_directions":     [v.value for v in sorted(self.allowed_directions)],
            "allowed_market_caps":    [v.value for v in sorted(self.allowed_market_caps)],
            "allow_expired_recs":     self.allow_expired_recs,
        }


@dataclass(frozen=True)
class ConcentrationPolicy:
    """
    Guards against excessive concentration in individual securities,
    sectors, or asset classes.
    """

    policy_name:            str   = "concentration"
    max_single_weight:      float = 0.10     # 10% max per security
    min_single_weight:      float = 0.005    # 0.5% minimum meaningful position
    max_sector_weight:      float = 0.30     # 30% max per sector
    max_industry_weight:    float = 0.20     # 20% max per industry
    max_asset_class_weight: float = 0.70     # 70% max per asset class
    max_top3_weight:        float = 0.40     # Top 3 holdings ≤ 40%
    max_top5_weight:        float = 0.55     # Top 5 holdings ≤ 55%

    def check_blueprint(self, blueprint) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []

        for slot in blueprint.slots:
            aw = abs(slot.target_weight)
            if aw > self.max_single_weight + 1e-9:
                violations.append(PolicyViolation(
                    policy_name=self.policy_name,
                    rule="max_single_weight",
                    message=f"{slot.symbol}: weight {aw:.4f} exceeds max {self.max_single_weight:.4f}",
                    details={"symbol": slot.symbol, "weight": aw, "limit": self.max_single_weight},
                ))

        for sector, w in blueprint.sector_weights.items():
            if w > self.max_sector_weight + 1e-9:
                violations.append(PolicyViolation(
                    policy_name=self.policy_name,
                    rule="max_sector_weight",
                    message=f"Sector '{sector}': weight {w:.4f} exceeds max {self.max_sector_weight:.4f}",
                    details={"sector": sector, "weight": w, "limit": self.max_sector_weight},
                ))

        for ac, w in blueprint.asset_class_weights.items():
            if w > self.max_asset_class_weight + 1e-9:
                violations.append(PolicyViolation(
                    policy_name=self.policy_name,
                    rule="max_asset_class_weight",
                    message=f"Asset class '{ac}': weight {w:.4f} exceeds max {self.max_asset_class_weight:.4f}",
                    details={"asset_class": ac, "weight": w, "limit": self.max_asset_class_weight},
                ))

        # Top-N concentration
        sorted_weights = sorted(
            [abs(s.target_weight) for s in blueprint.slots], reverse=True
        )
        top3 = sum(sorted_weights[:3])
        top5 = sum(sorted_weights[:5])

        if top3 > self.max_top3_weight + 1e-9:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="max_top3_weight",
                message=f"Top-3 weight {top3:.4f} exceeds max {self.max_top3_weight:.4f}",
                details={"top3_weight": top3, "limit": self.max_top3_weight},
            ))

        if top5 > self.max_top5_weight + 1e-9:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="max_top5_weight",
                message=f"Top-5 weight {top5:.4f} exceeds max {self.max_top5_weight:.4f}",
                details={"top5_weight": top5, "limit": self.max_top5_weight},
            ))

        return violations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":            self.policy_name,
            "max_single_weight":      self.max_single_weight,
            "min_single_weight":      self.min_single_weight,
            "max_sector_weight":      self.max_sector_weight,
            "max_industry_weight":    self.max_industry_weight,
            "max_asset_class_weight": self.max_asset_class_weight,
            "max_top3_weight":        self.max_top3_weight,
            "max_top5_weight":        self.max_top5_weight,
        }


@dataclass(frozen=True)
class GovernancePolicy:
    """
    Governance and audit requirements for institutional portfolios.
    """

    policy_name:                 str   = "governance"
    require_source_decision_id:  bool  = True   # Each slot must trace to a decision
    require_rationale:           bool  = False  # Rationale text must be non-empty
    min_conviction:              float = 0.0    # 0 = no minimum
    min_confidence:              float = 0.0    # 0 = no minimum
    max_risk_score:              float = 1.0    # 1 = no maximum

    def check_slot(self, slot) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []

        if self.require_source_decision_id and not slot.source_decision_id:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="require_source_decision_id",
                message=f"{slot.symbol}: missing source_decision_id",
                details={"symbol": slot.symbol},
            ))

        if self.require_rationale and not slot.rationale:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="require_rationale",
                message=f"{slot.symbol}: missing rationale",
                details={"symbol": slot.symbol},
            ))

        if self.min_conviction > 0 and slot.conviction < self.min_conviction:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="min_conviction",
                message=f"{slot.symbol}: conviction {slot.conviction:.3f} below min {self.min_conviction:.3f}",
                details={"symbol": slot.symbol, "conviction": slot.conviction, "min": self.min_conviction},
            ))

        if self.max_risk_score < 1.0 and slot.risk_score > self.max_risk_score:
            violations.append(PolicyViolation(
                policy_name=self.policy_name,
                rule="max_risk_score",
                message=f"{slot.symbol}: risk_score {slot.risk_score:.3f} above max {self.max_risk_score:.3f}",
                details={"symbol": slot.symbol, "risk_score": slot.risk_score, "max": self.max_risk_score},
            ))

        return violations

    def check_blueprint(self, blueprint) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []
        for slot in blueprint.slots:
            violations.extend(self.check_slot(slot))
        return violations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":                self.policy_name,
            "require_source_decision_id": self.require_source_decision_id,
            "require_rationale":          self.require_rationale,
            "min_conviction":             self.min_conviction,
            "min_confidence":             self.min_confidence,
            "max_risk_score":             self.max_risk_score,
        }


@dataclass(frozen=True)
class ConstructionPolicySet:
    """
    Aggregated set of policies applied during construction.
    Holds one of each policy type; pass None to skip.
    """

    universe:     Optional[InvestmentUniversePolicy] = None
    concentration:Optional[ConcentrationPolicy]      = None
    governance:   Optional[GovernancePolicy]          = None

    def check_blueprint(self, blueprint) -> List[PolicyViolation]:
        """Run all registered policies against a blueprint.  Order is deterministic."""
        violations: List[PolicyViolation] = []
        if self.concentration:
            violations.extend(self.concentration.check_blueprint(blueprint))
        if self.governance:
            violations.extend(self.governance.check_blueprint(blueprint))
        return violations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "universe":      self.universe.to_dict()      if self.universe      else None,
            "concentration": self.concentration.to_dict() if self.concentration else None,
            "governance":    self.governance.to_dict()    if self.governance    else None,
        }


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def default_policy_set(
    *,
    max_single_weight:      float = 0.10,
    max_sector_weight:      float = 0.30,
    max_asset_class_weight: float = 0.70,
    require_source_id:      bool  = False,
) -> ConstructionPolicySet:
    """Return a standard policy set suitable for most portfolios."""
    return ConstructionPolicySet(
        universe=InvestmentUniversePolicy(),
        concentration=ConcentrationPolicy(
            max_single_weight=max_single_weight,
            max_sector_weight=max_sector_weight,
            max_asset_class_weight=max_asset_class_weight,
        ),
        governance=GovernancePolicy(
            require_source_decision_id=require_source_id,
        ),
    )
