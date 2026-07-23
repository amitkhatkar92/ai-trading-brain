"""
risk_integration_request.py — iios.risk.integration
=====================================================
Immutable risk integration request value object.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import RequestType, VERSION
from .risk_integration_context import RiskIntegrationContext


@dataclass(frozen=True)
class RiskIntegrationRequest:
    """
    Immutable request submitted to the Risk Integration layer.

    Carries all input snapshots and data required by the full Risk
    Intelligence pipeline.

    Fields
    ------
    request_id :         Unique request identifier.
    context :            Integration context (type, routing, timeout).
    portfolio_snapshot : Portfolio state snapshot (required for portfolio-level requests).
    decision_snapshot :  Decision Intelligence snapshot (optional).
    execution_analytics_snapshot : Execution analytics snapshot (optional).
    execution_recovery_snapshot :  Execution recovery snapshot (optional).
    execution_monitoring_snapshot: Execution monitoring snapshot (optional).
    execution_gateway_snapshot :   Execution gateway snapshot (optional).
    market_snapshot :    Market data snapshot (optional).
    account_snapshot :   Account state snapshot (optional).
    position_snapshot :  Position state snapshot (optional).
    positions :          Map of position_id → weight (fraction of portfolio).
    returns :            Historical daily return series (most recent last).
    portfolio_value :    Total portfolio market value.
    limits :             Map of limit_name → limit_value.
    metadata :           Supplementary metadata.
    requested_at :       Wall-clock submission time.
    framework_version :  Framework version string.
    """
    request_id:                    str
    context:                       RiskIntegrationContext
    portfolio_snapshot:            Dict[str, Any]
    decision_snapshot:             Dict[str, Any]
    execution_analytics_snapshot:  Dict[str, Any]
    execution_recovery_snapshot:   Dict[str, Any]
    execution_monitoring_snapshot: Dict[str, Any]
    execution_gateway_snapshot:    Dict[str, Any]
    market_snapshot:               Dict[str, Any]
    account_snapshot:              Dict[str, Any]
    position_snapshot:             Dict[str, Any]
    positions:                     Dict[str, float]
    returns:                       List[float]
    portfolio_value:               float
    limits:                        Dict[str, float]
    metadata:                      Dict[str, Any]
    requested_at:                  float = field(default_factory=time.time)
    framework_version:             str   = VERSION

    @classmethod
    def create(
        cls,
        request_type: RequestType,
        portfolio_id: str,
        *,
        request_id:            Optional[str]              = None,
        context:               Optional[RiskIntegrationContext] = None,
        portfolio_snapshot:    Optional[Dict[str, Any]]   = None,
        decision_snapshot:     Optional[Dict[str, Any]]   = None,
        execution_analytics_snapshot:  Optional[Dict[str, Any]] = None,
        execution_recovery_snapshot:   Optional[Dict[str, Any]] = None,
        execution_monitoring_snapshot: Optional[Dict[str, Any]] = None,
        execution_gateway_snapshot:    Optional[Dict[str, Any]] = None,
        market_snapshot:       Optional[Dict[str, Any]]   = None,
        account_snapshot:      Optional[Dict[str, Any]]   = None,
        position_snapshot:     Optional[Dict[str, Any]]   = None,
        positions:             Optional[Dict[str, float]] = None,
        returns:               Optional[List[float]]      = None,
        portfolio_value:       float                      = 0.0,
        limits:                Optional[Dict[str, float]] = None,
        metadata:              Optional[Dict[str, Any]]   = None,
        workflow_id:           str                        = "",
        strategy_id:           str                        = "",
        account_id:            str                        = "",
        environment:           str                        = "production",
    ) -> "RiskIntegrationRequest":
        ctx = context or RiskIntegrationContext.create(
            request_type = request_type,
            portfolio_id = portfolio_id,
            workflow_id  = workflow_id,
            strategy_id  = strategy_id,
            account_id   = account_id,
            environment  = environment,
        )
        return cls(
            request_id                    = request_id or str(uuid.uuid4()),
            context                       = ctx,
            portfolio_snapshot            = dict(portfolio_snapshot or {}),
            decision_snapshot             = dict(decision_snapshot or {}),
            execution_analytics_snapshot  = dict(execution_analytics_snapshot or {}),
            execution_recovery_snapshot   = dict(execution_recovery_snapshot or {}),
            execution_monitoring_snapshot = dict(execution_monitoring_snapshot or {}),
            execution_gateway_snapshot    = dict(execution_gateway_snapshot or {}),
            market_snapshot               = dict(market_snapshot or {}),
            account_snapshot              = dict(account_snapshot or {}),
            position_snapshot             = dict(position_snapshot or {}),
            positions                     = dict(positions or {}),
            returns                       = list(returns or []),
            portfolio_value               = portfolio_value,
            limits                        = dict(limits or {}),
            metadata                      = dict(metadata or {}),
        )

    @property
    def request_type(self) -> RequestType:
        return self.context.request_type

    @property
    def portfolio_id(self) -> str:
        return self.context.portfolio_id

    @property
    def workflow_id(self) -> str:
        return self.context.workflow_id

    @property
    def strategy_id(self) -> str:
        return self.context.strategy_id

    @property
    def account_id(self) -> str:
        return self.context.account_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "context":           self.context.to_dict(),
            "portfolio_id":      self.portfolio_id,
            "request_type":      self.request_type.value,
            "portfolio_value":   self.portfolio_value,
            "positions_count":   len(self.positions),
            "returns_count":     len(self.returns),
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }
