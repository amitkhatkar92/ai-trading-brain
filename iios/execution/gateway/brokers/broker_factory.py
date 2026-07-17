"""iios/execution/gateway/brokers/broker_factory.py
==================================================
BrokerFactory — static factory helpers for the Broker Abstraction Layer.

Centralises object construction so the manager and registry never
build domain objects inline.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, FrozenSet, Iterable, Optional

from .broker_capabilities import BrokerCapabilities
from .broker_configuration import BrokerConfiguration
from .broker_connection import BrokerConnection, ConnectionPool
from .broker_health import BrokerHealthRecord, make_health_record
from .broker_response import BrokerResponse, make_success_response, make_failure_response
from .broker_session import BrokerSession, BrokerSessionManager
from .broker_statistics import BrokerStatistics, BrokerStatisticsStore
from .broker_history import BrokerHistory
from .broker_events import BrokerEvent, _make_event
from .constants import (
    ACTOR_BROKER_MANAGER,
    BrokerCapability,
    BrokerEventType,
    DEFAULT_MAX_BROKERS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_SESSION_TIMEOUT_SECS,
)


class BrokerFactory:
    """
    Stateless factory for Broker Abstraction Layer objects.

    All methods are static — no instance is needed.
    """

    # ── BrokerConfiguration ───────────────────────────────────────────────────

    @staticmethod
    def create_configuration(
        broker_id:   str,
        broker_name: str,
        *,
        environment: str = "paper",
        **kwargs: Any,
    ) -> BrokerConfiguration:
        """Create a BrokerConfiguration with sensible defaults."""
        return BrokerConfiguration(
            broker_id=broker_id,
            broker_name=broker_name,
            environment=environment,
            **kwargs,
        )

    # ── BrokerCapabilities ────────────────────────────────────────────────────

    @staticmethod
    def create_capabilities(
        *capabilities: BrokerCapability,
    ) -> BrokerCapabilities:
        """Create a BrokerCapabilities from positional BrokerCapability values."""
        return BrokerCapabilities(frozenset(capabilities))

    @staticmethod
    def create_capabilities_from_iterable(
        capabilities: Iterable[BrokerCapability],
    ) -> BrokerCapabilities:
        """Create a BrokerCapabilities from any iterable."""
        return BrokerCapabilities(frozenset(capabilities))

    # ── Connection ────────────────────────────────────────────────────────────

    @staticmethod
    def create_connection(
        broker_id:     str,
        connection_id: str = "default",
    ) -> BrokerConnection:
        """Create a BrokerConnection in DISCONNECTED state."""
        return BrokerConnection(broker_id=broker_id, connection_id=connection_id)

    @staticmethod
    def create_connection_pool(broker_id: str) -> ConnectionPool:
        """Create an empty ConnectionPool for a broker."""
        return ConnectionPool(broker_id=broker_id)

    # ── Session ───────────────────────────────────────────────────────────────

    @staticmethod
    def create_session(broker_id: str) -> BrokerSession:
        """Create a BrokerSession in unauthenticated state."""
        return BrokerSession(broker_id=broker_id)

    @staticmethod
    def create_session_manager() -> BrokerSessionManager:
        """Create an empty BrokerSessionManager."""
        return BrokerSessionManager()

    # ── Health ────────────────────────────────────────────────────────────────

    @staticmethod
    def create_health_record(
        broker_id:     str,
        is_healthy:    bool,
        latency_ms:    float = 0.0,
        *,
        error_message: Optional[str] = None,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> BrokerHealthRecord:
        """Create a BrokerHealthRecord stamped at the current time."""
        return make_health_record(
            broker_id=broker_id,
            is_healthy=is_healthy,
            latency_ms=latency_ms,
            error_message=error_message,
            metadata=metadata,
        )

    # ── Statistics ────────────────────────────────────────────────────────────

    @staticmethod
    def create_statistics(broker_id: str) -> BrokerStatistics:
        """Create a zeroed BrokerStatistics for a broker."""
        return BrokerStatistics(broker_id=broker_id)

    @staticmethod
    def create_statistics_store() -> BrokerStatisticsStore:
        """Create an empty BrokerStatisticsStore."""
        return BrokerStatisticsStore()

    # ── History ───────────────────────────────────────────────────────────────

    @staticmethod
    def create_history(max_size: int = DEFAULT_MAX_HISTORY) -> BrokerHistory:
        """Create an empty BrokerHistory with the given capacity."""
        return BrokerHistory(max_size=max_size)

    # ── Response helpers ──────────────────────────────────────────────────────

    @staticmethod
    def success_response(
        request_id: str,
        broker_id:  str,
        *,
        data:       Optional[Dict[str, Any]] = None,
        elapsed_ms: float = 0.0,
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> BrokerResponse:
        return make_success_response(
            request_id=request_id,
            broker_id=broker_id,
            data=data,
            elapsed_ms=elapsed_ms,
            metadata=metadata,
        )

    @staticmethod
    def failure_response(
        request_id:    str,
        broker_id:     str,
        *,
        error_code:    Optional[str] = None,
        error_message: Optional[str] = None,
        elapsed_ms:    float = 0.0,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> BrokerResponse:
        return make_failure_response(
            request_id=request_id,
            broker_id=broker_id,
            error_code=error_code,
            error_message=error_message,
            elapsed_ms=elapsed_ms,
            metadata=metadata,
        )
