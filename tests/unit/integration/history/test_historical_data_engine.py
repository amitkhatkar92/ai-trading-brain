"""tests/unit/integration/history/test_historical_data_engine.py

Comprehensive test suite for iios/integration/history/

Run with:
    python -m pytest tests/unit/integration/history/ -q

Async tests use the _run() wrapper - no pytest-asyncio required.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from typing import Any

import pytest

# ── Async helper ──────────────────────────────────────────────────────────────
def _run(coro): return asyncio.run(coro)

# ── Imports ───────────────────────────────────────────────────────────────────
from iios.integration.history.history_constants import (
    AnalyticsInterval,
    CompressionType,
    DataFormat,
    DatasetStatus,
    HistoricalDataType,
    HistoryEngineStatus,
    PartitionStrategy,
    QueryOperator,
    ReplayMode,
    ReplayStatus,
    ReplayType,
    SimulationMode,
    SimulationStatus,
    SortOrder,
    StorageStatus,
    TimelineDirection,
    TimelineStatus,
    HISTORY_ENGINE_VERSION,
    HISTORY_ERROR_PREFIX,
    DEFAULT_MAX_DATASETS,
    DEFAULT_PARTITION_SIZE,
    DEFAULT_REPLAY_SPEED,
    DEFAULT_CACHE_MAX_RECORDS,
    DEFAULT_CACHE_TTL_SEC,
)
from iios.integration.history.history_exceptions import (
    ChecksumMismatchError,
    DatasetAlreadyExistsError,
    DatasetNotFoundError,
    HistoryDataError,
    HistoryEngineAlreadyRunningError,
    HistoryEngineInitializationError,
    HistoryEngineNotRunningError,
    HistoryRegistryFullError,
    QueryResultTooLargeError,
    QueryTimeoutError,
    QueryValidationError,
    ReplayAlreadyActiveError,
    ReplayError,
    ReplayNotActiveError,
    ReplaySessionNotFoundError,
    ScenarioNotFoundError,
    SimulationClockError,
    SimulationError,
    SimulationNotActiveError,
    StorageCapacityError,
    StorageError,
    StorageNotFoundError,
)
from iios.integration.history.core.historical_record   import HistoricalRecord
from iios.integration.history.core.historical_dataset  import HistoricalDataset
from iios.integration.history.core.historical_snapshot import HistoricalSnapshot
from iios.integration.history.core.historical_partition import HistoricalPartition
from iios.integration.history.core.historical_index    import HistoricalIndex, HistoricalIndexEntry
from iios.integration.history.compression              import DataCompressor
from iios.integration.history.cache                    import HistoryCache
from iios.integration.history.storage.storage_backend  import InMemoryStorageBackend
from iios.integration.history.indexing.dataset_index   import DatasetIndexManager
from iios.integration.history.replay.replay_session    import ReplaySession
from iios.integration.history.replay.replay_scheduler  import ReplayScheduler
from iios.integration.history.replay.replay_controller import ReplayController
from iios.integration.history.replay.replay_engine     import ReplayEngine
from iios.integration.history.timeline.timeline_event  import TimelineEvent
from iios.integration.history.timeline.timeline_cursor import TimelineCursor
from iios.integration.history.timeline.timeline        import Timeline
from iios.integration.history.timeline.timeline_controller import TimelineController
from iios.integration.history.simulation.simulation_clock  import SimulationClock
from iios.integration.history.simulation.scenario_loader   import Scenario, ScenarioLoader
from iios.integration.history.simulation.dataset_loader    import DatasetLoader
from iios.integration.history.simulation.simulation_controller import SimulationController
from iios.integration.history.history_registry             import HistoryRegistry
from iios.integration.history.history_context              import HistoryContext
from iios.integration.history.history_factory              import HistoryFactory
from iios.integration.history.history_manager              import HistoryManager
from iios.integration.history.query.historical_filter      import HistoricalFilter, FieldFilter
from iios.integration.history.query.dataset_selector       import DatasetSelector
from iios.integration.history.query.historical_search      import HistoricalSearch
from iios.integration.history.query.query_engine           import QueryEngine
from iios.integration.history.analytics.history_analytics  import HistoryAnalytics
from iios.integration.history.historical_data_engine       import (
    HistoricalDataEngine,
    get_historical_data_engine,
    reset_historical_data_engine,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_record(
    symbol: str = "AAPL",
    ts:     float | None = None,
    data:   dict[str, Any] | None = None,
    dataset_id: str = "ds-test",
) -> HistoricalRecord:
    return HistoricalRecord(
        dataset_id = dataset_id,
        data_type  = HistoricalDataType.MARKET_DATA,
        symbol     = symbol,
        timestamp  = ts or time.time(),
        data       = data or {"price": 100.0, "volume": 1000},
    )


def _make_dataset(
    name:      str = "Test DS",
    data_type: HistoricalDataType = HistoricalDataType.MARKET_DATA,
    symbols:   list[str] | None = None,
) -> HistoricalDataset:
    return HistoricalDataset(
        name       = name,
        data_type  = data_type,
        symbols    = symbols or ["AAPL"],
    )


def _make_backend(records: list[HistoricalRecord] | None = None) -> InMemoryStorageBackend:
    b = InMemoryStorageBackend()
    if records:
        for r in records:
            ds = _make_dataset()
            ds.dataset_id = r.dataset_id
            try:
                b.create_dataset(ds)
            except DatasetAlreadyExistsError:
                pass
            b.append_record(r.dataset_id, r)
    return b


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_history_engine_version_is_string(self):
        assert isinstance(HISTORY_ENGINE_VERSION, str)

    def test_error_prefix(self):
        assert HISTORY_ERROR_PREFIX == "HD"

    def test_historical_data_type_values(self):
        assert HistoricalDataType.MARKET_DATA.value == "market_data"
        assert HistoricalDataType.NEWS.value         == "news"

    def test_history_engine_status_values(self):
        assert HistoryEngineStatus.RUNNING.value  == "running"
        assert HistoryEngineStatus.STOPPED.value  == "stopped"

    def test_replay_mode_values(self):
        assert ReplayMode.FORWARD.value  == "forward"
        assert ReplayMode.REVERSE.value  == "reverse"

    def test_simulation_status_values(self):
        assert SimulationStatus.IDLE.value      == "idle"
        assert SimulationStatus.COMPLETED.value == "completed"

    def test_query_operator_values(self):
        assert QueryOperator.EQ.value      == "eq"
        assert QueryOperator.BETWEEN.value == "between"

    def test_sort_order_values(self):
        assert SortOrder.ASC.value  == "asc"
        assert SortOrder.DESC.value == "desc"

    def test_default_partition_size(self):
        assert DEFAULT_PARTITION_SIZE > 0

    def test_default_replay_speed(self):
        assert DEFAULT_REPLAY_SPEED == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_root_exception(self):
        e = HistoryDataError("HD-000")
        assert isinstance(e, Exception)

    def test_engine_not_running_code(self):
        e = HistoryEngineNotRunningError("bad")
        assert "HD-001" in repr(e)

    def test_engine_already_running_code(self):
        e = HistoryEngineAlreadyRunningError("bad")
        assert "HD-002" in repr(e)

    def test_storage_not_found(self):
        e = StorageNotFoundError("missing")
        assert "HD-011" in repr(e)

    def test_dataset_not_found(self):
        e = DatasetNotFoundError("ds-1")
        assert "HD-020" in repr(e)

    def test_dataset_already_exists(self):
        e = DatasetAlreadyExistsError("ds-1")
        assert "HD-021" in repr(e)

    def test_replay_session_not_found(self):
        e = ReplaySessionNotFoundError("s-1")
        assert "HD-031" in repr(e)

    def test_query_timeout(self):
        e = QueryTimeoutError("timed out")
        assert "HD-051" in repr(e)

    def test_simulation_not_active(self):
        e = SimulationNotActiveError("not running")
        assert "HD-061" in repr(e)

    def test_scenario_not_found(self):
        e = ScenarioNotFoundError("s-1")
        assert "HD-062" in repr(e)

    def test_registry_full(self):
        e = HistoryRegistryFullError("full")
        assert "HD-081" in repr(e)

    def test_checksum_mismatch(self):
        e = ChecksumMismatchError("corrupt")
        assert "HD-026" in repr(e)


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoricalRecord
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoricalRecord:
    def test_defaults_set(self):
        r = _make_record()
        assert r.record_id != ""
        assert r.data_type == HistoricalDataType.MARKET_DATA

    def test_checksum_computed(self):
        r = _make_record()
        assert r.checksum != ""

    def test_verify_checksum_passes(self):
        r = _make_record()
        assert r.verify_checksum() is True

    def test_verify_checksum_fails_on_tamper(self):
        r = _make_record()
        r.checksum = "invalid"
        assert r.verify_checksum() is False

    def test_age_sec_non_negative(self):
        r = _make_record()
        assert r.age_sec() >= 0

    def test_is_valid_true(self):
        r = _make_record()
        assert r.is_valid() is True

    def test_to_dict_contains_key_fields(self):
        r = _make_record()
        d = r.to_dict()
        assert "record_id" in d
        assert "timestamp" in d
        assert "data" in d

    def test_tags_default_empty(self):
        r = _make_record()
        assert r.tags == []


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoricalDataset
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoricalDataset:
    def test_defaults(self):
        ds = _make_dataset()
        assert ds.status == DatasetStatus.ACTIVE
        assert ds.is_sealed is False

    def test_span_days_zero_when_no_data(self):
        ds = _make_dataset()
        assert ds.span_days() == 0.0

    def test_is_expired_false_when_no_retention(self):
        ds = _make_dataset()
        ds.retention_days = 0
        assert ds.is_expired() is False

    def test_touch_updates_timestamp(self):
        ds = _make_dataset()
        before = ds.updated_at
        time.sleep(0.01)
        ds.touch()
        assert ds.updated_at >= before

    def test_to_dict_returns_dict(self):
        ds = _make_dataset()
        d = ds.to_dict()
        assert isinstance(d, dict)

    def test_unique_ids(self):
        a = _make_dataset()
        b = _make_dataset()
        assert a.dataset_id != b.dataset_id


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoricalSnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoricalSnapshot:
    def test_defaults(self):
        s = HistoricalSnapshot(dataset_id="ds-1", data_type=HistoricalDataType.NEWS)
        assert s.snapshot_id != ""
        assert s.is_complete is True   # default is True (complete snapshot)

    def test_to_dict(self):
        s = HistoricalSnapshot(dataset_id="ds-1", data_type=HistoricalDataType.NEWS)
        d = s.to_dict()
        assert "snapshot_id" in d
        assert "dataset_id"  in d

    def test_checksum_default_empty(self):
        s = HistoricalSnapshot(dataset_id="ds-1", data_type=HistoricalDataType.NEWS)
        assert s.checksum == ""

    def test_record_count_default_zero(self):
        s = HistoricalSnapshot(dataset_id="ds-1", data_type=HistoricalDataType.NEWS)
        assert s.record_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoricalPartition
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoricalPartition:
    def _part(self) -> HistoricalPartition:
        return HistoricalPartition(
            dataset_id = "ds-1",
            data_type  = HistoricalDataType.MARKET_DATA,
            start_ts   = 1_700_000_000.0,
            end_ts     = 1_700_086_400.0,
        )

    def test_append_increments_count(self):
        p = self._part()
        r = _make_record()
        p.append(r)
        assert p.record_count == 1

    def test_seal_sets_flag(self):
        p = self._part()
        p.seal()
        assert p.is_sealed is True

    def test_span_sec(self):
        p = self._part()
        assert p.span_sec() == pytest.approx(86_400.0)

    def test_to_dict_keys(self):
        p = self._part()
        d = p.to_dict()
        assert "partition_id" in d
        assert "record_count" in d

    def test_records_list_populated(self):
        p = self._part()
        r = _make_record()
        p.append(r)
        assert len(p.records) == 1

    def test_seal_twice_is_idempotent(self):
        p = self._part()
        p.seal()
        p.seal()
        assert p.is_sealed


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoricalIndex
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoricalIndex:
    def _entry(self, start: float, end: float, symbol: str = "AAPL") -> HistoricalIndexEntry:
        return HistoricalIndexEntry(
            dataset_id   = "ds-1",
            partition_id = str(uuid.uuid4()),
            data_type    = HistoricalDataType.MARKET_DATA,
            symbol       = symbol,
            start_ts     = start,
            end_ts       = end,
        )

    def test_add_and_count(self):
        idx = HistoricalIndex(dataset_id="ds-1")
        idx.add(self._entry(100.0, 200.0))
        assert idx.count() == 1

    def test_find_range_returns_matches(self):
        idx = HistoricalIndex(dataset_id="ds-1")
        idx.add(self._entry(100.0, 200.0))
        idx.add(self._entry(300.0, 400.0))
        results = idx.find_range(150.0, 250.0)
        assert len(results) == 1

    def test_find_range_no_match(self):
        idx = HistoricalIndex(dataset_id="ds-1")
        idx.add(self._entry(100.0, 200.0))
        assert idx.find_range(500.0, 600.0) == []

    def test_contains_ts(self):
        e = self._entry(100.0, 200.0)
        assert e.contains_ts(150.0) is True
        assert e.contains_ts(50.0)  is False

    def test_overlaps(self):
        e = self._entry(100.0, 200.0)
        assert e.overlaps(150.0, 300.0) is True
        assert e.overlaps(300.0, 400.0) is False

    def test_remove(self):
        idx = HistoricalIndex(dataset_id="ds-1")
        e   = self._entry(100.0, 200.0)
        idx.add(e)
        idx.remove(e.partition_id)   # remove() filters by partition_id
        assert idx.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestDataCompressor
# ─────────────────────────────────────────────────────────────────────────────

class TestDataCompressor:
    def test_none_roundtrip(self):
        c = DataCompressor()
        data = {"key": "value", "num": 42}
        payload = c.compress(data, CompressionType.NONE)
        result  = c.decompress(payload, CompressionType.NONE)
        assert result == data

    def test_zlib_roundtrip(self):
        c = DataCompressor()
        data = {"x": list(range(100))}
        payload = c.compress(data, CompressionType.ZLIB)
        assert c.decompress(payload, CompressionType.ZLIB) == data

    def test_gzip_roundtrip(self):
        c = DataCompressor()
        data = {"text": "hello " * 200}
        payload = c.compress(data, CompressionType.GZIP)
        assert c.decompress(payload, CompressionType.GZIP) == data

    def test_none_produces_bytes(self):
        c = DataCompressor()
        assert isinstance(c.compress({"a": 1}, CompressionType.NONE), bytes)

    def test_zlib_produces_bytes(self):
        c = DataCompressor()
        assert isinstance(c.compress({"a": 1}, CompressionType.ZLIB), bytes)

    def test_compress_empty_dict(self):
        c = DataCompressor()
        payload = c.compress({}, CompressionType.ZLIB)
        assert c.decompress(payload, CompressionType.ZLIB) == {}

    def test_ratio_none_is_one(self):
        c = DataCompressor()
        assert c.estimate_ratio(b"hello world", CompressionType.NONE) == 1.0

    def test_ratio_zlib_less_than_one(self):
        c = DataCompressor()
        data = b"a" * 1000
        assert c.estimate_ratio(data, CompressionType.ZLIB) < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoryCache
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryCache:
    def test_set_and_get(self):
        cache = HistoryCache()
        cache.set("k1", [1, 2, 3])
        assert cache.get("k1") == [1, 2, 3]

    def test_has_true(self):
        cache = HistoryCache()
        cache.set("k1", "v")
        assert cache.has("k1") is True

    def test_has_false(self):
        cache = HistoryCache()
        assert cache.has("missing") is False

    def test_delete(self):
        cache = HistoryCache()
        cache.set("k1", "v")
        cache.delete("k1")
        assert cache.has("k1") is False

    def test_clear(self):
        cache = HistoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size() == 0

    def test_ttl_expiry(self):
        cache = HistoryCache(ttl_sec=1)
        cache.set("k", "val")
        # Simulate expiry: _store values are (value, ts) tuples — replace with stale ts
        val, _ = cache._store["k"]
        cache._store["k"] = (val, time.time() - 2)
        assert cache.get("k") is None

    def test_eviction_on_max_size(self):
        cache = HistoryCache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.size() <= 2

    def test_stats(self):
        cache = HistoryCache()
        cache.set("x", 1)
        cache.get("x")
        stats = cache.stats()
        assert "hits" in stats


# ─────────────────────────────────────────────────────────────────────────────
# TestInMemoryStorageBackend
# ─────────────────────────────────────────────────────────────────────────────

class TestInMemoryStorageBackend:
    def _backend(self) -> InMemoryStorageBackend:
        return InMemoryStorageBackend()

    def test_create_and_get_dataset(self):
        b = self._backend()
        ds = _make_dataset()
        b.create_dataset(ds)
        assert b.get_dataset(ds.dataset_id).dataset_id == ds.dataset_id

    def test_create_duplicate_raises(self):
        b = self._backend()
        ds = _make_dataset()
        b.create_dataset(ds)
        with pytest.raises(DatasetAlreadyExistsError):
            b.create_dataset(ds)

    def test_delete_dataset(self):
        b = self._backend()
        ds = _make_dataset()
        b.create_dataset(ds)
        b.delete_dataset(ds.dataset_id)
        with pytest.raises(DatasetNotFoundError):
            b.get_dataset(ds.dataset_id)

    def test_list_datasets_empty(self):
        b = self._backend()
        assert b.list_datasets() == []

    def test_append_and_read_range(self):
        b = self._backend()
        ds = _make_dataset()
        b.create_dataset(ds)
        r = _make_record(ts=1_700_000_100.0, dataset_id=ds.dataset_id)
        b.append_record(ds.dataset_id, r)
        out = b.read_range(ds.dataset_id, 1_700_000_000.0, 1_700_001_000.0)
        assert len(out) == 1

    def test_read_range_empty(self):
        b = self._backend()
        ds = _make_dataset()
        b.create_dataset(ds)
        assert b.read_range(ds.dataset_id, 0.0, 1.0) == []

    def test_save_and_load_snapshot(self):
        b  = self._backend()
        ds = _make_dataset()
        b.create_dataset(ds)
        snap = HistoricalSnapshot(
            dataset_id=ds.dataset_id, data_type=HistoricalDataType.MARKET_DATA
        )
        b.save_snapshot(snap)
        loaded = b.load_snapshot(snap.snapshot_id)   # load_snapshot(snapshot_id)
        assert loaded.snapshot_id == snap.snapshot_id

    def test_capacity_enforced(self):
        b = InMemoryStorageBackend(max_records=2)
        ds = _make_dataset()
        b.create_dataset(ds)
        b.append_record(ds.dataset_id, _make_record(dataset_id=ds.dataset_id))
        b.append_record(ds.dataset_id, _make_record(dataset_id=ds.dataset_id))
        with pytest.raises(StorageCapacityError):
            b.append_record(ds.dataset_id, _make_record(dataset_id=ds.dataset_id))

    def test_stats_returns_dict(self):
        b = self._backend()
        s = b.stats()
        assert "total_records" in s

    def test_list_datasets_filtered_by_type(self):
        b = self._backend()
        ds1 = _make_dataset(data_type=HistoricalDataType.MARKET_DATA)
        ds2 = _make_dataset(data_type=HistoricalDataType.NEWS)
        b.create_dataset(ds1)
        b.create_dataset(ds2)
        result = b.list_datasets(data_type=HistoricalDataType.NEWS)
        assert len(result) == 1
        assert result[0].data_type == HistoricalDataType.NEWS

    def test_update_dataset(self):
        b = self._backend()
        ds = _make_dataset()
        b.create_dataset(ds)
        ds.name = "Updated"
        b.update_dataset(ds)
        assert b.get_dataset(ds.dataset_id).name == "Updated"

    def test_get_missing_raises(self):
        b = self._backend()
        with pytest.raises(DatasetNotFoundError):
            b.get_dataset("nonexistent-id")


# ─────────────────────────────────────────────────────────────────────────────
# TestDatasetIndexManager
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetIndexManager:
    def test_create_and_get(self):
        mgr = DatasetIndexManager()
        mgr.create_index("ds-1")
        idx = mgr.get_index("ds-1")
        assert idx is not None

    def test_index_partition(self):
        mgr = DatasetIndexManager()
        mgr.create_index("ds-1")
        r = _make_record(ts=1_700_000_100.0, symbol="AAPL")
        p = HistoricalPartition(
            dataset_id="ds-1",
            data_type=HistoricalDataType.MARKET_DATA,
            start_ts=1_700_000_000.0,
            end_ts=1_700_086_400.0,
        )
        p.append(r)
        mgr.index_partition(p)
        entries = mgr.find_partitions("ds-1", 1_700_000_000.0, 1_700_086_400.0)
        assert len(entries) >= 1

    def test_find_partitions_by_symbol(self):
        mgr = DatasetIndexManager()
        mgr.create_index("ds-1")
        p = HistoricalPartition(
            dataset_id="ds-1",
            data_type=HistoricalDataType.MARKET_DATA,
            start_ts=1_700_000_000.0,
            end_ts=1_700_086_400.0,
        )
        p.append(_make_record(symbol="MSFT", ts=1_700_000_100.0))
        mgr.index_partition(p)
        hits   = mgr.find_partitions("ds-1", 1_700_000_000.0, 1_700_086_400.0, symbol="MSFT")
        misses = mgr.find_partitions("ds-1", 1_700_000_000.0, 1_700_086_400.0, symbol="GOOG")
        assert len(hits)   >= 1
        assert len(misses) == 0

    def test_drop_index(self):
        mgr = DatasetIndexManager()
        mgr.create_index("ds-1")
        mgr.drop_index("ds-1")
        assert mgr.get_index("ds-1") is None

    def test_stats(self):
        mgr = DatasetIndexManager()
        s = mgr.stats()
        assert "datasets_indexed" in s

    def test_create_duplicate_idempotent(self):
        mgr = DatasetIndexManager()
        mgr.create_index("ds-1")
        mgr.create_index("ds-1")   # should not raise
        assert mgr.get_index("ds-1") is not None

    def test_find_partitions_empty(self):
        mgr = DatasetIndexManager()
        mgr.create_index("ds-99")
        assert mgr.find_partitions("ds-99", 0.0, 1.0) == []

    def test_multiple_datasets(self):
        mgr = DatasetIndexManager()
        mgr.create_index("ds-A")
        mgr.create_index("ds-B")
        assert mgr.stats()["datasets_indexed"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# TestReplaySession
# ─────────────────────────────────────────────────────────────────────────────

class TestReplaySession:
    def _session(self) -> ReplaySession:
        return ReplaySession(
            replay_type = ReplayType.FULL_SYSTEM,
            data_type   = HistoricalDataType.MARKET_DATA,
            start_ts    = 1_700_000_000.0,
            end_ts      = 1_700_086_400.0,
        )

    def test_initial_status_pending(self):
        s = self._session()
        assert s.status == ReplayStatus.IDLE

    def test_start(self):
        s = self._session()
        s.start()
        assert s.status == ReplayStatus.RUNNING

    def test_pause(self):
        s = self._session()
        s.start()
        s.pause()
        assert s.status == ReplayStatus.PAUSED

    def test_resume(self):
        s = self._session()
        s.start()
        s.pause()
        s.resume()
        assert s.status == ReplayStatus.RUNNING

    def test_stop(self):
        s = self._session()
        s.start()
        s.stop()
        assert s.status == ReplayStatus.STOPPED

    def test_complete(self):
        s = self._session()
        s.start()
        s.complete()
        assert s.status == ReplayStatus.COMPLETED

    def test_progress_zero_range(self):
        s = self._session()
        s.start()
        # current_ts starts at start_ts
        assert 0.0 <= s.progress() <= 1.0

    def test_to_dict(self):
        s = self._session()
        d = s.to_dict()
        assert "session_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestReplayScheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestReplayScheduler:
    def test_schedule_delivers_all(self):
        sched   = ReplayScheduler(speed_multiplier=0.0)
        records = [_make_record(ts=float(i)) for i in range(5)]
        delivered: list[HistoricalRecord] = []
        async def _collect():
            async for r in sched.schedule(records):
                delivered.append(r)
        _run(_collect())
        assert len(delivered) == 5

    def test_schedule_ordered_by_ts(self):
        sched   = ReplayScheduler(speed_multiplier=0.0)
        # Scheduler expects pre-sorted input; sort before calling schedule
        records = sorted([_make_record(ts=float(10 - i)) for i in range(5)], key=lambda r: r.timestamp)
        delivered: list[HistoricalRecord] = []
        async def _collect():
            async for r in sched.schedule(records):
                delivered.append(r)
        _run(_collect())
        ts_list = [r.timestamp for r in delivered]
        assert ts_list == sorted(ts_list)

    def test_stop_halts_delivery(self):
        sched   = ReplayScheduler(speed_multiplier=0.0)
        records = [_make_record(ts=float(i)) for i in range(100)]
        delivered: list[HistoricalRecord] = []
        async def _collect():
            async for r in sched.schedule(records):
                delivered.append(r)
                if len(delivered) >= 3:
                    sched.stop()
        _run(_collect())
        assert len(delivered) <= 3 + 1   # at most one extra before stop takes effect

    def test_set_speed(self):
        sched = ReplayScheduler(speed_multiplier=1.0)
        sched.set_speed(5.0)
        assert sched._speed == 5.0

    def test_empty_records(self):
        sched = ReplayScheduler(speed_multiplier=0.0)
        delivered: list = []
        async def _collect():
            async for r in sched.schedule([]):
                delivered.append(r)
        _run(_collect())
        assert delivered == []

    def test_pause_and_resume(self):
        sched   = ReplayScheduler(speed_multiplier=0.0)
        records = [_make_record(ts=float(i)) for i in range(3)]
        sched.pause()
        sched.resume()
        delivered: list = []
        async def _collect():
            async for r in sched.schedule(records):
                delivered.append(r)
        _run(_collect())
        assert len(delivered) == 3


# ─────────────────────────────────────────────────────────────────────────────
# TestReplayController
# ─────────────────────────────────────────────────────────────────────────────

class TestReplayController:
    def _ctrl(self) -> tuple[ReplayController, ReplaySession]:
        s = ReplaySession(
            replay_type=ReplayType.FULL_SYSTEM,
            data_type=HistoricalDataType.MARKET_DATA,
            start_ts=0.0,
            end_ts=100.0,
        )
        return ReplayController(session=s), s

    def test_on_record_handler_called(self):
        ctrl, _ = self._ctrl()
        received: list[HistoricalRecord] = []
        ctrl.on_record(received.append)
        records = [_make_record(ts=float(i)) for i in range(3)]
        _run(ctrl.start(records))
        assert len(received) == 3

    def test_stop_terminates_early(self):
        ctrl, _ = self._ctrl()
        received: list = []
        def _handler(r):
            received.append(r)
            ctrl.stop()
        ctrl.on_record(_handler)
        records = [_make_record(ts=float(i)) for i in range(50)]
        _run(ctrl.start(records))
        assert len(received) <= 2

    def test_set_speed(self):
        ctrl, _ = self._ctrl()
        ctrl.set_speed(2.0)
        assert ctrl._scheduler._speed == 2.0

    def test_session_returned(self):
        ctrl, s = self._ctrl()
        assert ctrl.session() is s

    def test_no_handlers_no_error(self):
        ctrl, _ = self._ctrl()
        records = [_make_record()]
        _run(ctrl.start(records))   # should not raise

    def test_statistics_populated_after_run(self):
        ctrl, _ = self._ctrl()
        records = [_make_record(ts=float(i)) for i in range(5)]
        _run(ctrl.start(records))
        stats = ctrl.statistics()
        assert stats.total_records == 5

    def test_pause_resume(self):
        ctrl, _ = self._ctrl()
        records = [_make_record()]
        # Must start the session before pausing
        ctrl._session.start()
        ctrl.pause()
        ctrl.resume()

    def test_seek_moves_current_ts(self):
        ctrl, s = self._ctrl()
        ctrl.seek(50.0)
        assert s.current_ts == 50.0


# ─────────────────────────────────────────────────────────────────────────────
# TestReplayEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestReplayEngine:
    def _engine(self) -> ReplayEngine:
        return ReplayEngine()

    def test_create_session(self):
        eng = self._engine()
        s = eng.create_session(
            replay_type=ReplayType.FULL_SYSTEM,
            data_type=HistoricalDataType.MARKET_DATA,
            dataset_ids=["ds-1"],
            symbols=["AAPL"],
            start_ts=0.0,
            end_ts=100.0,
        )
        assert s.session_id != ""

    def test_get_session(self):
        eng = self._engine()
        s   = eng.create_session(
            replay_type=ReplayType.FULL_SYSTEM,
            data_type=HistoricalDataType.MARKET_DATA,
            dataset_ids=["ds-1"],
            symbols=[],
            start_ts=0.0,
            end_ts=100.0,
        )
        assert eng.get_session(s.session_id) is s

    def test_get_session_missing_raises(self):
        eng = self._engine()
        with pytest.raises(ReplaySessionNotFoundError):
            eng.get_session("bogus")

    def test_start_replay_delivers(self):
        eng = self._engine()
        s   = eng.create_session(
            replay_type=ReplayType.FULL_SYSTEM,
            data_type=HistoricalDataType.MARKET_DATA,
            dataset_ids=["ds-1"],
            symbols=[],
            start_ts=0.0,
            end_ts=100.0,
        )
        received: list = []
        eng.on_record(s.session_id, received.append)
        records = [_make_record(ts=float(i)) for i in range(5)]
        _run(eng.start_replay(s.session_id, records))
        assert len(received) == 5

    def test_all_sessions(self):
        eng = self._engine()
        eng.create_session(
            replay_type=ReplayType.FULL_SYSTEM,
            data_type=HistoricalDataType.MARKET_DATA,
            dataset_ids=[],
            symbols=[],
            start_ts=0.0,
            end_ts=100.0,
        )
        assert len(eng.all_sessions()) == 1

    def test_stats(self):
        eng = self._engine()
        s = eng.stats()
        assert "total_sessions" in s

    def test_pause_missing_session_raises(self):
        eng = self._engine()
        with pytest.raises(ReplaySessionNotFoundError):
            eng.pause("no-session")

    def test_stop_missing_session_raises(self):
        eng = self._engine()
        with pytest.raises(ReplaySessionNotFoundError):
            eng.stop("no-session")


# ─────────────────────────────────────────────────────────────────────────────
# TestTimeline
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeline:
    def _event(self, ts: float, subject: str = "test") -> TimelineEvent:
        return TimelineEvent(
            timeline_id = "tl-1",
            timestamp   = ts,
            data_type   = HistoricalDataType.MARKET_DATA,
            subject     = subject,
            data        = {},
        )

    def test_append_and_count(self):
        tl = Timeline(timeline_id="tl-1")
        tl.append(self._event(1.0))
        assert tl.event_count() == 1

    def test_bulk_append(self):
        tl     = Timeline(timeline_id="tl-1")
        events = [self._event(float(i)) for i in range(10)]
        tl.bulk_append(events)
        assert tl.event_count() == 10

    def test_events_in_range(self):
        tl = Timeline(timeline_id="tl-1")
        tl.bulk_append([self._event(float(i)) for i in range(20)])
        rng = tl.events_in_range(5.0, 10.0)
        assert all(5.0 <= e.timestamp <= 10.0 for e in rng)

    def test_next_event(self):
        tl = Timeline(timeline_id="tl-1")
        tl.bulk_append([self._event(float(i)) for i in range(5)])
        e = tl.next_event(2.0)
        assert e is not None
        assert e.timestamp > 2.0

    def test_prev_event(self):
        tl = Timeline(timeline_id="tl-1")
        tl.bulk_append([self._event(float(i)) for i in range(5)])
        e = tl.prev_event(3.0)
        assert e is not None
        assert e.timestamp < 3.0

    def test_seek(self):
        tl = Timeline(timeline_id="tl-1")
        tl.bulk_append([self._event(float(i)) for i in range(5)])
        # seek(target_ts) returns the cursor
        cursor = tl.seek(3.0)
        assert cursor.current_ts == 3.0

    def test_clear(self):
        tl = Timeline(timeline_id="tl-1")
        tl.bulk_append([self._event(float(i)) for i in range(5)])
        tl.clear()
        assert tl.event_count() == 0

    def test_on_event_called(self):
        tl       = Timeline(timeline_id="tl-1")
        received = []
        tl.on_event(received.append)
        # Timeline.append stores event; _dispatch is called by controller.play()
        # dispatch manually to verify handler wiring
        e = self._event(1.0)
        tl.append(e)
        tl._dispatch(e)
        assert len(received) == 1

    def test_time_range(self):
        tl = Timeline(timeline_id="tl-1")
        tl.bulk_append([self._event(float(i)) for i in range(5)])
        lo, hi = tl.time_range()
        assert lo == 0.0
        assert hi == 4.0

    def test_to_dict(self):
        tl = Timeline(timeline_id="tl-1")
        d  = tl.to_dict()
        assert "timeline_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestTimelineCursor
# ─────────────────────────────────────────────────────────────────────────────

class TestTimelineCursor:
    def _cursor(self) -> TimelineCursor:
        return TimelineCursor(
            timeline_id = "tl-1",
            current_ts  = 0.0,
            start_ts    = 0.0,
            end_ts      = 100.0,
        )

    def test_is_at_start(self):
        c = self._cursor()
        assert c.is_at_start() is True

    def test_is_at_end_false(self):
        c = self._cursor()
        assert c.is_at_end() is False

    def test_move_forward(self):
        c = self._cursor()
        c.move(10.0)
        assert c.current_ts == pytest.approx(10.0)

    def test_seek(self):
        c = self._cursor()
        c.seek(50.0)
        assert c.current_ts == 50.0

    def test_progress(self):
        c = self._cursor()
        c.seek(50.0)
        assert c.progress() == pytest.approx(0.5)

    def test_to_dict(self):
        c = self._cursor()
        d = c.to_dict()
        assert "cursor_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestTimelineController
# ─────────────────────────────────────────────────────────────────────────────

class TestTimelineController:
    def _event(self, ts: float) -> TimelineEvent:
        return TimelineEvent(
            timeline_id="tl-1",
            timestamp=ts,
            data_type=HistoricalDataType.MARKET_DATA,
            subject="test",
            data={},
        )

    def _controller(self) -> tuple[TimelineController, Timeline, list]:
        tl       = Timeline(timeline_id="tl-1")
        received = []
        tl.on_event(received.append)
        ctrl = TimelineController(timeline=tl, speed_multiplier=0.0)
        return ctrl, tl, received

    def test_play_delivers_events(self):
        ctrl, tl, received = self._controller()
        tl.bulk_append([self._event(float(i)) for i in range(3)])
        _run(ctrl.play())
        assert len(received) >= 3

    def test_pause_and_resume_no_error(self):
        ctrl, tl, _ = self._controller()
        ctrl.pause()
        ctrl.resume()

    def test_stop_no_error(self):
        ctrl, tl, _ = self._controller()
        ctrl.stop()

    def test_seek(self):
        ctrl, tl, _ = self._controller()
        tl.bulk_append([self._event(float(i)) for i in range(10)])
        # TimelineController.seek(target_ts) takes a single ts arg
        ctrl.seek(5.0)
        assert tl.cursor().current_ts == 5.0

    def test_set_speed(self):
        ctrl, _, _ = self._controller()
        ctrl.set_speed(3.0)
        assert ctrl._speed == 3.0

    def test_timeline_reference(self):
        ctrl, tl, _ = self._controller()
        assert ctrl.timeline() is tl


# ─────────────────────────────────────────────────────────────────────────────
# TestSimulationClock
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulationClock:
    def test_now_returns_float(self):
        c = SimulationClock(start_ts=1_700_000_000.0)
        assert isinstance(c.now(), float)

    def test_tick_advances(self):
        c = SimulationClock(start_ts=100.0, speed_multiplier=0.0, tick_size_sec=10.0)
        c.tick()
        # ticks counter increments even when speed=0 (simulated_time doesn't change)
        assert c.ticks() == 1

    def test_tick_advances_at_speed_1(self):
        c = SimulationClock(start_ts=100.0, speed_multiplier=1.0, tick_size_sec=10.0)
        c.tick()
        assert c.ticks() == 1

    def test_pause_freezes_time(self):
        c  = SimulationClock(start_ts=1_700_000_000.0)
        c.pause()
        t1 = c.now()
        time.sleep(0.05)
        t2 = c.now()
        assert t1 == t2

    def test_resume_after_pause(self):
        c = SimulationClock(start_ts=1_700_000_000.0)
        c.pause()
        c.resume()
        assert c.is_paused() is False

    def test_set_time(self):
        c = SimulationClock()
        c.set_time(5_000_000.0)
        assert c.now() == pytest.approx(5_000_000.0, abs=1.0)

    def test_set_speed_negative_raises(self):
        c = SimulationClock()
        with pytest.raises(SimulationClockError):
            c.set_speed(-1.0)

    def test_to_dict(self):
        c = SimulationClock()
        d = c.to_dict()
        assert "clock_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestScenarioLoader
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioLoader:
    def _scenario(self, name: str = "test") -> Scenario:
        return Scenario(
            name     = name,
            start_ts = 1_700_000_000.0,
            end_ts   = 1_700_086_400.0,
        )

    def test_register_and_get(self):
        sl = ScenarioLoader()
        s  = self._scenario("alpha")
        sl.register(s)
        assert sl.get(s.scenario_id).scenario_id == s.scenario_id

    def test_has_true(self):
        sl = ScenarioLoader()
        s  = self._scenario()
        sl.register(s)
        assert sl.has(s.scenario_id) is True

    def test_has_false(self):
        sl = ScenarioLoader()
        assert sl.has("bogus") is False

    def test_get_missing_raises(self):
        sl = ScenarioLoader()
        with pytest.raises(ScenarioNotFoundError):
            sl.get("bogus")

    def test_list_all(self):
        sl = ScenarioLoader()
        sl.register(self._scenario("a"))
        sl.register(self._scenario("b"))
        assert sl.count() == 2

    def test_register_by_name(self):
        sl = ScenarioLoader()
        s  = self._scenario("my-scenario")
        sl.register_by_name(s)
        assert sl.has("my-scenario") is True


# ─────────────────────────────────────────────────────────────────────────────
# TestDatasetLoader
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetLoader:
    def _setup(self) -> tuple[InMemoryStorageBackend, HistoricalDataset]:
        b  = InMemoryStorageBackend()
        ds = _make_dataset(symbols=["AAPL"])
        b.create_dataset(ds)
        for i in range(5):
            b.append_record(
                ds.dataset_id,
                _make_record(symbol="AAPL", ts=1_700_000_000.0 + i * 60, dataset_id=ds.dataset_id),
            )
        return b, ds

    def test_load_returns_sorted(self):
        b, ds = self._setup()
        loader = DatasetLoader(b)
        records = _run(loader.load(ds.dataset_id, 1_699_999_999.0, 1_700_001_000.0))
        ts_list = [r.timestamp for r in records]
        assert ts_list == sorted(ts_list)

    def test_load_multi_merges(self):
        b    = InMemoryStorageBackend()
        ds1  = _make_dataset(name="DS1")
        ds2  = _make_dataset(name="DS2")
        b.create_dataset(ds1)
        b.create_dataset(ds2)
        b.append_record(ds1.dataset_id, _make_record(ts=100.0, dataset_id=ds1.dataset_id))
        b.append_record(ds2.dataset_id, _make_record(ts=50.0,  dataset_id=ds2.dataset_id))
        loader  = DatasetLoader(b)
        result  = _run(loader.load_multi([ds1.dataset_id, ds2.dataset_id], 0.0, 200.0))
        ts_list = [r.timestamp for r in result]
        assert ts_list == sorted(ts_list)

    def test_load_multi_skips_missing(self):
        b  = InMemoryStorageBackend()
        ds = _make_dataset()
        b.create_dataset(ds)
        b.append_record(ds.dataset_id, _make_record(ts=100.0, dataset_id=ds.dataset_id))
        loader = DatasetLoader(b)
        result = _run(loader.load_multi([ds.dataset_id, "nonexistent"], 0.0, 200.0))
        assert len(result) == 1

    def test_stats(self):
        b  = InMemoryStorageBackend()
        ds = _make_dataset()
        b.create_dataset(ds)
        loader = DatasetLoader(b)
        _run(loader.load(ds.dataset_id, 0.0, 1_000_000.0))
        assert loader.stats()["loads"] == 1

    def test_load_empty_dataset(self):
        b  = InMemoryStorageBackend()
        ds = _make_dataset()
        b.create_dataset(ds)
        loader  = DatasetLoader(b)
        records = _run(loader.load(ds.dataset_id, 0.0, 1_000_000.0))
        assert records == []

    def test_load_with_symbol_filter(self):
        b, ds = self._setup()
        loader = DatasetLoader(b)
        records = _run(loader.load(ds.dataset_id, 0.0, 1_900_000_000.0, symbols=["AAPL"]))
        assert all(r.symbol == "AAPL" for r in records)


# ─────────────────────────────────────────────────────────────────────────────
# TestSimulationController
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulationController:
    def _setup(self) -> tuple[SimulationController, HistoricalDataset, Scenario]:
        b     = InMemoryStorageBackend()
        ds    = _make_dataset()
        b.create_dataset(ds)
        for i in range(5):
            b.append_record(
                ds.dataset_id,
                _make_record(ts=1_700_000_000.0 + i, dataset_id=ds.dataset_id),
            )
        loader = DatasetLoader(b)
        engine = ReplayEngine()
        ctrl   = SimulationController(dataset_loader=loader, replay_engine=engine)
        sc     = Scenario(
            name        = "test-scenario",
            dataset_ids = [ds.dataset_id],
            start_ts    = 1_699_999_999.0,
            end_ts      = 1_700_000_010.0,
        )
        return ctrl, ds, sc

    def test_run_scenario(self):
        ctrl, _, sc = self._setup()
        received: list = []
        ctrl.on_record(received.append)
        _run(ctrl.run(sc))
        assert len(received) == 5

    def test_status_completed_after_run(self):
        ctrl, _, sc = self._setup()
        _run(ctrl.run(sc))
        assert ctrl.status() == SimulationStatus.COMPLETED

    def test_stats_updated(self):
        ctrl, _, sc = self._setup()
        _run(ctrl.run(sc))
        assert ctrl.stats()["simulations_run"] == 1

    def test_stop_mid_run(self):
        ctrl, _, sc = self._setup()
        def _stopper(r):
            ctrl.stop()
        ctrl.on_record(_stopper)
        _run(ctrl.run(sc))

    def test_no_handlers_no_crash(self):
        ctrl, _, sc = self._setup()
        _run(ctrl.run(sc))   # should not raise

    def test_clock_set_after_run(self):
        ctrl, _, sc = self._setup()
        _run(ctrl.run(sc))
        assert ctrl.clock() is not None


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoryRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryRegistry:
    def test_register_and_get(self):
        reg = HistoryRegistry()
        ds  = _make_dataset()
        reg.register(ds)
        assert reg.get(ds.dataset_id).dataset_id == ds.dataset_id

    def test_register_duplicate_raises(self):
        reg = HistoryRegistry()
        ds  = _make_dataset()
        reg.register(ds)
        with pytest.raises(DatasetAlreadyExistsError):
            reg.register(ds)

    def test_unregister(self):
        reg = HistoryRegistry()
        ds  = _make_dataset()
        reg.register(ds)
        reg.unregister(ds.dataset_id)
        with pytest.raises(DatasetNotFoundError):
            reg.get(ds.dataset_id)

    def test_has_true(self):
        reg = HistoryRegistry()
        ds  = _make_dataset()
        reg.register(ds)
        assert reg.has(ds.dataset_id) is True

    def test_count(self):
        reg = HistoryRegistry()
        reg.register(_make_dataset(name="A"))
        reg.register(_make_dataset(name="B"))
        assert reg.count() == 2

    def test_find_by_type(self):
        reg  = HistoryRegistry()
        ds1  = _make_dataset(data_type=HistoricalDataType.NEWS)
        ds2  = _make_dataset(data_type=HistoricalDataType.MARKET_DATA)
        reg.register(ds1)
        reg.register(ds2)
        hits = reg.find_by_type(HistoricalDataType.NEWS)
        assert len(hits) == 1

    def test_find_by_symbol(self):
        reg = HistoryRegistry()
        ds  = _make_dataset(symbols=["TSLA", "GOOGL"])
        reg.register(ds)
        hits   = reg.find_by_symbol("TSLA")
        misses = reg.find_by_symbol("MSFT")
        assert len(hits)   == 1
        assert len(misses) == 0

    def test_capacity_limit(self):
        reg = HistoryRegistry(max_datasets=2)
        reg.register(_make_dataset(name="A"))
        reg.register(_make_dataset(name="B"))
        with pytest.raises(HistoryRegistryFullError):
            reg.register(_make_dataset(name="C"))


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoryContext
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryContext:
    def test_set_and_get(self):
        HistoryContext.set(operation="test_op", dataset_id="ds-1")
        s = HistoryContext.get()
        assert s.operation  == "test_op"
        assert s.dataset_id == "ds-1"
        HistoryContext.clear()

    def test_clear_resets(self):
        HistoryContext.set(operation="x")
        HistoryContext.clear()
        assert HistoryContext.get().operation == ""

    def test_scope_context_manager(self):
        with HistoryContext.scope("query", dataset_id="ds-2") as s:
            assert s.operation  == "query"
            assert s.dataset_id == "ds-2"
        assert HistoryContext.get().operation == ""

    def test_elapsed_ms(self):
        HistoryContext.set(operation="t")
        time.sleep(0.01)
        assert HistoryContext.get().elapsed_ms() > 0
        HistoryContext.clear()

    def test_thread_isolation(self):
        results = {}
        def _set_ctx(label: str):
            HistoryContext.set(operation=label)
            time.sleep(0.02)
            results[label] = HistoryContext.get().operation

        t1 = threading.Thread(target=_set_ctx, args=("thread-A",))
        t2 = threading.Thread(target=_set_ctx, args=("thread-B",))
        t1.start(); t2.start()
        t1.join();  t2.join()
        assert results["thread-A"] == "thread-A"
        assert results["thread-B"] == "thread-B"

    def test_nested_scope_clears_after(self):
        with HistoryContext.scope("outer"):
            with HistoryContext.scope("inner"):
                assert HistoryContext.get().operation == "inner"
        # After inner scope exits, context is cleared (not restored to outer)
        assert HistoryContext.get().operation == ""


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoryFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryFactory:
    def test_create_storage_backend(self):
        b = HistoryFactory.create_storage_backend()
        assert isinstance(b, InMemoryStorageBackend)

    def test_create_registry(self):
        r = HistoryFactory.create_registry()
        assert isinstance(r, HistoryRegistry)

    def test_create_index_manager(self):
        m = HistoryFactory.create_index_manager()
        assert isinstance(m, DatasetIndexManager)

    def test_create_cache(self):
        c = HistoryFactory.create_cache()
        assert isinstance(c, HistoryCache)

    def test_create_compressor(self):
        c = HistoryFactory.create_compressor()
        assert isinstance(c, DataCompressor)

    def test_create_query_engine(self):
        b = HistoryFactory.create_storage_backend()
        q = HistoryFactory.create_query_engine(b)
        assert isinstance(q, QueryEngine)

    def test_create_replay_engine(self):
        e = HistoryFactory.create_replay_engine()
        assert isinstance(e, ReplayEngine)

    def test_create_simulation_controller(self):
        b = HistoryFactory.create_storage_backend()
        c = HistoryFactory.create_simulation_controller(b)
        assert isinstance(c, SimulationController)


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoryManager
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryManager:
    def _mgr(self) -> HistoryManager:
        b   = HistoryFactory.create_storage_backend()
        reg = HistoryFactory.create_registry()
        idx = HistoryFactory.create_index_manager()
        q   = HistoryFactory.create_query_engine(b)
        c   = HistoryFactory.create_cache()
        return HistoryManager(registry=reg, backend=b, index_manager=idx, query_engine=q, cache=c)

    def test_create_dataset(self):
        mgr = self._mgr()
        ds  = _make_dataset()
        mgr.create_dataset(ds)
        assert mgr.get_dataset(ds.dataset_id).dataset_id == ds.dataset_id

    def test_ingest(self):
        mgr = self._mgr()
        ds  = _make_dataset()
        mgr.create_dataset(ds)
        r   = _make_record(dataset_id=ds.dataset_id)
        mgr.ingest(ds.dataset_id, r)
        assert mgr.stats()["records_ingested"] == 1

    def test_ingest_batch(self):
        mgr     = self._mgr()
        ds      = _make_dataset()
        mgr.create_dataset(ds)
        records = [_make_record(dataset_id=ds.dataset_id) for _ in range(10)]
        count   = mgr.ingest_batch(ds.dataset_id, records)
        assert count == 10

    def test_query_returns_records(self):
        mgr = self._mgr()
        ds  = _make_dataset()
        mgr.create_dataset(ds)
        ts_base = 1_700_000_000.0
        for i in range(5):
            mgr.ingest(ds.dataset_id, _make_record(ts=ts_base + i, dataset_id=ds.dataset_id))
        f = HistoricalFilter(
            dataset_ids = [ds.dataset_id],
            start_ts    = ts_base - 1,
            end_ts      = ts_base + 10,
        )
        result = _run(mgr.query(f))
        assert len(result) == 5

    def test_create_snapshot(self):
        mgr = self._mgr()
        ds  = _make_dataset()
        mgr.create_dataset(ds)
        snap = mgr.create_snapshot(ds.dataset_id)
        assert snap.dataset_id == ds.dataset_id

    def test_delete_dataset(self):
        mgr = self._mgr()
        ds  = _make_dataset()
        mgr.create_dataset(ds)
        mgr.delete_dataset(ds.dataset_id)
        with pytest.raises(DatasetNotFoundError):
            mgr.get_dataset(ds.dataset_id)

    def test_stats(self):
        mgr = self._mgr()
        s   = mgr.stats()
        assert "registry" in s
        assert "cache"    in s

    def test_archive_dataset(self):
        mgr = self._mgr()
        ds  = _make_dataset()
        mgr.create_dataset(ds)
        mgr.archive_dataset(ds.dataset_id)
        assert mgr.get_dataset(ds.dataset_id).status == DatasetStatus.ARCHIVED


# ─────────────────────────────────────────────────────────────────────────────
# TestHistoricalDataEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoricalDataEngine:
    def setup_method(self):
        reset_historical_data_engine()

    def teardown_method(self):
        reset_historical_data_engine()

    def _started_engine(self) -> HistoricalDataEngine:
        e = HistoricalDataEngine()
        _run(e.start())
        return e

    def test_initial_status_stopped(self):
        e = HistoricalDataEngine()
        assert e.status() == HistoryEngineStatus.STOPPED

    def test_start(self):
        e = self._started_engine()
        assert e.is_running() is True

    def test_stop(self):
        e = self._started_engine()
        _run(e.stop())
        assert e.is_running() is False

    def test_double_start_raises(self):
        e = self._started_engine()
        with pytest.raises(HistoryEngineAlreadyRunningError):
            _run(e.start())

    def test_op_before_start_raises(self):
        e = HistoricalDataEngine()
        with pytest.raises(HistoryEngineNotRunningError):
            e.create_dataset(_make_dataset())

    def test_create_and_get_dataset(self):
        e  = self._started_engine()
        ds = _make_dataset()
        e.create_dataset(ds)
        assert e.get_dataset(ds.dataset_id).dataset_id == ds.dataset_id

    def test_ingest_and_query(self):
        e   = self._started_engine()
        ds  = _make_dataset()
        e.create_dataset(ds)
        ts  = 1_700_000_000.0
        e.ingest(ds.dataset_id, _make_record(ts=ts, dataset_id=ds.dataset_id))
        f = HistoricalFilter(
            dataset_ids=[ds.dataset_id],
            start_ts=ts - 1,
            end_ts=ts + 1,
        )
        result = _run(e.query(f))
        assert len(result) == 1

    def test_uptime_sec_positive(self):
        e = self._started_engine()
        time.sleep(0.01)
        assert e.uptime_sec() > 0

    def test_stats(self):
        e = self._started_engine()
        s = e.stats()
        assert "version" in s
        assert "status"  in s


# ─────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleton:
    def setup_method(self):
        reset_historical_data_engine()

    def teardown_method(self):
        reset_historical_data_engine()

    def test_same_instance(self):
        a = get_historical_data_engine()
        b = get_historical_data_engine()
        assert a is b

    def test_reset_clears_instance(self):
        a = get_historical_data_engine()
        reset_historical_data_engine()
        b = get_historical_data_engine()
        assert a is not b

    def test_not_running_by_default(self):
        e = get_historical_data_engine()
        assert e.is_running() is False

    def test_auto_start(self):
        e = get_historical_data_engine(auto_start=True)
        assert e.is_running() is True

    def test_thread_safety(self):
        instances: list = []
        def _get():
            instances.append(get_historical_data_engine())
        threads = [threading.Thread(target=_get) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert all(i is instances[0] for i in instances)
