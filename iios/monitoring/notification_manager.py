"""
iios/monitoring/notification_manager.py
=========================================
Notification delivery for IIOS alerts.

Supports:
  - Telegram (via Bot API, requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
  - Console (always available)
  - Log file (always available)
  - Webhook (HTTP POST to any URL)

All channels degrade gracefully — a missing dependency or network failure
is logged but never propagates to the caller.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Optional

from .monitoring_constants import NotificationChannel, AlertLevel
from .monitoring_models import AlertEvent, NotificationRecord

__all__ = [
    "NotificationChannel",
    "NotificationManager",
    "ConsoleChannel",
    "LogChannel",
    "TelegramChannel",
    "WebhookChannel",
    "get_notification_manager",
]

_LOG = logging.getLogger("iios.monitoring.notifications")
_instance_lock = threading.Lock()
_instance: Optional["NotificationManager"] = None


# ---------------------------------------------------------------------------
# Channel ABC
# ---------------------------------------------------------------------------


class BaseChannel(ABC):
    """Abstract notification channel."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel identifier."""

    @abstractmethod
    def send(self, subject: str, body: str, alert: Optional[AlertEvent] = None) -> bool:
        """Send notification. Returns True on success."""


# ---------------------------------------------------------------------------
# Concrete channels
# ---------------------------------------------------------------------------


class ConsoleChannel(BaseChannel):
    """Prints notifications to stdout/stderr."""

    @property
    def name(self) -> str:
        return NotificationChannel.CONSOLE.value

    def send(self, subject: str, body: str, alert: Optional[AlertEvent] = None) -> bool:
        level_icon = {
            AlertLevel.CRITICAL.value: "🔴",
            AlertLevel.ERROR.value:    "🟠",
            AlertLevel.WARNING.value:  "🟡",
        }.get(alert.level if alert else "", "🔵")
        print(f"{level_icon} [{subject}] {body}")
        return True


class LogChannel(BaseChannel):
    """Writes notifications to the Python logging system."""

    @property
    def name(self) -> str:
        return NotificationChannel.LOG.value

    def send(self, subject: str, body: str, alert: Optional[AlertEvent] = None) -> bool:
        level = (alert.level if alert else AlertLevel.INFO.value).upper()
        log_fn = {
            "CRITICAL": _LOG.critical,
            "ERROR":    _LOG.error,
            "WARNING":  _LOG.warning,
        }.get(level, _LOG.info)
        log_fn("NOTIFY [%s] %s", subject, body)
        return True


