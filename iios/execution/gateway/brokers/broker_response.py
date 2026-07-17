"""iios/execution/gateway/brokers/broker_response.py
==================================================
Standardized broker response model.

All broker operations return a BrokerResponse with a uniform
status, optional payload, and correlation IDs.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    RETRYABLE_RESPONSE_STATUSES,
    ResponseStatus,
    VERSION,
)


@dataclass(frozen=True)
class BrokerResponse:
    """
    Immutable outcome of a broker operation.

    Every broker interface method returns a BrokerResponse so that
    the caller receives a uniform object regardless of broker
    implementation.

    Fields
    ------
    response_id:
        Unique ID for this response.
    request_id:
        Correlates back to the originating BrokerRequest.request_id.
    broker_id:
        The broker that produced this response.
    status:
        Standardised outcome status (SUCCESS, FAILURE, etc.).
    data:
        Optional response payload — order details, position list, etc.
        The key schema depends on the request type.
    error_code:
        Broker-specific error code when status is not SUCCESS.
    error_message:
        Human-readable description of the error.
    retryable:
        True when the caller may safely retry the same request.
    created_at:
        Unix timestamp when this response was created.
    elapsed_ms:
        Wall time from request submission to response creation.
    version:
        BAL version string.
    metadata:
        Arbitrary key-value pairs.
    """

    response_id:   str
    request_id:    str
    broker_id:     str
    status:        ResponseStatus
    data:          Optional[Dict[str, Any]]
    error_code:    Optional[str]
    error_message: Optional[str]
    retryable:     bool
    created_at:    float
    elapsed_ms:    float
    version:       str                = VERSION
    metadata:      Dict[str, Any]     = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == ResponseStatus.FAILURE

    @property
    def is_error(self) -> bool:
        return self.status == ResponseStatus.ERROR

    @property
    def is_retryable(self) -> bool:
        return self.retryable or self.status in RETRYABLE_RESPONSE_STATUSES

    @property
    def is_auth_failure(self) -> bool:
        return self.status == ResponseStatus.AUTH_FAILURE

    @property
    def is_network_failure(self) -> bool:
        return self.status == ResponseStatus.NETWORK_FAILURE

    @property
    def is_rate_limited(self) -> bool:
        return self.status == ResponseStatus.RATE_LIMITED

    @property
    def has_data(self) -> bool:
        return self.data is not None and len(self.data) > 0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "broker_id":     self.broker_id,
            "status":        self.status.value,
            "data":          dict(self.data) if self.data else None,
            "error_code":    self.error_code,
            "error_message": self.error_message,
            "retryable":     self.retryable,
            "created_at":    self.created_at,
            "elapsed_ms":    self.elapsed_ms,
            "version":       self.version,
            "metadata":      dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"BrokerResponse("
            f"response_id={self.response_id!r}, "
            f"broker_id={self.broker_id!r}, "
            f"status={self.status.value!r}"
            f")"
        )


# ── Factory functions ─────────────────────────────────────────────────────────

def make_success_response(
    request_id: str,
    broker_id:  str,
    *,
    data:       Optional[Dict[str, Any]] = None,
    elapsed_ms: float = 0.0,
    metadata:   Optional[Dict[str, Any]] = None,
) -> BrokerResponse:
    """Create a SUCCESS response."""
    return BrokerResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        broker_id=broker_id,
        status=ResponseStatus.SUCCESS,
        data=data,
        error_code=None,
        error_message=None,
        retryable=False,
        created_at=time.time(),
        elapsed_ms=max(0.0, elapsed_ms),
        metadata=dict(metadata or {}),
    )


def make_failure_response(
    request_id:    str,
    broker_id:     str,
    *,
    error_code:    Optional[str] = None,
    error_message: Optional[str] = None,
    elapsed_ms:    float = 0.0,
    metadata:      Optional[Dict[str, Any]] = None,
) -> BrokerResponse:
    """Create a FAILURE response (non-retryable, broker-level rejection)."""
    return BrokerResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        broker_id=broker_id,
        status=ResponseStatus.FAILURE,
        data=None,
        error_code=error_code,
        error_message=error_message,
        retryable=False,
        created_at=time.time(),
        elapsed_ms=max(0.0, elapsed_ms),
        metadata=dict(metadata or {}),
    )


def make_error_response(
    request_id:    str,
    broker_id:     str,
    *,
    error_code:    Optional[str] = None,
    error_message: Optional[str] = None,
    elapsed_ms:    float = 0.0,
    metadata:      Optional[Dict[str, Any]] = None,
) -> BrokerResponse:
    """Create an ERROR response (non-retryable, unexpected error)."""
    return BrokerResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        broker_id=broker_id,
        status=ResponseStatus.ERROR,
        data=None,
        error_code=error_code,
        error_message=error_message,
        retryable=False,
        created_at=time.time(),
        elapsed_ms=max(0.0, elapsed_ms),
        metadata=dict(metadata or {}),
    )


def make_retryable_error_response(
    request_id:    str,
    broker_id:     str,
    *,
    error_code:    Optional[str] = None,
    error_message: Optional[str] = None,
    elapsed_ms:    float = 0.0,
    metadata:      Optional[Dict[str, Any]] = None,
) -> BrokerResponse:
    """Create a RETRYABLE_ERROR response."""
    return BrokerResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        broker_id=broker_id,
        status=ResponseStatus.RETRYABLE_ERROR,
        data=None,
        error_code=error_code,
        error_message=error_message,
        retryable=True,
        created_at=time.time(),
        elapsed_ms=max(0.0, elapsed_ms),
        metadata=dict(metadata or {}),
    )


def make_auth_failure_response(
    request_id:    str,
    broker_id:     str,
    *,
    error_message: Optional[str] = None,
    elapsed_ms:    float = 0.0,
    metadata:      Optional[Dict[str, Any]] = None,
) -> BrokerResponse:
    """Create an AUTH_FAILURE response."""
    return BrokerResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        broker_id=broker_id,
        status=ResponseStatus.AUTH_FAILURE,
        data=None,
        error_code="AUTH_FAILURE",
        error_message=error_message or "Authentication failed.",
        retryable=False,
        created_at=time.time(),
        elapsed_ms=max(0.0, elapsed_ms),
        metadata=dict(metadata or {}),
    )


def make_network_failure_response(
    request_id:    str,
    broker_id:     str,
    *,
    error_message: Optional[str] = None,
    elapsed_ms:    float = 0.0,
    metadata:      Optional[Dict[str, Any]] = None,
) -> BrokerResponse:
    """Create a NETWORK_FAILURE response (retryable)."""
    return BrokerResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        broker_id=broker_id,
        status=ResponseStatus.NETWORK_FAILURE,
        data=None,
        error_code="NETWORK_FAILURE",
        error_message=error_message or "Network failure.",
        retryable=True,
        created_at=time.time(),
        elapsed_ms=max(0.0, elapsed_ms),
        metadata=dict(metadata or {}),
    )


def make_rate_limit_response(
    request_id:    str,
    broker_id:     str,
    *,
    error_message: Optional[str] = None,
    elapsed_ms:    float = 0.0,
    metadata:      Optional[Dict[str, Any]] = None,
) -> BrokerResponse:
    """Create a RATE_LIMITED response (retryable)."""
    return BrokerResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        broker_id=broker_id,
        status=ResponseStatus.RATE_LIMITED,
        data=None,
        error_code="RATE_LIMITED",
        error_message=error_message or "Rate limit exceeded.",
        retryable=True,
        created_at=time.time(),
        elapsed_ms=max(0.0, elapsed_ms),
        metadata=dict(metadata or {}),
    )
