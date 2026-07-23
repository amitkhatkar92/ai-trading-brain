"""
market_factory.py — iios.market.lifecycle
===========================================
Factory for constructing market session domain objects.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    MarketPriority,
    MarketScope,
    MarketTimeframe,
    MarketType,
)
from .market_session import MarketSession


class MarketFactory:
    """
    Factory for constructing :class:`MarketSession` instances.

    Enforces all mandatory fields and applies sensible defaults.
    Application code should use this factory rather than instantiating
    :class:`MarketSession` directly.
    """

    def create(
        self,
        market_analysis_id: str,
        *,
        session_id:       Optional[str]            = None,
        workflow_id:      str                       = "",
        exchange:         str                       = "",
        market_scope:     MarketScope               = MarketScope.DOMESTIC,
        market_type:      MarketType                = MarketType.CUSTOM,
        market_priority:  MarketPriority            = MarketPriority.MEDIUM,
        timeframe:        MarketTimeframe            = MarketTimeframe.D1,
        market_version:   int                       = 1,
        metadata:         Optional[Dict[str, Any]]  = None,
    ) -> MarketSession:
        """
        Construct a new :class:`MarketSession` in CREATED state.

        Parameters
        ----------
        market_analysis_id : Market analysis correlation identifier.
        session_id :         Optional explicit session ID (auto-generated if None).
        workflow_id :        Workflow routing context.
        exchange :           Exchange or venue identifier.
        market_scope :       Scope of the market analysis.
        market_type :        Type of market being analysed.
        market_priority :    Priority level.
        timeframe :          Analysis timeframe.
        market_version :     Initial version counter.
        metadata :           Supplementary metadata.

        Returns
        -------
        MarketSession
            Session in CREATED state.

        Raises
        ------
        ValueError
            If ``market_analysis_id`` is empty.
        """
        if not market_analysis_id:
            raise ValueError("market_analysis_id must be a non-empty string")

        return MarketSession(
            session_id         = session_id,
            market_analysis_id = market_analysis_id,
            workflow_id        = workflow_id,
            exchange           = exchange,
            market_scope       = market_scope,
            market_type        = market_type,
            market_priority    = market_priority,
            timeframe          = timeframe,
            market_version     = market_version,
            metadata           = metadata,
        )
