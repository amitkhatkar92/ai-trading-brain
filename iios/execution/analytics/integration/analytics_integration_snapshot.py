"""
analytics_integration_snapshot.py — iios.execution.analytics.integration
=========================================================================
Integration-layer record that wraps a published
:class:`~iios.execution.analytics.snapshot.ExecutionAnalyticsSnapshot`
with integration metadata.

The :class:`IntegrationSnapshotRecord` is the object stored in integration
history and the integration snapshot registry.  The underlying
:class:`ExecutionAnalyticsSnapshot` (M5) is the canonical analytics object
exposed to callers via :class:`AnalyticsIntegrationResponse`.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.execution.analytics.snapshot import ExecutionAnalyticsSnapshot

from .constants import INTEGRATION_VERSION


@dataclass(frozen=True)
class IntegrationSnapshotRecord:
    """
    Lightweight integration-layer wrapper around a published
    :class:`ExecutionAnalyticsSnapshot`.

    This object is used internally to track which snapshots were created by
    the integration subsystem, for which request, and when.  Callers receive
    the inner :attr:`snapshot` directly via
    :class:`AnalyticsIntegrationResponse`.

    Fields
    ------
    record_id :             Unique identifier for this record.
    request_id :            Request that triggered snapshot creation.
    analytics_session_id :  M1 analytics session identifier.
    execution_session_id :  Execution session that was analysed.
    snapshot :              The published :class:`ExecutionAnalyticsSnapshot`.
    published_by :          Identifier of the actor that published the snapshot.
    published_at :          Unix timestamp of publication.
    metadata :              Supplementary record metadata.
    framework_version :     Framework version string.
    """

    record_id:            str
    request_id:           str
    analytics_session_id: str
    execution_session_id: str
    snapshot:             ExecutionAnalyticsSnapshot
    published_by:         str  = "integration_manager"
    published_at:         float = field(default_factory=time.time)
    metadata:             Dict[str, Any] = field(default_factory=dict)
    framework_version:    str = INTEGRATION_VERSION

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def snapshot_id(self) -> str:
        """Short-cut to the inner snapshot identifier."""
        return self.snapshot.snapshot_id

    @property
    def has_performance(self) -> bool:
        """``True`` when the snapshot carries performance data."""
        return self.snapshot.has_performance

    @property
    def has_predictions(self) -> bool:
        """``True`` when the snapshot carries prediction data."""
        return self.snapshot.has_predictions

    @property
    def has_risk(self) -> bool:
        """``True`` when the snapshot carries risk forecast data."""
        return self.snapshot.has_risk

    @property
    def has_capacity(self) -> bool:
        """``True`` when the snapshot carries capacity forecast data."""
        return self.snapshot.has_capacity

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        analytics_session_id: str,
        execution_session_id: str,
        snapshot: ExecutionAnalyticsSnapshot,
        published_by: str = "integration_manager",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "IntegrationSnapshotRecord":
        """
        Create a new :class:`IntegrationSnapshotRecord` wrapping *snapshot*.

        Parameters
        ----------
        request_id :            Originating integration request identifier.
        analytics_session_id :  M1 analytics session identifier.
        execution_session_id :  Execution session being analysed.
        snapshot :              The published :class:`ExecutionAnalyticsSnapshot`.
        published_by :          Caller/actor identifier.
        metadata :              Optional supplementary metadata.
        """
        return cls(
            record_id            = str(uuid.uuid4()),
            request_id           = request_id,
            analytics_session_id = analytics_session_id,
            execution_session_id = execution_session_id,
            snapshot             = snapshot,
            published_by         = published_by,
            metadata             = metadata or {},
        )

    def __repr__(self) -> str:
        return (
            f"IntegrationSnapshotRecord("
            f"record_id={self.record_id!r}, "
            f"request_id={self.request_id!r}, "
            f"snapshot_id={self.snapshot_id!r})"
        )
