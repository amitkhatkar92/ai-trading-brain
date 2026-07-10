"""iios/integration/news/alternative/alternative_data_engine.py

Manages alternative dataset registration, ingestion, and retrieval.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from iios.integration.news.alternative.alternative_dataset import AlternativeDataset, AlternativeEvent
from iios.integration.news.alternative.alternative_source  import AlternativeSource
from iios.integration.news.alternative.alternative_statistics import AlternativeStatistics
from iios.integration.news.news_constants  import AlternativeDataType
from iios.integration.news.news_exceptions import AlternativeDataError, AlternativeDatasetNotFoundError

logger = logging.getLogger(__name__)


class AlternativeDataEngine:
    """
    Registry and ingestion engine for all alternative data.

    Any future alternative data type (satellite imagery scores, credit card
    aggregates, ESG ratings, …) registers a dataset here. The engine stores
    records and exposes query interfaces to the rest of IIOS.
    """

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._datasets: dict[str, AlternativeDataset] = {}
        self._sources:  dict[str, AlternativeSource]  = {}
        self._stats: dict[str, int] = {
            "datasets_registered": 0,
            "records_ingested":    0,
        }

    # ── Dataset management ────────────────────────────────────────────────────

    def register_dataset(self, dataset: AlternativeDataset) -> None:
        with self._lock:
            self._datasets[dataset.dataset_id] = dataset
            self._stats["datasets_registered"] += 1
            logger.info("[AltDataEngine] Registered dataset '%s' (%s).", dataset.name, dataset.alt_type.value)

    def unregister_dataset(self, dataset_id: str) -> None:
        with self._lock:
            if dataset_id not in self._datasets:
                raise AlternativeDatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            del self._datasets[dataset_id]

    def get_dataset(self, dataset_id: str) -> AlternativeDataset:
        with self._lock:
            ds = self._datasets.get(dataset_id)
            if ds is None:
                raise AlternativeDatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            return ds

    # ── Source management ─────────────────────────────────────────────────────

    def register_source(self, source: AlternativeSource) -> None:
        with self._lock:
            self._sources[source.source_id] = source

    def get_sources_by_type(self, alt_type: AlternativeDataType) -> list[AlternativeSource]:
        with self._lock:
            return [s for s in self._sources.values() if s.alt_type == alt_type]

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest(self, dataset_id: str, event: AlternativeEvent) -> None:
        """Add one alternative event to an existing dataset."""
        with self._lock:
            ds = self._datasets.get(dataset_id)
            if ds is None:
                raise AlternativeDatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            ds.add_record(event)
            self._stats["records_ingested"] += 1

    def ingest_batch(self, dataset_id: str, events: list[AlternativeEvent]) -> int:
        """Batch ingest. Returns number of records ingested."""
        count = 0
        with self._lock:
            ds = self._datasets.get(dataset_id)
            if ds is None:
                raise AlternativeDatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            for evt in events:
                ds.add_record(evt)
                count += 1
            self._stats["records_ingested"] += count
        return count

    # ── Query ─────────────────────────────────────────────────────────────────

    def query_by_symbol(self, symbol: str, alt_type: AlternativeDataType | None = None) -> list[AlternativeEvent]:
        with self._lock:
            results = []
            for ds in self._datasets.values():
                if alt_type and ds.alt_type != alt_type:
                    continue
                results.extend(e for e in ds.records if e.symbol == symbol)
            return sorted(results, key=lambda e: e.timestamp, reverse=True)

    def query_by_type(self, alt_type: AlternativeDataType) -> list[AlternativeDataset]:
        with self._lock:
            return [ds for ds in self._datasets.values() if ds.alt_type == alt_type]

    # ── Statistics ────────────────────────────────────────────────────────────

    def compute_statistics(self, dataset_id: str) -> AlternativeStatistics:
        with self._lock:
            ds = self._datasets.get(dataset_id)
            if ds is None:
                raise AlternativeDatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            vals = [e.value for e in ds.records if e.value != 0.0]
            syms = {e.symbol for e in ds.records}
            return AlternativeStatistics(
                dataset_id     = dataset_id,
                alt_type       = ds.alt_type,
                period_start   = ds.period_start,
                period_end     = ds.period_end,
                total_records  = ds.record_count,
                unique_symbols = len(syms),
                avg_value      = sum(vals) / len(vals) if vals else 0.0,
                min_value      = min(vals) if vals else 0.0,
                max_value      = max(vals) if vals else 0.0,
            )

    def dataset_count(self) -> int:
        with self._lock:
            return len(self._datasets)

    def stats(self) -> dict[str, Any]:
        return {**self._stats, "dataset_count": self.dataset_count()}
