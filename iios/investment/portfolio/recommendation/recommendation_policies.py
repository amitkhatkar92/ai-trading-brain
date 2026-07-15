"""iios/investment/portfolio/recommendation/recommendation_policies.py

Institutional recommendation policies.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from iios.investment.portfolio.recommendation.recommendation_types import (
    CASH_HIGH_THRESHOLD, CASH_LOW_THRESHOLD,
    CONSTRUCTION_QUALITY_MIN, CRITICAL_EXPIRY_HOURS,
    DEFAULT_EXPIRY_HOURS, DRAWDOWN_SEVERE_THRESHOLD,
    EQUITY_OVERWEIGHT_THRESHOLD, EQUITY_UNDERWEIGHT_THRESHOLD,
    HHI_CONCENTRATED_THRESHOLD, HIGH_EXPIRY_HOURS,
    INTERNATIONAL_LOW_THRESHOLD, LOW_EXPIRY_HOURS,
    MAX_ACTIVE_RECOMMENDATIONS, MAX_SECTOR_CONCENTRATION,
    MIN_CONFIDENCE_TO_PUBLISH, MIN_EFFECTIVE_POSITIONS,
    NO_ACTION_EXPIRY_HOURS, OPTIMIZATION_QUALITY_MIN,
    REC_COOLDOWN_HOURS, RISK_BUDGET_HIGH_THRESHOLD,
    RISK_BUDGET_LOW_THRESHOLD, SHARPE_POOR_THRESHOLD,
    VAR_CRITICAL_THRESHOLD,
    PolicyType, RecommendationPriority, RecommendationRisk,
)


@dataclass(frozen=True)
class PolicyParameters:
    """
    Configurable thresholds for the recommendation engine.
    All thresholds have sensible institutional defaults.
    Override via policy for custom behaviour.
    """

    # Risk thresholds
    risk_budget_high_threshold:   float = RISK_BUDGET_HIGH_THRESHOLD
    risk_budget_low_threshold:    float = RISK_BUDGET_LOW_THRESHOLD
    var_critical_threshold:       float = VAR_CRITICAL_THRESHOLD
    drawdown_severe_threshold:    float = DRAWDOWN_SEVERE_THRESHOLD

    # Allocation thresholds
    equity_overweight_threshold:  float = EQUITY_OVERWEIGHT_THRESHOLD
    equity_underweight_threshold: float = EQUITY_UNDERWEIGHT_THRESHOLD
    cash_high_threshold:          float = CASH_HIGH_THRESHOLD
    cash_low_threshold:           float = CASH_LOW_THRESHOLD
    international_low_threshold:  float = INTERNATIONAL_LOW_THRESHOLD

    # Diversification thresholds
    hhi_concentrated_threshold:   float = HHI_CONCENTRATED_THRESHOLD
    min_effective_positions:      float = MIN_EFFECTIVE_POSITIONS
    max_sector_concentration:     float = MAX_SECTOR_CONCENTRATION

    # Performance thresholds
    sharpe_poor_threshold:        float = SHARPE_POOR_THRESHOLD
    ir_poor_threshold:            float = 0.0
    calmar_poor_threshold:        float = 0.50

    # Quality thresholds
    construction_quality_min:     float = CONSTRUCTION_QUALITY_MIN
    optimization_quality_min:     float = OPTIMIZATION_QUALITY_MIN

    # Governance
    min_confidence_to_publish:    float = MIN_CONFIDENCE_TO_PUBLISH
    max_active_recommendations:   int   = MAX_ACTIVE_RECOMMENDATIONS
    rec_cooldown_hours:           float = REC_COOLDOWN_HOURS
    require_approval_for_high_risk: bool = False

    # Expiry hours per priority
    critical_expiry_hours:        float = CRITICAL_EXPIRY_HOURS
    high_expiry_hours:            float = HIGH_EXPIRY_HOURS
    default_expiry_hours:         float = DEFAULT_EXPIRY_HOURS
    low_expiry_hours:             float = LOW_EXPIRY_HOURS
    no_action_expiry_hours:       float = NO_ACTION_EXPIRY_HOURS

    # Scoring weights
    confidence_weight:            float = 0.40
    evidence_weight:              float = 0.30
    urgency_weight:               float = 0.20
    quality_weight:               float = 0.10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_budget_high_threshold":  self.risk_budget_high_threshold,
            "equity_overweight_threshold": self.equity_overweight_threshold,
            "min_confidence_to_publish":   self.min_confidence_to_publish,
            "max_active_recommendations":  self.max_active_recommendations,
            "default_expiry_hours":        self.default_expiry_hours,
        }


@dataclass(frozen=True)
class InstitutionalPolicy:
    """An institutional recommendation policy."""

    policy_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    name:         str            = ""
    description:  str            = ""
    policy_type:  PolicyType     = PolicyType.BALANCED
    parameters:   PolicyParameters = field(default_factory=PolicyParameters)
    is_default:   bool           = False
    is_active:    bool           = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":   self.policy_id,
            "name":        self.name,
            "policy_type": self.policy_type.value,
            "is_default":  self.is_default,
        }
