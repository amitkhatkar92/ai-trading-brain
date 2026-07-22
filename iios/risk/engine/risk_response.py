"""
risk_response.py — iios.risk.engine
======================================
Risk workflow response and snapshot value objects.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    EngineState,
    RiskWorkflowType,
    ResponseStatus,
)


# ---------------------------------------------------------------------------
# RiskEngineSnapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskEngineSnapshot:
    """
    Immutable point-in-time snapshot of a risk workflow output.

    Published at the end of every successful risk pipeline.

    Fields
    ------
    snapshot_id :       Unique identifier.
    risk_id :           Risk assessment identifier.
    portfolio_id :      Portfolio identifier.
    session_id :        Owning lifecycle session.
    workflow_type :     Workflow that produced this snapshot.
    engine_state :      Engine state at publication time.
    inputs_summary :    Keys of inputs collected (not raw data).
    outputs :           Produced risk assessment outputs.
    published_at :      Wall-clock publication time.
    framework_version : Framework version string.
    """
    snapshot_id:       str
    risk_id:           str
    portfolio_id:      str
    session_id:        str
    workflow_type:     RiskWorkflowType
    engine_state:      EngineState
    inputs_summary:    Dict[str, Any] = field(default_factory=dict)
    outputs:           Dict[str, Any] = field(default_factory=dict)
    published_at:      float          = field(default_factory=time.time)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        risk_id:       str,
        portfolio_id:  str,
        session_id:    str,
        workflow_type: RiskWorkflowType,
        engine_state:  EngineState,
        *,
        snapshot_id:    Optional[str]          = None,
        inputs_summary: Optional[Dict[str, Any]] = None,
        outputs:        Optional[Dict[str, Any]] = None,
    ) -> "RiskEngineSnapshot":
        return cls(
            snapshot_id    = snapshot_id or str(uuid.uuid4()),
            risk_id        = risk_id,
            portfolio_id   = portfolio_id,
            session_id     = session_id,
            workflow_type  = workflow_type,
            engine_state   = engine_state,
            inputs_summary = dict(inputs_summary or {}),
            outputs        = dict(outputs or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "risk_id":           self.risk_id,
            "portfolio_id":      self.portfolio_id,
            "session_id":        self.session_id,
            "workflow_type":     self.workflow_type.value,
            "engine_state":      self.engine_state.value,
            "inputs_summary":    dict(self.inputs_summary),
            "outputs":           dict(self.outputs),
            "published_at":      self.published_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# RiskResponse
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskResponse:
    """
    Immutable risk workflow response.

    Returned by every :class:`RiskEngine` operation.

    Fields
    ------
    response_id :       Unique identifier.
    request_id :        Originating request identifier.
    risk_id :           Risk assessment identifier.
    portfolio_id :      Portfolio identifier.
    workflow_type :     Workflow that was executed.
    status :            Outcome status (SUCCESS / FAILURE / PARTIAL).
    snapshot :          Published risk snapshot (None on failure).
    error_message :     Non-empty when status is FAILURE.
    elapsed_s :         Wall-clock processing duration in seconds.
    metadata :          Supplementary response metadata.
    created_at :        Wall-clock response creation time.
    framework_version : Framework version string.
    """
    response_id:       str
    request_id:        str
    risk_id:           str
    portfolio_id:      str
    workflow_type:     RiskWorkflowType
    status:            ResponseStatus
    snapshot:          Optional[RiskEngineSnapshot] = None
    error_message:     str                          = ""
    elapsed_s:         float                        = 0.0
    metadata:          Dict[str, Any]               = field(default_factory=dict)
    created_at:        float                        = field(default_factory=time.time)
    framework_version: str                          = VERSION

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == ResponseStatus.FAILURE

    @property
    def is_partial(self) -> bool:
        return self.status == ResponseStatus.PARTIAL

    @property
    def has_snapshot(self) -> bool:
        return self.snapshot is not None

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def create_success(
        cls,
        request_id:    str,
        risk_id:       str,
        portfolio_id:  str,
        workflow_type: RiskWorkflowType,
        *,
        response_id:  Optional[str]                  = None,
        snapshot:     Optional[RiskEngineSnapshot]   = None,
        elapsed_s:    float                          = 0.0,
        metadata:     Optional[Dict[str, Any]]       = None,
    ) -> "RiskResponse":
        return cls(
            response_id   = response_id or str(uuid.uuid4()),
            request_id    = request_id,
            risk_id       = risk_id,
            portfolio_id  = portfolio_id,
            workflow_type = workflow_type,
            status        = ResponseStatus.SUCCESS,
            snapshot      = snapshot,
            elapsed_s     = elapsed_s,
            metadata      = dict(metadata or {}),
        )

    @classmethod
    def create_failure(
        cls,
        request_id:    str,
        risk_id:       str,
        portfolio_id:  str,
        workflow_type: RiskWorkflowType,
        *,
        response_id:   Optional[str]            = None,
        error_message: str                      = "",
        elapsed_s:     float                    = 0.0,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "RiskResponse":
        return cls(
            response_id   = response_id or str(uuid.uuid4()),
            request_id    = request_id,
            risk_id       = risk_id,
            portfolio_id  = portfolio_id,
            workflow_type = workflow_type,
            status        = ResponseStatus.FAILURE,
            error_message = error_message,
            elapsed_s     = elapsed_s,
            metadata      = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":       self.response_id,
            "request_id":        self.request_id,
            "risk_id":           self.risk_id,
            "portfolio_id":      self.portfolio_id,
            "workflow_type":     self.workflow_type.value,
            "status":            self.status.value,
            "error_message":     self.error_message,
            "elapsed_s":         self.elapsed_s,
            "has_snapshot":      self.has_snapshot,
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }
