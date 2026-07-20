"""
analytics_integration_response.py — iios.execution.analytics.integration
=========================================================================
Immutable value object returned to callers after a completed analytics
integration workflow invocation.

The :class:`AnalyticsIntegrationResponse` is the outward-facing result
of :meth:`ExecutionAnalyticsIntegration.submit`.  Its ``snapshot`` field
carries the published :class:`~iios.execution.analytics.snapshot.ExecutionAnalyticsSnapshot`
which is the ONLY representation of analytics results exposed to callers.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.execution.analytics.snapshot import ExecutionAnalyticsSnapshot

from .constants import INTEGRATION_VERSION, IntegrationResponseStatus


@dataclass(frozen=True)
class AnalyticsIntegrationResponse:
    """
    Immutable result of one :meth:`ExecutionAnalyticsIntegration.submit` call.

    Callers should inspect:

    * ``status`` — overall outcome (SUCCESS / PARTIAL / FAILED / REJECTED).
    * ``snapshot`` — the published :class:`ExecutionAnalyticsSnapshot` or
      ``None`` if snapshot creation failed.
    * ``error_message`` — human-readable diagnosis on non-SUCCESS status.
    * ``processing_ms`` — total integration latency in milliseconds.

    Fields
    ------
    response_id :           Unique identifier for this response.
    request_id :            Foreign key to the originating request.
    analytics_session_id :  M1 analytics session that was coordinated.
    execution_session_id :  Execution session that was analysed.
    snapshot :              Published :class:`ExecutionAnalyticsSnapshot`,
                            or ``None`` when snapshot creation was skipped
                            or failed.
    status :                Overall outcome of the analytics workflow.
    error_message :         Non-empty only on FAILED or REJECTED status.
    processing_ms :         End-to-end latency of the integration workflow.
    metadata :              Supplementary response metadata.
    responded_at :          Unix timestamp of response creation.
    framework_version :     Framework version string.
    """

    # --- identity ---
    response_id:          str
    request_id:           str
    analytics_session_id: str
    execution_session_id: str

    # --- payload ---
    snapshot: Optional[ExecutionAnalyticsSnapshot]

    # --- outcome ---
    status:        IntegrationResponseStatus
    error_message: str = ""

    # --- timing ---
    processing_ms: float = 0.0
    responded_at:  float = field(default_factory=time.time)

    # --- metadata ---
    metadata: Dict[str, Any] = field(default_factory=dict)

    # --- version ---
    framework_version: str = INTEGRATION_VERSION

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def is_success(self) -> bool:
        """``True`` for SUCCESS or PARTIAL outcomes."""
        return self.status in (
            IntegrationResponseStatus.SUCCESS,
            IntegrationResponseStatus.PARTIAL,
        )

    @property
    def has_snapshot(self) -> bool:
        """``True`` when a published snapshot is attached."""
        return self.snapshot is not None

    @property
    def has_performance(self) -> bool:
        """``True`` when the snapshot carries performance data."""
        return self.snapshot is not None and self.snapshot.has_performance

    @property
    def has_predictions(self) -> bool:
        """``True`` when the snapshot carries prediction data."""
        return self.snapshot is not None and self.snapshot.has_predictions

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def success(
        cls,
        *,
        request_id: str,
        analytics_session_id: str,
        execution_session_id: str,
        snapshot: Optional[ExecutionAnalyticsSnapshot],
        processing_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AnalyticsIntegrationResponse":
        """Build a SUCCESS response (or PARTIAL if snapshot is None)."""
        status = (
            IntegrationResponseStatus.SUCCESS
            if snapshot is not None
            else IntegrationResponseStatus.PARTIAL
        )
        return cls(
            response_id          = str(uuid.uuid4()),
            request_id           = request_id,
            analytics_session_id = analytics_session_id,
            execution_session_id = execution_session_id,
            snapshot             = snapshot,
            status               = status,
            processing_ms        = processing_ms,
            metadata             = metadata or {},
        )

    @classmethod
    def failed(
        cls,
        *,
        request_id: str,
        analytics_session_id: str,
        execution_session_id: str,
        error_message: str,
        processing_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AnalyticsIntegrationResponse":
        """Build a FAILED response."""
        return cls(
            response_id          = str(uuid.uuid4()),
            request_id           = request_id,
            analytics_session_id = analytics_session_id,
            execution_session_id = execution_session_id,
            snapshot             = None,
            status               = IntegrationResponseStatus.FAILED,
            error_message        = error_message,
            processing_ms        = processing_ms,
            metadata             = metadata or {},
        )

    @classmethod
    def rejected(
        cls,
        *,
        request_id: str,
        execution_session_id: str,
        reason: str,
    ) -> "AnalyticsIntegrationResponse":
        """Build a REJECTED response (request-level rejection, no workflow)."""
        return cls(
            response_id          = str(uuid.uuid4()),
            request_id           = request_id,
            analytics_session_id = "",
            execution_session_id = execution_session_id,
            snapshot             = None,
            status               = IntegrationResponseStatus.REJECTED,
            error_message        = reason,
        )

    def __repr__(self) -> str:
        return (
            f"AnalyticsIntegrationResponse("
            f"response_id={self.response_id!r}, "
            f"request_id={self.request_id!r}, "
            f"status={self.status.value!r}, "
            f"processing_ms={self.processing_ms:.1f})"
        )
