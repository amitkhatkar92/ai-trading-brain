"""
portfolio_snapshot_factory.py — iios.portfolio.snapshot
========================================================
PortfolioSnapshotFactory — higher-level creation API built on top of
PortfolioSnapshotBuilder.

Provides three creation paths:
- ``create_snapshot``  — full creation with all parameters.
- ``create_minimal``   — minimal valid snapshot for testing / initialisation.
- ``create_from_dict`` — deserialise a snapshot produced by ``to_dict()``.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import VERSION, SNAPSHOT_SYSTEM_ID, PortfolioHealth, SnapshotStatus
from .exceptions import SnapshotBuildError
from .portfolio_snapshot import PortfolioSnapshot
from .portfolio_snapshot_builder import PortfolioSnapshotBuilder
from .portfolio_snapshot_metadata import (
    PortfolioSnapshotMetadata,
    SnapshotAuditMetadata,
)


class PortfolioSnapshotFactory:
    """
    Convenience factory for PortfolioSnapshot creation.

    All factory methods delegate to a shared builder instance.
    """

    def __init__(self) -> None:
        self._builder = PortfolioSnapshotBuilder()

    # ------------------------------------------------------------------
    # Full creation
    # ------------------------------------------------------------------

    def create_snapshot(self, **kwargs: Any) -> PortfolioSnapshot:
        """
        Create a full PortfolioSnapshot.

        Keyword arguments are forwarded verbatim to
        ``PortfolioSnapshotBuilder.build()``.
        """
        return self._builder.build(**kwargs)

    # ------------------------------------------------------------------
    # Minimal creation (testing / initialisation)
    # ------------------------------------------------------------------

    def create_minimal(
        self,
        portfolio_id:         str,
        portfolio_session_id: str = "",
        *,
        portfolio_name:       str = "Unnamed Portfolio",
        lifecycle_state:      str = "running",
    ) -> PortfolioSnapshot:
        """
        Create the smallest valid PortfolioSnapshot.

        The resulting snapshot has DRAFT status with no holdings and
        empty summaries.  Intended for initialisation and test fixtures.
        """
        if not portfolio_session_id:
            portfolio_session_id = f"sess-{uuid.uuid4().hex[:8]}"
        return self._builder.build(
            portfolio_id         = portfolio_id,
            portfolio_session_id = portfolio_session_id,
            portfolio_name       = portfolio_name,
            lifecycle_state      = lifecycle_state,
        )

    # ------------------------------------------------------------------
    # Deserialisation
    # ------------------------------------------------------------------

    def create_from_dict(self, data: Dict[str, Any]) -> PortfolioSnapshot:
        """
        Reconstruct a PortfolioSnapshot from the dict produced by
        ``PortfolioSnapshot.to_dict()``.

        This is a re-hydration path, not a build path — identifiers
        are preserved as-is from the dict.  The snapshot is NOT
        re-registered into any store.
        """
        if not isinstance(data, dict):
            raise SnapshotBuildError(
                "create_from_dict requires a dict", portfolio_id=""
            )
        required = ("snapshot_id", "portfolio_id", "portfolio_session_id")
        for field in required:
            if not data.get(field):
                raise SnapshotBuildError(
                    f"create_from_dict: missing or empty field {field!r}",
                    portfolio_id=data.get("portfolio_id", ""),
                )

        meta_data = data.get("portfolio_metadata") or {}
        audit_data = data.get("audit_metadata") or {}

        portfolio_metadata = PortfolioSnapshotMetadata(
            snapshot_id       = meta_data.get("snapshot_id", data["snapshot_id"]),
            portfolio_id      = meta_data.get("portfolio_id", data["portfolio_id"]),
            created_at        = meta_data.get("created_at", time.time()),
            tags              = tuple(meta_data.get("tags", [])),
            labels            = dict(meta_data.get("labels", {})),
            build_source      = meta_data.get("build_source", SNAPSHOT_SYSTEM_ID),
            description       = meta_data.get("description", ""),
            framework_version = meta_data.get("framework_version", VERSION),
        )

        audit_metadata = SnapshotAuditMetadata(
            built_by               = audit_data.get("built_by", SNAPSHOT_SYSTEM_ID),
            validated_by           = audit_data.get("validated_by", ""),
            published_by           = audit_data.get("published_by", ""),
            build_duration_ms      = audit_data.get("build_duration_ms", 0.0),
            validation_duration_ms = audit_data.get("validation_duration_ms", 0.0),
            framework_version      = audit_data.get("framework_version", VERSION),
            built_at               = audit_data.get("built_at", time.time()),
            validated_at           = audit_data.get("validated_at", 0.0),
            published_at           = audit_data.get("published_at", 0.0),
            build_context          = dict(audit_data.get("build_context", {})),
        )

        return PortfolioSnapshot(
            snapshot_id          = data["snapshot_id"],
            snapshot_version     = data.get("snapshot_version", 1),
            portfolio_session_id = data["portfolio_session_id"],
            portfolio_id         = data["portfolio_id"],
            portfolio_version    = data.get("portfolio_version", 1),
            portfolio_name       = data.get("portfolio_name", ""),
            portfolio_type       = data.get("portfolio_type", ""),
            portfolio_scope      = data.get("portfolio_scope", ""),
            portfolio_objective  = data.get("portfolio_objective", ""),
            portfolio_currency   = data.get("portfolio_currency", "INR"),
            portfolio_status     = data.get("portfolio_status", "active"),
            lifecycle_state      = data.get("lifecycle_state", "running"),
            portfolio_health     = data.get("portfolio_health", PortfolioHealth.HEALTHY.value),
            snapshot_status      = data.get("snapshot_status", SnapshotStatus.DRAFT.value),
            decision_summary        = dict(data.get("decision_summary") or {}),
            allocation_summary      = dict(data.get("allocation_summary") or {}),
            rebalancing_summary     = dict(data.get("rebalancing_summary") or {}),
            exposure_summary        = dict(data.get("exposure_summary") or {}),
            diversification_summary = dict(data.get("diversification_summary") or {}),
            risk_summary            = dict(data.get("risk_summary") or {}),
            liquidity_summary       = dict(data.get("liquidity_summary") or {}),
            cash_summary            = dict(data.get("cash_summary") or {}),
            constraint_summary      = dict(data.get("constraint_summary") or {}),
            optimization_summary    = dict(data.get("optimization_summary") or {}),
            current_holdings    = tuple(data.get("current_holdings") or []),
            target_holdings     = tuple(data.get("target_holdings") or []),
            cash_balance        = float(data.get("cash_balance", 0.0)),
            reserved_capital    = float(data.get("reserved_capital", 0.0)),
            sector_allocation   = dict(data.get("sector_allocation") or {}),
            industry_allocation = dict(data.get("industry_allocation") or {}),
            asset_allocation    = dict(data.get("asset_allocation") or {}),
            strategy_allocation = dict(data.get("strategy_allocation") or {}),
            regional_allocation = dict(data.get("regional_allocation") or {}),
            currency_allocation = dict(data.get("currency_allocation") or {}),
            position_count      = int(data.get("position_count", 0)),
            exposure_metrics    = dict(data.get("exposure_metrics") or {}),
            portfolio_statistics = dict(data.get("portfolio_statistics") or {}),
            portfolio_metadata  = portfolio_metadata,
            audit_metadata      = audit_metadata,
            framework_version   = data.get("framework_version", VERSION),
            timestamp           = float(data.get("timestamp", time.time())),
        )
