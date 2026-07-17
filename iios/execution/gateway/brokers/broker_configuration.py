"""iios/execution/gateway/brokers/broker_configuration.py
==================================================
BrokerConfiguration — immutable configuration record for a registered
broker.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import (
    DEFAULT_AUTH_TIMEOUT_SECS,
    DEFAULT_CONNECTION_TIMEOUT_SECS,
    DEFAULT_HEARTBEAT_INTERVAL_SECS,
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RECONNECT_DELAY_SECS,
    DEFAULT_REQUEST_TIMEOUT_SECS,
    DEFAULT_SESSION_TIMEOUT_SECS,
)


@dataclass(frozen=True)
class BrokerConfiguration:
    """
    Immutable configuration for a broker registration.

    Holds connection, authentication, and retry parameters.
    Never contains credentials — those are managed by the
    broker implementation itself.

    Parameters
    ----------
    broker_id:
        Unique identifier for this broker instance.
    broker_name:
        Human-readable display name.
    environment:
        ``"live"`` or ``"paper"``.  Defaults to ``"paper"``.
    timeout_secs:
        Maximum seconds to wait for a connection.
    auth_timeout_secs:
        Maximum seconds to wait for authentication.
    request_timeout_secs:
        Maximum seconds to wait for a broker API response.
    heartbeat_interval_secs:
        Interval between heartbeat pings.
    auto_reconnect:
        Whether the manager should automatically reconnect on failure.
    max_reconnect_attempts:
        Maximum number of reconnection attempts before marking FAILED.
    reconnect_delay_secs:
        Seconds to wait between reconnection attempts.
    max_retries:
        Maximum number of request retries on retryable errors.
    session_timeout_secs:
        Seconds before an authenticated session is considered expired.
    metadata:
        Arbitrary key-value pairs passed to the broker implementation.
    """

    broker_id:                str
    broker_name:              str
    environment:              str   = "paper"
    timeout_secs:             float = DEFAULT_CONNECTION_TIMEOUT_SECS
    auth_timeout_secs:        float = DEFAULT_AUTH_TIMEOUT_SECS
    request_timeout_secs:     float = DEFAULT_REQUEST_TIMEOUT_SECS
    heartbeat_interval_secs:  float = DEFAULT_HEARTBEAT_INTERVAL_SECS
    auto_reconnect:           bool  = True
    max_reconnect_attempts:   int   = DEFAULT_MAX_RECONNECT_ATTEMPTS
    reconnect_delay_secs:     float = DEFAULT_RECONNECT_DELAY_SECS
    max_retries:              int   = DEFAULT_MAX_RETRIES
    session_timeout_secs:     float = DEFAULT_SESSION_TIMEOUT_SECS
    metadata: Dict[str, Any]  = field(default_factory=dict)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_live(self) -> bool:
        """True when environment is 'live'."""
        return self.environment == "live"

    @property
    def is_paper(self) -> bool:
        """True when environment is 'paper'."""
        return self.environment == "paper"

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broker_id":               self.broker_id,
            "broker_name":             self.broker_name,
            "environment":             self.environment,
            "timeout_secs":            self.timeout_secs,
            "auth_timeout_secs":       self.auth_timeout_secs,
            "request_timeout_secs":    self.request_timeout_secs,
            "heartbeat_interval_secs": self.heartbeat_interval_secs,
            "auto_reconnect":          self.auto_reconnect,
            "max_reconnect_attempts":  self.max_reconnect_attempts,
            "reconnect_delay_secs":    self.reconnect_delay_secs,
            "max_retries":             self.max_retries,
            "session_timeout_secs":    self.session_timeout_secs,
            "metadata":                dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"BrokerConfiguration("
            f"broker_id={self.broker_id!r}, "
            f"broker_name={self.broker_name!r}, "
            f"environment={self.environment!r}"
            f")"
        )
