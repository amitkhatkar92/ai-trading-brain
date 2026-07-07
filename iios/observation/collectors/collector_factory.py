"""
iios/observation/collectors/collector_factory.py
================================================
CollectorFactory — creates and configures collector instances.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional, Type

from ..observation_constants import CollectorType, ObservationSource, ObservationType
from .base_collector         import BaseCollector, CollectorConfig, RetryPolicy
from .sync_collector         import SyncCollector
from .async_collector        import AsyncCollector
from .stream_collector       import StreamCollector
from .batch_collector        import BatchCollector
from .scheduled_collector    import ScheduledCollector, ScheduleConfig
from .event_collector        import EventCollector
from .collector_constants    import CollectorCategory, ExecutionMode, RetryStrategy, ScheduleType
from .collector_exceptions   import CollectorConfigError

__all__ = ["CollectorFactory", "get_collector_factory", "reset_collector_factory"]

_LOG  = logging.getLogger("iios.collector.factory")
_lock = threading.Lock()
_factory: Optional["CollectorFactory"] = None

_TYPE_MAP: dict[str, Type[BaseCollector]] = {
    "sync":      SyncCollector,
    "async":     AsyncCollector,
    "stream":    StreamCollector,
    "batch":     BatchCollector,
    "scheduled": ScheduledCollector,
    "event":     EventCollector,
}


class CollectorFactory:
    """
    Creates collector instances from typed config or plain dicts.

    Supports plugin registration via ``register_type(name, cls)``.
    """

    def __init__(self) -> None:
        self._custom: dict[str, Type[BaseCollector]] = {}

    def register_type(self, type_name: str, cls: Type[BaseCollector]) -> None:
        """Register a custom collector class under *type_name*."""
        self._custom[type_name.lower()] = cls

    def build(
        self,
        cls:    Type[BaseCollector],
        config: CollectorConfig,
        **kwargs: Any,
    ) -> BaseCollector:
        """Instantiate *cls* with *config* and optional kwargs."""
        if not config.name:
            raise CollectorConfigError("CollectorConfig must have a name.")
        return cls(config, **kwargs)

    def from_dict(self, d: dict[str, Any]) -> BaseCollector:
        """
        Build a collector from a plain dict.

        Required keys: ``name``, ``type`` (sync|async|stream|batch|scheduled|event|<custom>).
        """
        name = d.get("name", "")
        if not name:
            raise CollectorConfigError("Collector config dict must have 'name'.")

        collector_type = str(d.get("type", "sync")).lower()

        try:
            source = ObservationSource[d.get("source", "UNKNOWN").upper()]
        except KeyError:
            source = ObservationSource.UNKNOWN
        try:
            obs_type = ObservationType[d.get("obs_type", "UNKNOWN").upper()]
        except KeyError:
            obs_type = ObservationType.UNKNOWN
        try:
            category = CollectorCategory[d.get("category", "MARKET_DATA").upper()]
        except KeyError:
            category = CollectorCategory.MARKET_DATA
        try:
            col_type = CollectorType[d.get("collector_type", "PULL").upper()]
        except KeyError:
            col_type = CollectorType.PULL
        try:
            retry_strat = RetryStrategy[d.get("retry_strategy", "EXPONENTIAL").upper()]
        except KeyError:
            retry_strat = RetryStrategy.EXPONENTIAL

        config = CollectorConfig(
            name            = name,
            collector_type  = col_type,
            category        = category,
            source          = source,
            obs_type        = obs_type,
            poll_interval_s = float(d.get("poll_interval_s", 60.0)),
            batch_size      = int(d.get("batch_size", 100)),
            timeout_s       = float(d.get("timeout_s", 30.0)),
            enabled         = bool(d.get("enabled", True)),
            instruments     = list(d.get("instruments", [])),
            exchanges       = list(d.get("exchanges", [])),
            attributes      = dict(d.get("attributes", {})),
            retry_policy    = RetryPolicy(
                max_retries = int(d.get("max_retries", 3)),
                strategy    = retry_strat,
            ),
        )

        # Custom types take priority
        cls = self._custom.get(collector_type) or _TYPE_MAP.get(collector_type)
        if cls is None:
            raise CollectorConfigError(
                f"Unknown collector type: {collector_type!r}. "
                f"Valid: {list(_TYPE_MAP)}"
            )
        return cls(config)

    def make_sync(
        self,
        name:        str,
        source:      ObservationSource = ObservationSource.UNKNOWN,
        obs_type:    ObservationType   = ObservationType.UNKNOWN,
        category:    CollectorCategory = CollectorCategory.MARKET_DATA,
        instruments: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> SyncCollector:
        config = CollectorConfig(
            name        = name,
            source      = source,
            obs_type    = obs_type,
            category    = category,
            instruments = instruments or [],
        )
        for k, v in kwargs.items():
            if hasattr(config, k):
                setattr(config, k, v)
        return SyncCollector(config)

    def make_scheduled(
        self,
        name:        str,
        interval_s:  float              = 60.0,
        source:      ObservationSource  = ObservationSource.UNKNOWN,
        obs_type:    ObservationType    = ObservationType.UNKNOWN,
        category:    CollectorCategory  = CollectorCategory.MARKET_DATA,
        instruments: Optional[list[str]] = None,
    ) -> ScheduledCollector:
        config   = CollectorConfig(
            name        = name,
            source      = source,
            obs_type    = obs_type,
            category    = category,
            instruments = instruments or [],
        )
        schedule = ScheduleConfig(
            schedule_type = ScheduleType.INTERVAL,
            interval_s    = interval_s,
        )
        return ScheduledCollector(config, schedule=schedule)

    def make_event(
        self,
        name:     str,
        source:   ObservationSource = ObservationSource.UNKNOWN,
        obs_type: ObservationType   = ObservationType.UNKNOWN,
        category: CollectorCategory = CollectorCategory.MARKET_DATA,
    ) -> EventCollector:
        config = CollectorConfig(
            name     = name,
            source   = source,
            obs_type = obs_type,
            category = category,
        )
        return EventCollector(config)

    def make_batch(
        self,
        name:      str,
        source:    ObservationSource = ObservationSource.UNKNOWN,
        obs_type:  ObservationType   = ObservationType.UNKNOWN,
        category:  CollectorCategory = CollectorCategory.MARKET_DATA,
        page_size: int               = 100,
    ) -> BatchCollector:
        config = CollectorConfig(
            name       = name,
            source     = source,
            obs_type   = obs_type,
            category   = category,
            batch_size = page_size,
        )
        return BatchCollector(config, page_size=page_size)


def get_collector_factory() -> CollectorFactory:
    global _factory
    if _factory is None:
        with _lock:
            if _factory is None:
                _factory = CollectorFactory()
    return _factory


def reset_collector_factory() -> None:
    global _factory
    with _lock:
        _factory = None
