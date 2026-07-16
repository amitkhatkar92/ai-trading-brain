"""iios/execution/positions/snapshot/position_snapshot_store.py
==================================================
PositionSnapshotStore — primary facade for the Position Snapshot module.

The store is the single entry point for all snapshot operations:
  * Build → Validate → Publish → Archive lifecycle
  * Query by ID, position, portfolio, strategy, workflow, instrument, timestamp
  * Bundle production for batch consumers
  * Statistics, event history, cache management

PositionSnapshot is the ONLY object published outside
the Position Management subsystem.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import copy
import threading
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.lifecycle import Position

from .constants import (
    ACTOR_STORE,
    DEFAULT_MAX_CACHE_ENTRIES,
    DEFAULT_MAX_EVENT_HISTORY,
    DEFAULT_MAX_STORE_POSITIONS,
    STORE_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    PositionSnapshotNotRunningError,
    SnapshotNotFoundError,
    SnapshotStoreError,
)
from .position_snapshot import PositionSnapshot
from .position_snapshot_builder import PositionSnapshotBuilder
from .position_snapshot_bundle import SnapshotBundle, make_snapshot_bundle
from .position_snapshot_cache import PositionSnapshotCache
from .position_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived_event,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
)
from .position_snapshot_history import SnapshotEventHistory
from .position_snapshot_registry import PositionSnapshotRegistry
from .position_snapshot_statistics import SnapshotStatistics
from .position_snapshot_validation import SnapshotValidationResult, SnapshotValidator

if TYPE_CHECKING:
    from iios.execution.positions.risk.position_risk_state import PositionRiskState

_log   = get_logger(__name__, engine_id=STORE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=STORE_SYSTEM_ID)


class PositionSnapshotStore(LifecycleAwareMixin):
    """
    Primary facade for the IIOS Position Snapshot subsystem.

    Responsibilities
    ----------------
    * Build snapshots from validated Position + optional risk data.
    * Validate, publish, and archive snapshots.
    * Store all versions for historical retrieval.
    * Provide indexed query access across 6 dimensions.
    * Cache the latest snapshot per position for fast access.
    * Emit domain events and maintain bounded event history.
    * Track operational statistics.

    Non-responsibilities
    --------------------
    * No broker connectivity.
    * No position state-machine.
    * No risk evaluation.
    * No portfolio-level calculations.
    """

    def __init__(
        self,
        max_positions: int = DEFAULT_MAX_STORE_POSITIONS,
        max_cache:     int = DEFAULT_MAX_CACHE_ENTRIES,
        max_history:   int = DEFAULT_MAX_EVENT_HISTORY,
    ) -> None:
        super().__init__()
        self._registry   = PositionSnapshotRegistry(max_positions=max_positions)
        self._cache      = PositionSnapshotCache(max_entries=max_cache)
        self._builder    = PositionSnapshotBuilder()
        self._validator  = SnapshotValidator()
        self._statistics = SnapshotStatistics()
        self._history    = SnapshotEventHistory(max_events=max_history)
        self._lock       = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        self._cache.start()
        _audit.log_lifecycle_event(
            STORE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("PositionSnapshotStore started.")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            STORE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "PositionSnapshotStore stopped.",
            stored_positions=self._registry.count(),
            snapshots_created=self._statistics.snapshots_created,
        )
        self._cache.stop()
        self._registry.stop()

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionSnapshotNotRunningError()

    # ── Build & store ─────────────────────────────────────────────────────────

    def build_and_store(
        self,
        position:      Position,
        *,
        risk_state:    Optional["PositionRiskState"] = None,
        current_price: Optional[Decimal]             = None,
        order_id:      str                           = "",
        auto_publish:  bool                          = False,
    ) -> PositionSnapshot:
        """
        Build a snapshot from *position*, validate it, store it, and
        optionally publish it in a single call.

        Parameters
        ----------
        position
            Source position (must be valid).
        risk_state
            Optional risk state; risk fields default to "0" if absent.
        current_price
            Current market price for market_value computation.
        order_id
            Optional external order identifier.
        auto_publish
            If ``True``, also publish the snapshot before returning it.

        Returns
        -------
        The stored (and optionally published) ``PositionSnapshot``.

        Raises
        ------
        PositionSnapshotNotRunningError
        SnapshotBuildError
        """
        self._assert_running()
        t0 = time.perf_counter()

        # Determine next version number for this position
        existing = self._registry.get_all_versions(position.position_id)
        next_version = len(existing) + 1

        snapshot = self._builder.build(
            position,
            risk_state=risk_state,
            current_price=current_price,
            order_id=order_id,
            snapshot_version=next_version,
        )

        # Validate
        val_result = self._validator.validate(snapshot)
        if val_result.is_valid:
            snapshot = snapshot.as_valid()
        else:
            snapshot = snapshot.as_invalid()

        # Store
        self._registry.store(snapshot)
        self._cache.put(snapshot.position_id, snapshot)

        # Events + statistics
        build_ms = (time.perf_counter() - t0) * 1_000
        with self._lock:
            self._statistics.record_created(build_ms)
            if val_result.is_valid:
                self._statistics.record_validation_success()
            else:
                self._statistics.record_validation_failure()
            self._statistics.record_cached()

        evt = make_snapshot_created_event(
            snapshot.snapshot_id,
            snapshot.snapshot_version,
            snapshot.position_id,
            portfolio_id=snapshot.portfolio_id,
            strategy_id=snapshot.strategy_id,
            instrument=snapshot.instrument,
            emitted_by=ACTOR_STORE,
        )
        self._history.append(evt)

        _log.info(
            "Snapshot created.",
            position_id=snapshot.position_id,
            snapshot_id=snapshot.snapshot_id[:8],
            version=snapshot.snapshot_version,
            valid=val_result.is_valid,
        )

        if auto_publish and val_result.is_valid:
            snapshot = self.publish(snapshot.snapshot_id)

        return snapshot

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def validate_snapshot(self, snapshot_id: str) -> SnapshotValidationResult:
        """
        Re-validate a stored snapshot and update its status.

        Raises
        ------
        PositionSnapshotNotRunningError
        SnapshotNotFoundError
        """
        self._assert_running()
        snap = self._registry.require_by_snapshot_id(snapshot_id)
        result = self._validator.validate(snap)

        if result.is_valid:
            new_snap = snap.as_valid()
            self._statistics.record_validation_success()
        else:
            new_snap = snap.as_invalid()
            self._statistics.record_validation_failure()

        try:
            self._registry.update(new_snap)
            self._cache.put(new_snap.position_id, new_snap)
        except Exception:
            pass  # update is best-effort; original snap still in store

        evt = make_snapshot_validated_event(
            new_snap.snapshot_id,
            new_snap.snapshot_version,
            new_snap.position_id,
            validation_passed=result.is_valid,
            emitted_by=ACTOR_STORE,
        )
        self._history.append(evt)
        return result

    def publish(self, snapshot_id: str) -> PositionSnapshot:
        """
        Transition a VALID snapshot to PUBLISHED status.

        Raises
        ------
        PositionSnapshotNotRunningError
        SnapshotNotFoundError
        SnapshotStoreError   — snapshot is not in a publishable status
        """
        self._assert_running()
        snap = self._registry.require_by_snapshot_id(snapshot_id)
        if not snap.is_publishable:
            raise SnapshotStoreError(
                f"Snapshot {snapshot_id!r} cannot be published from "
                f"status '{snap.snapshot_status}'"
            )
        published = snap.as_published()
        try:
            self._registry.update(published)
        except Exception:
            pass
        self._cache.put(published.position_id, published)

        with self._lock:
            self._statistics.record_published()

        evt = make_snapshot_published_event(
            published.snapshot_id,
            published.snapshot_version,
            published.position_id,
            portfolio_id=published.portfolio_id,
            strategy_id=published.strategy_id,
            instrument=published.instrument,
            emitted_by=ACTOR_STORE,
        )
        self._history.append(evt)
        _log.info(
            "Snapshot published.",
            snapshot_id=snapshot_id[:8],
            position_id=published.position_id,
        )
        return published

    def archive(self, snapshot_id: str) -> PositionSnapshot:
        """
        Transition a snapshot to ARCHIVED status.

        Raises
        ------
        PositionSnapshotNotRunningError
        SnapshotNotFoundError
        """
        self._assert_running()
        snap     = self._registry.require_by_snapshot_id(snapshot_id)
        archived = snap.as_archived()
        try:
            self._registry.update(archived)
        except Exception:
            pass
        self._cache.invalidate(archived.position_id)

        with self._lock:
            self._statistics.record_archived()

        evt = make_snapshot_archived_event(
            archived.snapshot_id,
            archived.snapshot_version,
            archived.position_id,
            emitted_by=ACTOR_STORE,
        )
        self._history.append(evt)
        return archived

    # ── Query: by snapshot ID ─────────────────────────────────────────────────

    def get_by_snapshot_id(self, snapshot_id: str) -> Optional[PositionSnapshot]:
        snap = self._registry.get_by_snapshot_id(snapshot_id)
        if snap is not None:
            with self._lock:
                self._statistics.record_retrieved()
        return snap

    def require_by_snapshot_id(self, snapshot_id: str) -> PositionSnapshot:
        snap = self._registry.require_by_snapshot_id(snapshot_id)
        with self._lock:
            self._statistics.record_retrieved()
        return snap

    # ── Query: by position ────────────────────────────────────────────────────

    def get_latest(self, position_id: str) -> Optional[PositionSnapshot]:
        """Return the most recently stored snapshot, or ``None``."""
        # Try cache first
        snap = self._cache.get(position_id)
        if snap is not None:
            with self._lock:
                self._statistics.record_retrieved()
            return snap
        # Fall back to registry
        snap = self._registry.get_latest(position_id)
        if snap is not None:
            with self._lock:
                self._statistics.record_retrieved()
        return snap

    def require_latest(self, position_id: str) -> PositionSnapshot:
        snap = self.get_latest(position_id)
        if snap is None:
            raise SnapshotNotFoundError(position_id)
        return snap

    def get_all_versions(self, position_id: str) -> List[PositionSnapshot]:
        """Return all snapshot versions for *position_id*, oldest first."""
        return self._registry.get_all_versions(position_id)

    def get_version(self, position_id: str, version: int) -> Optional[PositionSnapshot]:
        return self._registry.get_version(position_id, version)

    def all_latest_snapshots(self) -> List[PositionSnapshot]:
        """Return the latest snapshot for every tracked position."""
        return self._registry.all_latest_snapshots()

    # ── Query: by secondary index ─────────────────────────────────────────────

    def get_by_portfolio(self, portfolio_id: str) -> List[PositionSnapshot]:
        return self._registry.get_by_portfolio(portfolio_id)

    def get_by_strategy(self, strategy_id: str) -> List[PositionSnapshot]:
        return self._registry.get_by_strategy(strategy_id)

    def get_by_workflow(self, workflow_id: str) -> List[PositionSnapshot]:
        return self._registry.get_by_workflow(workflow_id)

    def get_by_instrument(self, instrument: str) -> List[PositionSnapshot]:
        return self._registry.get_by_instrument(instrument)

    def get_by_timestamp_range(self, start: float, end: float) -> List[PositionSnapshot]:
        return self._registry.get_by_timestamp_range(start, end)

    # ── Bundle production ─────────────────────────────────────────────────────

    def bundle_portfolio(
        self,
        portfolio_id: str,
        *,
        label: str = "",
    ) -> SnapshotBundle:
        snaps = self.get_by_portfolio(portfolio_id)
        return make_snapshot_bundle(
            snaps,
            label=label or f"portfolio:{portfolio_id}",
        )

    def bundle_strategy(
        self,
        strategy_id: str,
        *,
        label: str = "",
    ) -> SnapshotBundle:
        snaps = self.get_by_strategy(strategy_id)
        return make_snapshot_bundle(
            snaps,
            label=label or f"strategy:{strategy_id}",
        )

    def bundle_all(self, *, label: str = "all") -> SnapshotBundle:
        return make_snapshot_bundle(self.all_latest_snapshots(), label=label)

    # ── Removal ───────────────────────────────────────────────────────────────

    def remove(self, position_id: str) -> List[PositionSnapshot]:
        """
        Remove all snapshot versions for *position_id*.

        Raises
        ------
        PositionSnapshotNotRunningError
        SnapshotNotFoundError
        """
        self._assert_running()
        removed = self._registry.remove(position_id)
        self._cache.invalidate(position_id)
        return removed

    # ── State checks ──────────────────────────────────────────────────────────

    def contains(self, position_id: str) -> bool:
        return self._registry.contains(position_id)

    def count(self) -> int:
        return self._registry.count()

    def is_empty(self) -> bool:
        return self._registry.is_empty()

    # ── Statistics & history ──────────────────────────────────────────────────

    def statistics(self) -> SnapshotStatistics:
        with self._lock:
            return copy.copy(self._statistics)

    def event_history(self) -> SnapshotEventHistory:
        return self._history

    def events(self) -> List[SnapshotEvent]:
        return self._history.all()

    def cache(self) -> PositionSnapshotCache:
        """Direct access to the underlying cache (read-only queries)."""
        return self._cache
