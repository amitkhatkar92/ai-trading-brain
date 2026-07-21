"""
portfolio_factory.py — iios.portfolio.lifecycle
=================================================
Factory for creating :class:`PortfolioSession` instances.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    FACTORY_SYSTEM_ID,
    VERSION,
    PortfolioObjective,
    PortfolioScope,
    PortfolioStatus,
    PortfolioType,
)
from .portfolio_session import PortfolioSession


class PortfolioFactory:
    """
    Creates :class:`PortfolioSession` instances with validated defaults.

    Usage
    -----
    ::

        factory = PortfolioFactory()
        session = factory.create("pf-001", portfolio_name="Growth Fund")
    """

    def create(
        self,
        portfolio_id: str,
        *,
        session_id:           Optional[str]         = None,
        portfolio_name:       str                   = "",
        portfolio_type:       PortfolioType          = PortfolioType.CUSTOM,
        portfolio_scope:      PortfolioScope         = PortfolioScope.INSTITUTIONAL,
        portfolio_objective:  PortfolioObjective     = PortfolioObjective.CUSTOM,
        portfolio_currency:   str                   = "INR",
        portfolio_status:     PortfolioStatus        = PortfolioStatus.INACTIVE,
        metadata:             Optional[Dict[str, Any]] = None,
    ) -> PortfolioSession:
        """
        Create a new :class:`PortfolioSession` in CREATED state.

        Parameters
        ----------
        portfolio_id :        Caller-supplied portfolio identifier.
        session_id :          Optional explicit session ID; UUID auto-generated
                              if omitted.
        portfolio_name :      Human-readable name.
        portfolio_type :      Asset-composition classification.
        portfolio_scope :     Institutional scope.
        portfolio_objective : Investment objective.
        portfolio_currency :  Base currency (ISO 4217).
        portfolio_status :    Initial operational status.
        metadata :            Supplementary session metadata.

        Returns
        -------
        PortfolioSession
            A new session in CREATED state.
        """
        return PortfolioSession(
            session_id           = session_id,
            portfolio_id         = portfolio_id,
            portfolio_name       = portfolio_name,
            portfolio_type       = portfolio_type,
            portfolio_scope      = portfolio_scope,
            portfolio_objective  = portfolio_objective,
            portfolio_currency   = portfolio_currency,
            portfolio_status     = portfolio_status,
            metadata             = metadata,
        )
