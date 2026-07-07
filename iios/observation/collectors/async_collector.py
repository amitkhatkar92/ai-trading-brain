"""
iios/observation/collectors/async_collector.py
==============================================
AsyncCollector — asyncio-based non-blocking collector.

Use for high-concurrency sources: aiohttp, websockets, asyncpg, etc.
``run()`` is synchronous (drives asyncio in a dedicated event loop);
``_do_collect_async()`` is the async coroutine subclasses override.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from ..models.observation import Observation
from .base_collector      import BaseCollector, CollectorConfig
from .collector_constants import ExecutionMode

__all__ = ["AsyncCollector"]


class AsyncCollector(BaseCollector):
    """
    Async collector with a synchronous ``run()`` entry point.

    Subclass and implement:
    - ``_do_collect_async() -> Any``  — async coroutine that fetches data
    - ``_do_normalise(raw) -> list[Observation]``
    """

    def __init__(self, config: CollectorConfig) -> None:
        config.execution_mode = ExecutionMode.ASYNC
        super().__init__(config)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _do_collect(self) -> Any:
        """Run the async coroutine in a fresh event loop."""
        loop = asyncio.new_event_loop()
        try:
            self._loop = loop
            return loop.run_until_complete(self._do_collect_async())
        finally:
            loop.close()
            self._loop = None

    async def _do_collect_async(self) -> Any:
        """
        Override this coroutine to collect data asynchronously.

        Example::

            async def _do_collect_async(self):
                async with aiohttp.ClientSession() as s:
                    async with s.get(self._url) as r:
                        return await r.json()
        """
        return []

    def _do_normalise(self, raw: Any) -> list[Observation]:
        if isinstance(raw, list):
            return [o for o in raw if isinstance(o, Observation)]
        return []
