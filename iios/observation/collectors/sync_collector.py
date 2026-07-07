"""
iios/observation/collectors/sync_collector.py
=============================================
SyncCollector — synchronous (blocking) data collector.

Use for PULL-based REST APIs, database queries, or file reads
where single-threaded blocking I/O is acceptable.
"""
from __future__ import annotations

from typing import Any

from ..models.observation import Observation
from .base_collector      import BaseCollector, CollectorConfig
from .collector_constants import ExecutionMode

__all__ = ["SyncCollector"]


class SyncCollector(BaseCollector):
    """
    Synchronous collector. All I/O blocks the calling thread.

    Subclass and implement:
    - ``_do_collect() -> Any``           — perform blocking fetch
    - ``_do_normalise(raw) -> list[Observation]`` — convert raw data
    """

    def __init__(self, config: CollectorConfig) -> None:
        config.execution_mode = ExecutionMode.SYNC
        super().__init__(config)

    def _do_collect(self) -> Any:
        """Override to perform the synchronous data fetch."""
        return []

    def _do_normalise(self, raw: Any) -> list[Observation]:
        """Override to convert raw data to Observation objects."""
        if isinstance(raw, list):
            return [o for o in raw if isinstance(o, Observation)]
        return []
