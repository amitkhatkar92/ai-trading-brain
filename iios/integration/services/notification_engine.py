"""
notification_engine.py — iios.integration.services
----------------------------------------------------
NotificationEngine — routes notifications (email, SMS, push) through
provider-independent adapters.

MUST NOT import: smtplib, twilio, firebase-admin, or any notification library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import ServiceType

_log = get_logger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Data objects
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class NotificationRecord:
    """Immutable record of a sent notification."""
    notification_id:  str
    channel:          str   # "email" | "sms" | "push"
    recipient:        str
    subject:          str
    body:             str
    success:          bool
    latency_ms:       float
    created_at:       str


# ════════════════════════════════════════════════════════════════════════
# Abstract Interfaces
# ════════════════════════════════════════════════════════════════════════


class BaseNotificationAdapter(ABC):
    """Abstract notification adapter."""

    @abstractmethod
    def send(
        self,
        recipient: str,
        subject:   str,
        body:      str,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> NotificationRecord:
        """Send a notification and return a record."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the notification channel is available."""


class SimulatedEmailAdapter(BaseNotificationAdapter):
    """Simulated email adapter — no SMTP I/O."""

    def send(
        self,
        recipient: str,
        subject:   str,
        body:      str,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> NotificationRecord:
        return NotificationRecord(
            notification_id = f"notif-{uuid.uuid4().hex[:10]}",
            channel  = "email",
            recipient= recipient,
            subject  = subject,
            body     = body,
            success  = True,
            latency_ms = 1.0,
            created_at = datetime.now(timezone.utc).isoformat(),
        )

    def health_check(self) -> bool:
        return True


class SimulatedSmsAdapter(BaseNotificationAdapter):
    """Simulated SMS adapter — no provider I/O."""

    def send(
        self,
        recipient: str,
        subject:   str,
        body:      str,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> NotificationRecord:
        return NotificationRecord(
            notification_id = f"notif-{uuid.uuid4().hex[:10]}",
            channel  = "sms",
            recipient= recipient,
            subject  = subject,
            body     = body,
            success  = True,
            latency_ms = 1.0,
            created_at = datetime.now(timezone.utc).isoformat(),
        )

    def health_check(self) -> bool:
        return True


class SimulatedPushAdapter(BaseNotificationAdapter):
    """Simulated push notification adapter — no FCM/APNs I/O."""

    def send(
        self,
        recipient: str,
        subject:   str,
        body:      str,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> NotificationRecord:
        return NotificationRecord(
            notification_id = f"notif-{uuid.uuid4().hex[:10]}",
            channel  = "push",
            recipient= recipient,
            subject  = subject,
            body     = body,
            success  = True,
            latency_ms = 1.0,
            created_at = datetime.now(timezone.utc).isoformat(),
        )

    def health_check(self) -> bool:
        return True


# ════════════════════════════════════════════════════════════════════════
# Engine
# ════════════════════════════════════════════════════════════════════════


_DEFAULT_ADAPTERS: Dict[str, BaseNotificationAdapter] = {
    "email": SimulatedEmailAdapter(),
    "sms":   SimulatedSmsAdapter(),
    "push":  SimulatedPushAdapter(),
}


class NotificationEngine:
    """
    Routes notification requests to the appropriate channel adapter.
    """

    def __init__(
        self,
        adapters: Optional[Dict[str, BaseNotificationAdapter]] = None,
    ) -> None:
        self._lock     = threading.Lock()
        self._adapters = adapters or dict(_DEFAULT_ADAPTERS)
        self._sent     = 0
        self._errors   = 0

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg       = request.connector_config
            channel   = cfg.get("notification_channel", "email").lower()
            recipient = cfg.get("notification_recipient", "")
            subject   = cfg.get("notification_subject", "")
            body      = request.payload.get("body", "")

            adapter = self._adapters.get(channel)
            if adapter is None:
                raise ValueError(f"Unknown notification channel: {channel!r}")

            record = adapter.send(recipient=recipient, subject=subject, body=body,
                                  metadata=request.metadata)
            with self._lock:
                self._sent += 1
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id,
                data={"notification_id": record.notification_id, "channel": channel,
                      "recipient": recipient},
                latency_ms = latency_ms,
                adapter_id = "notification-engine",
                transport  = "internal",
            )
        except Exception as exc:
            with self._lock:
                self._errors += 1
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="notification-engine", transport="internal",
            )

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {"sent": self._sent, "errors": self._errors}

    def health_check(self) -> bool:
        return all(a.health_check() for a in self._adapters.values())
