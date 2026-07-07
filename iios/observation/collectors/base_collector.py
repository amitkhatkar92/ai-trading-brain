"""
iios/observation/collectors/base_collector.py
=============================================
BaseCollector — abstract base for all observation data collectors.

A collector is responsible for acquiring raw data from an external
source and wrapping it as an ``Observation`` for submission to the
Observation Engine pipeline.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    CollectorType,
    ObservationSource,
    ObservationType,
    SYSTEM_OBSERVER,
)
from ..models.observation        import Observation
from ..models.observation_source import ObservationSourceInfo
from ..models.observation_metadata import ObservationMetadata

__all__ = [
    "CollectorConfig",
    "CollectorStats",
    "BaseCollector",
]

_LOG = logging.getLogger("iios.observation.collector")


@dataclass
class CollectorConfig:
    """Configuration for a data collector."""

    name:             str            = ""
    collector_type:   CollectorType  = CollectorType.PULL
    source:           ObservationSource = ObservationSource.UNKNOWN
    obs_type:         ObservationType  = ObservationType.UNKNOWN
    poll_interval_s:  float          = 60.0
    batch_size:       int            = 100
    max_retries:      int            = 3
    timeout_s:        float          = 30.0
    enabled:          bool           = True
    attributes:       dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectorStats:
    """Runtime statistics for a single collector."""

    name:            str    = ""
    total_collected: int    = 0
    total_errors:    int    = 0
    last_run_at:     float  = 0.0
    last_error:      str    = ""
    is_running:      bool   = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":            self.name,
            "total_collected": self.total_collected,
            "total_errors":    self.total_errors,
            "last_run_at":     self.last_run_at,
            "last_error":      self.last_error,
            "is_running":      self.is_running,
        }


class BaseCollector(ABC):
    """Abstract base class for observation data collectors.

    Subclasses must implement ``collect()`` to produce a list of
    raw observations from their data source.

    Usage::

        class MarketDataCollector(BaseCollector):
            def collect(self) -> list[Observation]:
                raw = self._feed.get_latest_quotes()
                return [self._wrap(r) for r in raw]
    """

    def __init__(self, config: CollectorConfig) -> None:
        self._config = config
        self._stats  = CollectorStats(name=config.name)
        self._lock   = threading.RLock()
        self._log    = logging.getLogger(
            f"iios.observation.collector.{config.name or 'base'}"
        )

    @property
    def config(self) -> CollectorConfig:
        return self._config

    @property
    def stats(self) -> CollectorStats:
        return self._stats

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def is_enabled(self) -> bool:
        return self._config.enabled

    @abstractmethod
    def collect(self) -> list[Observation]:
        """Collect and return a list of raw observations."""

    def run(self) -> list[Observation]:
        """Public entry point: collect with error handling and stats."""
        if not self.is_enabled:
            return []

        with self._lock:
            self._stats.is_running = True
            self._stats.last_run_at = time.time()

        try:
            observations = self.collect()
            with self._lock:
                self._stats.total_collected += len(observations)
            return observations
        except Exception as exc:
            with self._lock:
                self._stats.total_errors += 1
                self._stats.last_error = str(exc)
            self._log.exception("Collector '%s' error: %s", self.name, exc)
            return []
        finally:
            with self._lock:
                self._stats.is_running = False

    def _make_source_info(
        self,
        instrument:    str = "",
        exchange:      str = "",
        correlation_id: str = "",
    ) -> ObservationSourceInfo:
        return ObservationSourceInfo(
            source         = self._config.source,
            source_name    = self._config.name,
            submitted_by   = SYSTEM_OBSERVER,
            instrument     = instrument,
            exchange       = exchange,
            correlation_id = correlation_id,
        )

    def _make_observation(
        self,
        content:    Any,
        title:      str           = "",
        instrument: str           = "",
        exchange:   str           = "",
    ) -> Observation:
        src = self._make_source_info(instrument=instrument, exchange=exchange)
        return Observation(
            obs_type    = self._config.obs_type,
            title       = title,
            content     = content,
            source_info = src,
        )
