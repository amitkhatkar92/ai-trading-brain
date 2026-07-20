"""
decision_response.py — iios.decision.engine
=============================================
Immutable decision response and snapshot value objects.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    DecisionResponseStatus,
)


@dataclass(frozen=True)
class DecisionSnapshot:
    """
    Immutable snapshot of a completed decision workflow.

    Produced by the engine and included in :class:`DecisionResponse`.

    Fields
    ------
    snapshot_id :         Unique identifier for this snapshot.
    request_id :          Source request identifier.
    session_id :          Decision lifecycle session identifier.
    pipeline_id :         Processing pipeline identifier.
    decision_id :         Decision identifier.
    workflow_id :         Routing — workflow.
    portfolio_id :        Routing — portfolio.
    strategy_id :         Routing — strategy.
    collection_inputs :   Map of collected institutional inputs.
    dispatch_results :    Map of dispatch/evaluation results.
    pipeline_state :      Final pipeline state string.
    collection_time_s :   Wall-clock seconds spent in collection.
    dispatch_time_s :     Wall-clock seconds spent in dispatch/evaluation.
    total_time_s :        End-to-end wall-clock seconds.
    metadata :            Supplementary metadata.
    created_at :          Wall-clock snapshot creation time.
    framework_version :   Framework version.
    """
    snapshot_id:        str
    request_id:         str
    session_id:         str
    pipeline_id:        str
    decision_id:        str
    workflow_id:        str              = ""
    portfolio_id:       str              = ""
    strategy_id:        str              = ""
    collection_inputs:  Dict[str, Any]   = field(default_factory=dict)
    dispatch_results:   Dict[str, Any]   = field(default_factory=dict)
    pipeline_state:     str              = ""
    collection_time_s:  float            = 0.0
    dispatch_time_s:    float            = 0.0
    total_time_s:       float            = 0.0
    metadata:           Dict[str, Any]   = field(default_factory=dict)
    created_at:         float            = field(default_factory=time.time)
    framework_version:  str              = VERSION


@dataclass(frozen=True)
class DecisionResponse:
    """
    Immutable response returned by :meth:`DecisionEngine.submit`.

    Fields
    ------
    response_id :        Unique identifier for this response.
    request_id :         Source :class:`DecisionRequest` identifier.
    session_id :         Decision lifecycle session identifier.
    decision_id :        Decision identifier.
    status :             Outcome status.
    snapshot :           Decision snapshot (present on SUCCESS or PARTIAL).
    collection_time_s :  Seconds spent in collection.
    dispatch_time_s :    Seconds spent in dispatch / evaluation.
    total_time_s :       End-to-end seconds.
    error :              Error message when ``status`` is FAILED or TIMEOUT.
    metadata :           Supplementary metadata.
    responded_at :       Wall-clock time the response was produced.
    framework_version :  Framework version.
    """
    response_id:        str
    request_id:         str
    session_id:         str
    decision_id:        str
    status:             DecisionResponseStatus
    snapshot:           Optional[DecisionSnapshot]  = None
    collection_time_s:  float                       = 0.0
    dispatch_time_s:    float                       = 0.0
    total_time_s:       float                       = 0.0
    error:              str                         = ""
    metadata:           Dict[str, Any]              = field(default_factory=dict)
    responded_at:       float                       = field(default_factory=time.time)
    framework_version:  str                         = VERSION

    @property
    def is_success(self) -> bool:
        return self.status == DecisionResponseStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status in (
            DecisionResponseStatus.FAILED,
            DecisionResponseStatus.TIMEOUT,
        )

    @classmethod
    def success(
        cls,
        request_id:       str,
        session_id:       str,
        decision_id:      str,
        snapshot:         DecisionSnapshot,
        *,
        collection_time_s: float = 0.0,
        dispatch_time_s:   float = 0.0,
        total_time_s:      float = 0.0,
        metadata:         Optional[Dict[str, Any]] = None,
    ) -> "DecisionResponse":
        """Factory for a successful response."""
        return cls(
            response_id       = str(uuid.uuid4()),
            request_id        = request_id,
            session_id        = session_id,
            decision_id       = decision_id,
            status            = DecisionResponseStatus.SUCCESS,
            snapshot          = snapshot,
            collection_time_s = collection_time_s,
            dispatch_time_s   = dispatch_time_s,
            total_time_s      = total_time_s,
            metadata          = dict(metadata or {}),
        )

    @classmethod
    def failure(
        cls,
        request_id:  str,
        session_id:  str,
        decision_id: str,
        *,
        error:       str = "",
        total_time_s: float = 0.0,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "DecisionResponse":
        """Factory for a failed response."""
        return cls(
            response_id  = str(uuid.uuid4()),
            request_id   = request_id,
            session_id   = session_id,
            decision_id  = decision_id,
            status       = DecisionResponseStatus.FAILED,
            error        = error,
            total_time_s = total_time_s,
            metadata     = dict(metadata or {}),
        )
