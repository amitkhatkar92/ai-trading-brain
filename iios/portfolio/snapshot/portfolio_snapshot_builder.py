"""
portfolio_snapshot_builder.py — iios.portfolio.snapshot
========================================================
PortfolioSnapshotBuilder — constructs PortfolioSnapshot objects from
validated upstream framework outputs.

Builder rejects
---------------
- Missing required identifiers (portfolio_id, portfolio_session_id)
- Duplicate snapshot IDs (tracked per-instance)
- Incomplete portfolio state (empty lifecycle_state)
- Invalid lifecycle state (not a recognised value)
- Invalid optimization state (non-string status in optimization_summary)

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    VERSION,
    SNAPSHOT_SYSTEM_ID,
    ACTOR_BUILDER,
    PortfolioHealth,
    SnapshotStatus,
)
from .exceptions import SnapshotBuildError, SnapshotDuplicateError
from .portfolio_snapshot import PortfolioSnapshot
from .portfolio_snapshot_metadata import (
    PortfolioSnapshotMetadata,
    SnapshotAuditMetadata,
)


class PortfolioSnapshotBuilder:
    """
    Constructs immutable PortfolioSnapshot objects.

    The builder is stateful only in that it tracks snapshot IDs it has
    already generated (to prevent duplicate emission).  It is safe to
    reuse across builds.

    Usage::
        builder = PortfolioSnapshotBuilder()
        snapshot = builder.build(
            portfolio_id="pf-001",
            portfolio_session_id="sess-001",
            portfolio_name="NIFTY Momentum",
            lifecycle_state="running",
        )
    """

    _VALID_LIFECYCLE_STATES = frozenset({
        "initialising", "running", "paused", "stopped", "error",
        "active", "inactive", "pending",
    })

    def __init__(self) -> None:
        self._lock    = threading.Lock()
        self._seen:   set[str] = set()   # snapshot_ids already emitted

    # ------------------------------------------------------------------
    # Primary build method
    # ------------------------------------------------------------------

    def build(
        self,
        *,
        # Required identifiers
        portfolio_id:         str,
        portfolio_session_id: str,
        # Core identity
        portfolio_name:       str   = "",
        portfolio_type:       str   = "",
        portfolio_scope:      str   = "",
        portfolio_objective:  str   = "",
        portfolio_currency:   str   = "INR",
        portfolio_status:     str   = "active",
        portfolio_version:    int   = 1,
        snapshot_version:     int   = 1,
        # Lifecycle & health
        lifecycle_state:      str   = "running",
        portfolio_health:     str   = PortfolioHealth.HEALTHY.value,
        snapshot_status:      str   = SnapshotStatus.DRAFT.value,
        # Upstream framework outputs
        decision_summary:        Optional[Dict[str, Any]] = None,
        allocation_summary:      Optional[Dict[str, Any]] = None,
        rebalancing_summary:     Optional[Dict[str, Any]] = None,
        exposure_summary:        Optional[Dict[str, Any]] = None,
        diversification_summary: Optional[Dict[str, Any]] = None,
        risk_summary:            Optional[Dict[str, Any]] = None,
        liquidity_summary:       Optional[Dict[str, Any]] = None,
        cash_summary:            Optional[Dict[str, Any]] = None,
        constraint_summary:      Optional[Dict[str, Any]] = None,
        optimization_summary:    Optional[Dict[str, Any]] = None,
        # Portfolio composition
        current_holdings:    Optional[List[Dict[str, Any]]] = None,
        target_holdings:     Optional[List[Dict[str, Any]]] = None,
        cash_balance:        float = 0.0,
        reserved_capital:    float = 0.0,
        sector_allocation:   Optional[Dict[str, float]] = None,
        industry_allocation: Optional[Dict[str, float]] = None,
        asset_allocation:    Optional[Dict[str, float]] = None,
        strategy_allocation: Optional[Dict[str, float]] = None,
        regional_allocation: Optional[Dict[str, float]] = None,
        currency_allocation: Optional[Dict[str, float]] = None,
        exposure_metrics:    Optional[Dict[str, Any]] = None,
        # Statistics
        portfolio_statistics: Optional[Dict[str, Any]] = None,
        # Metadata overrides
        tags:         Optional[List[str]] = None,
        labels:       Optional[Dict[str, str]] = None,
        build_source: str = SNAPSHOT_SYSTEM_ID,
        description:  str = "",
        # Overrides for testing / replay
        snapshot_id:  Optional[str] = None,
    ) -> PortfolioSnapshot:
        """Build and return a new PortfolioSnapshot."""
        t_start = time.perf_counter()

        self._reject_missing_identifiers(portfolio_id, portfolio_session_id)
        self._reject_invalid_lifecycle_state(lifecycle_state, portfolio_id)
        self._reject_invalid_optimization_state(
            optimization_summary or {}, portfolio_id
        )

        # Assign a new snapshot_id and check for duplicates
        sid = snapshot_id or str(uuid.uuid4())
        self._reject_duplicate(sid)

        build_duration_ms = (time.perf_counter() - t_start) * 1000

        # Determine position count from current_holdings
        holdings_now    = tuple(current_holdings or [])
        holdings_target = tuple(target_holdings or [])
        position_count  = len(holdings_now)

        audit = SnapshotAuditMetadata.create(
            built_by          = ACTOR_BUILDER,
            build_duration_ms = build_duration_ms,
            build_context     = {
                "portfolio_id":    portfolio_id,
                "session_id":      portfolio_session_id,
                "lifecycle_state": lifecycle_state,
            },
        )

        metadata = PortfolioSnapshotMetadata.create(
            snapshot_id  = sid,
            portfolio_id = portfolio_id,
            tags         = tags,
            labels       = labels,
            build_source = build_source,
            description  = description,
        )

        snapshot = PortfolioSnapshot(
            snapshot_id          = sid,
            snapshot_version     = snapshot_version,
            portfolio_session_id = portfolio_session_id,
            portfolio_id         = portfolio_id,
            portfolio_version    = portfolio_version,
            portfolio_name       = portfolio_name,
            portfolio_type       = portfolio_type,
            portfolio_scope      = portfolio_scope,
            portfolio_objective  = portfolio_objective,
            portfolio_currency   = portfolio_currency,
            portfolio_status     = portfolio_status,
            lifecycle_state      = lifecycle_state,
            portfolio_health     = portfolio_health,
            snapshot_status      = snapshot_status,
            # summaries
            decision_summary        = dict(decision_summary or {}),
            allocation_summary      = dict(allocation_summary or {}),
            rebalancing_summary     = dict(rebalancing_summary or {}),
            exposure_summary        = dict(exposure_summary or {}),
            diversification_summary = dict(diversification_summary or {}),
            risk_summary            = dict(risk_summary or {}),
            liquidity_summary       = dict(liquidity_summary or {}),
            cash_summary            = dict(cash_summary or {}),
            constraint_summary      = dict(constraint_summary or {}),
            optimization_summary    = dict(optimization_summary or {}),
            # composition
            current_holdings    = holdings_now,
            target_holdings     = holdings_target,
            cash_balance        = cash_balance,
            reserved_capital    = reserved_capital,
            sector_allocation   = dict(sector_allocation or {}),
            industry_allocation = dict(industry_allocation or {}),
            asset_allocation    = dict(asset_allocation or {}),
            strategy_allocation = dict(strategy_allocation or {}),
            regional_allocation = dict(regional_allocation or {}),
            currency_allocation = dict(currency_allocation or {}),
            position_count      = position_count,
            exposure_metrics    = dict(exposure_metrics or {}),
            # stats & metadata
            portfolio_statistics = dict(portfolio_statistics or {}),
            portfolio_metadata   = metadata,
            audit_metadata       = audit,
            # framework
            framework_version    = VERSION,
            timestamp            = time.time(),
        )
        return snapshot

    # ------------------------------------------------------------------
    # Context-dict build
    # ------------------------------------------------------------------

    def build_from_context(self, context: Dict[str, Any]) -> PortfolioSnapshot:
        """
        Build a snapshot from a context dict produced by upstream engines.

        Expected context keys mirror the keyword arguments of ``build()``.
        Any key absent from the context falls back to its default.
        """
        if not isinstance(context, dict):
            raise SnapshotBuildError(
                "build_from_context requires a dict context", portfolio_id=""
            )
        portfolio_id         = context.get("portfolio_id", "")
        portfolio_session_id = context.get("portfolio_session_id", "")
        return self.build(
            portfolio_id             = portfolio_id,
            portfolio_session_id     = portfolio_session_id,
            portfolio_name           = context.get("portfolio_name", ""),
            portfolio_type           = context.get("portfolio_type", ""),
            portfolio_scope          = context.get("portfolio_scope", ""),
            portfolio_objective      = context.get("portfolio_objective", ""),
            portfolio_currency       = context.get("portfolio_currency", "INR"),
            portfolio_status         = context.get("portfolio_status", "active"),
            portfolio_version        = context.get("portfolio_version", 1),
            snapshot_version         = context.get("snapshot_version", 1),
            lifecycle_state          = context.get("lifecycle_state", "running"),
            portfolio_health         = context.get("portfolio_health", PortfolioHealth.HEALTHY.value),
            snapshot_status          = context.get("snapshot_status", SnapshotStatus.DRAFT.value),
            decision_summary         = context.get("decision_summary"),
            allocation_summary       = context.get("allocation_summary"),
            rebalancing_summary      = context.get("rebalancing_summary"),
            exposure_summary         = context.get("exposure_summary"),
            diversification_summary  = context.get("diversification_summary"),
            risk_summary             = context.get("risk_summary"),
            liquidity_summary        = context.get("liquidity_summary"),
            cash_summary             = context.get("cash_summary"),
            constraint_summary       = context.get("constraint_summary"),
            optimization_summary     = context.get("optimization_summary"),
            current_holdings         = context.get("current_holdings"),
            target_holdings          = context.get("target_holdings"),
            cash_balance             = context.get("cash_balance", 0.0),
            reserved_capital         = context.get("reserved_capital", 0.0),
            sector_allocation        = context.get("sector_allocation"),
            industry_allocation      = context.get("industry_allocation"),
            asset_allocation         = context.get("asset_allocation"),
            strategy_allocation      = context.get("strategy_allocation"),
            regional_allocation      = context.get("regional_allocation"),
            currency_allocation      = context.get("currency_allocation"),
            exposure_metrics         = context.get("exposure_metrics"),
            portfolio_statistics     = context.get("portfolio_statistics"),
            tags                     = context.get("tags"),
            labels                   = context.get("labels"),
            description              = context.get("description", ""),
            snapshot_id              = context.get("snapshot_id"),
        )

    # ------------------------------------------------------------------
    # Instance state reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear the seen-IDs set (useful for testing)."""
        with self._lock:
            self._seen.clear()

    # ------------------------------------------------------------------
    # Private validators
    # ------------------------------------------------------------------

    def _reject_missing_identifiers(
        self, portfolio_id: str, portfolio_session_id: str
    ) -> None:
        if not portfolio_id:
            raise SnapshotBuildError(
                "portfolio_id is required and must not be empty",
                portfolio_id="",
            )
        if not portfolio_session_id:
            raise SnapshotBuildError(
                "portfolio_session_id is required and must not be empty",
                portfolio_id=portfolio_id,
            )

    def _reject_invalid_lifecycle_state(
        self, lifecycle_state: str, portfolio_id: str
    ) -> None:
        if not lifecycle_state:
            raise SnapshotBuildError(
                "lifecycle_state must not be empty",
                portfolio_id=portfolio_id,
            )
        if lifecycle_state.lower() not in self._VALID_LIFECYCLE_STATES:
            raise SnapshotBuildError(
                f"Invalid lifecycle_state: {lifecycle_state!r}.  "
                f"Recognised values: {sorted(self._VALID_LIFECYCLE_STATES)}",
                portfolio_id=portfolio_id,
            )

    def _reject_invalid_optimization_state(
        self, optimization_summary: Dict[str, Any], portfolio_id: str
    ) -> None:
        status = optimization_summary.get("status")
        if status is not None and not isinstance(status, str):
            raise SnapshotBuildError(
                f"optimization_summary[status] must be a string, got {type(status).__name__}",
                portfolio_id=portfolio_id,
            )

    def _reject_duplicate(self, snapshot_id: str) -> None:
        with self._lock:
            if snapshot_id in self._seen:
                raise SnapshotDuplicateError(snapshot_id)
            self._seen.add(snapshot_id)
