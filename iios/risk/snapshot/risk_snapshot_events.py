"""
risk_snapshot_events.py — iios.risk.snapshot
=============================================
Domain event value objects for the Risk Snapshot Framework.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import SnapshotEventType, VERSION


@dataclass(frozen=True)
class RiskSnapshotEvent:
    """Immutable domain event for the snapshot framework."""
    event_id:        str
    event_type:      SnapshotEventType
    snapshot_id:     str
    portfolio_id:    str
    actor:           str
    payload:         Dict[str, Any]
    framework_version: str = VERSION
    occurred_at:     float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "snapshot_id":       self.snapshot_id,
            "portfolio_id":      self.portfolio_id,
            "actor":             self.actor,
            "payload":           self.payload,
            "framework_version": self.framework_version,
            "occurred_at":       self.occurred_at,
        }


def _make_event(
    event_type:   SnapshotEventType,
    snapshot_id:  str,
    portfolio_id: str,
    actor:        str,
    payload:      Optional[Dict[str, Any]] = None,
) -> RiskSnapshotEvent:
    return RiskSnapshotEvent(
        event_id     = str(uuid.uuid4()),
        event_type   = event_type,
        snapshot_id  = snapshot_id,
        portfolio_id = portfolio_id,
        actor        = actor,
        payload      = payload or {},
    )


def make_snapshot_built(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_BUILT, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_published(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_PUBLISHED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_validated(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_VALIDATED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_superseded(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_SUPERSEDED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_archived(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_ARCHIVED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_failed(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_FAILED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_retrieved(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_RETRIEVED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_expired(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_EXPIRED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_bundled(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_BUNDLED, snapshot_id, portfolio_id, actor, kwargs)


def make_snapshot_stored(
    snapshot_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskSnapshotEvent:
    return _make_event(SnapshotEventType.SNAPSHOT_STORED, snapshot_id, portfolio_id, actor, kwargs)
