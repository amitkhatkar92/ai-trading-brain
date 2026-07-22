"""
portfolio_integration_snapshot.py — iios.portfolio.integration
===============================================================
PortfolioIntegrationSnapshot — utility that builds a PortfolioSnapshot
from an integration workflow context.

This is an internal utility.  External consumers receive the
PortfolioSnapshot object via PortfolioIntegrationResponse.snapshot.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.portfolio.snapshot import (
    PortfolioSnapshot,
    PortfolioSnapshotBuilder,
    SnapshotStatus,
    PortfolioHealth,
)

from .constants import VERSION, INTEGRATION_SYSTEM_ID
from .portfolio_integration_request import PortfolioIntegrationRequest


class PortfolioIntegrationSnapshot:
    """
    Builds an immutable PortfolioSnapshot from an integration request and
    the partial workflow results gathered so far.

    The builder is stateless — create one instance and reuse it.
    """

    def __init__(self) -> None:
        # Each build() call uses a fresh builder to avoid duplicate-ID tracking
        # accumulating indefinitely.
        pass

    def build(
        self,
        request:    PortfolioIntegrationRequest,
        session_id: str,
        result:     Dict[str, Any],
        *,
        snapshot_status: SnapshotStatus = SnapshotStatus.PUBLISHED,
    ) -> PortfolioSnapshot:
        """
        Build a PortfolioSnapshot from the current workflow state.

        Parameters
        ----------
        request :         The originating integration request.
        session_id :      Lifecycle session_id (may be auto-generated if not yet set).
        result :          Accumulated workflow result dict.
        snapshot_status : Status to assign the snapshot (default PUBLISHED).

        Returns
        -------
        PortfolioSnapshot
        """
        inp = request.inputs

        # Determine session id
        if not session_id:
            import uuid
            session_id = f"int-sess-{uuid.uuid4().hex[:8]}"

        # Derive lifecycle state from inputs (default "running")
        lifecycle_state = inp.get("lifecycle_state", "running")

        # Derive portfolio health from result
        health_val = inp.get("portfolio_health", PortfolioHealth.HEALTHY.value)

        # Build summaries from result dict (pass-through what's available)
        builder = PortfolioSnapshotBuilder()
        return builder.build(
            portfolio_id            = request.portfolio_id,
            portfolio_session_id    = session_id,
            portfolio_name          = inp.get("portfolio_name", "Unnamed Portfolio"),
            portfolio_type          = inp.get("portfolio_type", ""),
            portfolio_scope         = inp.get("portfolio_scope", ""),
            portfolio_objective     = inp.get("portfolio_objective", ""),
            portfolio_currency      = inp.get("portfolio_currency", "INR"),
            portfolio_status        = inp.get("portfolio_status", "active"),
            portfolio_version       = int(inp.get("portfolio_version", 1)),
            snapshot_version        = int(inp.get("snapshot_version", 1)),
            lifecycle_state         = lifecycle_state,
            portfolio_health        = health_val,
            snapshot_status         = snapshot_status.value,
            decision_summary        = result.get("decision", {}),
            allocation_summary      = result.get("allocation", {}),
            rebalancing_summary     = result.get("rebalancing", {}),
            exposure_summary        = result.get("exposure", {}),
            diversification_summary = result.get("diversification", {}),
            risk_summary            = result.get("risk", {}),
            liquidity_summary       = result.get("liquidity", {}),
            cash_summary            = result.get("cash", {}),
            constraint_summary      = result.get("constraints", {}),
            optimization_summary    = result.get("optimization", {}),
            current_holdings        = inp.get("current_holdings", []),
            target_holdings         = inp.get("target_holdings", []),
            cash_balance            = float(inp.get("cash_balance", 0.0)),
            reserved_capital        = float(inp.get("reserved_capital", 0.0)),
            sector_allocation       = dict(inp.get("sector_allocation") or {}),
            industry_allocation     = dict(inp.get("industry_allocation") or {}),
            asset_allocation        = dict(inp.get("asset_allocation") or {}),
            strategy_allocation     = dict(inp.get("strategy_allocation") or {}),
            regional_allocation     = dict(inp.get("regional_allocation") or {}),
            currency_allocation     = dict(inp.get("currency_allocation") or {}),
            exposure_metrics        = dict(inp.get("exposure_metrics") or {}),
            portfolio_statistics    = result.get("statistics", {}),
            description             = (
                f"Integration snapshot for {request.service_type} "
                f"(request={request.request_id})"
            ),
            build_source            = INTEGRATION_SYSTEM_ID,
        )
