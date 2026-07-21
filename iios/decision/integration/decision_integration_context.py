"""
decision_integration_context.py — iios.decision.integration
=============================================================
Mutable per-request workflow context.  Used internally by the integration
engine to carry state across workflow phases.  Never exposed publicly.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from .constants import IntegrationPhase, VERSION


class DecisionIntegrationContext:
    """
    Mutable workflow context for a single integration request.

    Each call to :meth:`DecisionIntegrationEngine.submit` creates one
    instance of this class.  It is discarded once the response is built.

    Attributes
    ----------
    context_id :        Unique identifier for this context.
    request_id :        Originating request identifier.
    decision_id :       Decision identifier.
    session_id :        M1 lifecycle session identifier (set once created).
    phase :             Current workflow phase.
    started_at :        Wall-clock start time.
    phase_times :       Per-phase wall-clock durations.
    session :           M1 :class:`DecisionSession` (after creation).
    engine_response :   M2 :class:`DecisionResponse` (after engine call).
    policy_response :   M3 policy response (after policy evaluation).
    optimization_response : M4 optimization response (after optimization).
    decision_snapshot : M5 :class:`DecisionSnapshot` (after build).
    error :             Exception if the workflow failed.
    """

    __slots__ = (
        "context_id",
        "request_id",
        "decision_id",
        "session_id",
        "phase",
        "started_at",
        "phase_times",
        "session",
        "engine_response",
        "policy_response",
        "optimization_response",
        "decision_snapshot",
        "error",
        "_phase_start",
    )

    def __init__(self, request_id: str, decision_id: str) -> None:
        self.context_id:              str                = str(uuid.uuid4())
        self.request_id:              str                = request_id
        self.decision_id:             str                = decision_id
        self.session_id:              str                = ""
        self.phase:                   IntegrationPhase   = IntegrationPhase.IDLE
        self.started_at:              float              = time.monotonic()
        self.phase_times:             Dict[str, float]   = {}
        self.session:                 Optional[Any]      = None
        self.engine_response:         Optional[Any]      = None
        self.policy_response:         Optional[Any]      = None
        self.optimization_response:   Optional[Any]      = None
        self.decision_snapshot:       Optional[Any]      = None
        self.error:                   Optional[Exception] = None
        self._phase_start:            float              = time.monotonic()

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def enter_phase(self, phase: IntegrationPhase) -> None:
        """Record end of the previous phase and start of ``phase``."""
        now = time.monotonic()
        if self.phase != IntegrationPhase.IDLE:
            self.phase_times[self.phase.value] = now - self._phase_start
        self.phase        = phase
        self._phase_start = now

    def close_phase(self) -> None:
        """Record the end of the current phase."""
        now = time.monotonic()
        if self.phase != IntegrationPhase.IDLE:
            self.phase_times[self.phase.value] = now - self._phase_start

    # ------------------------------------------------------------------
    # Elapsed helpers
    # ------------------------------------------------------------------

    def elapsed_s(self) -> float:
        """Total wall-clock seconds since the context was created."""
        return time.monotonic() - self.started_at

    def phase_time(self, phase: IntegrationPhase) -> float:
        return self.phase_times.get(phase.value, 0.0)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"DecisionIntegrationContext("
            f"request_id={self.request_id!r}, "
            f"decision_id={self.decision_id!r}, "
            f"phase={self.phase.value!r})"
        )
