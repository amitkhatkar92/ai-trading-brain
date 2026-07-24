"""
integration_policy_events.py — iios.integration.policies
----------------------------------------------------------
Event bus for the Integration Governance Policy Framework.

Emits 9 governance lifecycle events.  Listener exceptions are
suppressed to prevent disruption of the evaluation pipeline.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .constants import PolicyEventType


@dataclass(frozen=True)
class IntegrationPolicyEvent:
    """
    Immutable event emitted during the governance evaluation lifecycle.
    """

    event_id:   str
    event_type: PolicyEventType
    engine_id:  str
    request_id: str
    payload:    Dict[str, Any]
    emitted_at: str

    @classmethod
    def create(
        cls,
        event_type: PolicyEventType,
        engine_id:  str,
        request_id: str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> "IntegrationPolicyEvent":
        return cls(
            event_id   = f"pevnt-{uuid.uuid4().hex[:12]}",
            event_type = event_type,
            engine_id  = engine_id,
            request_id = request_id,
            payload    = dict(payload or {}),
            emitted_at = datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "engine_id":  self.engine_id,
            "request_id": self.request_id,
            "payload":    self.payload,
            "emitted_at": self.emitted_at,
        }


class IntegrationPolicyEventBus:
    """
    Thread-safe event bus for governance lifecycle events.

    Listener exceptions are suppressed so that a misbehaving listener
    cannot halt governance evaluation.
    """

    def __init__(self) -> None:
        self._listeners: List[Callable[[IntegrationPolicyEvent], None]] = []
        self._lock = threading.Lock()

    def add_listener(self, fn: Callable[[IntegrationPolicyEvent], None]) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[IntegrationPolicyEvent], None]) -> None:
        with self._lock:
            self._listeners = [l for l in self._listeners if l is not fn]

    def emit(
        self,
        event_type: PolicyEventType,
        engine_id:  str,
        request_id: str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> IntegrationPolicyEvent:
        event = IntegrationPolicyEvent.create(event_type, engine_id, request_id, payload)
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                pass
        return event

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
