"""
iios/observation/observation_factory.py
=======================================
ObservationFactory — constructs Observation objects from raw inputs.

The factory is the preferred way to create observations because it:
1. Generates unique IDs deterministically
2. Sets sensible defaults
3. Validates required fields early
4. Assigns source info from collector config
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from typing import Any, Optional

from .observation_constants import (
    DEFAULT_CONFIDENCE,
    OBSERVATION_NAMESPACE,
    SYSTEM_OBSERVER,
    ObservationDomain,
    ObservationPriority,
    ObservationSource,
    ObservationType,
)
from .models.observation          import Observation
from .models.observation_identifier import ObservationId
from .models.observation_source   import ObservationSourceInfo
from .models.observation_metadata import ObservationMetadata

__all__ = ["ObservationFactory", "get_observation_factory", "reset_observation_factory"]

_lock     = threading.Lock()
_factory: Optional["ObservationFactory"] = None


class ObservationFactory:
    """Creates observation objects from structured or raw inputs."""

    def create(
        self,
        content:    Any,
        obs_type:   ObservationType          = ObservationType.UNKNOWN,
        title:      str                      = "",
        source:     ObservationSource        = ObservationSource.SYSTEM,
        domain:     ObservationDomain        = ObservationDomain.GENERAL,
        priority:   ObservationPriority      = ObservationPriority.MEDIUM,
        confidence: float                    = DEFAULT_CONFIDENCE,
        instrument: str                      = "",
        exchange:   str                      = "",
        tags:       Optional[list[str]]      = None,
        actor:      str                      = SYSTEM_OBSERVER,
        attributes: Optional[dict[str, Any]] = None,
        ttl_seconds: int                     = 86_400,
    ) -> Observation:
        src = ObservationSourceInfo(
            source       = source,
            submitted_by = actor,
            instrument   = instrument,
            exchange     = exchange,
        )
        meta = ObservationMetadata(
            created_by  = actor,
            domain      = domain,
            source      = source,
            priority    = priority,
            confidence  = confidence,
            tags        = list(tags or []),
            attributes  = dict(attributes or {}),
            ttl_seconds = ttl_seconds,
        )
        obs = Observation(
            obs_type    = obs_type,
            title       = title,
            content     = content,
            source_info = src,
            metadata    = meta,
        )
        return obs

    def create_market_data(
        self,
        content:    dict[str, Any],
        instrument: str,
        exchange:   str           = "NSE",
        source:     ObservationSource = ObservationSource.YFINANCE,
        actor:      str           = SYSTEM_OBSERVER,
    ) -> Observation:
        return self.create(
            content    = content,
            obs_type   = ObservationType.MARKET_DATA,
            title      = f"Market data: {instrument}",
            source     = source,
            domain     = ObservationDomain.MARKET,
            priority   = ObservationPriority.HIGH,
            confidence = 0.90,
            instrument = instrument,
            exchange   = exchange,
            tags       = [instrument.lower(), exchange.lower(), "market_data"],
            actor      = actor,
        )

    def create_signal(
        self,
        content:    dict[str, Any],
        instrument: str,
        confidence: float          = 0.70,
        actor:      str            = SYSTEM_OBSERVER,
    ) -> Observation:
        return self.create(
            content    = content,
            obs_type   = ObservationType.SIGNAL,
            title      = f"Signal: {instrument}",
            source     = ObservationSource.INTERNAL_AGENT,
            domain     = ObservationDomain.TRADING,
            priority   = ObservationPriority.HIGH,
            confidence = confidence,
            instrument = instrument,
            tags       = [instrument.lower(), "signal"],
            actor      = actor,
        )

    def create_system_event(
        self,
        content:    Any,
        title:      str  = "System event",
        actor:      str  = SYSTEM_OBSERVER,
    ) -> Observation:
        return self.create(
            content    = content,
            obs_type   = ObservationType.SYSTEM_EVENT,
            title      = title,
            source     = ObservationSource.SYSTEM,
            domain     = ObservationDomain.SYSTEM,
            priority   = ObservationPriority.MEDIUM,
            confidence = 1.00,
            actor      = actor,
        )

    def create_batch(
        self,
        items:    list[dict[str, Any]],
        actor:    str = SYSTEM_OBSERVER,
    ) -> list[Observation]:
        """Create multiple observations from a list of dicts.

        Each dict must have a ``content`` key; all other keys map to
        ``create()`` arguments.
        """
        out: list[Observation] = []
        for item in items:
            kw = dict(item)
            content = kw.pop("content", None)
            kw.setdefault("actor", actor)
            out.append(self.create(content=content, **kw))
        return out


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_factory() -> ObservationFactory:
    global _factory
    if _factory is None:
        with _lock:
            if _factory is None:
                _factory = ObservationFactory()
    return _factory


def reset_observation_factory() -> None:
    global _factory
    with _lock:
        _factory = None
