"""
analytics_integration_request.py — iios.execution.analytics.integration
=========================================================================
Immutable value object representing a caller's request for execution
analytics via the integration subsystem.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from iios.execution.analytics.lifecycle import AnalyticsMode, AnalyticsScope

from .constants import (
    ACTOR_SYSTEM,
    DEFAULT_PRIORITY,
    INTEGRATION_VERSION,
)


@dataclass(frozen=True)
class AnalyticsIntegrationRequest:
    """
    Immutable analytics integration request.

    Carries all parameters needed by the integration manager to coordinate
    the M1-M5 analytics pipeline for one execution session.

    Mandatory parameter
    -------------------
    execution_session_id : str
        Identifier of the execution session being analysed.

    Optional parameters
    -------------------
    request_id :           auto-generated UUID if omitted
    analytics_scope :      defaults to ``AnalyticsScope.EXECUTION``
    analytics_mode :       defaults to ``AnalyticsMode.ON_DEMAND``
    workflow_id :          forwarded to M1 session; empty string is valid
    portfolio_id :         forwarded to M1 session; empty string is valid
    strategy_id :          forwarded to M1 session; empty string is valid
    include_performance :  run M3 performance analytics (default True)
    include_predictions :  run M4 predictive intelligence (default True)
    include_snapshot :     build and publish M5 snapshot (default True)
    priority :             scheduling priority 1-10 (default 5)
    requester :            caller identifier for audit purposes
    reason :               human-readable purpose description
    tags :                 immutable tag tuple for downstream filtering
    metadata :             supplementary data for the integration context
    created_at :           creation timestamp (auto-generated if omitted)
    """

    # --- required ---
    execution_session_id: str

    # --- routing ---
    request_id:      str           = field(default_factory=lambda: str(uuid.uuid4()))
    analytics_scope: AnalyticsScope = AnalyticsScope.EXECUTION
    analytics_mode:  AnalyticsMode  = AnalyticsMode.ON_DEMAND
    workflow_id:     str           = ""
    portfolio_id:    str           = ""
    strategy_id:     str           = ""

    # --- feature flags ---
    include_performance: bool = True
    include_predictions: bool = True
    include_snapshot:    bool = True

    # --- scheduling ---
    priority: int = DEFAULT_PRIORITY

    # --- audit ---
    requester: str = ACTOR_SYSTEM
    reason:    str = ""

    # --- tagging / metadata ---
    tags:     Tuple[str, ...]   = field(default_factory=tuple)
    metadata: Dict[str, Any]    = field(default_factory=dict)

    # --- timing ---
    created_at: float = field(default_factory=time.time)

    # --- version ---
    framework_version: str = INTEGRATION_VERSION

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        """
        Return ``True`` if the request is structurally sound.

        Checks that the mandatory ``execution_session_id`` is a non-empty
        string and that ``priority`` is in the 1–10 range.
        """
        if not isinstance(self.execution_session_id, str):
            return False
        if not self.execution_session_id.strip():
            return False
        if not (1 <= self.priority <= 10):
            return False
        return True

    @property
    def has_session_context(self) -> bool:
        """``True`` when at least one of workflow/portfolio/strategy is set."""
        return bool(self.workflow_id or self.portfolio_id or self.strategy_id)

    def __repr__(self) -> str:
        return (
            f"AnalyticsIntegrationRequest("
            f"request_id={self.request_id!r}, "
            f"execution_session_id={self.execution_session_id!r}, "
            f"scope={self.analytics_scope.value!r})"
        )
