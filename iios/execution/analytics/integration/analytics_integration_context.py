"""
analytics_integration_context.py — iios.execution.analytics.integration
=========================================================================
Immutable context object that carries execution state for one analytics
integration workflow invocation.

The context is created by the integration manager after an M1 session has
been established and is threaded through each subsequent pipeline step.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from iios.execution.analytics.lifecycle import AnalyticsMode, AnalyticsScope

from .constants import INTEGRATION_VERSION
from .analytics_integration_request import AnalyticsIntegrationRequest


@dataclass(frozen=True)
class AnalyticsIntegrationContext:
    """
    Immutable execution context for a single analytics integration workflow.

    Created by :class:`AnalyticsIntegrationManager` after the M1 analytics
    session has been successfully established.  All downstream pipeline
    stages (M2-M5) receive the same context instance.

    Fields
    ------
    context_id :            Unique identifier for this context object.
    request_id :            Foreign key to the originating
                            :class:`AnalyticsIntegrationRequest`.
    analytics_session_id :  M1 analytics session identifier; set after
                            :meth:`AnalyticsLifecycle.create` succeeds.
    execution_session_id :  Propagated from the originating request.
    analytics_scope :       Propagated from the originating request.
    analytics_mode :        Propagated from the originating request.
    workflow_id :           Propagated from the originating request.
    portfolio_id :          Propagated from the originating request.
    strategy_id :           Propagated from the originating request.
    context_metadata :      Free-form supplementary data attached during
                            context construction.
    created_at :            Unix timestamp of context creation.
    framework_version :     Framework version string.
    """

    # --- identity ---
    context_id:           str
    request_id:           str
    analytics_session_id: str
    execution_session_id: str

    # --- scope ---
    analytics_scope: AnalyticsScope
    analytics_mode:  AnalyticsMode

    # --- session routing ---
    workflow_id:  str = ""
    portfolio_id: str = ""
    strategy_id:  str = ""

    # --- metadata ---
    context_metadata: Dict[str, Any] = field(default_factory=dict)

    # --- timing ---
    created_at: float = field(default_factory=time.time)

    # --- version ---
    framework_version: str = INTEGRATION_VERSION

    # ------------------------------------------------------------------
    # Factory helper
    # ------------------------------------------------------------------
    @classmethod
    def from_request(
        cls,
        request: AnalyticsIntegrationRequest,
        analytics_session_id: str,
        *,
        extra_metadata: Dict[str, Any] | None = None,
    ) -> "AnalyticsIntegrationContext":
        """
        Build a context object from a request and the newly created M1
        analytics session identifier.

        Parameters
        ----------
        request :               The originating integration request.
        analytics_session_id :  Identifier returned by M1 ``create()``.
        extra_metadata :        Optional additional context metadata merged
                                with ``request.metadata``.
        """
        merged: Dict[str, Any] = dict(request.metadata)
        if extra_metadata:
            merged.update(extra_metadata)

        return cls(
            context_id           = str(uuid.uuid4()),
            request_id           = request.request_id,
            analytics_session_id = analytics_session_id,
            execution_session_id = request.execution_session_id,
            analytics_scope      = request.analytics_scope,
            analytics_mode       = request.analytics_mode,
            workflow_id          = request.workflow_id,
            portfolio_id         = request.portfolio_id,
            strategy_id          = request.strategy_id,
            context_metadata     = merged,
        )

    def __repr__(self) -> str:
        return (
            f"AnalyticsIntegrationContext("
            f"context_id={self.context_id!r}, "
            f"request_id={self.request_id!r}, "
            f"analytics_session_id={self.analytics_session_id!r})"
        )
