"""
iios/observation/collectors/batch_collector.py
==============================================
BatchCollector — paginated batch collector with checkpointing.

Use for bulk historical imports, paginated REST APIs, or large DB queries
where data is processed in pages and progress must survive restarts.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation import Observation
from .base_collector      import BaseCollector, CollectorConfig
from .collector_constants import ExecutionMode

__all__ = ["BatchCheckpoint", "BatchCollector"]


@dataclass
class BatchCheckpoint:
    """Tracks pagination progress for recovery after failure."""
    collector_name:  str   = ""
    last_page:       int   = 0
    last_cursor:     str   = ""
    last_timestamp:  float = 0.0
    total_pages:     int   = 0
    items_collected: int   = 0
    saved_at:        float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector_name":  self.collector_name,
            "last_page":       self.last_page,
            "last_cursor":     self.last_cursor,
            "last_timestamp":  self.last_timestamp,
            "total_pages":     self.total_pages,
            "items_collected": self.items_collected,
            "saved_at":        self.saved_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BatchCheckpoint":
        return cls(
            collector_name  = d.get("collector_name", ""),
            last_page       = int(d.get("last_page", 0)),
            last_cursor     = str(d.get("last_cursor", "")),
            last_timestamp  = float(d.get("last_timestamp", 0.0)),
            total_pages     = int(d.get("total_pages", 0)),
            items_collected = int(d.get("items_collected", 0)),
            saved_at        = float(d.get("saved_at", 0.0)),
        )


class BatchCollector(BaseCollector):
    """
    Collector that paginates through a dataset and checkpoints progress.

    Subclass and implement:
    - ``_do_collect_batch(page, cursor) -> (items, next_cursor, has_more)``
    - ``_do_normalise_item(item) -> Optional[Observation]``
    """

    def __init__(
        self,
        config:    CollectorConfig,
        page_size: int = 0,
    ) -> None:
        config.execution_mode = ExecutionMode.BATCH
        super().__init__(config)
        self._page_size   = page_size or config.batch_size
        self._bcheckpoint = BatchCheckpoint(collector_name=config.name)

    def _do_collect(self) -> Any:
        """Paginate through the dataset, accumulating all items."""
        all_items: list[Any] = []
        cursor    = self._bcheckpoint.last_cursor
        page      = self._bcheckpoint.last_page
        collected = 0

        while True:
            items, next_cursor, has_more = self._do_collect_batch(page, cursor)
            all_items.extend(items)
            collected += len(items)
            page      += 1
            cursor     = next_cursor

            self._bcheckpoint.last_page       = page
            self._bcheckpoint.last_cursor     = cursor
            self._bcheckpoint.items_collected += len(items)
            self.save_checkpoint(self._bcheckpoint.to_dict())

            if not has_more or collected >= self.config.batch_size:
                break

        # Reset cursor after a complete pass
        self._bcheckpoint.last_page   = 0
        self._bcheckpoint.last_cursor = ""
        return all_items

    def _do_normalise(self, raw: Any) -> list[Observation]:
        if not isinstance(raw, list):
            return []
        result: list[Observation] = []
        for item in raw:
            obs = self._do_normalise_item(item)
            if obs is not None:
                result.append(obs)
        return result

    def _do_collect_batch(
        self,
        page:   int,
        cursor: str,
    ) -> tuple[list[Any], str, bool]:
        """
        Override to fetch one page of data.

        Returns:
            (items: list, next_cursor: str, has_more: bool)
        """
        return [], "", False

    def _do_normalise_item(self, item: Any) -> Optional[Observation]:
        """Override to convert a single batch item to an Observation."""
        if isinstance(item, Observation):
            return item
        return None

    @property
    def checkpoint(self) -> BatchCheckpoint:
        return self._bcheckpoint

    def restore_checkpoint(self, data: dict[str, Any]) -> None:
        """Restore pagination state from a previously saved checkpoint."""
        self._bcheckpoint = BatchCheckpoint.from_dict(data)
