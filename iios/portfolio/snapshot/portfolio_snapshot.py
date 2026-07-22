"""
portfolio_snapshot.py — iios.portfolio.snapshot
================================================
PortfolioSnapshot — the ONLY published representation of the Portfolio
Intelligence subsystem.

PortfolioSnapshot is an immutable frozen dataclass.  Every downstream
subsystem (Execution Intelligence, Risk Intelligence, AI Supervisor,
Compliance, Reporting, Dashboard) MUST consume PortfolioSnapshot
instead of internal Portfolio objects.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    VERSION,
    PortfolioHealth,
    SnapshotStatus,
    VALID_SNAPSHOT_TRANSITIONS,
)
from .portfolio_snapshot_metadata import PortfolioSnapshotMetadata, SnapshotAuditMetadata


@dataclass(frozen=True)
class PortfolioSnapshot:
    """
    Immutable, versioned, auditable representation of a portfolio at a
    specific point in time.

    PortfolioSnapshot is the publication contract between the Portfolio
    Intelligence subsystem and all downstream consumers.  It carries
    a full description of the portfolio's state, composition, risk
    profile, and governance outcomes without exposing any mutable
    internal objects.

    Fields (identity)
    -----------------
    snapshot_id :          Unique identifier for this snapshot.
    snapshot_version :     Monotonically increasing version per portfolio.
    portfolio_session_id : Portfolio lifecycle session identifier.
    portfolio_id :         Portfolio identifier.
    portfolio_version :    Version of the portfolio domain object.
    portfolio_name :       Human-readable portfolio name.
    portfolio_type :       Asset-composition classification.
    portfolio_scope :      Institutional scope.
    portfolio_objective :  Investment objective.
    portfolio_currency :   Base currency (ISO 4217).
    portfolio_status :     Operational status.
    lifecycle_state :      Portfolio lifecycle state value.
    portfolio_health :     Operational health at snapshot time.
    snapshot_status :      Publication lifecycle of this snapshot.

    Fields (summaries — populated from upstream frameworks)
    -------------------------------------------------------
    decision_summary :        Decision Intelligence outcomes.
    allocation_summary :      Allocation engine outputs.
    rebalancing_summary :     Rebalancing engine outputs.
    exposure_summary :        Exposure metrics.
    diversification_summary : Diversification metrics.
    risk_summary :            Risk engine outputs.
    liquidity_summary :       Liquidity assessment.
    cash_summary :            Cash and reserve status.
    constraint_summary :      Constraint evaluation outcomes.
    optimization_summary :    Optimization framework outputs.

    Fields (composition)
    --------------------
    current_holdings :    Tuple of current position dicts.
    target_holdings :     Tuple of target position dicts.
    cash_balance :        Available cash balance.
    reserved_capital :    Reserved/locked capital.
    sector_allocation :   Sector → weight mapping.
    industry_allocation : Industry → weight mapping.
    asset_allocation :    Asset class → weight mapping.
    strategy_allocation : Strategy → weight mapping.
    regional_allocation : Region → weight mapping.
    currency_allocation : Currency → weight mapping.
    position_count :      Number of current positions.
    exposure_metrics :    Gross/net exposure and factor metrics.

    Fields (statistics and metadata)
    ---------------------------------
    portfolio_statistics : Portfolio performance/risk statistics.
    portfolio_metadata :   Descriptive metadata.
    audit_metadata :       Build/validation/publication audit trail.
    framework_version :    Framework version string.
    timestamp :            Wall-clock snapshot creation time.
    """

    # --- Identity ---
    snapshot_id:          str
    snapshot_version:     int
    portfolio_session_id: str
    portfolio_id:         str
    portfolio_version:    int
    portfolio_name:       str
    portfolio_type:       str
    portfolio_scope:      str
    portfolio_objective:  str
    portfolio_currency:   str
    portfolio_status:     str
    lifecycle_state:      str
    portfolio_health:     str   # PortfolioHealth.value
    snapshot_status:      str   # SnapshotStatus.value

    # --- Summaries ---
    decision_summary:        Dict[str, Any]
    allocation_summary:      Dict[str, Any]
    rebalancing_summary:     Dict[str, Any]
    exposure_summary:        Dict[str, Any]
    diversification_summary: Dict[str, Any]
    risk_summary:            Dict[str, Any]
    liquidity_summary:       Dict[str, Any]
    cash_summary:            Dict[str, Any]
    constraint_summary:      Dict[str, Any]
    optimization_summary:    Dict[str, Any]

    # --- Composition ---
    current_holdings:     tuple            # Tuple[Dict[str, Any], ...]
    target_holdings:      tuple            # Tuple[Dict[str, Any], ...]
    cash_balance:         float
    reserved_capital:     float
    sector_allocation:    Dict[str, float]
    industry_allocation:  Dict[str, float]
    asset_allocation:     Dict[str, float]
    strategy_allocation:  Dict[str, float]
    regional_allocation:  Dict[str, float]
    currency_allocation:  Dict[str, float]
    position_count:       int
    exposure_metrics:     Dict[str, Any]

    # --- Statistics ---
    portfolio_statistics: Dict[str, Any]

    # --- Metadata ---
    portfolio_metadata:   PortfolioSnapshotMetadata
    audit_metadata:       SnapshotAuditMetadata

    # --- Framework ---
    framework_version:    str
    timestamp:            float

    # ==================================================================
    # Derived properties
    # ==================================================================

    @property
    def is_published(self) -> bool:
        return self.snapshot_status == SnapshotStatus.PUBLISHED.value

    @property
    def is_validated(self) -> bool:
        return self.snapshot_status in (
            SnapshotStatus.VALIDATED.value,
            SnapshotStatus.PUBLISHED.value,
        )

    @property
    def is_archived(self) -> bool:
        return self.snapshot_status == SnapshotStatus.ARCHIVED.value

    @property
    def is_draft(self) -> bool:
        return self.snapshot_status == SnapshotStatus.DRAFT.value

    @property
    def is_healthy(self) -> bool:
        return self.portfolio_health == PortfolioHealth.HEALTHY.value

    @property
    def total_allocation(self) -> float:
        """Sum of all sector allocation weights (should be ≤ 1.0 in a valid snapshot)."""
        return sum(self.sector_allocation.values())

    # ==================================================================
    # Non-mutating status transitions
    # ==================================================================

    def with_status(self, status: SnapshotStatus) -> "PortfolioSnapshot":
        """Return a new snapshot with an updated status (non-mutating)."""
        return dataclasses.replace(self, snapshot_status=status.value)

    def with_audit(self, audit: SnapshotAuditMetadata) -> "PortfolioSnapshot":
        """Return a new snapshot with updated audit metadata (non-mutating)."""
        return dataclasses.replace(self, audit_metadata=audit)

    # ==================================================================
    # Serialisation
    # ==================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the snapshot to a fully JSON-compatible dict."""
        return {
            # Identity
            "snapshot_id":          self.snapshot_id,
            "snapshot_version":     self.snapshot_version,
            "portfolio_session_id": self.portfolio_session_id,
            "portfolio_id":         self.portfolio_id,
            "portfolio_version":    self.portfolio_version,
            "portfolio_name":       self.portfolio_name,
            "portfolio_type":       self.portfolio_type,
            "portfolio_scope":      self.portfolio_scope,
            "portfolio_objective":  self.portfolio_objective,
            "portfolio_currency":   self.portfolio_currency,
            "portfolio_status":     self.portfolio_status,
            "lifecycle_state":      self.lifecycle_state,
            "portfolio_health":     self.portfolio_health,
            "snapshot_status":      self.snapshot_status,
            # Summaries
            "decision_summary":        dict(self.decision_summary),
            "allocation_summary":      dict(self.allocation_summary),
            "rebalancing_summary":     dict(self.rebalancing_summary),
            "exposure_summary":        dict(self.exposure_summary),
            "diversification_summary": dict(self.diversification_summary),
            "risk_summary":            dict(self.risk_summary),
            "liquidity_summary":       dict(self.liquidity_summary),
            "cash_summary":            dict(self.cash_summary),
            "constraint_summary":      dict(self.constraint_summary),
            "optimization_summary":    dict(self.optimization_summary),
            # Composition
            "current_holdings":    list(self.current_holdings),
            "target_holdings":     list(self.target_holdings),
            "cash_balance":        self.cash_balance,
            "reserved_capital":    self.reserved_capital,
            "sector_allocation":   dict(self.sector_allocation),
            "industry_allocation": dict(self.industry_allocation),
            "asset_allocation":    dict(self.asset_allocation),
            "strategy_allocation": dict(self.strategy_allocation),
            "regional_allocation": dict(self.regional_allocation),
            "currency_allocation": dict(self.currency_allocation),
            "position_count":      self.position_count,
            "exposure_metrics":    dict(self.exposure_metrics),
            # Statistics & metadata
            "portfolio_statistics": dict(self.portfolio_statistics),
            "portfolio_metadata":   self.portfolio_metadata.to_dict(),
            "audit_metadata":       self.audit_metadata.to_dict(),
            # Framework
            "framework_version": self.framework_version,
            "timestamp":         self.timestamp,
        }
