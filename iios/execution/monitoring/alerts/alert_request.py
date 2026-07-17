"""iios/execution/monitoring/alerts/alert_request.py
==================================================
AlertRequest — immutable request for an alert evaluation cycle.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .alert_context import AlertContext


@dataclass(frozen=True)
class AlertRequest:
    """
    Immutable structured request for alert evaluation.

    Wraps an AlertContext and optionally restricts evaluation to a
    specific subset of rule IDs.  An empty ``rule_ids`` means: evaluate
    ALL registered and enabled rules.
    """

    request_id:   str
    session_id:   str
    context:      AlertContext
    rule_ids:     Tuple[str, ...]  # empty = evaluate ALL registered rules
    requested_at: float
    metadata:     Dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "session_id":   self.session_id,
            "rule_ids":     list(self.rule_ids),
            "requested_at": self.requested_at,
        }


def make_alert_request(
    session_id: str,
    context:    AlertContext,
    *,
    rule_ids:     Tuple[str, ...]      = (),
    metadata:     Optional[Dict[str, Any]] = None,
    request_id:   Optional[str]        = None,
    requested_at: Optional[float]      = None,
) -> AlertRequest:
    """Factory for AlertRequest."""
    return AlertRequest(
        request_id   = request_id or str(uuid.uuid4()),
        session_id   = session_id,
        context      = context,
        rule_ids     = rule_ids,
        requested_at = requested_at if requested_at is not None else time.time(),
        metadata     = dict(metadata) if metadata else {},
    )
