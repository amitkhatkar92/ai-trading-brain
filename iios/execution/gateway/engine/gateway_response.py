"""iios/execution/gateway/engine/gateway_response.py
==================================================
GatewayResponse — immutable result returned to the caller after a
request submission to the Execution Gateway Engine.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import DispatchOutcome, RequestStatus, VERSION


@dataclass(frozen=True)
class GatewayResponse:
    """
    Immutable result of a single gateway request submission.

    Returned by ``ExecutionGatewayEngine.submit_request()`` and
    ``GatewayManager.process_request()``.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    response_id:          str
    request_id:           str
    lifecycle_request_id: str     # M1 GatewayRequest.gateway_id
    session_id:           str

    # ── Outcome ───────────────────────────────────────────────────────────────
    status:           str          # RequestStatus.value
    outcome:          Optional[str]  # DispatchOutcome.value or None
    dispatch_result:  Dict[str, Any]

    # ── Error (empty if success) ──────────────────────────────────────────────
    error_code:    str
    error_message: str

    # ── Request identifiers ───────────────────────────────────────────────────
    portfolio_id: str
    strategy_id:  str
    execution_id: str
    order_id:     str
    symbol:       str

    # ── Timing ────────────────────────────────────────────────────────────────
    created_at:  float
    elapsed_ms:  float

    # ── Metadata ──────────────────────────────────────────────────────────────
    version:  str               = VERSION
    metadata: Dict[str, Any]    = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_accepted(self) -> bool:
        """True if dispatch outcome was ACCEPTED."""
        return self.outcome == DispatchOutcome.ACCEPTED.value

    @property
    def is_rejected(self) -> bool:
        """True if dispatch outcome was REJECTED."""
        return self.outcome == DispatchOutcome.REJECTED.value

    @property
    def is_deferred(self) -> bool:
        """True if dispatch outcome was DEFERRED."""
        return self.outcome == DispatchOutcome.DEFERRED.value

    @property
    def is_completed(self) -> bool:
        return self.status == RequestStatus.COMPLETED.value

    @property
    def is_failed(self) -> bool:
        return self.status == RequestStatus.FAILED.value

    @property
    def is_cancelled(self) -> bool:
        return self.status == RequestStatus.CANCELLED.value

    @property
    def has_error(self) -> bool:
        return bool(self.error_code or self.error_message)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":          self.response_id,
            "request_id":           self.request_id,
            "lifecycle_request_id": self.lifecycle_request_id,
            "session_id":           self.session_id,
            "status":               self.status,
            "outcome":              self.outcome,
            "dispatch_result":      dict(self.dispatch_result),
            "error_code":           self.error_code,
            "error_message":        self.error_message,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "execution_id":         self.execution_id,
            "order_id":             self.order_id,
            "symbol":               self.symbol,
            "created_at":           self.created_at,
            "elapsed_ms":           self.elapsed_ms,
            "version":              self.version,
            "metadata":             dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"GatewayResponse("
            f"request_id={self.request_id!r}, "
            f"status={self.status!r}, "
            f"outcome={self.outcome!r})"
        )


def make_gateway_response(
    request_id:           str,
    lifecycle_request_id: str,
    session_id:           str,
    status:               RequestStatus,
    outcome:              Optional[DispatchOutcome],
    dispatch_result:      Dict[str, Any],
    error_code:           str,
    error_message:        str,
    portfolio_id:         str,
    strategy_id:          str,
    execution_id:         str,
    order_id:             str,
    symbol:               str,
    elapsed_ms:           float,
    metadata:             Optional[Dict[str, Any]] = None,
) -> GatewayResponse:
    """Build a ``GatewayResponse`` with an auto-generated ``response_id``."""
    return GatewayResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        lifecycle_request_id=lifecycle_request_id,
        session_id=session_id,
        status=status.value,
        outcome=outcome.value if outcome is not None else None,
        dispatch_result=dict(dispatch_result),
        error_code=error_code,
        error_message=error_message,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        execution_id=execution_id,
        order_id=order_id,
        symbol=symbol,
        created_at=time.time(),
        elapsed_ms=elapsed_ms,
        metadata=metadata or {},
    )
