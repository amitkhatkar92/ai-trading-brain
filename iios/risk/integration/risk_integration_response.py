"""
risk_integration_response.py — iios.risk.integration
======================================================
Immutable risk integration response value object.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationStatus, RequestType, VERSION


@dataclass(frozen=True)
class RiskIntegrationResponse:
    """
    Immutable response returned by the Risk Integration layer.

    Contains the :class:`~iios.risk.snapshot.RiskSnapshot` published
    during the integration workflow, plus status, timing, and metadata.

    The ``risk_snapshot`` field holds the serialised snapshot dict; callers
    requiring the full object should retrieve it from the snapshot store via
    the snapshot_id.
    """
    response_id:        str
    request_id:         str
    portfolio_id:       str
    request_type:       RequestType
    status:             IntegrationStatus
    snapshot_id:        str
    risk_score:         float
    risk_level:         str
    risk_rating:        str
    duration_s:         float
    risk_snapshot:      Dict[str, Any]   # serialised RiskSnapshot.to_dict()
    error_message:      str
    validation_passed:  bool
    workflow_steps:     int
    framework_version:  str   = VERSION
    completed_at:       float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        request_id:   str,
        portfolio_id: str,
        request_type: RequestType,
        status:       IntegrationStatus,
        *,
        response_id:       Optional[str]         = None,
        snapshot_id:       str                   = "",
        risk_score:        float                 = 0.0,
        risk_level:        str                   = "unknown",
        risk_rating:       str                   = "unknown",
        duration_s:        float                 = 0.0,
        risk_snapshot:     Optional[Dict[str, Any]] = None,
        error_message:     str                   = "",
        validation_passed: bool                  = True,
        workflow_steps:    int                   = 0,
    ) -> "RiskIntegrationResponse":
        return cls(
            response_id        = response_id or str(uuid.uuid4()),
            request_id         = request_id,
            portfolio_id       = portfolio_id,
            request_type       = request_type,
            status             = status,
            snapshot_id        = snapshot_id,
            risk_score         = risk_score,
            risk_level         = risk_level,
            risk_rating        = risk_rating,
            duration_s         = duration_s,
            risk_snapshot      = dict(risk_snapshot or {}),
            error_message      = error_message,
            validation_passed  = validation_passed,
            workflow_steps     = workflow_steps,
        )

    @classmethod
    def success(
        cls,
        request_id:   str,
        portfolio_id: str,
        request_type: RequestType,
        snapshot_dict: Dict[str, Any],
        duration_s:    float,
        *,
        workflow_steps: int = 0,
    ) -> "RiskIntegrationResponse":
        """Create a successful response from a RiskSnapshot dict."""
        import uuid as _uuid
        snap_id = snapshot_dict.get("snapshot_id") or str(_uuid.uuid4())
        return cls.create(
            request_id     = request_id,
            portfolio_id   = portfolio_id,
            request_type   = request_type,
            status         = IntegrationStatus.COMPLETED,
            snapshot_id    = snap_id,
            risk_score     = snapshot_dict.get("summary", {}).get("overall_risk_score", 0.0),
            risk_level     = snapshot_dict.get("summary", {}).get("risk_level",  "unknown"),
            risk_rating    = snapshot_dict.get("summary", {}).get("risk_rating", "unknown"),
            duration_s     = duration_s,
            risk_snapshot  = snapshot_dict,
            validation_passed = True,
            workflow_steps    = workflow_steps,
        )

    @classmethod
    def failure(
        cls,
        request_id:    str,
        portfolio_id:  str,
        request_type:  RequestType,
        error_message: str,
        duration_s:    float,
    ) -> "RiskIntegrationResponse":
        """Create a failed response."""
        return cls.create(
            request_id    = request_id,
            portfolio_id  = portfolio_id,
            request_type  = request_type,
            status        = IntegrationStatus.FAILED,
            error_message = error_message,
            duration_s    = duration_s,
            validation_passed = False,
        )

    @property
    def is_success(self) -> bool:
        return self.status == IntegrationStatus.COMPLETED

    @property
    def has_snapshot(self) -> bool:
        return bool(self.snapshot_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":       self.response_id,
            "request_id":        self.request_id,
            "portfolio_id":      self.portfolio_id,
            "request_type":      self.request_type.value,
            "status":            self.status.value,
            "snapshot_id":       self.snapshot_id,
            "risk_score":        self.risk_score,
            "risk_level":        self.risk_level,
            "risk_rating":       self.risk_rating,
            "duration_s":        self.duration_s,
            "error_message":     self.error_message,
            "validation_passed": self.validation_passed,
            "workflow_steps":    self.workflow_steps,
            "framework_version": self.framework_version,
            "completed_at":      self.completed_at,
        }
