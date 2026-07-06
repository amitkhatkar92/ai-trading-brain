"""
tests/unit/configuration/test_configuration_cache.py
======================================================
Unit tests for ConfigurationCache.
"""

from __future__ import annotations

import time
import threading
import pytest

from iios.configuration.configuration_cache import ConfigurationCache, CacheSnapshot
from iios.configuration.configuration_exception import ConfigurationError


class TestConfigurationCache:
    # ------------------------------------------------------------------
    # Basic get / put
    # ------------------------------------------------------------------

    def test_empty_cache_get_returns_default(self):
        c = ConfigurationCache()
        assert c.get("risk.vix_threshold", 99.0) == 99.0

    def test_put_and_get_scalar(self):
        c = ConfigurationCache()
        c.put({"risk": {"vix_threshold": 45.0}})
        assert c.get("risk.vix_threshold") == 45.0

    def test_put_and_get_nested(self):
        c = ConfigurationCache()
        c.put({"a": {"b": {"c": 42}}})
        assert c.get("a.b.c") == 42

    def test_get_missing_key(self):
        c = ConfigurationCache()
        c.put({"risk": {"vix_threshold": 45.0}})
        assert c.get("risk.nonexistent", "fallback") == "fallback"

    def test_get_all_returns_deep_copy(self):
        c = ConfigurationCache()
        data = {"risk": {"vix_threshold": 45.0}}
        c.put(data)
        retrieved = c.get_all()
        retrieved["risk"]["vix_threshold"] = 99.0
        # Cache should be unaffected
        assert c.get("risk.vix_threshold") == 45.0

    def test_is_empty_before_put(self):
        c = ConfigurationCache()
        assert c.is_empty

    def test_not_empty_after_put(self):
        c = ConfigurationCache()
        c.put({"key": "value"})
        assert not c.is_empty

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    def test_version_increments(self):
        c = ConfigurationCache()
        assert c.version == 0
        c.put({"a": 1})
        assert c.version == 1
        c.put({"a": 2})
        assert c.version == 2

    def test_snapshot_has_correct_version(self):
        c = ConfigurationCache()
        snap = c.put({"a": 1})
        assert snap.version == 1

    def test_snapshot_has_checksum(self):
        c = ConfigurationCache()
        snap = c.put({"a": 1})
        assert len(snap.checksum) == 64  # SHA-256 hex

    def test_current_snapshot_property(self):
        c = ConfigurationCache()
        snap = c.put({"x": 1})
        assert c.current_snapshot is snap

    # ------------------------------------------------------------------
    # TTL / staleness
    # ------------------------------------------------------------------

    def test_is_stale_before_put(self):
        c = ConfigurationCache(ttl_seconds=60)
        assert c.is_stale

    def test_not_stale_immediately_after_put(self):
        c = ConfigurationCache(ttl_seconds=60)
        c.put({"a": 1})
        assert not c.is_stale

    def test_zero_ttl_never_stale(self):
        c = ConfigurationCache(ttl_seconds=0)
        c.put({"a": 1})
        assert not c.is_stale

    def test_stale_after_ttl_expires(self):
        c = ConfigurationCache(ttl_seconds=1)
        c.put({"a": 1})
        time.sleep(1.1)
        assert c.is_stale

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def test_history_grows_with_puts(self):
        c = ConfigurationCache()
        c.put({"v": 1})
        c.put({"v": 2})
        c.put({"v": 3})
        # history holds previous snapshots (not the current one)
        assert len(c.history) == 2

    def test_history_bounded_by_max(self):
        c = ConfigurationCache(max_history=3)
        for i in range(10):
            c.put({"v": i})
        assert len(c.history) <= 3

    def test_rollback_restores_value(self):
        c = ConfigurationCache()
        c.put({"a": "first"})   # version 1
        v1 = c.version
        c.put({"a": "second"})  # version 2
        c.rollback(v1)
        assert c.get("a") == "first"

    def test_rollback_advances_version(self):
        c = ConfigurationCache()
        c.put({"a": 1})  # v1
        c.put({"a": 2})  # v2
        c.rollback(1)
        assert c.version == 3  # rolled-back as new version 3

    def test_rollback_missing_version_raises(self):
        c = ConfigurationCache()
        c.put({"a": 1})
        with pytest.raises(ConfigurationError):
            c.rollback(999)

    # ------------------------------------------------------------------
    # Invalidate / clear
    # ------------------------------------------------------------------

    def test_invalidate_marks_stale(self):
        c = ConfigurationCache(ttl_seconds=3600)
        c.put({"a": 1})
        c.invalidate()
        assert c.is_stale

    def test_clear_resets_all(self):
        c = ConfigurationCache()
        c.put({"a": 1})
        c.put({"a": 2})
        c.clear()
        assert c.is_empty
        assert c.version == 0
        assert c.history == []

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

    def test_diff_changed_key(self):
        c = ConfigurationCache()
        c.put({"risk": {"vix": 45.0}})   # v1
        c.put({"risk": {"vix": 50.0}})   # v2
        diffs = c.diff(1, 2)
        assert "risk.vix" in diffs
        assert diffs["risk.vix"] == (45.0, 50.0)

    def test_diff_no_change(self):
        c = ConfigurationCache()
        c.put({"a": 1})   # v1
        c.put({"a": 1})   # v2
        diffs = c.diff(1, 2)
        assert diffs == {}

    # ------------------------------------------------------------------
    # Change callbacks
    # ------------------------------------------------------------------

    def test_on_change_callback_fired(self):
        c = ConfigurationCache()
        received = []

        def callback(snap: CacheSnapshot) -> None:
            received.append(snap)

        c.on_change(callback)
        c.put({"a": 1})
        assert len(received) == 1
        assert received[0].data == {"a": 1}

    def test_remove_change_handler(self):
        c = ConfigurationCache()
        received = []

        def callback(snap: CacheSnapshot) -> None:
            received.append(snap)

        c.on_change(callback)
        c.remove_change_handler(callback)
        c.put({"a": 1})
        assert received == []

    # ------------------------------------------------------------------
    # Thread safety
    # ------------------------------------------------------------------

    def test_concurrent_puts_are_safe(self):
        c = ConfigurationCache()
        errors = []

        def worker(i: int) -> None:
            try:
                c.put({f"key_{i}": i})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert c.version == 20
