"""
integration_gateway_context.py — iios.integration.gateway
-----------------------------------------------------------
IntegrationGatewayContext — mutable execution context threaded through
the gateway workflow for a single request.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    CONTEXT_ID_PREFIX,
    GatewayState,
    GatewayWorkflowStep,
)
from .integration_gateway_request import IntegrationGatewayRequest


class IntegrationGatewayContext:
    """
    Mutable context object that tracks gateway workflow execution state
    for a single request.

    Passed by reference through each coordinator step so that every
    stage can read results produced by prior stages and write its own
    outputs without requiring extra return values.
    """

    __slots__ = (
        "_context_id",
        "_request",
        "_gateway_id",
        "_gateway_state",
        "_lifecycle_session_id",
        "_engine_request_id",
        "_engine_response_id",
        "_governance_request_id",
        "_governance_decision",
        "_snapshot_id",
        "_current_step",
        "_errors",
        "_warnings",
        "_step_timings",
        "_created_at",
    )

    def __init__(
        self,
        request:      IntegrationGatewayRequest,
        gateway_id:   str,
        gateway_state: GatewayState = GatewayState.ACTIVE,
        *,
        context_id:   Optional[str] = None,
    ) -> None:
        self._context_id            = context_id or f"{CONTEXT_ID_PREFIX}{uuid.uuid4().hex[:12]}"
        self._request               = request
        self._gateway_id            = gateway_id
        self._gateway_state         = gateway_state
        self._lifecycle_session_id  = ""
        self._engine_request_id     = ""
        self._engine_response_id    = ""
        self._governance_request_id = ""
        self._governance_decision   = ""
        self._snapshot_id           = ""
        self._current_step          = GatewayWorkflowStep.REQUEST_RECEIVED
        self._errors:   List[str]           = []
        self._warnings: List[str]           = []
        self._step_timings: Dict[str, float] = {}
        self._created_at = time.monotonic()

    # ─── identity ─────────────────────────────────────────────────────

    @property
    def context_id(self) -> str:
        return self._context_id

    @property
    def request(self) -> IntegrationGatewayRequest:
        return self._request

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    # ─── mutable coordination state ───────────────────────────────────

    @property
    def gateway_state(self) -> GatewayState:
        return self._gateway_state

    @gateway_state.setter
    def gateway_state(self, value: GatewayState) -> None:
        self._gateway_state = value

    @property
    def lifecycle_session_id(self) -> str:
        return self._lifecycle_session_id

    @lifecycle_session_id.setter
    def lifecycle_session_id(self, value: str) -> None:
        self._lifecycle_session_id = value

    @property
    def engine_request_id(self) -> str:
        return self._engine_request_id

    @engine_request_id.setter
    def engine_request_id(self, value: str) -> None:
        self._engine_request_id = value

    @property
    def engine_response_id(self) -> str:
        return self._engine_response_id

    @engine_response_id.setter
    def engine_response_id(self, value: str) -> None:
        self._engine_response_id = value

    @property
    def governance_request_id(self) -> str:
        return self._governance_request_id

    @governance_request_id.setter
    def governance_request_id(self, value: str) -> None:
        self._governance_request_id = value

    @property
    def governance_decision(self) -> str:
        return self._governance_decision

    @governance_decision.setter
    def governance_decision(self, value: str) -> None:
        self._governance_decision = value

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    @snapshot_id.setter
    def snapshot_id(self, value: str) -> None:
        self._snapshot_id = value

    @property
    def current_step(self) -> GatewayWorkflowStep:
        return self._current_step

    # ─── step progression ─────────────────────────────────────────────

    def advance_step(self, step: GatewayWorkflowStep) -> None:
        """Advance workflow to the given step."""
        self._current_step = step

    def record_timing(self, step: GatewayWorkflowStep, elapsed_ms: float) -> None:
        """Record how long a step took."""
        self._step_timings[step.value] = elapsed_ms

    # ─── error / warning tracking ─────────────────────────────────────

    def add_error(self, message: str) -> None:
        """Append an error message to the context."""
        self._errors.append(message)

    def add_warning(self, message: str) -> None:
        """Append a warning message to the context."""
        self._warnings.append(message)

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    @property
    def warnings(self) -> List[str]:
        return list(self._warnings)

    @property
    def has_errors(self) -> bool:
        return bool(self._errors)

    # ─── timing ───────────────────────────────────────────────────────

    def elapsed_ms(self) -> float:
        """Milliseconds elapsed since the context was created."""
        return (time.monotonic() - self._created_at) * 1_000

    @property
    def step_timings(self) -> Dict[str, float]:
        return dict(self._step_timings)

    # ─── serialization ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":            self._context_id,
            "request_id":            self._request.request_id,
            "gateway_id":            self._gateway_id,
            "gateway_state":         self._gateway_state.value,
            "lifecycle_session_id":  self._lifecycle_session_id,
            "engine_request_id":     self._engine_request_id,
            "engine_response_id":    self._engine_response_id,
            "governance_request_id": self._governance_request_id,
            "governance_decision":   self._governance_decision,
            "snapshot_id":           self._snapshot_id,
            "current_step":          self._current_step.value,
            "errors":                list(self._errors),
            "warnings":              list(self._warnings),
            "step_timings":          dict(self._step_timings),
            "elapsed_ms":            self.elapsed_ms(),
        }

    def __repr__(self) -> str:
        return (
            f"IntegrationGatewayContext("
            f"context_id={self._context_id!r}, "
            f"step={self._current_step.value!r}, "
            f"errors={len(self._errors)})"
        )
