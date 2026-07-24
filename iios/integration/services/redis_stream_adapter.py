"""
redis_stream_adapter.py — iios.integration.services
-----------------------------------------------------
Provider-independent Redis Streams adapter interface.

MUST NOT import: redis, redis-py, aioredis, or any Redis library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse


# ════════════════════════════════════════════════════════════════════════
# Data objects
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class RedisStreamEntry:
    """A single Redis Streams entry."""
    stream_key: str
    entry_id:   str
    fields:     Dict[str, Any]
    timestamp:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseRedisStreamAdapter(ABC):
    """Abstract Redis Streams adapter — implementors inject redis-py."""

    @abstractmethod
    def xadd(
        self,
        stream_key: str,
        fields:     Dict[str, Any],
        max_len:    Optional[int] = None,
    ) -> RedisStreamEntry:
        """Append an entry to a Redis stream."""

    @abstractmethod
    def xread(
        self,
        stream_key:   str,
        consumer_group: str,
        consumer:     str,
        count:        int = 10,
        block_ms:     int = 0,
    ) -> List[RedisStreamEntry]:
        """Read entries from a Redis stream consumer group."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the Redis connection is alive."""

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg       = request.connector_config
            operation = cfg.get("redis_operation", "xadd").lower()
            key       = cfg.get("redis_stream_key", "iios:stream")
            if operation == "xread":
                entries = self.xread(
                    stream_key=key,
                    consumer_group=cfg.get("redis_consumer_group", "iios-group"),
                    consumer=cfg.get("redis_consumer", "iios-consumer"),
                    count=cfg.get("redis_count", 10),
                    block_ms=request.timeout_ms,
                )
                data = {"entries": [e.__dict__ for e in entries], "count": len(entries)}
            else:
                entry = self.xadd(stream_key=key, fields=request.payload)
                data  = {"stream_key": entry.stream_key, "entry_id": entry.entry_id}
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=data, latency_ms=latency_ms,
                adapter_id="redis-stream-adapter", transport="redis_protocol",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="redis-stream-adapter", transport="redis_protocol",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation
# ════════════════════════════════════════════════════════════════════════


class SimulatedRedisStreamAdapter(BaseRedisStreamAdapter):
    """In-process Redis Streams simulation — no Redis I/O."""

    def __init__(self) -> None:
        self._seq = 0

    def xadd(
        self,
        stream_key: str,
        fields:     Dict[str, Any],
        max_len:    Optional[int] = None,
    ) -> RedisStreamEntry:
        self._seq += 1
        entry_id = f"0-{self._seq}"
        return RedisStreamEntry(stream_key=stream_key, entry_id=entry_id, fields=fields)

    def xread(
        self,
        stream_key:     str,
        consumer_group: str,
        consumer:       str,
        count:          int = 10,
        block_ms:       int = 0,
    ) -> List[RedisStreamEntry]:
        return [
            RedisStreamEntry(
                stream_key=stream_key, entry_id=f"0-{i}",
                fields={"simulated": True, "index": i},
            )
            for i in range(min(count, 1))
        ]

    def health_check(self) -> bool:
        return True
