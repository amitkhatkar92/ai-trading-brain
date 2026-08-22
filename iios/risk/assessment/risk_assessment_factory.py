"""
risk_assessment_factory.py — iios.risk.assessment
===================================================
Object factory for the Risk Assessment Framework.

Provides convenience constructors for creating properly-configured
assessment objects with default settings.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    AssessmentDomain,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_VAR_HORIZON_DAYS,
    OptimizationObjective,
    VERSION,
)
from .risk_assessment_context import RiskAssessmentContext
from .risk_assessment_request import RiskAssessmentRequest


class RiskAssessmentFactory:
    """
    Convenience factory for assessment value objects.

    All methods return properly-initialised immutable objects.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Context factory
    # ------------------------------------------------------------------

    def create_context(
        self,
        assessment_id: str,
        portfolio_id:  str,
        risk_id:       str,
        *,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        var_horizon_days: int   = DEFAULT_VAR_HORIZON_DAYS,
        lookback_days:    int   = DEFAULT_LOOKBACK_DAYS,
        metadata:         Optional[Dict[str, Any]] = None,
    ) -> RiskAssessmentContext:
        """Create a context with all domains and capabilities enabled."""
        return RiskAssessmentContext.create(
            assessment_id    = assessment_id,
            portfolio_id     = portfolio_id,
            risk_id          = risk_id,
            confidence_level = confidence_level,
            var_horizon_days = var_horizon_days,
            lookback_days    = lookback_days,
            metadata         = metadata,
        )

    # ------------------------------------------------------------------
    # Request factory
    # ------------------------------------------------------------------

    def create_request(
        self,
        assessment_id:  str,
        portfolio_id:   str,
        risk_id:        str,
        portfolio_value: float,
        *,
        positions:       Optional[Dict[str, float]] = None,
        returns:         Optional[List[float]]      = None,
        limits:          Optional[Dict[str, float]] = None,
        policy_approved: bool                       = False,
        policy_response: Optional[Dict[str, Any]]  = None,
        market_data:     Optional[Dict[str, Any]]  = None,
        account_data:    Optional[Dict[str, Any]]  = None,
        order_data:      Optional[Dict[str, Any]]  = None,
        historical_risk: Optional[Dict[str, Any]]  = None,
        metadata:        Optional[Dict[str, Any]]  = None,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        var_horizon_days: int   = DEFAULT_VAR_HORIZON_DAYS,
        lookback_days:    int   = DEFAULT_LOOKBACK_DAYS,
    ) -> RiskAssessmentRequest:
        """Create a fully-configured assessment request."""
        return RiskAssessmentRequest.create(
            assessment_id    = assessment_id,
            portfolio_id     = portfolio_id,
            risk_id          = risk_id,
            portfolio_value  = portfolio_value,
            positions        = positions,
            returns          = returns,
            limits           = limits,
            policy_approved  = policy_approved,
            policy_response  = policy_response,
            market_data      = market_data,
            account_data     = account_data,
            order_data       = order_data,
            historical_risk  = historical_risk,
            metadata         = metadata,
            confidence_level = confidence_level,
            var_horizon_days = var_horizon_days,
            lookback_days    = lookback_days,
        )

    # ------------------------------------------------------------------
    # Quick request factory (approved, minimal)
    # ------------------------------------------------------------------

    def create_approved_request(
        self,
        portfolio_id:    str,
        portfolio_value: float,
        *,
        positions:  Optional[Dict[str, float]] = None,
        returns:    Optional[List[float]]       = None,
        limits:     Optional[Dict[str, float]]  = None,
    ) -> RiskAssessmentRequest:
        """Create a policy-approved request with auto-generated IDs."""
        assessment_id = str(uuid.uuid4())
        risk_id       = str(uuid.uuid4())
        return self.create_request(
            assessment_id    = assessment_id,
            portfolio_id     = portfolio_id,
            risk_id          = risk_id,
            portfolio_value  = portfolio_value,
            positions        = positions,
            returns          = returns,
            limits           = limits,
            policy_approved  = True,
        )
