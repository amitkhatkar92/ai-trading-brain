"""
escalation_manager.py -- iios.ai.collaboration.escalation
===========================================================
:class:`EscalationManager` — creates, tracks, and resolves escalation requests.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..exceptions.collaboration_exceptions import (
    AIEscalationNotFoundError,
    AIEscalationPolicyViolationError,
)
from .escalation_decision import EscalationAction, EscalationDecision
from .escalation_request  import EscalationRequest, EscalationStatus
from .escalation_rule     import EscalationTrigger


class EscalationManager:
    """
    Thread-safe store and resolver for :class:`EscalationRequest` objects.

    One instance is shared by the :class:`CollaborationContainer`.
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock                       = threading.RLock()
        self._requests: Dict[str, EscalationRequest]          = {}
        self._decisions: Dict[str, EscalationDecision]        = {}

    # ── Create ────────────────────────────────────────────────────────────────

    def create(
        self,
        session_id:   str,
        trigger:      EscalationTrigger,
        reason:       str,
        requested_by: str,
        escalate_to:  Optional[str] = None,
    ) -> EscalationRequest:
        req = EscalationRequest.create(
            session_id   = session_id,
            trigger      = trigger,
            reason       = reason,
            requested_by = requested_by,
            escalate_to  = escalate_to,
        )
        with self._lock:
            self._requests[req.request_id] = req
        return req

    # ── Update ────────────────────────────────────────────────────────────────

    def start_review(self, request_id: str) -> EscalationRequest:
        req = self._get(request_id)
        if req.is_terminal():
            raise AIEscalationPolicyViolationError(
                f"Escalation '{request_id}' is already in terminal state '{req.status.value}'."
            )
        req.update_status(EscalationStatus.REVIEWING)
        return req

    def resolve(
        self,
        request_id: str,
        action:     EscalationAction,
        decided_by: str,
        rationale:  str = "",
        **data,
    ) -> EscalationDecision:
        req = self._get(request_id)
        if req.is_terminal():
            raise AIEscalationPolicyViolationError(
                f"Escalation '{request_id}' is already resolved."
            )
        decision = EscalationDecision.create(
            request_id = request_id,
            session_id = req.session_id,
            action     = action,
            decided_by = decided_by,
            rationale  = rationale,
            **data,
        )
        terminal_status = (
            EscalationStatus.RESOLVED
            if action in (EscalationAction.APPROVE, EscalationAction.OVERRIDE, EscalationAction.CLOSE)
            else EscalationStatus.REJECTED
        )
        req.update_status(terminal_status, resolution=rationale or action.value)
        with self._lock:
            self._decisions[decision.decision_id] = decision
        return decision

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_request(self, request_id: str) -> EscalationRequest:
        return self._get(request_id)

    def get_decision(self, decision_id: str) -> EscalationDecision:
        with self._lock:
            d = self._decisions.get(decision_id)
        if d is None:
            raise AIEscalationNotFoundError(f"Escalation decision '{decision_id}' not found.")
        return d

    def list_for_session(self, session_id: str) -> List[EscalationRequest]:
        with self._lock:
            return [r for r in self._requests.values() if r.session_id == session_id]

    def list_pending(self) -> List[EscalationRequest]:
        with self._lock:
            return [r for r in self._requests.values() if r.status == EscalationStatus.PENDING]

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get(self, request_id: str) -> EscalationRequest:
        with self._lock:
            r = self._requests.get(request_id)
        if r is None:
            raise AIEscalationNotFoundError(f"Escalation request '{request_id}' not found.")
        return r
