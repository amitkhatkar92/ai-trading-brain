"""
webhook_engine.py — iios.integration.services
-----------------------------------------------
WebhookEngine — registration, management, and simulated dispatch of webhooks.

MUST NOT import: requests, httpx, or any HTTP library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse

_log = get_logger(__name__)


@dataclass(frozen=True)
class WebhookEndpoint:
    """An immutable webhook endpoint registration."""
    webhook_id:  str
    url:         str
    secret:      str          # HMAC signing secret (never logged)
    topics:      tuple        # tuple[str, ...]
    active:      bool = True
    created_at:  str  = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def register(
        cls,
        url:    str,
        secret: str,
        topics: List[str],
    ) -> "WebhookEndpoint":
        return cls(
            webhook_id = f"wh-{uuid.uuid4().hex[:12]}",
            url        = url,
            secret     = secret,
            topics     = tuple(topics),
        )


@dataclass
class WebhookDeliveryRecord:
    """Mutable record of a webhook delivery attempt."""
    delivery_id:  str
    webhook_id:   str
    topic:        str
    attempt:      int
    success:      bool
    latency_ms:   float
    created_at:   str


class WebhookEngine:
    """
    Manages webhook endpoint registration and (simulated) event delivery.

    No actual HTTP calls are made — the engine records deliveries for
    inspection in tests. Implementors inject a real HTTP client at deployment.
    """

    def __init__(self) -> None:
        self._lock      = threading.Lock()
        self._endpoints: Dict[str, WebhookEndpoint]     = {}
        self._deliveries: List[WebhookDeliveryRecord]    = []
        self._max_deliveries = 10_000

    # ── Registration ─────────────────────────────────────────────────────

    def register(
        self,
        url:    str,
        secret: str,
        topics: List[str],
    ) -> WebhookEndpoint:
        endpoint = WebhookEndpoint.register(url=url, secret=secret, topics=topics)
        with self._lock:
            self._endpoints[endpoint.webhook_id] = endpoint
        _log.debug(f"webhook-engine: registered {endpoint.webhook_id!r} → {url!r}")
        return endpoint

    def deregister(self, webhook_id: str) -> bool:
        with self._lock:
            if webhook_id in self._endpoints:
                del self._endpoints[webhook_id]
                return True
        return False

    def get_endpoint(self, webhook_id: str) -> Optional[WebhookEndpoint]:
        with self._lock:
            return self._endpoints.get(webhook_id)

    def list_endpoints(self) -> List[WebhookEndpoint]:
        with self._lock:
            return list(self._endpoints.values())

    # ── Dispatch ─────────────────────────────────────────────────────────

    def dispatch(
        self,
        topic:   str,
        payload: Dict[str, Any],
    ) -> List[WebhookDeliveryRecord]:
        """
        Simulate dispatching a webhook event to all endpoints subscribed to topic.
        Returns a list of delivery records.
        """
        with self._lock:
            targets = [
                ep for ep in self._endpoints.values()
                if ep.active and (not ep.topics or topic in ep.topics)
            ]

        records: List[WebhookDeliveryRecord] = []
        for ep in targets:
            start = time.perf_counter_ns()
            # Simulated delivery — no real HTTP
            success    = True
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000 + 1.0
            record = WebhookDeliveryRecord(
                delivery_id = f"whdlv-{uuid.uuid4().hex[:10]}",
                webhook_id  = ep.webhook_id,
                topic       = topic,
                attempt     = 1,
                success     = success,
                latency_ms  = latency_ms,
                created_at  = datetime.now(timezone.utc).isoformat(),
            )
            records.append(record)

        with self._lock:
            for r in records:
                if len(self._deliveries) < self._max_deliveries:
                    self._deliveries.append(r)

        return records

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        topic = request.connector_config.get("webhook_topic", "default")
        records = self.dispatch(topic=topic, payload=request.payload)
        latency_ms = (time.perf_counter_ns() - start) / 1_000_000
        return ConnectorResponse.success(
            request.request_id,
            data={"delivered_count": len(records), "topic": topic},
            latency_ms=latency_ms,
            adapter_id="webhook-engine",
            transport="http",
        )

    @property
    def delivery_count(self) -> int:
        with self._lock:
            return len(self._deliveries)

    def recent_deliveries(self, n: int = 20) -> List[WebhookDeliveryRecord]:
        with self._lock:
            return list(self._deliveries[-n:])
