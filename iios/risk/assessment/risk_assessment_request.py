"""
risk_assessment_request.py — iios.risk.assessment
===================================================
Immutable risk assessment request value object.

Carries all input data (portfolio, positions, returns, limits, policy
response) required by the quantitative assessment pipeline.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_VAR_HORIZON_DAYS,
    VERSION,
)
from .risk_assessment_context import RiskAssessmentContext


@dataclass(frozen=True)
class RiskAssessmentRequest:
    """
    Immutable request submitted to the Risk Assessment Framework.

    The framework evaluates only policy-approved requests.  The
    ``policy_approved`` flag must be set to ``True`` before the engine
    will process the assessment.

    Fields
    ------
    request_id :          Unique request identifier.
    assessment_id :       Assessment correlation identifier.
    portfolio_id :        Target portfolio.
    risk_id :             Originating risk workflow identifier.
    context :             Assessment configuration context.
    portfolio_value :     Total portfolio market value.
    positions :           Map of position_id → weight (fraction of portfolio).
    returns :             Historical daily return series (most recent last).
    limits :              Map of limit_name → limit_value.
    policy_approved :     Must be True — engine rejects unapproved requests.
    policy_response :     Serialised RiskPolicyResponse metadata (informational).
    market_data :         Current market snapshot (optional).
    account_data :        Account snapshot (optional).
    order_data :          Order snapshot (optional).
    historical_risk :     Previous risk assessment data (optional).
    requested_at :        Wall-clock submission time.
    metadata :            Supplementary metadata.
    framework_version :   Framework version string.
    """
    request_id:        str
    assessment_id:     str
    portfolio_id:      str
    risk_id:           str
    context:           RiskAssessmentContext
    portfolio_value:   float
    positions:         Dict[str, float]
    returns:           List[float]
    limits:            Dict[str, float]
    policy_approved:   bool
    policy_response:   Dict[str, Any]
    market_data:       Dict[str, Any]
    account_data:      Dict[str, Any]
    order_data:        Dict[str, Any]
    historical_risk:   Dict[str, Any]
    requested_at:      float          = field(default_factory=time.time)
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        assessment_id:  str,
        portfolio_id:   str,
        risk_id:        str,
        portfolio_value: float,
        *,
        request_id:       Optional[str]              = None,
        context:          Optional[RiskAssessmentContext] = None,
        positions:        Optional[Dict[str, float]] = None,
        returns:          Optional[List[float]]      = None,
        limits:           Optional[Dict[str, float]] = None,
        policy_approved:  bool                       = False,
        policy_response:  Optional[Dict[str, Any]]  = None,
        market_data:      Optional[Dict[str, Any]]  = None,
        account_data:     Optional[Dict[str, Any]]  = None,
        order_data:       Optional[Dict[str, Any]]  = None,
        historical_risk:  Optional[Dict[str, Any]]  = None,
        metadata:         Optional[Dict[str, Any]]  = None,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        var_horizon_days: int   = DEFAULT_VAR_HORIZON_DAYS,
        lookback_days:    int   = DEFAULT_LOOKBACK_DAYS,
    ) -> "RiskAssessmentRequest":
        ctx = context or RiskAssessmentContext.create(
            assessment_id    = assessment_id,
            portfolio_id     = portfolio_id,
            risk_id          = risk_id,
            confidence_level = confidence_level,
            var_horizon_days = var_horizon_days,
            lookback_days    = lookback_days,
        )
        return cls(
            request_id      = request_id or str(uuid.uuid4()),
            assessment_id   = assessment_id,
            portfolio_id    = portfolio_id,
            risk_id         = risk_id,
            context         = ctx,
            portfolio_value = portfolio_value,
            positions       = dict(positions or {}),
            returns         = list(returns or []),
            limits          = dict(limits or {}),
            policy_approved = policy_approved,
            policy_response = dict(policy_response or {}),
            market_data     = dict(market_data or {}),
            account_data    = dict(account_data or {}),
            order_data      = dict(order_data or {}),
            historical_risk = dict(historical_risk or {}),
            metadata        = dict(metadata or {}),
        )

    # ------------------------------------------------------------------
    # Derived helpers (no mutation)
    # ------------------------------------------------------------------

    @property
    def confidence_level(self) -> float:
        return self.context.confidence_level

    @property
    def var_horizon_days(self) -> int:
        return self.context.var_horizon_days

    @property
    def total_positions(self) -> int:
        return len(self.positions)

    @property
    def has_returns(self) -> bool:
        return len(self.returns) > 0

    def get_limit(self, name: str, default: float = 0.0) -> float:
        return self.limits.get(name, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":      self.request_id,
            "assessment_id":   self.assessment_id,
            "portfolio_id":    self.portfolio_id,
            "risk_id":         self.risk_id,
            "portfolio_value": self.portfolio_value,
            "total_positions": self.total_positions,
            "returns_count":   len(self.returns),
            "limits_count":    len(self.limits),
            "policy_approved": self.policy_approved,
            "requested_at":    self.requested_at,
            "framework_version": self.framework_version,
        }
