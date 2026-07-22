"""
risk_factory.py — iios.risk.lifecycle
========================================
Factory for constructing risk session domain objects.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    RiskPriority,
    RiskScope,
    RiskType,
)
from .risk_session import RiskSession


class RiskFactory:
    """
    Factory for constructing :class:`RiskSession` instances.

    Enforces all mandatory fields and applies sensible defaults.
    Application code should use this factory rather than instantiating
    :class:`RiskSession` directly.

    Usage
    -----
    ::

        factory = RiskFactory()
        session = factory.create("risk-001", "pf-001")
    """

    def create(
        self,
        risk_id:      str,
        portfolio_id: str,
        *,
        session_id:    Optional[str]          = None,
        assessment_id: str                    = "",
        workflow_id:   str                    = "",
        strategy_id:   str                    = "",
        risk_scope:    RiskScope              = RiskScope.PORTFOLIO,
        risk_type:     RiskType               = RiskType.CUSTOM,
        risk_priority: RiskPriority           = RiskPriority.MEDIUM,
        risk_version:  int                    = 1,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> RiskSession:
        """
        Construct a new :class:`RiskSession` in CREATED state.

        Parameters
        ----------
        risk_id :       Risk assessment identifier.
        portfolio_id :  Portfolio being assessed.
        session_id :    Optional explicit session ID (auto-generated if None).
        assessment_id : Assessment correlation identifier.
        workflow_id :   Workflow routing context.
        strategy_id :   Strategy being assessed.
        risk_scope :    Scope of the risk assessment.
        risk_type :     Type of risk being assessed.
        risk_priority : Priority level.
        risk_version :  Initial version counter.
        metadata :      Supplementary metadata.

        Returns
        -------
        RiskSession
            Session in CREATED state.
        """
        if not risk_id:
            raise ValueError("risk_id must be a non-empty string")
        if not portfolio_id:
            raise ValueError("portfolio_id must be a non-empty string")

        return RiskSession(
            session_id    = session_id,
            risk_id       = risk_id,
            assessment_id = assessment_id,
            workflow_id   = workflow_id,
            portfolio_id  = portfolio_id,
            strategy_id   = strategy_id,
            risk_scope    = risk_scope,
            risk_type     = risk_type,
            risk_priority = risk_priority,
            risk_version  = risk_version,
            metadata      = metadata,
        )
