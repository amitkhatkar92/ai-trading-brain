"""iios/execution/monitoring/history/execution_history.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.monitoring.core.execution_record import ExecutionRecord


class ExecutionHistory:
    """
    Append-only store of completed ExecutionRecords for historical analysis.
    """

    def __init__(self, max_records: int = 100_000) -> None:
        self._records:    list[ExecutionRecord]   = []
        self._by_broker:  dict[str, list[ExecutionRecord]] = {}
        self._by_symbol:  dict[str, list[ExecutionRecord]] = {}
        self._max_records = max_records
        self._lock        = threading.RLock()

    def append(self, record: ExecutionRecord) -> None:
        with self._lock:
            if len(self._records) >= self._max_records:
                self._records.pop(0)   # simple FIFO eviction
            self._records.append(record)
            self._by_broker.setdefault(record.broker_id, []).append(record)
            self._by_symbol.setdefault(record.symbol, []).append(record)

    def all_records(self) -> list[ExecutionRecord]:
        with self._lock:
            return list(self._records)

    def for_broker(self, broker_id: str) -> list[ExecutionRecord]:
        with self._lock:
            return list(self._by_broker.get(broker_id, []))

    def for_symbol(self, symbol: str) -> list[ExecutionRecord]:
        with self._lock:
            return list(self._by_symbol.get(symbol, []))

    def size(self) -> int:
        with self._lock:
            return len(self._records)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_records":    len(self._records),
                "brokers":          list(self._by_broker.keys()),
                "symbols":          list(self._by_symbol.keys()),
                "max_records":      self._max_records,
            }
