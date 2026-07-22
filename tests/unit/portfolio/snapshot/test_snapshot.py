"""
test_snapshot.py — tests/unit/portfolio/snapshot
=================================================
Comprehensive test suite for the Portfolio Snapshot subsystem (C10 M5).

Sections
--------
1.  Constants
2.  Exceptions
3.  Metadata value objects
4.  PortfolioSnapshot core
5.  SnapshotEvents
6.  SnapshotValidation (12 checks)
7.  SnapshotStatistics
8.  SnapshotCache
9.  SnapshotHistory
10. SnapshotStore
11. SnapshotRegistry
12. SnapshotBuilder
13. SnapshotFactory
14. SnapshotBundle
15. End-to-end publish workflow
16. Concurrency safety
17. Regression
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List

import pytest

from iios.portfolio.snapshot import (
    # constants
    SNAPSHOT_SYSTEM_ID,
    VERSION,
    SnapshotStatus,
    PortfolioHealth,
    SnapshotEventType,
    SnapshotValidationCode,
    VALID_SNAPSHOT_TRANSITIONS,
    PUBLISHED_STATUSES,
    TERMINAL_STATUSES,
    DEFAULT_MAX_STORE,
    DEFAULT_MAX_CACHE,
    DEFAULT_MAX_HISTORY_PER_PF,
    # exceptions
    PortfolioSnapshotError,
    SnapshotBuildError,
    SnapshotNotFoundError,
    SnapshotValidationError,
    SnapshotDuplicateError,
    SnapshotStoreError,
    SnapshotCacheError,
    SnapshotVersionError,
    SnapshotCapacityError,
    SnapshotPublicationError,
    # metadata
    SnapshotAuditMetadata,
    PortfolioSnapshotMetadata,
    # core
    PortfolioSnapshot,
    # events
    SnapshotEvent,
    make_snapshot_created,
    make_snapshot_validated,
    make_snapshot_published,
    make_snapshot_archived,
    make_snapshot_retrieved,
    make_snapshot_cached,
    # validation
    SnapshotValidationCheckResult,
    SnapshotValidationResult,
    PortfolioSnapshotValidator,
    # infrastructure
    PortfolioSnapshotStatistics,
    PortfolioSnapshotCache,
    PortfolioSnapshotHistory,
    PortfolioSnapshotStore,
    PortfolioSnapshotRegistry,
    # build
    PortfolioSnapshotBuilder,
    PortfolioSnapshotFactory,
    # bundle
    PortfolioSnapshotBundle,
)


# ===========================================================================
# Helpers / fixtures
# ===========================================================================

def _make_snapshot(
    portfolio_id: str = "pf-001",
    portfolio_session_id: str = "sess-001",
    portfolio_name: str = "Test Portfolio",
    lifecycle_state: str = "running",
    snapshot_status: str = SnapshotStatus.DRAFT.value,
    portfolio_health: str = PortfolioHealth.HEALTHY.value,
    snapshot_version: int = 1,
    snapshot_id: str | None = None,
    **extra,
) -> PortfolioSnapshot:
    """Build a minimal valid PortfolioSnapshot."""
    builder = PortfolioSnapshotBuilder()
    return builder.build(
        portfolio_id         = portfolio_id,
        portfolio_session_id = portfolio_session_id,
        portfolio_name       = portfolio_name,
        lifecycle_state      = lifecycle_state,
        snapshot_status      = snapshot_status,
        portfolio_health     = portfolio_health,
        snapshot_version     = snapshot_version,
        snapshot_id          = snapshot_id,
        **extra,
    )


@pytest.fixture
def snap() -> PortfolioSnapshot:
    return _make_snapshot()


@pytest.fixture
def builder() -> PortfolioSnapshotBuilder:
    return PortfolioSnapshotBuilder()


@pytest.fixture
def registry() -> PortfolioSnapshotRegistry:
    return PortfolioSnapshotRegistry()


@pytest.fixture
def store() -> PortfolioSnapshotStore:
    return PortfolioSnapshotStore()


@pytest.fixture
def cache() -> PortfolioSnapshotCache:
    return PortfolioSnapshotCache()


@pytest.fixture
def history() -> PortfolioSnapshotHistory:
    return PortfolioSnapshotHistory()


@pytest.fixture
def validator() -> PortfolioSnapshotValidator:
    return PortfolioSnapshotValidator()


@pytest.fixture
def factory() -> PortfolioSnapshotFactory:
    return PortfolioSnapshotFactory()


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_system_id_is_string(self):
        assert isinstance(SNAPSHOT_SYSTEM_ID, str)
        assert SNAPSHOT_SYSTEM_ID.startswith("iios:")

    def test_version_string(self):
        assert isinstance(VERSION, str)
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_snapshot_status_values(self):
        vals = {s.value for s in SnapshotStatus}
        assert "draft" in vals
        assert "validated" in vals
        assert "published" in vals
        assert "archived" in vals

    def test_portfolio_health_values(self):
        vals = {h.value for h in PortfolioHealth}
        assert {"healthy", "degraded", "critical", "unknown"} == vals

    def test_event_type_count(self):
        assert len(SnapshotEventType) == 6

    def test_validation_code_count(self):
        assert len(SnapshotValidationCode) == 12

    def test_transitions_draft_to_validated(self):
        assert SnapshotStatus.VALIDATED in VALID_SNAPSHOT_TRANSITIONS[SnapshotStatus.DRAFT]

    def test_transitions_draft_to_archived(self):
        assert SnapshotStatus.ARCHIVED in VALID_SNAPSHOT_TRANSITIONS[SnapshotStatus.DRAFT]

    def test_transitions_validated_to_published(self):
        assert SnapshotStatus.PUBLISHED in VALID_SNAPSHOT_TRANSITIONS[SnapshotStatus.VALIDATED]

    def test_transitions_published_to_archived_only(self):
        targets = VALID_SNAPSHOT_TRANSITIONS[SnapshotStatus.PUBLISHED]
        assert targets == frozenset({SnapshotStatus.ARCHIVED})

    def test_transitions_archived_is_terminal(self):
        assert VALID_SNAPSHOT_TRANSITIONS[SnapshotStatus.ARCHIVED] == frozenset()

    def test_published_statuses(self):
        assert SnapshotStatus.PUBLISHED in PUBLISHED_STATUSES
        assert SnapshotStatus.VALIDATED in PUBLISHED_STATUSES

    def test_terminal_statuses(self):
        assert SnapshotStatus.ARCHIVED in TERMINAL_STATUSES

    def test_defaults_are_positive(self):
        assert DEFAULT_MAX_STORE > 0
        assert DEFAULT_MAX_CACHE > 0
        assert DEFAULT_MAX_HISTORY_PER_PF > 0


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_error_hierarchy(self):
        err = PortfolioSnapshotError("test")
        assert isinstance(err, Exception)
        assert "PS-000" in str(err.code)

    def test_build_error(self):
        err = SnapshotBuildError("bad input", portfolio_id="pf-1")
        assert err.portfolio_id == "pf-1"
        assert isinstance(err, PortfolioSnapshotError)
        assert "PS-001" in str(err.code)

    def test_not_found_error(self):
        err = SnapshotNotFoundError("snap-99")
        assert err.snapshot_id == "snap-99"
        assert "PS-002" in str(err.code)

    def test_not_found_error_empty_id(self):
        err = SnapshotNotFoundError()
        assert err.snapshot_id == ""

    def test_validation_error(self):
        err = SnapshotValidationError("fail", failed_checks=("a", "b"))
        assert err.failed_checks == ("a", "b")
        assert "PS-003" in str(err.code)

    def test_duplicate_error(self):
        err = SnapshotDuplicateError("dup-id")
        assert err.snapshot_id == "dup-id"
        assert "PS-004" in str(err.code)

    def test_store_error(self):
        err = SnapshotStoreError("store full")
        assert "PS-005" in str(err.code)

    def test_cache_error(self):
        err = SnapshotCacheError("cache problem")
        assert "PS-006" in str(err.code)

    def test_version_error(self):
        err = SnapshotVersionError("no version", version=42)
        assert err.version == 42
        assert "PS-007" in str(err.code)

    def test_capacity_error(self):
        err = SnapshotCapacityError(9999)
        assert err.limit == 9999
        assert "PS-008" in str(err.code)

    def test_publication_error(self):
        err = SnapshotPublicationError("cannot publish", portfolio_id="pf-x")
        assert err.portfolio_id == "pf-x"
        assert "PS-009" in str(err.code)

    def test_all_errors_are_subclasses_of_base(self):
        for cls in (
            SnapshotBuildError, SnapshotNotFoundError, SnapshotValidationError,
            SnapshotDuplicateError, SnapshotStoreError, SnapshotCacheError,
            SnapshotVersionError, SnapshotCapacityError, SnapshotPublicationError,
        ):
            assert issubclass(cls, PortfolioSnapshotError)


# ===========================================================================
# 3. Metadata value objects
# ===========================================================================

class TestAuditMetadata:
    def test_create_defaults(self):
        m = SnapshotAuditMetadata.create()
        assert m.built_by
        assert m.built_at > 0
        assert m.validated_at == 0.0
        assert m.published_at == 0.0

    def test_is_frozen(self):
        m = SnapshotAuditMetadata.create()
        with pytest.raises((AttributeError, TypeError)):
            m.built_by = "new"  # type: ignore[misc]

    def test_with_validation(self):
        m = SnapshotAuditMetadata.create()
        m2 = m.with_validation(validated_by="validator", validation_duration_ms=5.0)
        assert m2.validated_by == "validator"
        assert m2.validated_at > 0
        assert m2.validation_duration_ms == 5.0
        # original unchanged
        assert m.validated_by == ""

    def test_with_publication(self):
        m = SnapshotAuditMetadata.create()
        m2 = m.with_publication(published_by="publisher")
        assert m2.published_by == "publisher"
        assert m2.published_at > 0

    def test_to_dict_keys(self):
        m = SnapshotAuditMetadata.create()
        d = m.to_dict()
        for key in ("built_by", "validated_by", "published_by", "build_duration_ms",
                    "framework_version", "built_at"):
            assert key in d

    def test_build_context_is_copied(self):
        ctx = {"k": "v"}
        m = SnapshotAuditMetadata.create(build_context=ctx)
        ctx["extra"] = "should not appear"
        assert "extra" not in m.build_context


class TestPortfolioSnapshotMetadata:
    def test_create(self):
        m = PortfolioSnapshotMetadata.create("s-1", "pf-1")
        assert m.snapshot_id == "s-1"
        assert m.portfolio_id == "pf-1"
        assert m.framework_version == VERSION

    def test_tags_are_tuple(self):
        m = PortfolioSnapshotMetadata.create("s-1", "pf-1", tags=["a", "b"])
        assert isinstance(m.tags, tuple)
        assert "a" in m.tags

    def test_labels_are_dict(self):
        m = PortfolioSnapshotMetadata.create("s-1", "pf-1", labels={"env": "prod"})
        assert m.labels["env"] == "prod"

    def test_is_frozen(self):
        m = PortfolioSnapshotMetadata.create("s-1", "pf-1")
        with pytest.raises((AttributeError, TypeError)):
            m.snapshot_id = "x"  # type: ignore[misc]

    def test_to_dict_round_trip(self):
        m = PortfolioSnapshotMetadata.create("s-1", "pf-1", tags=["t"], labels={"k": "v"})
        d = m.to_dict()
        assert d["snapshot_id"] == "s-1"
        assert d["tags"] == ["t"]
        assert d["labels"] == {"k": "v"}


# ===========================================================================
# 4. PortfolioSnapshot core
# ===========================================================================

class TestPortfolioSnapshot:
    def test_construction(self, snap):
        assert snap.portfolio_id == "pf-001"
        assert snap.portfolio_session_id == "sess-001"

    def test_is_frozen(self, snap):
        with pytest.raises((AttributeError, TypeError)):
            snap.portfolio_id = "new"  # type: ignore[misc]

    def test_is_draft(self, snap):
        assert snap.is_draft
        assert not snap.is_published
        assert not snap.is_validated
        assert not snap.is_archived

    def test_with_status_to_validated(self, snap):
        v = snap.with_status(SnapshotStatus.VALIDATED)
        assert v.is_validated
        assert v.snapshot_id == snap.snapshot_id
        # original unchanged
        assert snap.is_draft

    def test_with_status_to_published(self, snap):
        p = snap.with_status(SnapshotStatus.PUBLISHED)
        assert p.is_published
        assert p.is_validated

    def test_with_status_to_archived(self, snap):
        a = snap.with_status(SnapshotStatus.ARCHIVED)
        assert a.is_archived

    def test_is_healthy(self, snap):
        assert snap.is_healthy

    def test_is_not_healthy_degraded(self):
        s = _make_snapshot(portfolio_health=PortfolioHealth.DEGRADED.value)
        assert not s.is_healthy

    def test_to_dict_has_all_summary_keys(self, snap):
        d = snap.to_dict()
        for key in (
            "decision_summary", "allocation_summary", "rebalancing_summary",
            "exposure_summary", "diversification_summary", "risk_summary",
            "liquidity_summary", "cash_summary", "constraint_summary",
            "optimization_summary",
        ):
            assert key in d

    def test_to_dict_has_composition_keys(self, snap):
        d = snap.to_dict()
        for key in (
            "current_holdings", "target_holdings", "cash_balance",
            "reserved_capital", "sector_allocation", "industry_allocation",
            "asset_allocation", "strategy_allocation", "regional_allocation",
            "currency_allocation", "position_count", "exposure_metrics",
        ):
            assert key in d

    def test_to_dict_has_metadata_keys(self, snap):
        d = snap.to_dict()
        assert "portfolio_metadata" in d
        assert "audit_metadata" in d
        assert "framework_version" in d
        assert "timestamp" in d

    def test_to_dict_metadata_is_dict(self, snap):
        d = snap.to_dict()
        assert isinstance(d["portfolio_metadata"], dict)
        assert isinstance(d["audit_metadata"], dict)

    def test_holdings_are_tuple(self):
        s = _make_snapshot(current_holdings=[{"sym": "RELIANCE"}])
        assert isinstance(s.current_holdings, tuple)
        assert s.position_count == 1

    def test_position_count_matches_holdings(self):
        s = _make_snapshot(
            current_holdings=[{"sym": "TCS"}, {"sym": "INFY"}],
        )
        assert s.position_count == 2

    def test_with_audit(self, snap):
        new_audit = SnapshotAuditMetadata.create(build_duration_ms=99.0)
        updated = snap.with_audit(new_audit)
        assert updated.audit_metadata.build_duration_ms == 99.0
        assert snap.audit_metadata.build_duration_ms != 99.0

    def test_snapshot_id_is_uuid(self, snap):
        # Must be parseable as UUID
        uuid.UUID(snap.snapshot_id)

    def test_timestamp_is_recent(self, snap):
        assert snap.timestamp <= time.time()
        assert snap.timestamp >= time.time() - 5


# ===========================================================================
# 5. SnapshotEvents
# ===========================================================================

class TestSnapshotEvents:
    def _check_event(self, event, expected_type, snapshot_id="s-1", portfolio_id="p-1"):
        assert isinstance(event, SnapshotEvent)
        assert event.event_type == expected_type.value
        assert event.snapshot_id == snapshot_id
        assert event.portfolio_id == portfolio_id
        assert event.occurred_at > 0
        assert isinstance(event.payload, dict)
        uuid.UUID(event.event_id)   # must be valid UUID

    def test_make_snapshot_created(self):
        e = make_snapshot_created("s-1", "p-1")
        self._check_event(e, SnapshotEventType.SNAPSHOT_CREATED)

    def test_make_snapshot_validated(self):
        e = make_snapshot_validated("s-1", "p-1", passed_checks=12)
        self._check_event(e, SnapshotEventType.SNAPSHOT_VALIDATED)
        assert e.payload["passed_checks"] == 12

    def test_make_snapshot_published(self):
        e = make_snapshot_published("s-1", "p-1", publisher="engine")
        self._check_event(e, SnapshotEventType.SNAPSHOT_PUBLISHED)
        assert e.payload["publisher"] == "engine"

    def test_make_snapshot_archived(self):
        e = make_snapshot_archived("s-1", "p-1", reason="eod")
        self._check_event(e, SnapshotEventType.SNAPSHOT_ARCHIVED)
        assert e.payload["reason"] == "eod"

    def test_make_snapshot_retrieved(self):
        e = make_snapshot_retrieved("s-1", "p-1", requester="risk")
        self._check_event(e, SnapshotEventType.SNAPSHOT_RETRIEVED)

    def test_make_snapshot_cached(self):
        e = make_snapshot_cached("s-1", "p-1", cache_key="cache-1")
        self._check_event(e, SnapshotEventType.SNAPSHOT_CACHED)
        assert e.payload["cache_key"] == "cache-1"

    def test_event_is_frozen(self):
        e = make_snapshot_created("s-1", "p-1")
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "new"  # type: ignore[misc]

    def test_event_to_dict(self):
        e = make_snapshot_created("s-1", "p-1")
        d = e.to_dict()
        assert d["snapshot_id"] == "s-1"
        assert d["portfolio_id"] == "p-1"

    def test_each_event_has_unique_id(self):
        ids = {make_snapshot_created("s-1", "p-1").event_id for _ in range(10)}
        assert len(ids) == 10

    def test_custom_payload_merged(self):
        e = make_snapshot_created("s-1", "p-1", payload={"extra": "data"})
        assert e.payload["extra"] == "data"


# ===========================================================================
# 6. SnapshotValidation (12 checks)
# ===========================================================================

class TestSnapshotValidation:
    def test_valid_snapshot_passes_all_12(self, snap, validator):
        result = validator.validate(snap)
        assert result.is_valid
        assert result.passed_count == 12
        assert result.failed_count == 0

    def test_result_is_frozen(self, snap, validator):
        result = validator.validate(snap)
        with pytest.raises((AttributeError, TypeError)):
            result.is_valid = False  # type: ignore[misc]

    def test_check_result_is_frozen(self, snap, validator):
        result = validator.validate(snap)
        chk = result.checks[0]
        with pytest.raises((AttributeError, TypeError)):
            chk.passed = False  # type: ignore[misc]

    def test_identifier_consistency_fails_empty_portfolio_id(self, validator):
        snap = _make_snapshot()
        import dataclasses
        bad = dataclasses.replace(snap, portfolio_id="")
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.IDENTIFIER_CONSISTENCY.value in codes

    def test_identifier_consistency_fails_mismatched_metadata(self, validator):
        snap = _make_snapshot()
        import dataclasses
        bad = dataclasses.replace(snap, portfolio_id="different-pf")
        result = validator.validate(bad)
        assert not result.is_valid

    def test_lifecycle_consistency_fails_unknown_state(self, validator):
        import dataclasses
        snap = _make_snapshot()
        bad = dataclasses.replace(snap, lifecycle_state="bogus_state_xyz")
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.LIFECYCLE_CONSISTENCY.value in codes

    def test_lifecycle_consistency_fails_empty_state(self, validator):
        import dataclasses
        snap = _make_snapshot()
        bad = dataclasses.replace(snap, lifecycle_state="")
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.LIFECYCLE_CONSISTENCY.value in codes

    def test_allocation_consistency_fails_negative_cash(self, validator):
        import dataclasses
        snap = _make_snapshot()
        bad = dataclasses.replace(snap, cash_balance=-100.0)
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.ALLOCATION_CONSISTENCY.value in codes

    def test_allocation_consistency_fails_negative_weight(self, validator):
        import dataclasses
        snap = _make_snapshot(sector_allocation={"IT": -0.1})
        result = validator.validate(snap)
        assert not result.is_valid

    def test_portfolio_consistency_fails_negative_position_count(self, validator):
        import dataclasses
        snap = _make_snapshot()
        bad = dataclasses.replace(snap, position_count=-1)
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.PORTFOLIO_CONSISTENCY.value in codes

    def test_portfolio_consistency_fails_count_mismatch(self, validator):
        import dataclasses
        snap = _make_snapshot(current_holdings=[{"sym": "TCS"}])
        bad = dataclasses.replace(snap, position_count=5)
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.PORTFOLIO_CONSISTENCY.value in codes

    def test_snapshot_completeness_fails_empty_name(self, validator):
        import dataclasses
        snap = _make_snapshot()
        bad = dataclasses.replace(snap, portfolio_name="")
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.SNAPSHOT_COMPLETENESS.value in codes

    def test_version_compatibility_fails_empty_framework(self, validator):
        import dataclasses
        snap = _make_snapshot()
        bad = dataclasses.replace(snap, framework_version="")
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.VERSION_COMPATIBILITY.value in codes

    def test_audit_consistency_fails_empty_built_by(self, validator):
        import dataclasses
        snap = _make_snapshot()
        new_audit = dataclasses.replace(snap.audit_metadata, built_by="")
        bad = dataclasses.replace(snap, audit_metadata=new_audit)
        result = validator.validate(bad)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.AUDIT_CONSISTENCY.value in codes

    def test_error_messages_populate_on_failure(self, validator):
        import dataclasses
        snap = _make_snapshot()
        bad = dataclasses.replace(snap, portfolio_name="", cash_balance=-1.0)
        result = validator.validate(bad)
        assert len(result.error_messages) >= 2

    def test_duration_is_positive(self, snap, validator):
        result = validator.validate(snap)
        assert result.duration_s >= 0

    def test_from_checks_helper(self):
        checks = (
            SnapshotValidationCheckResult(code="c1", passed=True, message=""),
            SnapshotValidationCheckResult(code="c2", passed=False, message="fail"),
        )
        result = SnapshotValidationResult.from_checks(checks, 0.001)
        assert not result.is_valid
        assert result.passed_count == 1
        assert result.failed_count == 1


# ===========================================================================
# 7. SnapshotStatistics
# ===========================================================================

class TestSnapshotStatistics:
    def test_initial_state_all_zeros(self):
        stats = PortfolioSnapshotStatistics()
        d = stats.snapshot()
        for key in (
            "snapshots_created", "snapshots_published", "snapshots_archived",
            "validation_successes", "validation_failures",
            "cache_hits", "cache_misses",
        ):
            assert d[key] == 0

    def test_record_created(self):
        stats = PortfolioSnapshotStatistics()
        stats.record_created(build_time_ms=10.0)
        stats.record_created(build_time_ms=20.0)
        d = stats.snapshot()
        assert d["snapshots_created"] == 2
        assert d["avg_build_time_ms"] == 15.0

    def test_record_published(self):
        stats = PortfolioSnapshotStatistics()
        stats.record_published()
        assert stats.snapshot()["snapshots_published"] == 1

    def test_record_archived(self):
        stats = PortfolioSnapshotStatistics()
        stats.record_archived()
        assert stats.snapshot()["snapshots_archived"] == 1

    def test_record_validation(self):
        stats = PortfolioSnapshotStatistics()
        stats.record_validation_success(duration_ms=5.0)
        stats.record_validation_failure(duration_ms=5.0)
        d = stats.snapshot()
        assert d["validation_successes"] == 1
        assert d["validation_failures"] == 1
        assert d["avg_validation_time_ms"] == 5.0

    def test_record_cache_hits_misses(self):
        stats = PortfolioSnapshotStatistics()
        stats.record_cache_hit()
        stats.record_cache_miss()
        d = stats.snapshot()
        assert d["cache_hits"] == 1
        assert d["cache_misses"] == 1

    def test_record_snapshot_size(self):
        stats = PortfolioSnapshotStatistics()
        stats.record_snapshot_size(30)
        stats.record_snapshot_size(50)
        assert stats.snapshot()["avg_snapshot_size_keys"] == 40.0

    def test_reset(self):
        stats = PortfolioSnapshotStatistics()
        stats.record_created()
        stats.record_published()
        stats.reset()
        d = stats.snapshot()
        assert d["snapshots_created"] == 0
        assert d["snapshots_published"] == 0

    def test_avg_build_zero_when_no_samples(self):
        stats = PortfolioSnapshotStatistics()
        assert stats.snapshot()["avg_build_time_ms"] == 0.0


# ===========================================================================
# 8. SnapshotCache
# ===========================================================================

class TestSnapshotCache:
    def test_put_and_get(self, snap, cache):
        cache.put(snap)
        result = cache.get(snap.snapshot_id)
        assert result is snap

    def test_get_missing_returns_none(self, cache):
        assert cache.get("nonexistent") is None

    def test_contains(self, snap, cache):
        cache.put(snap)
        assert cache.contains(snap.snapshot_id)
        assert not cache.contains("other")

    def test_get_latest(self, snap, cache):
        cache.put(snap)
        result = cache.get_latest(snap.portfolio_id)
        assert result is snap

    def test_get_latest_missing_returns_none(self, cache):
        assert cache.get_latest("pf-nonexistent") is None

    def test_lru_eviction_on_capacity(self):
        cache = PortfolioSnapshotCache(max_size=3)
        snaps = [_make_snapshot(portfolio_id=f"pf-{i}", portfolio_session_id=f"s-{i}") for i in range(4)]
        for s in snaps:
            cache.put(s)
        assert cache.size() == 3
        # LRU (first inserted) should be gone
        assert cache.get(snaps[0].snapshot_id) is None

    def test_put_updates_existing(self, snap, cache):
        cache.put(snap)
        updated = snap.with_status(SnapshotStatus.VALIDATED)
        cache.put(updated)
        result = cache.get(snap.snapshot_id)
        assert result.is_validated

    def test_invalidate(self, snap, cache):
        cache.put(snap)
        result = cache.invalidate(snap.snapshot_id)
        assert result is True
        assert cache.get(snap.snapshot_id) is None

    def test_invalidate_missing_returns_false(self, cache):
        assert cache.invalidate("nonexistent") is False

    def test_invalidate_portfolio(self):
        cache = PortfolioSnapshotCache()
        s1 = _make_snapshot(portfolio_id="pf-x", portfolio_session_id="s-1", snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(portfolio_id="pf-x", portfolio_session_id="s-1", snapshot_id=str(uuid.uuid4()))
        cache.put(s1)
        cache.put(s2)
        removed = cache.invalidate_portfolio("pf-x")
        assert removed == 2
        assert cache.size() == 0

    def test_clear(self, snap, cache):
        cache.put(snap)
        cache.clear()
        assert cache.size() == 0

    def test_statistics_hit_rate(self):
        cache = PortfolioSnapshotCache()
        s = _make_snapshot()
        cache.put(s)
        cache.get(s.snapshot_id)   # hit
        cache.get("missing")       # miss
        stats = cache.statistics()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_max_size_zero_raises(self):
        with pytest.raises(Exception):
            PortfolioSnapshotCache(max_size=0)


# ===========================================================================
# 9. SnapshotHistory
# ===========================================================================

class TestSnapshotHistory:
    def test_record_and_get_versions(self, history):
        s1 = _make_snapshot(snapshot_version=1)
        s2 = _make_snapshot(snapshot_version=2)
        history.record(s1)
        history.record(s2)
        versions = history.get_versions("pf-001")
        assert len(versions) == 2

    def test_get_versions_empty(self, history):
        assert history.get_versions("nonexistent") == []

    def test_latest(self, history):
        s1 = _make_snapshot(snapshot_version=1)
        s2 = _make_snapshot(snapshot_version=2)
        history.record(s1)
        history.record(s2)
        assert history.latest("pf-001").snapshot_version == 2

    def test_latest_missing_returns_none(self, history):
        assert history.latest("nonexistent") is None

    def test_get_version_by_number(self, history):
        s1 = _make_snapshot(snapshot_version=1)
        s3 = _make_snapshot(snapshot_version=3)
        history.record(s1)
        history.record(s3)
        found = history.get_version("pf-001", 3)
        assert found is s3

    def test_get_version_missing_returns_none(self, history):
        s = _make_snapshot(snapshot_version=1)
        history.record(s)
        assert history.get_version("pf-001", 99) is None

    def test_version_count(self, history):
        for v in range(5):
            history.record(_make_snapshot(snapshot_version=v + 1))
        assert history.version_count("pf-001") == 5

    def test_bounded_deque_drops_oldest(self):
        hist = PortfolioSnapshotHistory(max_versions_per_portfolio=3)
        for v in range(5):
            hist.record(_make_snapshot(snapshot_version=v + 1))
        versions = hist.get_versions("pf-001")
        assert len(versions) == 3
        assert versions[0].snapshot_version == 3

    def test_portfolio_count(self, history):
        history.record(_make_snapshot(portfolio_id="pf-1", portfolio_session_id="s-1"))
        history.record(_make_snapshot(portfolio_id="pf-2", portfolio_session_id="s-2"))
        assert history.portfolio_count() == 2

    def test_has_portfolio(self, history):
        history.record(_make_snapshot())
        assert history.has_portfolio("pf-001")
        assert not history.has_portfolio("pf-999")

    def test_clear_portfolio(self, history):
        history.record(_make_snapshot())
        assert history.clear_portfolio("pf-001") is True
        assert history.version_count("pf-001") == 0
        assert history.clear_portfolio("pf-001") is False

    def test_clear(self, history):
        history.record(_make_snapshot())
        history.clear()
        assert history.portfolio_count() == 0

    def test_limit_parameter(self, history):
        for v in range(10):
            history.record(_make_snapshot(snapshot_version=v + 1))
        versions = history.get_versions("pf-001", limit=3)
        assert len(versions) == 3
        # Should be the 3 most recent
        assert versions[-1].snapshot_version == 10


# ===========================================================================
# 10. SnapshotStore
# ===========================================================================

class TestSnapshotStore:
    def test_save_and_get(self, snap, store):
        store.save(snap)
        result = store.get(snap.snapshot_id)
        assert result is snap

    def test_get_missing_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_get_or_raise_missing(self, store):
        with pytest.raises(SnapshotNotFoundError):
            store.get_or_raise("nonexistent")

    def test_duplicate_raises(self, snap, store):
        store.save(snap)
        with pytest.raises(SnapshotDuplicateError):
            store.save(snap)

    def test_capacity_error(self):
        store = PortfolioSnapshotStore(max_size=2)
        for i in range(2):
            store.save(_make_snapshot(
                portfolio_id=f"pf-{i}", portfolio_session_id=f"s-{i}",
                snapshot_id=str(uuid.uuid4()),
            ))
        with pytest.raises(SnapshotCapacityError):
            store.save(_make_snapshot(
                portfolio_id="pf-overflow", portfolio_session_id="s-overflow",
                snapshot_id=str(uuid.uuid4()),
            ))

    def test_get_latest(self, store):
        s1 = _make_snapshot(snapshot_version=1)
        s2 = _make_snapshot(snapshot_version=2)
        store.save(s1)
        store.save(s2)
        latest = store.get_latest("pf-001")
        # latest should be s2 (last saved)
        assert latest.snapshot_version == 2

    def test_find_by_portfolio(self, store):
        s1 = _make_snapshot(portfolio_id="pf-A", portfolio_session_id="s-1", snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(portfolio_id="pf-A", portfolio_session_id="s-1", snapshot_id=str(uuid.uuid4()))
        s3 = _make_snapshot(portfolio_id="pf-B", portfolio_session_id="s-2", snapshot_id=str(uuid.uuid4()))
        for s in (s1, s2, s3):
            store.save(s)
        results = store.find_by_portfolio("pf-A")
        assert len(results) == 2

    def test_find_by_session(self, store):
        s1 = _make_snapshot(portfolio_session_id="sess-X", snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(portfolio_id="pf-002", portfolio_session_id="sess-Y", snapshot_id=str(uuid.uuid4()))
        store.save(s1)
        store.save(s2)
        results = store.find_by_session("sess-X")
        assert len(results) == 1

    def test_find_by_type(self, store):
        s1 = _make_snapshot(portfolio_type="equity", snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(portfolio_type="debt", portfolio_id="pf-002", portfolio_session_id="s-2", snapshot_id=str(uuid.uuid4()))
        store.save(s1)
        store.save(s2)
        assert len(store.find_by_type("equity")) == 1
        assert len(store.find_by_type("debt")) == 1

    def test_find_by_status(self, store):
        s1 = _make_snapshot(snapshot_status=SnapshotStatus.DRAFT.value, snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(
            portfolio_id="pf-002", portfolio_session_id="s-2",
            snapshot_status=SnapshotStatus.PUBLISHED.value,
            snapshot_id=str(uuid.uuid4()),
        )
        store.save(s1)
        store.save(s2)
        published = store.find_by_status(SnapshotStatus.PUBLISHED)
        assert len(published) == 1

    def test_find_by_health(self, store):
        s1 = _make_snapshot(portfolio_health=PortfolioHealth.HEALTHY.value, snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(
            portfolio_id="pf-002", portfolio_session_id="s-2",
            portfolio_health=PortfolioHealth.DEGRADED.value,
            snapshot_id=str(uuid.uuid4()),
        )
        store.save(s1)
        store.save(s2)
        assert len(store.find_by_health("healthy")) == 1
        assert len(store.find_by_health("degraded")) == 1

    def test_find_by_name(self, store):
        s1 = _make_snapshot(portfolio_name="Alpha Fund", snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(portfolio_id="pf-002", portfolio_session_id="s-2", portfolio_name="Beta Fund", snapshot_id=str(uuid.uuid4()))
        store.save(s1)
        store.save(s2)
        assert len(store.find_by_name("Alpha Fund")) == 1

    def test_find_by_timestamp_range(self, store):
        before = time.time() - 1
        s = _make_snapshot()
        store.save(s)
        after = time.time() + 1
        found = store.find_by_timestamp_range(before, after)
        assert s in found

    def test_archive(self, snap, store):
        store.save(snap)
        result = store.archive(snap.snapshot_id)
        assert result is True
        archived = store.get(snap.snapshot_id)
        assert archived.is_archived

    def test_archive_nonexistent_returns_false(self, store):
        assert store.archive("nonexistent") is False

    def test_archive_already_archived_returns_false(self, store):
        s = _make_snapshot(snapshot_status=SnapshotStatus.ARCHIVED.value)
        store.save(s)
        assert store.archive(s.snapshot_id) is False

    def test_count(self, store):
        for i in range(3):
            store.save(_make_snapshot(
                portfolio_id=f"pf-{i}", portfolio_session_id=f"s-{i}",
                snapshot_id=str(uuid.uuid4()),
            ))
        assert store.count() == 3

    def test_contains(self, snap, store):
        store.save(snap)
        assert store.contains(snap.snapshot_id)

    def test_clear(self, snap, store):
        store.save(snap)
        store.clear()
        assert store.count() == 0
        assert store.get(snap.snapshot_id) is None

    def test_update(self, snap, store):
        store.save(snap)
        updated = snap.with_status(SnapshotStatus.PUBLISHED)
        store.update(updated)
        result = store.get(snap.snapshot_id)
        assert result.is_published

    def test_all(self, store):
        for i in range(3):
            store.save(_make_snapshot(
                portfolio_id=f"pf-{i}", portfolio_session_id=f"s-{i}",
                snapshot_id=str(uuid.uuid4()),
            ))
        assert len(store.all()) == 3

    def test_query_generic_filter(self, store):
        s1 = _make_snapshot(portfolio_type="equity", snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(
            portfolio_id="pf-002", portfolio_session_id="s-2",
            portfolio_type="debt", snapshot_id=str(uuid.uuid4()),
        )
        store.save(s1)
        store.save(s2)
        results = store.query(portfolio_type="equity")
        assert len(results) == 1


# ===========================================================================
# 11. SnapshotRegistry
# ===========================================================================

class TestSnapshotRegistry:
    def test_register_and_get(self, snap, registry):
        registry.register(snap)
        result = registry.get(snap.snapshot_id)
        assert result is not None
        assert result.snapshot_id == snap.snapshot_id

    def test_get_missing_returns_none(self, registry):
        assert registry.get("nonexistent") is None

    def test_get_or_raise_missing(self, registry):
        with pytest.raises(SnapshotNotFoundError):
            registry.get_or_raise("nonexistent")

    def test_get_latest(self, registry):
        s1 = _make_snapshot(snapshot_version=1)
        s2 = _make_snapshot(snapshot_version=2)
        registry.register(s1)
        registry.register(s2)
        latest = registry.get_latest("pf-001")
        assert latest is not None

    def test_get_history(self, registry):
        for v in range(3):
            registry.register(_make_snapshot(snapshot_version=v + 1))
        history = registry.get_history("pf-001")
        assert len(history) == 3

    def test_publish(self, snap, registry):
        registry.register(snap)
        published = registry.publish(snap.snapshot_id)
        assert published.is_published

    def test_publish_updates_cache(self, snap, registry):
        registry.register(snap)
        registry.publish(snap.snapshot_id)
        cached = registry.get(snap.snapshot_id)
        assert cached.is_published

    def test_archive(self, snap, registry):
        registry.register(snap)
        result = registry.archive(snap.snapshot_id)
        assert result is True
        archived = registry.get(snap.snapshot_id)
        assert archived.is_archived

    def test_count(self, registry):
        for i in range(5):
            registry.register(_make_snapshot(
                portfolio_id=f"pf-{i}", portfolio_session_id=f"s-{i}",
            ))
        assert registry.count() == 5

    def test_query_by_type(self, registry):
        registry.register(_make_snapshot(portfolio_type="equity"))
        registry.register(_make_snapshot(
            portfolio_id="pf-002", portfolio_session_id="s-2", portfolio_type="debt",
        ))
        results = registry.query(portfolio_type="equity")
        assert len(results) == 1

    def test_find_by_portfolio(self, registry):
        for i in range(3):
            registry.register(_make_snapshot(snapshot_version=i + 1))
        results = registry.find_by_portfolio("pf-001")
        assert len(results) == 3

    def test_statistics_returned(self, registry):
        snap = _make_snapshot()
        registry.register(snap)
        stats = registry.statistics()
        assert "snapshots_created" in stats

    def test_auto_validate_on_register(self):
        reg = PortfolioSnapshotRegistry(auto_validate=True)
        snap = _make_snapshot()
        registered = reg.register(snap)
        assert registered.is_validated

    def test_clear(self, registry):
        registry.register(_make_snapshot())
        registry.clear()
        assert registry.count() == 0

    def test_validate_without_registering(self, snap, registry):
        result = registry.validate(snap)
        assert result.is_valid
        assert registry.count() == 0  # not registered

    def test_get_by_session(self, registry):
        s = _make_snapshot(portfolio_session_id="my-session")
        registry.register(s)
        results = registry.get_by_session("my-session")
        assert len(results) == 1

    def test_find_by_health(self, registry):
        registry.register(_make_snapshot(portfolio_health=PortfolioHealth.DEGRADED.value,
                                          portfolio_id="pf-d", portfolio_session_id="s-d"))
        results = registry.find_by_health("degraded")
        assert len(results) == 1


# ===========================================================================
# 12. SnapshotBuilder
# ===========================================================================

class TestSnapshotBuilder:
    def test_basic_build(self, builder):
        snap = builder.build(
            portfolio_id="pf-1",
            portfolio_session_id="sess-1",
            portfolio_name="My Fund",
            lifecycle_state="running",
        )
        assert snap.portfolio_id == "pf-1"
        assert snap.portfolio_name == "My Fund"
        assert snap.is_draft

    def test_rejects_empty_portfolio_id(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build(portfolio_id="", portfolio_session_id="s-1")

    def test_rejects_empty_session_id(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build(portfolio_id="pf-1", portfolio_session_id="")

    def test_rejects_invalid_lifecycle_state(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build(
                portfolio_id="pf-1",
                portfolio_session_id="s-1",
                lifecycle_state="__invalid__",
            )

    def test_rejects_empty_lifecycle_state(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build(
                portfolio_id="pf-1",
                portfolio_session_id="s-1",
                lifecycle_state="",
            )

    def test_rejects_non_string_optimization_status(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build(
                portfolio_id="pf-1",
                portfolio_session_id="s-1",
                optimization_summary={"status": 123},
            )

    def test_rejects_duplicate_snapshot_id(self, builder):
        sid = str(uuid.uuid4())
        builder.build(portfolio_id="pf-1", portfolio_session_id="s-1", snapshot_id=sid)
        with pytest.raises(SnapshotDuplicateError):
            builder.build(portfolio_id="pf-1", portfolio_session_id="s-1", snapshot_id=sid)

    def test_unique_ids_generated_automatically(self, builder):
        s1 = builder.build(portfolio_id="pf-1", portfolio_session_id="s-1")
        s2 = builder.build(portfolio_id="pf-1", portfolio_session_id="s-1")
        assert s1.snapshot_id != s2.snapshot_id

    def test_reset_clears_seen_ids(self):
        builder = PortfolioSnapshotBuilder()
        sid = str(uuid.uuid4())
        builder.build(portfolio_id="pf-1", portfolio_session_id="s-1", snapshot_id=sid)
        builder.reset()
        # Should not raise after reset
        builder.build(portfolio_id="pf-1", portfolio_session_id="s-1", snapshot_id=sid)

    def test_build_with_holdings(self, builder):
        snap = builder.build(
            portfolio_id="pf-1",
            portfolio_session_id="s-1",
            current_holdings=[{"sym": "TCS"}, {"sym": "INFY"}],
        )
        assert snap.position_count == 2
        assert len(snap.current_holdings) == 2

    def test_build_from_context(self, builder):
        ctx = {
            "portfolio_id":         "pf-ctx",
            "portfolio_session_id": "sess-ctx",
            "portfolio_name":       "Context Fund",
            "lifecycle_state":      "active",
            "portfolio_type":       "equity",
        }
        snap = builder.build_from_context(ctx)
        assert snap.portfolio_id == "pf-ctx"
        assert snap.portfolio_name == "Context Fund"
        assert snap.portfolio_type == "equity"

    def test_build_from_context_rejects_non_dict(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build_from_context("not a dict")  # type: ignore

    def test_build_from_context_rejects_empty_portfolio_id(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build_from_context({"portfolio_session_id": "s-1"})

    def test_allocation_dicts_are_copied(self, builder):
        allocs = {"IT": 0.3, "Finance": 0.2}
        snap = builder.build(
            portfolio_id="pf-1",
            portfolio_session_id="s-1",
            sector_allocation=allocs,
        )
        allocs["IT"] = 0.99
        assert snap.sector_allocation["IT"] == 0.3

    def test_build_all_valid_lifecycle_states(self, builder):
        for state in ("initialising", "running", "paused", "stopped", "error",
                      "active", "inactive", "pending"):
            builder.build(portfolio_id="pf-1", portfolio_session_id="s-1",
                          lifecycle_state=state)


# ===========================================================================
# 13. SnapshotFactory
# ===========================================================================

class TestSnapshotFactory:
    def test_create_snapshot(self, factory):
        snap = factory.create_snapshot(
            portfolio_id="pf-f",
            portfolio_session_id="s-f",
            portfolio_name="Factory Fund",
            lifecycle_state="running",
        )
        assert snap.portfolio_id == "pf-f"

    def test_create_minimal(self, factory):
        snap = factory.create_minimal("pf-m")
        assert snap.portfolio_id == "pf-m"
        assert snap.portfolio_name == "Unnamed Portfolio"
        assert snap.is_draft

    def test_create_minimal_generates_session_id(self, factory):
        snap = factory.create_minimal("pf-m")
        assert snap.portfolio_session_id != ""

    def test_create_minimal_custom_name(self, factory):
        snap = factory.create_minimal("pf-m", portfolio_name="My Fund")
        assert snap.portfolio_name == "My Fund"

    def test_create_from_dict_round_trip(self, factory):
        original = factory.create_minimal("pf-rt", portfolio_name="Round Trip Fund")
        d = original.to_dict()
        restored = factory.create_from_dict(d)
        assert restored.snapshot_id == original.snapshot_id
        assert restored.portfolio_id == original.portfolio_id
        assert restored.portfolio_name == original.portfolio_name

    def test_create_from_dict_missing_snapshot_id_raises(self, factory):
        with pytest.raises(SnapshotBuildError):
            factory.create_from_dict({"portfolio_id": "pf-1", "portfolio_session_id": "s-1"})

    def test_create_from_dict_missing_portfolio_id_raises(self, factory):
        with pytest.raises(SnapshotBuildError):
            factory.create_from_dict({"snapshot_id": "s-1", "portfolio_session_id": "s-1"})

    def test_create_from_dict_non_dict_raises(self, factory):
        with pytest.raises(SnapshotBuildError):
            factory.create_from_dict("not a dict")  # type: ignore

    def test_create_from_dict_preserves_holdings(self, factory):
        original = factory.create_snapshot(
            portfolio_id="pf-h", portfolio_session_id="s-h",
            current_holdings=[{"sym": "NIFTY"}],
        )
        restored = factory.create_from_dict(original.to_dict())
        assert len(restored.current_holdings) == 1
        assert restored.current_holdings[0]["sym"] == "NIFTY"

    def test_create_from_dict_preserves_summaries(self, factory):
        original = factory.create_snapshot(
            portfolio_id="pf-s", portfolio_session_id="s-s",
            risk_summary={"var_95": 0.02},
        )
        restored = factory.create_from_dict(original.to_dict())
        assert restored.risk_summary["var_95"] == 0.02


# ===========================================================================
# 14. SnapshotBundle
# ===========================================================================

class TestSnapshotBundle:
    def test_create_empty_bundle(self):
        bundle = PortfolioSnapshotBundle.empty()
        assert bundle.is_empty
        assert bundle.snapshot_count == 0

    def test_create_with_snapshots(self):
        s1 = _make_snapshot(portfolio_id="pf-1", portfolio_session_id="s-1")
        s2 = _make_snapshot(portfolio_id="pf-2", portfolio_session_id="s-2")
        bundle = PortfolioSnapshotBundle.create([s1, s2], bundle_name="My Bundle")
        assert bundle.snapshot_count == 2
        assert bundle.bundle_name == "My Bundle"

    def test_is_frozen(self):
        bundle = PortfolioSnapshotBundle.empty()
        with pytest.raises((AttributeError, TypeError)):
            bundle.bundle_id = "new"  # type: ignore[misc]

    def test_snapshots_are_tuple(self):
        s = _make_snapshot()
        bundle = PortfolioSnapshotBundle.create([s])
        assert isinstance(bundle.snapshots, tuple)

    def test_get_by_portfolio(self):
        s1 = _make_snapshot(portfolio_id="pf-A", portfolio_session_id="s-1", snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(portfolio_id="pf-A", portfolio_session_id="s-1", snapshot_id=str(uuid.uuid4()))
        s3 = _make_snapshot(portfolio_id="pf-B", portfolio_session_id="s-2", snapshot_id=str(uuid.uuid4()))
        bundle = PortfolioSnapshotBundle.create([s1, s2, s3])
        results = bundle.get_by_portfolio("pf-A")
        assert len(results) == 2

    def test_get_by_id(self):
        s = _make_snapshot()
        bundle = PortfolioSnapshotBundle.create([s])
        result = bundle.get_by_id(s.snapshot_id)
        assert result is s

    def test_get_by_id_missing_returns_none(self):
        bundle = PortfolioSnapshotBundle.empty()
        assert bundle.get_by_id("nonexistent") is None

    def test_latest_per_portfolio(self):
        s1 = _make_snapshot(portfolio_id="pf-A", portfolio_session_id="s-1",
                             snapshot_version=1, snapshot_id=str(uuid.uuid4()))
        s2 = _make_snapshot(portfolio_id="pf-A", portfolio_session_id="s-1",
                             snapshot_version=3, snapshot_id=str(uuid.uuid4()))
        s3 = _make_snapshot(portfolio_id="pf-B", portfolio_session_id="s-2",
                             snapshot_version=2, snapshot_id=str(uuid.uuid4()))
        bundle = PortfolioSnapshotBundle.create([s1, s2, s3])
        latest = bundle.latest_per_portfolio()
        assert latest["pf-A"].snapshot_version == 3
        assert "pf-B" in latest

    def test_portfolio_ids(self):
        s1 = _make_snapshot(portfolio_id="pf-1", portfolio_session_id="s-1")
        s2 = _make_snapshot(portfolio_id="pf-2", portfolio_session_id="s-2")
        bundle = PortfolioSnapshotBundle.create([s1, s2])
        ids = bundle.portfolio_ids()
        assert set(ids) == {"pf-1", "pf-2"}

    def test_to_dict_has_required_keys(self):
        bundle = PortfolioSnapshotBundle.create([_make_snapshot()], bundle_name="Test")
        d = bundle.to_dict()
        for key in ("bundle_id", "bundle_name", "snapshot_count", "snapshots",
                    "created_at", "metadata", "framework_version"):
            assert key in d

    def test_to_dict_snapshots_are_dicts(self):
        bundle = PortfolioSnapshotBundle.create([_make_snapshot()])
        d = bundle.to_dict()
        assert isinstance(d["snapshots"][0], dict)

    def test_metadata_is_copied(self):
        meta = {"env": "prod"}
        bundle = PortfolioSnapshotBundle.create([], metadata=meta)
        meta["env"] = "dev"
        assert bundle.metadata["env"] == "prod"

    def test_bundle_id_is_uuid(self):
        bundle = PortfolioSnapshotBundle.empty()
        uuid.UUID(bundle.bundle_id)


# ===========================================================================
# 15. End-to-end publish workflow
# ===========================================================================

class TestEndToEndPublish:
    def test_full_lifecycle(self):
        """DRAFT → VALIDATED → PUBLISHED → ARCHIVED through the registry."""
        registry = PortfolioSnapshotRegistry(auto_validate=True)
        builder  = PortfolioSnapshotBuilder()

        snap = builder.build(
            portfolio_id="pf-e2e",
            portfolio_session_id="sess-e2e",
            portfolio_name="E2E Portfolio",
            lifecycle_state="running",
            portfolio_type="equity",
            sector_allocation={"IT": 0.4, "Finance": 0.3},
            current_holdings=[{"sym": "TCS"}, {"sym": "INFY"}],
            risk_summary={"var_95": 0.015},
        )

        # Register (auto_validate=True → VALIDATED)
        registered = registry.register(snap)
        assert registered.is_validated

        # Publish
        published = registry.publish(registered.snapshot_id)
        assert published.is_published

        # Archive
        registry.archive(published.snapshot_id)
        archived = registry.get(published.snapshot_id)
        assert archived.is_archived

        # Statistics
        stats = registry.statistics()
        assert stats["snapshots_created"] >= 1
        assert stats["snapshots_published"] >= 1
        assert stats["snapshots_archived"] >= 1

    def test_bundle_aggregation(self):
        """Multiple portfolios bundled and delivered."""
        factory = PortfolioSnapshotFactory()
        snaps = [factory.create_minimal(f"pf-{i}", portfolio_name=f"Fund {i}") for i in range(5)]
        bundle = PortfolioSnapshotBundle.create(snaps, bundle_name="Daily Batch")
        assert bundle.snapshot_count == 5
        assert len(bundle.portfolio_ids()) == 5

    def test_validation_before_publish(self):
        """Validator must pass before publish."""
        registry = PortfolioSnapshotRegistry()
        snap = _make_snapshot()
        registry.register(snap)

        result = registry.validate(snap)
        assert result.is_valid

        published = registry.publish(snap.snapshot_id)
        assert published.is_published

    def test_from_dict_re_registration(self):
        """Snapshot round-tripped through to_dict / from_dict is valid and re-registerable."""
        factory  = PortfolioSnapshotFactory()
        registry = PortfolioSnapshotRegistry()

        original = factory.create_minimal("pf-rt2", portfolio_name="Roundtrip")
        registry.register(original)

        d       = original.to_dict()
        # Simulate new snapshot_id on restore (otherwise duplicate)
        d["snapshot_id"] = str(uuid.uuid4())
        d["portfolio_metadata"]["snapshot_id"] = d["snapshot_id"]

        restored = factory.create_from_dict(d)
        registry.register(restored)

        assert registry.count() == 2


# ===========================================================================
# 16. Concurrency safety
# ===========================================================================

class TestConcurrencySafety:
    def test_store_concurrent_writes(self):
        store = PortfolioSnapshotStore(max_size=200)
        errors = []

        def writer(i: int):
            try:
                store.save(_make_snapshot(
                    portfolio_id=f"pf-{i}",
                    portfolio_session_id=f"s-{i}",
                    snapshot_id=str(uuid.uuid4()),
                ))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert store.count() == 50

    def test_cache_concurrent_put_get(self):
        cache = PortfolioSnapshotCache(max_size=200)
        snaps = [_make_snapshot(
            portfolio_id=f"pf-{i}", portfolio_session_id=f"s-{i}",
            snapshot_id=str(uuid.uuid4()),
        ) for i in range(50)]
        errors = []

        def worker(s):
            try:
                cache.put(s)
                cache.get(s.snapshot_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(s,)) for s in snaps]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_statistics_concurrent_increments(self):
        stats = PortfolioSnapshotStatistics()
        n = 100

        def incrementer():
            for _ in range(n):
                stats.record_created()

        threads = [threading.Thread(target=incrementer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.snapshot()["snapshots_created"] == 5 * n

    def test_history_concurrent_record(self):
        history = PortfolioSnapshotHistory()
        errors = []

        def recorder(portfolio_id, version):
            try:
                history.record(_make_snapshot(
                    portfolio_id=portfolio_id,
                    portfolio_session_id=f"s-{portfolio_id}",
                    snapshot_version=version,
                ))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=recorder, args=(f"pf-{i % 5}", i))
            for i in range(50)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# ===========================================================================
# 17. Regression
# ===========================================================================

class TestRegression:
    def test_snapshot_dict_keys_stable(self, snap):
        """to_dict() output must be stable across calls."""
        d1 = snap.to_dict()
        d2 = snap.to_dict()
        assert d1.keys() == d2.keys()

    def test_snapshot_id_never_empty(self, builder):
        for _ in range(20):
            s = builder.build(portfolio_id="pf-1", portfolio_session_id="s-1")
            assert s.snapshot_id != ""

    def test_builder_error_codes_are_unique(self):
        codes = set()
        for cls in (
            PortfolioSnapshotError, SnapshotBuildError, SnapshotNotFoundError,
            SnapshotValidationError, SnapshotDuplicateError, SnapshotStoreError,
            SnapshotCacheError, SnapshotVersionError, SnapshotCapacityError,
            SnapshotPublicationError,
        ):
            codes.add(cls.error_code)
        assert len(codes) == 10

    def test_event_types_cover_all_6(self):
        factories = [
            make_snapshot_created, make_snapshot_validated, make_snapshot_published,
            make_snapshot_archived, make_snapshot_retrieved, make_snapshot_cached,
        ]
        event_types = {f("s-1", "p-1").event_type for f in factories}
        all_types = {e.value for e in SnapshotEventType}
        assert event_types == all_types

    def test_validation_codes_cover_all_12(self, snap, validator):
        result = validator.validate(snap)
        checked_codes = {c.code for c in result.checks}
        all_codes = {c.value for c in SnapshotValidationCode}
        assert checked_codes == all_codes

    def test_store_secondary_index_consistent_after_update(self):
        store = PortfolioSnapshotStore()
        snap = _make_snapshot(snapshot_status=SnapshotStatus.DRAFT.value)
        store.save(snap)
        updated = snap.with_status(SnapshotStatus.PUBLISHED)
        store.update(updated)
        # Draft index should not contain snap anymore
        drafts = store.find_by_status(SnapshotStatus.DRAFT)
        published = store.find_by_status(SnapshotStatus.PUBLISHED)
        assert all(s.snapshot_id != snap.snapshot_id for s in drafts)
        assert any(s.snapshot_id == snap.snapshot_id for s in published)

    def test_bundle_snapshot_count_property(self):
        snaps = [_make_snapshot(
            portfolio_id=f"pf-{i}", portfolio_session_id=f"s-{i}",
        ) for i in range(7)]
        bundle = PortfolioSnapshotBundle.create(snaps)
        assert bundle.snapshot_count == 7
        assert not bundle.is_empty

    def test_factory_create_from_dict_is_valid(self, factory, validator):
        original = factory.create_minimal("pf-v", portfolio_name="Validation Test")
        d        = original.to_dict()
        restored = factory.create_from_dict(d)
        result   = validator.validate(restored)
        assert result.is_valid

    def test_all_snapshot_status_transitions_valid_enum(self):
        for status in SnapshotStatus:
            targets = VALID_SNAPSHOT_TRANSITIONS[status]
            for t in targets:
                assert isinstance(t, SnapshotStatus)
