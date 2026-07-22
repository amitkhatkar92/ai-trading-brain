"""
portfolio_integration_response.py — iios.portfolio.integration
===============================================================
PortfolioIntegrationResponse — the immutable result returned by
PortfolioIntegrationEngine.submit().

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    ResponseStatus,
    WorkflowStage,
)


@dataclass(frozen=True)
class PortfolioIntegrationResponse:
    """
    Immutable result of an integration workflow.

    Returned by :meth:`PortfolioIntegrationEngine.submit`.

    Fields
    ------
    response_id :       Unique response identifier.
    request_id :        Identifier of the originating request.
    portfolio_id :      Target portfolio identifier.
    service_type :      Service that was executed.
    status :            Success / Failure / Partial.
    workflow_stage :    Furthest stage reached by the workflow.
    snapshot :          Published PortfolioSnapshot (None on failure).
    result :            Service-specific result dict.
    error :             Error message (empty on success).
    started_at :        Wall-clock time the workflow started.
    completed_at :      Wall-clock time the workflow completed.
    duration_ms :       Wall-clock duration of the workflow.
    framework_version : Framework version string.
    """
    response_id:       str
    request_id:        str
    portfolio_id:      str
    service_type:      str   # IntegrationServiceType.value
    status:            str   # ResponseStatus.value
    workflow_stage:    str   # WorkflowStage.value
    snapshot:          object    # Optional[PortfolioSnapshot] — avoid circular import
    result:            Dict[str, Any]
    error:             str
    started_at:        float
    completed_at:      float
    duration_ms:       float
    framework_version: str

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS.value

    @property
    def is_failure(self) -> bool:
        return self.status == ResponseStatus.FAILURE.value

    @property
    def is_partial(self) -> bool:
        return self.status == ResponseStatus.PARTIAL.value

    @property
    def has_snapshot(self) -> bool:
        return self.snapshot is not None

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":      self.response_id,
            "request_id":       self.request_id,
            "portfolio_id":     self.portfolio_id,
            "service_type":     self.service_type,
            "status":           self.status,
            "workflow_stage":   self.workflow_stage,
            "snapshot":         self.snapshot.to_dict() if self.snapshot is not None else None,
            "result":           dict(self.result),
            "error":            self.error,
            "started_at":       self.started_at,
            "completed_at":     self.completed_at,
            "duration_ms":      self.duration_ms,
            "framework_version": self.framework_version,
        }

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        request_id:  str,
        portfolio_id: str,
        service_type: str,
        *,
        snapshot:    object = None,
        result:      Dict[str, Any] | None = None,
        workflow_stage: str = WorkflowStage.COMPLETED.value,
        started_at:  float = 0.0,
    ) -> "PortfolioIntegrationResponse":
        now = time.time()
        return cls(
            response_id       = str(uuid.uuid4()),
            request_id        = request_id,
            portfolio_id      = portfolio_id,
            service_type      = service_type,
            status            = ResponseStatus.SUCCESS.value,
            workflow_stage    = workflow_stage,
            snapshot          = snapshot,
            result            = dict(result or {}),
            error             = "",
            started_at        = started_at or now,
            completed_at      = now,
            duration_ms       = (now - (started_at or now)) * 1000,
            framework_version = VERSION,
        )

    @classmethod
    def failure(
        cls,
        request_id:  str,
        portfolio_id: str,
        service_type: str,
        error:       str,
        *,
        workflow_stage: str = WorkflowStage.FAILED.value,
        started_at:  float = 0.0,
        result:      Dict[str, Any] | None = None,
    ) -> "PortfolioIntegrationResponse":
        now = time.time()
        return cls(
            response_id       = str(uuid.uuid4()),
            request_id        = request_id,
            portfolio_id      = portfolio_id,
            service_type      = service_type,
            status            = ResponseStatus.FAILURE.value,
            workflow_stage    = workflow_stage,
            snapshot          = None,
            result            = dict(result or {}),
            error             = error,
            started_at        = started_at or now,
            completed_at      = now,
            duration_ms       = (now - (started_at or now)) * 1000,
            framework_version = VERSION,
        )
