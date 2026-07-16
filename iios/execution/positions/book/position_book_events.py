"""iios/execution/positions/book/position_book_events.py
==================================================
BookEvent — immutable domain event emitted by the Position Book.

Factory functions produce one event per book milestone:
  POSITION_ADDED, POSITION_UPDATED, POSITION_REMOVED,
  SNAPSHOT_CREATED, SNAPSHOT_PUBLISHED, BOOK_VALIDATED

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import ACTOR_BOOK, BookEventType, VERSION


@dataclass(frozen=True)
class BookEvent:
    """
    Immutable domain event emitted by the Position Book.

    Events are append-only and never mutated after creation.
    """

    event_id:    str
    event_type:  BookEventType
    position_id: str
    portfolio_id: str
    strategy_id: str
    actor:       str
    occurred_at: float
    version:     str = VERSION
    metadata:    Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "position_id": self.position_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "metadata":    dict(self.metadata),
        }


# ── Private helper ────────────────────────────────────────────────────────────

def _book_evt(
    event_type:  BookEventType,
    position_id: str = "",
    portfolio_id: str = "",
    strategy_id: str = "",
    actor:       str = ACTOR_BOOK,
    metadata:    Dict[str, Any] | None = None,
) -> BookEvent:
    return BookEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_position_added_event(
    position_id: str,
    portfolio_id: str = "",
    strategy_id: str = "",
    actor:       str = ACTOR_BOOK,
    metadata:    Dict[str, Any] | None = None,
) -> BookEvent:
    return _book_evt(
        BookEventType.POSITION_ADDED,
        position_id, portfolio_id, strategy_id, actor, metadata,
    )


def make_position_updated_event(
    position_id: str,
    portfolio_id: str = "",
    strategy_id: str = "",
    actor:       str = ACTOR_BOOK,
    metadata:    Dict[str, Any] | None = None,
) -> BookEvent:
    return _book_evt(
        BookEventType.POSITION_UPDATED,
        position_id, portfolio_id, strategy_id, actor, metadata,
    )


def make_position_removed_event(
    position_id: str,
    portfolio_id: str = "",
    strategy_id: str = "",
    actor:       str = ACTOR_BOOK,
    metadata:    Dict[str, Any] | None = None,
) -> BookEvent:
    return _book_evt(
        BookEventType.POSITION_REMOVED,
        position_id, portfolio_id, strategy_id, actor, metadata,
    )


def make_snapshot_created_event(
    actor:    str = ACTOR_BOOK,
    metadata: Dict[str, Any] | None = None,
) -> BookEvent:
    return _book_evt(BookEventType.SNAPSHOT_CREATED, actor=actor, metadata=metadata)


def make_snapshot_published_event(
    actor:    str = ACTOR_BOOK,
    metadata: Dict[str, Any] | None = None,
) -> BookEvent:
    return _book_evt(BookEventType.SNAPSHOT_PUBLISHED, actor=actor, metadata=metadata)


def make_book_validated_event(
    actor:    str = ACTOR_BOOK,
    metadata: Dict[str, Any] | None = None,
) -> BookEvent:
    return _book_evt(BookEventType.BOOK_VALIDATED, actor=actor, metadata=metadata)