class TelegramChannel(BaseChannel):
    """Sends alerts via the Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    @property
    def name(self) -> str:
        return NotificationChannel.TELEGRAM.value

    def send(self, subject: str, body: str, alert: Optional[AlertEvent] = None) -> bool:
        try:
            import urllib.request
            icon = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡"}.get(
                (alert.level if alert else ""), "🔵"
            )
            text = f"{icon} *{subject}*\n{body}"
            if alert:
                text += (
                    f"\n`component={alert.component} layer={alert.layer}`"
                    f"\n`{alert.timestamp}`"
                )
            payload = json.dumps({
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }).encode()
            req = urllib.request.Request(
                self._api_url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as exc:
            _LOG.warning("Telegram notification failed: %s", exc)
            return False


class WebhookChannel(BaseChannel):
    """Posts alerts to an HTTP webhook URL."""

    def __init__(self, url: str, headers: Optional[dict[str, str]] = None) -> None:
        self._url = url
        self._headers = headers or {"Content-Type": "application/json"}

    @property
    def name(self) -> str:
        return NotificationChannel.WEBHOOK.value

    def send(self, subject: str, body: str, alert: Optional[AlertEvent] = None) -> bool:
        try:
            import urllib.request
            import dataclasses
            payload_dict: dict[str, Any] = {"subject": subject, "body": body}
            if alert:
                payload_dict["alert"] = dataclasses.asdict(alert)
            data = json.dumps(payload_dict, default=str).encode()
            req = urllib.request.Request(self._url, data=data, headers=self._headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status < 300
        except Exception as exc:
            _LOG.warning("Webhook notification failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class NotificationManager:
    """Routes alert notifications to registered channels.

    Channels are called in registration order. Failures are logged but
    never block delivery to subsequent channels.

    Args:
        min_level:        Minimum alert level to notify (default WARNING).
        rate_limit_per_min: Maximum notifications per minute per channel.
    """

    def __init__(
        self,
        min_level: str = AlertLevel.WARNING.value,
        rate_limit_per_min: int = 20,
    ) -> None:
        self._lock = threading.Lock()
        self._channels: list[BaseChannel] = []
        self._min_level = self._level_rank(min_level)
        self._rate_limit = rate_limit_per_min
        # channel_name → deque of send timestamps
        self._send_times: dict[str, deque] = {}
        self._records: deque[NotificationRecord] = deque(maxlen=500)
        self._sent_count = 0

        # Always register console and log channels
        self.add_channel(LogChannel())

    # ------------------------------------------------------------------
    # Channel registration
    # ------------------------------------------------------------------

    def add_channel(self, channel: BaseChannel) -> "NotificationManager":
        with self._lock:
            self._channels.append(channel)
            self._send_times[channel.name] = deque()
        return self

    def remove_channel(self, name: str) -> None:
        with self._lock:
            self._channels = [c for c in self._channels if c.name != name]

    # ------------------------------------------------------------------
    # Notify
    # ------------------------------------------------------------------

    def notify_alert(self, alert: AlertEvent) -> list[NotificationRecord]:
        """Send *alert* to all applicable channels."""
        if self._level_rank(alert.level) < self._min_level:
            return []

        subject = f"[{alert.level}] {alert.title}"
        body = alert.message
        if alert.component:
            body += f" (component={alert.component})"

        return self.notify(subject, body, alert=alert)

    def notify(
        self,
        subject: str,
        body: str,
        alert: Optional[AlertEvent] = None,
        channels: Optional[list[str]] = None,
    ) -> list[NotificationRecord]:
        """Send a notification to all (or specified) channels."""
        with self._lock:
            selected = [
                c for c in self._channels
                if channels is None or c.name in channels
            ]

        records: list[NotificationRecord] = []
        for channel in selected:
            if not self._check_rate_limit(channel.name):
                continue
            success = False
            error: Optional[str] = None
            try:
                success = channel.send(subject, body, alert)
            except Exception as exc:
                error = str(exc)
                _LOG.warning("Channel %r send error: %s", channel.name, exc)

            record = NotificationRecord(
                channel=channel.name,
                recipient=channel.name,
                subject=subject,
                body=body,
                alert_id=alert.alert_id if alert else "",
                success=success,
                error=error,
            )
            with self._lock:
                self._records.append(record)
                self._sent_count += 1
            records.append(record)

        return records

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def recent_notifications(self, n: int = 20) -> list[NotificationRecord]:
        with self._lock:
            return list(reversed(list(self._records)))[:n]

    @property
    def sent_count(self) -> int:
        return self._sent_count

    @property
    def channel_names(self) -> list[str]:
        with self._lock:
            return [c.name for c in self._channels]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_rate_limit(self, channel_name: str) -> bool:
        now = time.monotonic()
        window_start = now - 60.0
        with self._lock:
            dq = self._send_times.setdefault(channel_name, deque())
            while dq and dq[0] < window_start:
                dq.popleft()
            if len(dq) >= self._rate_limit:
                return False
            dq.append(now)
        return True

    @staticmethod
    def _level_rank(level: str) -> int:
        return {"INFO": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 3}.get(level.upper(), 0)


def get_notification_manager() -> NotificationManager:
    """Return (or create) the global ``NotificationManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = NotificationManager()
        return _instance


def _reset_notification_manager() -> None:
    global _instance
    with _instance_lock:
        _instance = None
