"""
market_snapshot_events.py — iios.market.snapshot
=================================================
Domain event factories for the Market Snapshot subsystem.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import SNAPSHOT_SYSTEM_ID, SnapshotEventType


@dataclass(frozen=True)
class MarketSnapshotEvent:
    """Immutable domain event for snapshot lifecycle transitions."""
    event_id:     str
    event_type:   SnapshotEventType
    snapshot_id:  str
    exchange:     str
    actor:        str
    payload:      Dict[str, Any]
    occurred_at:  float
    correlation_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "snapshot_id":   self.snapshot_id,
            "exchange":      self.exchange,
            "actor":         self.actor,
            "payload":       self.payload,
            "occurred_at":   self.occurred_at,
            "correlation_id": self.correlation_id,
            "source":        SNAPSHOT_SYSTEM_ID,
        }


def _make(
    event_type:    SnapshotEventType,
    snapshot_id:   str,
    exchange:      str,
    actor:         str,
    payload:       Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str]           = None,
) -> MarketSnapshotEvent:
    return MarketSnapshotEvent(
        event_id       = str(uuid.uuid4()),
        event_type     = event_type,
        snapshot_id    = snapshot_id,
        exchange       = exchange,
        actor          = actor,
        payload        = dict(payload or {}),
        occurred_at    = time.time(),
        correlation_id = correlation_id or str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per SnapshotEventType
# ---------------------------------------------------------------------------

def snapshot_created_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_CREATED, snapshot_id, exchange, actor, kwargs)


def snapshot_built_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_BUILT, snapshot_id, exchange, actor, kwargs)


def snapshot_validated_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_VALIDATED, snapshot_id, exchange, actor, kwargs)


def snapshot_published_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_PUBLISHED, snapshot_id, exchange, actor, kwargs)


def snapshot_invalidated_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_INVALIDATED, snapshot_id, exchange, actor, kwargs)


def snapshot_archived_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_ARCHIVED, snapshot_id, exchange, actor, kwargs)


def snapshot_expired_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_EXPIRED, snapshot_id, exchange, actor, kwargs)


def snapshot_retrieved_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_RETRIEVED, snapshot_id, exchange, actor, kwargs)


def snapshot_updated_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_UPDATED, snapshot_id, exchange, actor, kwargs)


def snapshot_failed_event(
    snapshot_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_FAILED, snapshot_id, exchange, actor, kwargs)
