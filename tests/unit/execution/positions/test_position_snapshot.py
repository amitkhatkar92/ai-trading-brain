"""tests/unit/execution/positions/test_position_snapshot.py
==================================================
Test suite for C6 Phase 3 M5 — IIOS Position Snapshot.

Coverage targets (95%+):
  * Constants, enums: SnapshotStatus, SnapshotEventType, SnapshotOperationType
  * Status sets: PUBLISHABLE_STATUSES, ACTIVE_STATUSES, TERMINAL_STATUSES
  * Exceptions — hierarchy, error codes, fields
  * SnapshotAuditMetadata — construction, to_dict, from_dict
  * PositionSnapshot — construction, properties, status transitions, to_dict, from_dict
  * SnapshotValidationResult — ok, fail, raise_if_invalid
  * SnapshotValidator — all 7 checks, composite validate
  * SnapshotEvent + 6 factory functions
  * SnapshotEventHistory — append, extend, filters, eviction, clear
  * SnapshotVersionHistory — add, latest, all_versions, get_version, purge
  * SnapshotStatistics — counters, averages, to_dict
  * SnapshotBundle — construction, filters, to_dict
  * PositionSnapshotBuilder — happy path, with risk, with price, validation failures
  * PositionSnapshotFactory — all 4 create methods
  * PositionSnapshotRegistry — lifecycle guard, store, remove, all indexes
  * PositionSnapshotCache — lifecycle, put/get/invalidate/clear, hit_rate
  * PositionSnapshotStore — full lifecycle, build_and_store, validate, publish,
      archive, all query methods, bundles, statistics, events, concurrency
  * Regression guards

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from decimal import Decimal
from typing import List

import pytest

from iios.execution.positions.lifecycle import (
    Position,
    PositionDirection,
    PositionFactory,
    PositionProduct,
    PositionState,
)

from iios.execution.positions.snapshot import (
    # constants
    SNAPSHOT_SYSTEM_ID,
    STORE_SYSTEM_ID,
    CACHE_SYSTEM_ID,
    VERSION,
    ACTOR_SNAPSHOT,
    ACTOR_STORE,
    PUBLISHABLE_STATUSES,
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    # enums
    SnapshotStatus,
    SnapshotEventType,
    SnapshotOperationType,
    # exceptions
    PositionSnapshotError,
    PositionSnapshotNotRunningError,
    SnapshotNotFoundError,
    DuplicateSnapshotError,
    SnapshotValidationError,
    SnapshotBuildError,
    SnapshotCapacityError,
    SnapshotStoreError,
    SnapshotCacheError,
    SnapshotVersionError,
    # value objects
    PositionSnapshot,
    SnapshotAuditMetadata, make_audit_metadata,
    SnapshotValidationResult, SnapshotValidator,
    SnapshotEvent,
    make_snapshot_created_event,
    make_snapshot_validated_event,
    make_snapshot_published_event,
    make_snapshot_archived_event,
    make_snapshot_retrieved_event,
    make_snapshot_cached_event,
    SnapshotEventHistory,
    SnapshotVersionHistory,
    SnapshotStatistics,
    SnapshotBundle, make_snapshot_bundle,
    # builder / factory
    PositionSnapshotBuilder,
    PositionSnapshotFactory,
    # infrastructure
    PositionSnapshotRegistry,
    PositionSnapshotCache,
    # primary facade
    PositionSnapshotStore,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def _make_position(
    instrument:   str = "NIFTY50",
    quantity:     Decimal = Decimal("100"),
    portfolio_id: str = "port-1",
    strategy_id:  str = "strat-1",
    workflow_id:  str = "wf-1",
) -> Position:
    f = PositionFactory()
    return f.create(
        instrument=instrument,
        exchange="NSE",
        product=PositionProduct.FUTURES,
        direction=PositionDirection.LONG,
        quantity=quantity,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id="dec-1",
        workflow_id=workflow_id,
        execution_id="exec-1",
    )


def _make_snapshot(
    position_id:      str = "pos-1",
    instrument:       str = "NIFTY50",
    snapshot_version: int = 1,
    status:           str = SnapshotStatus.VALID.value,
) -> PositionSnapshot:
    return PositionSnapshot(
        snapshot_id=str(uuid.uuid4()),
        snapshot_version=snapshot_version,
        snapshot_status=status,
        position_id=position_id,
        execution_id="exec-1",
        order_id="",
        portfolio_id="port-1",
        strategy_id="strat-1",
        decision_id="dec-1",
        workflow_id="wf-1",
        correlation_id="",
        instrument=instrument,
        exchange="NSE",
        product="FUTURES",
        direction="LONG",
        lifecycle_state="OPEN",
        risk_state="NORMAL",
        current_quantity="100",
        closed_quantity="0",
        average_entry_price="2500",
        average_exit_price="0",
        current_price="2510",
        market_value="251000",
        realized_pnl="0",
        unrealized_pnl="1000",
        exposure="250000",
        margin_used="50000",
        margin_available="50000",
        execution_duration_s=10.0,
        snapshot_taken_at=time.time(),
        position_created_at=time.time() - 10,
        position_updated_at=time.time() - 5,
    )


def _started_store(**kwargs) -> PositionSnapshotStore:
    s = PositionSnapshotStore(**kwargs)
    s.start()
    return s


# ══════════════════════════════════════════════════════════════════════════════
# 1. Constants & enums
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_system_ids_not_empty(self):
        assert SNAPSHOT_SYSTEM_ID
        assert STORE_SYSTEM_ID
        assert CACHE_SYSTEM_ID

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_snapshot_status_values(self):
        assert SnapshotStatus.DRAFT.value     == "DRAFT"
        assert SnapshotStatus.VALID.value     == "VALID"
        assert SnapshotStatus.PUBLISHED.value == "PUBLISHED"
        assert SnapshotStatus.ARCHIVED.value  == "ARCHIVED"
        assert SnapshotStatus.INVALID.value   == "INVALID"

    def test_event_type_values(self):
        assert SnapshotEventType.SNAPSHOT_CREATED.value   == "SNAPSHOT_CREATED"
        assert SnapshotEventType.SNAPSHOT_PUBLISHED.value == "SNAPSHOT_PUBLISHED"
        assert SnapshotEventType.SNAPSHOT_ARCHIVED.value  == "SNAPSHOT_ARCHIVED"

    def test_operation_type_values(self):
        for op in SnapshotOperationType:
            assert op.value

    def test_publishable_statuses(self):
        assert SnapshotStatus.VALID     in PUBLISHABLE_STATUSES
        assert SnapshotStatus.PUBLISHED in PUBLISHABLE_STATUSES
        assert SnapshotStatus.DRAFT     not in PUBLISHABLE_STATUSES

    def test_terminal_statuses(self):
        assert SnapshotStatus.ARCHIVED in TERMINAL_STATUSES
        assert SnapshotStatus.INVALID  in TERMINAL_STATUSES
        assert SnapshotStatus.VALID    not in TERMINAL_STATUSES


# ══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_hierarchy(self):
        e = PositionSnapshotError("base", code="PS5-000")
        assert isinstance(e, Exception)

    def test_not_running(self):
        e = PositionSnapshotNotRunningError()
        assert "not running" in str(e).lower()
        assert isinstance(e, PositionSnapshotError)

    def test_not_found(self):
        e = SnapshotNotFoundError("pos-1")
        assert e.identifier == "pos-1"

    def test_duplicate(self):
        e = DuplicateSnapshotError("snap-abc")
        assert e.snapshot_id == "snap-abc"

    def test_validation_error_has_errors_tuple(self):
        e = SnapshotValidationError("bad", errors=("e1",))
        assert "e1" in e.errors

    def test_build_error_has_fields(self):
        e = SnapshotBuildError("fail", "pos-x", errors=("missing id",))
        assert e.position_id == "pos-x"
        assert "missing id" in e.errors

    def test_capacity_error(self):
        e = SnapshotCapacityError(500)
        assert e.capacity == 500

    def test_store_error(self):
        e = SnapshotStoreError("store fail")
        assert isinstance(e, PositionSnapshotError)

    def test_cache_error(self):
        e = SnapshotCacheError("cache fail")
        assert isinstance(e, PositionSnapshotError)

    def test_version_error(self):
        e = SnapshotVersionError("incompatible")
        assert isinstance(e, PositionSnapshotError)


# ══════════════════════════════════════════════════════════════════════════════
# 3. SnapshotAuditMetadata
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotAuditMetadata:
    def test_construction(self):
        m = SnapshotAuditMetadata(
            built_by="test",
            built_at=time.time(),
            build_duration_ms=1.5,
            source_position_id="pos-1",
            source_snapshot_version=1,
            validation_passed=True,
            validation_errors=(),
        )
        assert m.validation_passed is True
        assert m.source_snapshot_version == 1

    def test_make_audit_metadata_factory(self):
        m = make_audit_metadata(
            source_position_id="pos-1",
            source_snapshot_version=2,
            build_duration_ms=0.5,
            validation_passed=False,
            validation_errors=("err1",),
        )
        assert m.validation_passed is False
        assert "err1" in m.validation_errors
        assert m.built_at > 0

    def test_to_dict(self):
        m = make_audit_metadata("pos-1", 1, 0.3, True)
        d = m.to_dict()
        assert "built_by" in d
        assert "build_duration_ms" in d
        assert d["validation_passed"] is True

    def test_from_dict_roundtrip(self):
        m = make_audit_metadata("pos-x", 3, 2.5, True)
        m2 = SnapshotAuditMetadata.from_dict(m.to_dict())
        assert m2.source_position_id == "pos-x"
        assert m2.source_snapshot_version == 3


# ══════════════════════════════════════════════════════════════════════════════
# 4. PositionSnapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionSnapshot:
    def test_construction(self):
        snap = _make_snapshot()
        assert snap.position_id == "pos-1"
        assert snap.instrument  == "NIFTY50"
        assert snap.snapshot_version == 1

    def test_snapshot_id_is_uuid(self):
        snap = _make_snapshot()
        uuid.UUID(snap.snapshot_id)

    def test_status_properties_valid(self):
        snap = _make_snapshot(status=SnapshotStatus.VALID.value)
        assert snap.is_valid       is True
        assert snap.is_draft       is False
        assert snap.is_published   is False
        assert snap.is_archived    is False
        assert snap.is_publishable is True
        assert snap.is_terminal    is False

    def test_status_properties_published(self):
        snap = _make_snapshot(status=SnapshotStatus.PUBLISHED.value)
        assert snap.is_published   is True
        assert snap.is_publishable is True

    def test_status_properties_archived(self):
        snap = _make_snapshot(status=SnapshotStatus.ARCHIVED.value)
        assert snap.is_archived is True
        assert snap.is_terminal is True

    def test_status_properties_invalid(self):
        snap = _make_snapshot(status=SnapshotStatus.INVALID.value)
        assert snap.is_invalid  is True
        assert snap.is_terminal is True

    def test_as_valid(self):
        snap  = _make_snapshot(status=SnapshotStatus.DRAFT.value)
        valid = snap.as_valid()
        assert valid.is_valid  is True
        assert snap.is_draft   is True  # original unchanged

    def test_as_published(self):
        snap      = _make_snapshot(status=SnapshotStatus.VALID.value)
        published = snap.as_published()
        assert published.is_published is True
        assert published.published_at > 0.0

    def test_as_archived(self):
        snap     = _make_snapshot()
        archived = snap.as_archived()
        assert archived.is_archived is True
        assert archived.archived_at > 0.0

    def test_as_invalid(self):
        snap    = _make_snapshot()
        invalid = snap.as_invalid()
        assert invalid.is_invalid is True

    def test_age_s_positive(self):
        snap = _make_snapshot()
        time.sleep(0.01)
        assert snap.age_s > 0

    def test_to_dict_keys(self):
        snap = _make_snapshot()
        d    = snap.to_dict()
        required = {
            "snapshot_id", "snapshot_version", "snapshot_status",
            "position_id", "instrument", "lifecycle_state", "risk_state",
            "realized_pnl", "unrealized_pnl", "market_value",
            "snapshot_taken_at", "version",
        }
        assert required <= d.keys()

    def test_from_dict_roundtrip(self):
        snap  = _make_snapshot("p-rt", "BANKNIFTY")
        snap2 = PositionSnapshot.from_dict(snap.to_dict())
        assert snap2.position_id  == "p-rt"
        assert snap2.instrument   == "BANKNIFTY"
        assert snap2.snapshot_id  == snap.snapshot_id

    def test_from_dict_missing_optional_fields(self):
        minimal = {
            "snapshot_id": str(uuid.uuid4()),
            "position_id": "pos-x",
            "instrument":  "RELIANCE",
            "snapshot_taken_at": time.time(),
        }
        snap = PositionSnapshot.from_dict(minimal)
        assert snap.position_id == "pos-x"
        assert snap.order_id    == ""

    def test_frozen_prevents_mutation(self):
        snap = _make_snapshot()
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            snap.position_id = "mutated"  # type: ignore[misc]

    def test_repr(self):
        snap = _make_snapshot("repr-pos")
        assert "repr-pos" in repr(snap)
        assert "NIFTY50" in repr(snap)


# ══════════════════════════════════════════════════════════════════════════════
# 5. SnapshotValidation
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotValidationResult:
    def test_ok(self):
        r = SnapshotValidationResult.ok()
        assert r.is_valid is True
        assert r.errors   == ()

    def test_ok_with_warnings(self):
        r = SnapshotValidationResult.ok(["minor warning"])
        assert r.is_valid is True
        assert len(r.warnings) == 1

    def test_fail(self):
        r = SnapshotValidationResult.fail(["err1", "err2"])
        assert r.is_valid is False
        assert "err1" in r.errors

    def test_raise_if_invalid(self):
        with pytest.raises(SnapshotValidationError):
            SnapshotValidationResult.fail(["bad"]).raise_if_invalid()

    def test_raise_if_valid_does_not_raise(self):
        SnapshotValidationResult.ok().raise_if_invalid()


class TestSnapshotValidator:
    def _v(self) -> SnapshotValidator:
        return SnapshotValidator()

    def test_valid_snapshot_passes_all(self):
        snap   = _make_snapshot()
        result = self._v().validate(snap)
        assert result.is_valid

    def test_empty_snapshot_id_fails(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, snapshot_id="")
        result = self._v().validate_identifier_consistency(bad)
        assert not result.is_valid

    def test_empty_position_id_fails(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, position_id="")
        result = self._v().validate_identifier_consistency(bad)
        assert not result.is_valid

    def test_zero_snapshot_version_fails(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, snapshot_version=0)
        result = self._v().validate_identifier_consistency(bad)
        assert not result.is_valid

    def test_invalid_lifecycle_state_fails(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, lifecycle_state="BOGUS_STATE")
        result = self._v().validate_lifecycle_consistency(bad)
        assert not result.is_valid

    def test_valid_lifecycle_states_pass(self):
        for state in ("CREATED", "OPEN", "CLOSED", "ARCHIVED"):
            snap   = _make_snapshot()
            good   = dataclasses.replace(snap, lifecycle_state=state)
            result = self._v().validate_lifecycle_consistency(good)
            assert result.is_valid, f"Expected VALID for state={state}"

    def test_invalid_risk_state_fails(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, risk_state="BOGUS_RISK")
        result = self._v().validate_risk_consistency(bad)
        assert not result.is_valid

    def test_empty_risk_state_passes(self):
        snap   = _make_snapshot()
        empty  = dataclasses.replace(snap, risk_state="")
        result = self._v().validate_risk_consistency(empty)
        assert result.is_valid

    def test_invalid_pnl_decimal_fails(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, realized_pnl="not-a-number")
        result = self._v().validate_pnl_consistency(bad)
        assert not result.is_valid

    def test_negative_quantity_fails(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, current_quantity="-10")
        result = self._v().validate_quantity_consistency(bad)
        assert not result.is_valid

    def test_zero_snapshot_taken_at_fails_completeness(self):
        snap   = _make_snapshot()
        bad    = dataclasses.replace(snap, snapshot_taken_at=0.0)
        result = self._v().validate_completeness(bad)
        assert not result.is_valid

    def test_version_mismatch_produces_warning(self):
        snap   = _make_snapshot()
        old    = dataclasses.replace(snap, version="0.9.0")
        result = self._v().validate_version_compatibility(old)
        assert result.is_valid       # not an error — just a warning
        assert len(result.warnings) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 6. SnapshotEvent factories
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotEvents:
    def _kw(self):
        return dict(portfolio_id="port-1", strategy_id="strat-1", instrument="NIFTY50")

    def test_make_created_event(self):
        e = make_snapshot_created_event("snap-1", 1, "pos-1", **self._kw())
        assert e.event_type    == SnapshotEventType.SNAPSHOT_CREATED
        assert e.position_id   == "pos-1"
        assert e.snapshot_id   == "snap-1"
        uuid.UUID(e.event_id)

    def test_make_validated_event_pass(self):
        e = make_snapshot_validated_event("snap-1", 1, "pos-1", validation_passed=True)
        assert e.snapshot_status == SnapshotStatus.VALID.value

    def test_make_validated_event_fail(self):
        e = make_snapshot_validated_event("snap-1", 1, "pos-1", validation_passed=False)
        assert e.snapshot_status == SnapshotStatus.INVALID.value

    def test_make_published_event(self):
        e = make_snapshot_published_event("snap-1", 1, "pos-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED

    def test_make_archived_event(self):
        e = make_snapshot_archived_event("snap-1", 1, "pos-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_ARCHIVED

    def test_make_retrieved_event(self):
        e = make_snapshot_retrieved_event("snap-1", 1, "pos-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_RETRIEVED

    def test_make_cached_event(self):
        e = make_snapshot_cached_event("snap-1", 1, "pos-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_CACHED

    def test_to_dict_contains_all_fields(self):
        e = make_snapshot_created_event("snap-1", 1, "pos-1")
        d = e.to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert "snapshot_id" in d


# ══════════════════════════════════════════════════════════════════════════════
# 7. SnapshotEventHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotEventHistory:
    def _evt(self, pos="pos-1"):
        return make_snapshot_created_event(str(uuid.uuid4()), 1, pos)

    def test_max_events_lt_1_raises(self):
        with pytest.raises(ValueError):
            SnapshotEventHistory(max_events=0)

    def test_append_and_count(self):
        h = SnapshotEventHistory()
        h.append(self._evt())
        assert h.count() == 1

    def test_extend(self):
        h = SnapshotEventHistory()
        h.extend([self._evt(), self._evt()])
        assert h.count() == 2

    def test_latest(self):
        h = SnapshotEventHistory()
        for i in range(5):
            h.append(self._evt(f"pos-{i}"))
        assert len(h.latest(3)) == 3

    def test_for_position(self):
        h = SnapshotEventHistory()
        h.append(self._evt("A"))
        h.append(self._evt("B"))
        h.append(self._evt("A"))
        assert len(h.for_position("A")) == 2

    def test_for_type(self):
        h = SnapshotEventHistory()
        h.append(self._evt())
        h.append(make_snapshot_published_event(str(uuid.uuid4()), 1, "pos-1"))
        created = h.for_type(SnapshotEventType.SNAPSHOT_CREATED)
        assert len(created) == 1

    def test_filter(self):
        h = SnapshotEventHistory()
        h.append(self._evt("x"))
        h.append(self._evt("y"))
        result = h.filter(lambda e: e.position_id == "x")
        assert len(result) == 1

    def test_eviction_when_full(self):
        h = SnapshotEventHistory(max_events=3)
        for i in range(5):
            h.append(self._evt(f"pos-{i}"))
        assert h.count() == 3

    def test_clear(self):
        h = SnapshotEventHistory()
        h.append(self._evt())
        h.clear()
        assert h.is_empty()

    def test_len(self):
        h = SnapshotEventHistory()
        h.append(self._evt())
        assert len(h) == 1


# ══════════════════════════════════════════════════════════════════════════════
# 8. SnapshotVersionHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotVersionHistory:
    def test_max_versions_lt_1_raises(self):
        with pytest.raises(ValueError):
            SnapshotVersionHistory(max_versions=0)

    def test_add_and_get_latest(self):
        h   = SnapshotVersionHistory()
        s1  = _make_snapshot("vp", snapshot_version=1)
        s2  = _make_snapshot("vp", snapshot_version=2)
        h.add(s1)
        h.add(s2)
        assert h.get_latest("vp") is s2

    def test_get_latest_none_when_absent(self):
        h = SnapshotVersionHistory()
        assert h.get_latest("ghost") is None

    def test_get_all_versions_ordered(self):
        h = SnapshotVersionHistory()
        for v in (1, 2, 3):
            h.add(_make_snapshot("vp", snapshot_version=v))
        versions = h.get_all_versions("vp")
        assert len(versions) == 3
        assert versions[0].snapshot_version == 1
        assert versions[-1].snapshot_version == 3

    def test_get_version(self):
        h  = SnapshotVersionHistory()
        s2 = _make_snapshot("vp", snapshot_version=2)
        h.add(_make_snapshot("vp", snapshot_version=1))
        h.add(s2)
        assert h.get_version("vp", 2) is s2
        assert h.get_version("vp", 99) is None

    def test_get_by_snapshot_id(self):
        h   = SnapshotVersionHistory()
        s   = _make_snapshot("vp", snapshot_version=1)
        h.add(s)
        assert h.get_by_snapshot_id(s.snapshot_id) is s
        assert h.get_by_snapshot_id("ghost-id") is None

    def test_purge(self):
        h = SnapshotVersionHistory()
        h.add(_make_snapshot("vp"))
        h.add(_make_snapshot("vp", snapshot_version=2))
        removed = h.purge("vp")
        assert removed == 2
        assert h.get_latest("vp") is None

    def test_eviction_when_full(self):
        h = SnapshotVersionHistory(max_versions=2)
        for v in range(1, 5):
            h.add(_make_snapshot("vp", snapshot_version=v))
        versions = h.get_all_versions("vp")
        assert len(versions) == 2   # only 2 most recent kept

    def test_count(self):
        h = SnapshotVersionHistory()
        h.add(_make_snapshot("vp", snapshot_version=1))
        h.add(_make_snapshot("vp", snapshot_version=2))
        assert h.count("vp") == 2

    def test_all_position_ids(self):
        h = SnapshotVersionHistory()
        h.add(_make_snapshot("A"))
        h.add(_make_snapshot("B"))
        ids = h.all_position_ids()
        assert "A" in ids
        assert "B" in ids

    def test_total_count(self):
        h = SnapshotVersionHistory()
        h.add(_make_snapshot("A"))
        h.add(_make_snapshot("B"))
        assert h.total_count() == 2


# ══════════════════════════════════════════════════════════════════════════════
# 9. SnapshotStatistics
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotStatistics:
    def test_initial_zeroes(self):
        s = SnapshotStatistics()
        assert s.snapshots_created == 0

    def test_record_created(self):
        s = SnapshotStatistics()
        s.record_created(build_time_ms=5.0)
        assert s.snapshots_created == 1
        assert s.average_build_time_ms == 5.0

    def test_record_published_and_archived(self):
        s = SnapshotStatistics()
        s.record_created()
        s.record_published()
        s.record_archived()
        assert s.snapshots_published == 1
        assert s.snapshots_archived  == 1

    def test_validation_success_rate(self):
        s = SnapshotStatistics()
        s.record_validation_success()
        s.record_validation_success()
        s.record_validation_failure()
        assert abs(s.validation_success_rate - (2/3)) < 1e-9

    def test_validation_success_rate_no_evals(self):
        assert SnapshotStatistics().validation_success_rate == 1.0

    def test_record_retrieved_and_cached(self):
        s = SnapshotStatistics()
        s.record_retrieved()
        s.record_cached()
        assert s.snapshots_retrieved == 1
        assert s.snapshots_cached    == 1

    def test_to_dict(self):
        d = SnapshotStatistics().to_dict()
        assert "snapshots_created"   in d
        assert "validation_successes" in d


# ══════════════════════════════════════════════════════════════════════════════
# 10. SnapshotBundle
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotBundle:
    def test_empty_bundle(self):
        b = make_snapshot_bundle([])
        assert b.is_empty is True
        assert b.count    == 0

    def test_bundle_count(self):
        snaps = [_make_snapshot(f"p{i}") for i in range(3)]
        b     = make_snapshot_bundle(snaps, label="test")
        assert b.count    == 3
        assert b.label    == "test"
        assert b.is_empty is False

    def test_bundle_id_is_uuid(self):
        b = make_snapshot_bundle([])
        uuid.UUID(b.bundle_id)

    def test_position_ids(self):
        snaps = [_make_snapshot(f"p{i}") for i in range(3)]
        b     = make_snapshot_bundle(snaps)
        assert len(b.position_ids) == 3

    def test_by_portfolio(self):
        s1 = dataclasses.replace(_make_snapshot("A"), portfolio_id="port-X")
        s2 = dataclasses.replace(_make_snapshot("B"), portfolio_id="port-Y")
        b  = make_snapshot_bundle([s1, s2])
        assert len(b.by_portfolio("port-X")) == 1

    def test_by_strategy(self):
        s1 = dataclasses.replace(_make_snapshot("A"), strategy_id="strat-X")
        s2 = dataclasses.replace(_make_snapshot("B"), strategy_id="strat-Y")
        b  = make_snapshot_bundle([s1, s2])
        assert len(b.by_strategy("strat-X")) == 1

    def test_by_instrument(self):
        s1 = _make_snapshot("A", instrument="NIFTY50")
        s2 = _make_snapshot("B", instrument="BANKNIFTY")
        b  = make_snapshot_bundle([s1, s2])
        assert len(b.by_instrument("NIFTY50")) == 1

    def test_published_only(self):
        s1 = _make_snapshot(status=SnapshotStatus.PUBLISHED.value)
        s2 = _make_snapshot(status=SnapshotStatus.VALID.value)
        b  = make_snapshot_bundle([s1, s2])
        assert len(b.published_only()) == 1

    def test_to_dict(self):
        b = make_snapshot_bundle([_make_snapshot()])
        d = b.to_dict()
        assert "bundle_id" in d
        assert "count"     in d

    def test_frozen(self):
        b = make_snapshot_bundle([])
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            b.label = "mutated"  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# 11. PositionSnapshotBuilder
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionSnapshotBuilder:
    def _b(self) -> PositionSnapshotBuilder:
        return PositionSnapshotBuilder()

    def test_build_from_position(self):
        pos  = _make_position()
        snap = self._b().build(pos)
        assert snap.position_id       == pos.position_id
        assert snap.instrument        == "NIFTY50"
        assert snap.snapshot_status   == SnapshotStatus.DRAFT.value
        assert snap.lifecycle_state   == "CREATED"
        assert snap.snapshot_version  == 1

    def test_build_with_current_price(self):
        pos  = _make_position()
        snap = self._b().build(pos, current_price=Decimal("2600"))
        assert snap.current_price == "2600"
        # market_value = price * open_quantity (0 for CREATED state)

    def test_build_with_custom_version(self):
        pos  = _make_position()
        snap = self._b().build(pos, snapshot_version=5)
        assert snap.snapshot_version == 5

    def test_build_sets_taken_at(self):
        pos  = _make_position()
        snap = self._b().build(pos)
        assert snap.snapshot_taken_at > 0.0

    def test_build_embeds_audit_metadata(self):
        pos  = _make_position()
        snap = self._b().build(pos)
        assert "built_by" in snap.audit_metadata
        assert snap.audit_metadata["source_position_id"] == pos.position_id

    def test_build_empty_position_id_fails(self):
        pos = _make_position()
        object.__setattr__(pos, "_position_id", "")
        with pytest.raises(SnapshotBuildError):
            self._b().build(pos)

    def test_build_empty_instrument_fails(self):
        pos = _make_position()
        object.__setattr__(pos, "_instrument", "")
        with pytest.raises(SnapshotBuildError):
            self._b().build(pos)

    def test_build_empty_exchange_fails(self):
        pos = _make_position()
        object.__setattr__(pos, "_exchange", "")
        with pytest.raises(SnapshotBuildError):
            self._b().build(pos)

    def test_build_with_order_id(self):
        pos  = _make_position()
        snap = self._b().build(pos, order_id="ORD-123")
        assert snap.order_id == "ORD-123"

    def test_build_snapshot_id_is_uuid(self):
        snap = self._b().build(_make_position())
        uuid.UUID(snap.snapshot_id)

    def test_build_position_statistics_present(self):
        snap = self._b().build(_make_position())
        assert "fill_ratio" in snap.position_statistics
        assert "holding_time_s" in snap.position_statistics


# ══════════════════════════════════════════════════════════════════════════════
# 12. PositionSnapshotFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionSnapshotFactory:
    def _f(self) -> PositionSnapshotFactory:
        return PositionSnapshotFactory()

    def test_create(self):
        f    = self._f()
        snap = f.create(_make_position())
        assert isinstance(snap, PositionSnapshot)
        assert snap.snapshot_status == SnapshotStatus.DRAFT.value

    def test_create_minimal(self):
        f    = self._f()
        snap = f.create_minimal(_make_position())
        assert snap.risk_state == ""   # no risk state provided
        assert snap.current_price == "0"

    def test_create_with_price(self):
        f    = self._f()
        snap = f.create_with_price(_make_position(), Decimal("3000"))
        assert snap.current_price == "3000"

    def test_create_all_produce_different_snapshot_ids(self):
        f   = self._f()
        pos = _make_position()
        ids = {f.create(pos).snapshot_id for _ in range(5)}
        assert len(ids) == 5   # each build produces a new UUID


# ══════════════════════════════════════════════════════════════════════════════
# 13. PositionSnapshotRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionSnapshotRegistry:
    def _started(self, max_positions=100):
        r = PositionSnapshotRegistry(max_positions=max_positions)
        r.start()
        return r

    def test_start_stop(self):
        r = PositionSnapshotRegistry()
        r.start()
        assert r.lifecycle_state().value == "running"
        r.stop()
        assert r.lifecycle_state().value != "running"

    def test_store_and_get_latest(self):
        r    = self._started()
        snap = _make_snapshot("rp-1")
        r.store(snap)
        assert r.get_latest("rp-1") is snap
        r.stop()

    def test_store_requires_running(self):
        r = PositionSnapshotRegistry()
        with pytest.raises(PositionSnapshotNotRunningError):
            r.store(_make_snapshot())

    def test_duplicate_snapshot_id_raises(self):
        r    = self._started()
        snap = _make_snapshot("dup-pos")
        r.store(snap)
        with pytest.raises(DuplicateSnapshotError):
            r.store(snap)   # same snapshot_id
        r.stop()

    def test_capacity_enforced(self):
        r    = self._started(max_positions=1)
        r.store(_make_snapshot("p1"))
        snap2 = _make_snapshot("p2")   # new position → at capacity
        with pytest.raises(SnapshotCapacityError):
            r.store(snap2)
        r.stop()

    def test_remove(self):
        r    = self._started()
        snap = _make_snapshot("rm-pos")
        r.store(snap)
        removed = r.remove("rm-pos")
        assert len(removed) == 1
        assert r.get_latest("rm-pos") is None
        r.stop()

    def test_remove_not_found_raises(self):
        r = self._started()
        with pytest.raises(SnapshotNotFoundError):
            r.remove("ghost")
        r.stop()

    def test_get_by_snapshot_id(self):
        r    = self._started()
        snap = _make_snapshot("si-pos")
        r.store(snap)
        assert r.get_by_snapshot_id(snap.snapshot_id) is snap
        assert r.get_by_snapshot_id("ghost") is None
        r.stop()

    def test_get_all_versions(self):
        r  = self._started()
        s1 = _make_snapshot("mv-pos", snapshot_version=1)
        s2 = _make_snapshot("mv-pos", snapshot_version=2)
        r.store(s1)
        r.store(s2)
        assert len(r.get_all_versions("mv-pos")) == 2
        r.stop()

    def test_secondary_index_portfolio(self):
        r    = self._started()
        snap = dataclasses.replace(_make_snapshot("pf-pos"), portfolio_id="PF-X")
        r.store(snap)
        results = r.get_by_portfolio("PF-X")
        assert any(s.position_id == "pf-pos" for s in results)
        r.stop()

    def test_secondary_index_strategy(self):
        r    = self._started()
        snap = dataclasses.replace(_make_snapshot("st-pos"), strategy_id="ST-Y")
        r.store(snap)
        results = r.get_by_strategy("ST-Y")
        assert any(s.position_id == "st-pos" for s in results)
        r.stop()

    def test_secondary_index_instrument(self):
        r    = self._started()
        snap = _make_snapshot("ins-pos", instrument="RELIANCE")
        r.store(snap)
        results = r.get_by_instrument("RELIANCE")
        assert any(s.position_id == "ins-pos" for s in results)
        r.stop()

    def test_secondary_index_workflow(self):
        r    = self._started()
        snap = dataclasses.replace(_make_snapshot("wf-pos"), workflow_id="WF-Z")
        r.store(snap)
        results = r.get_by_workflow("WF-Z")
        assert any(s.position_id == "wf-pos" for s in results)
        r.stop()

    def test_all_latest_snapshots(self):
        r = self._started()
        r.store(_make_snapshot("a1"))
        r.store(_make_snapshot("a2"))
        r.store(_make_snapshot("a1", snapshot_version=2))
        snaps = r.all_latest_snapshots()
        assert len(snaps) == 2
        r.stop()

    def test_contains(self):
        r = self._started()
        r.store(_make_snapshot("cx"))
        assert r.contains("cx")   is True
        assert r.contains("none") is False
        r.stop()

    def test_count(self):
        r = self._started()
        assert r.count() == 0
        r.store(_make_snapshot("c1"))
        assert r.count() == 1
        r.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 14. PositionSnapshotCache
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionSnapshotCache:
    def _started(self, max_entries=100):
        c = PositionSnapshotCache(max_entries=max_entries)
        c.start()
        return c

    def test_start_stop(self):
        c = PositionSnapshotCache()
        c.start()
        assert c.lifecycle_state().value == "running"
        c.stop()

    def test_put_and_get(self):
        c    = self._started()
        snap = _make_snapshot("cache-pos")
        c.put("cache-pos", snap)
        assert c.get("cache-pos") is snap
        c.stop()

    def test_put_requires_running(self):
        c = PositionSnapshotCache()
        with pytest.raises(PositionSnapshotNotRunningError):
            c.put("pos", _make_snapshot())

    def test_get_returns_none_when_absent(self):
        c = self._started()
        assert c.get("absent") is None
        c.stop()

    def test_invalidate(self):
        c    = self._started()
        snap = _make_snapshot("inv-pos")
        c.put("inv-pos", snap)
        assert c.invalidate("inv-pos") is True
        assert c.get("inv-pos") is None
        assert c.invalidate("inv-pos") is False   # already gone
        c.stop()

    def test_clear(self):
        c = self._started()
        c.put("p1", _make_snapshot("p1"))
        c.put("p2", _make_snapshot("p2"))
        count = c.clear()
        assert count    == 2
        assert c.count() == 0
        c.stop()

    def test_is_cached(self):
        c = self._started()
        c.put("p", _make_snapshot("p"))
        assert c.is_cached("p")     is True
        assert c.is_cached("ghost") is False
        c.stop()

    def test_hit_rate(self):
        c = self._started()
        c.put("p", _make_snapshot("p"))
        c.get("p")        # hit
        c.get("p")        # hit
        c.get("absent")   # miss
        assert abs(c.hit_rate - (2/3)) < 1e-9
        c.stop()

    def test_hit_rate_zero_before_any_access(self):
        c = self._started()
        assert c.hit_rate == 0.0
        c.stop()

    def test_capacity_best_effort_drop(self):
        c = self._started(max_entries=1)
        c.put("p1", _make_snapshot("p1"))
        c.put("p2", _make_snapshot("p2"))  # silently dropped
        assert c.count() == 1
        c.stop()

    def test_overwrite_existing_entry(self):
        c    = self._started()
        s1   = _make_snapshot("upd-pos", snapshot_version=1)
        s2   = _make_snapshot("upd-pos", snapshot_version=2)
        c.put("upd-pos", s1)
        c.put("upd-pos", s2)
        assert c.get("upd-pos").snapshot_version == 2
        c.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 15. PositionSnapshotStore
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionSnapshotStore:
    def test_start_stop(self):
        s = PositionSnapshotStore()
        s.start()
        assert s.lifecycle_state().value == "running"
        s.stop()
        assert s.lifecycle_state().value != "running"

    def test_build_and_store_returns_snapshot(self):
        store = _started_store()
        pos   = _make_position()
        snap  = store.build_and_store(pos)
        assert isinstance(snap, PositionSnapshot)
        assert snap.position_id == pos.position_id
        store.stop()

    def test_build_and_store_valid_status(self):
        store = _started_store()
        snap  = store.build_and_store(_make_position())
        assert snap.is_valid is True
        store.stop()

    def test_build_and_store_auto_publish(self):
        store = _started_store()
        snap  = store.build_and_store(_make_position(), auto_publish=True)
        assert snap.is_published is True
        store.stop()

    def test_build_and_store_increments_version(self):
        store = _started_store()
        pos   = _make_position()
        s1    = store.build_and_store(pos)
        s2    = store.build_and_store(pos)
        assert s1.snapshot_version == 1
        assert s2.snapshot_version == 2
        store.stop()

    def test_build_and_store_not_running_raises(self):
        store = PositionSnapshotStore()
        with pytest.raises(PositionSnapshotNotRunningError):
            store.build_and_store(_make_position())

    def test_publish(self):
        store = _started_store()
        snap  = store.build_and_store(_make_position())
        pub   = store.publish(snap.snapshot_id)
        assert pub.is_published is True
        store.stop()

    def test_publish_non_publishable_status_raises(self):
        store = _started_store()
        pos   = _make_position()
        snap  = store.build_and_store(pos)
        # Force DRAFT
        sid = snap.snapshot_id
        # Archive first so it's no longer publishable
        arc = store.archive(sid)
        with pytest.raises(SnapshotStoreError):
            store.publish(arc.snapshot_id)  # archived snap not publishable
        store.stop()

    def test_archive(self):
        store = _started_store()
        snap  = store.build_and_store(_make_position())
        arc   = store.archive(snap.snapshot_id)
        assert arc.is_archived is True
        store.stop()

    def test_validate_snapshot(self):
        store  = _started_store()
        snap   = store.build_and_store(_make_position())
        result = store.validate_snapshot(snap.snapshot_id)
        assert result.is_valid is True
        store.stop()

    def test_get_latest(self):
        store = _started_store()
        pos   = _make_position()
        store.build_and_store(pos)
        snap  = store.get_latest(pos.position_id)
        assert snap is not None
        assert snap.position_id == pos.position_id
        store.stop()

    def test_get_latest_returns_none_when_absent(self):
        store = _started_store()
        assert store.get_latest("ghost") is None
        store.stop()

    def test_require_latest_raises_when_absent(self):
        store = _started_store()
        with pytest.raises(SnapshotNotFoundError):
            store.require_latest("ghost")
        store.stop()

    def test_get_by_snapshot_id(self):
        store = _started_store()
        pos   = _make_position()
        snap  = store.build_and_store(pos)
        found = store.get_by_snapshot_id(snap.snapshot_id)
        assert found is not None
        store.stop()

    def test_get_all_versions(self):
        store = _started_store()
        pos   = _make_position()
        store.build_and_store(pos)
        store.build_and_store(pos)
        versions = store.get_all_versions(pos.position_id)
        assert len(versions) == 2
        store.stop()

    def test_get_version(self):
        store = _started_store()
        pos   = _make_position()
        store.build_and_store(pos)   # version 1
        store.build_and_store(pos)   # version 2
        v1 = store.get_version(pos.position_id, 1)
        assert v1 is not None
        assert v1.snapshot_version == 1
        store.stop()

    def test_all_latest_snapshots(self):
        store = _started_store()
        p1    = _make_position("NIFTY50")
        p2    = _make_position("BANKNIFTY")
        store.build_and_store(p1)
        store.build_and_store(p2)
        snaps = store.all_latest_snapshots()
        assert len(snaps) == 2
        store.stop()

    def test_get_by_portfolio(self):
        store = _started_store()
        pos   = _make_position(portfolio_id="PFX")
        store.build_and_store(pos)
        results = store.get_by_portfolio("PFX")
        assert len(results) >= 1
        store.stop()

    def test_get_by_strategy(self):
        store = _started_store()
        pos   = _make_position(strategy_id="STX")
        store.build_and_store(pos)
        results = store.get_by_strategy("STX")
        assert len(results) >= 1
        store.stop()

    def test_get_by_workflow(self):
        store = _started_store()
        pos   = _make_position(workflow_id="WFX")
        store.build_and_store(pos)
        results = store.get_by_workflow("WFX")
        assert len(results) >= 1
        store.stop()

    def test_get_by_instrument(self):
        store = _started_store()
        pos   = _make_position(instrument="HINDALCO")
        store.build_and_store(pos)
        results = store.get_by_instrument("HINDALCO")
        assert len(results) >= 1
        store.stop()

    def test_get_by_timestamp_range(self):
        store = _started_store()
        pos   = _make_position()
        t0    = time.time()
        store.build_and_store(pos)
        t1    = time.time()
        results = store.get_by_timestamp_range(t0 - 1, t1 + 1)
        assert len(results) >= 1
        store.stop()

    def test_bundle_portfolio(self):
        store = _started_store()
        pos   = _make_position(portfolio_id="BP")
        store.build_and_store(pos)
        bundle = store.bundle_portfolio("BP")
        assert isinstance(bundle, SnapshotBundle)
        assert bundle.count >= 1
        store.stop()

    def test_bundle_strategy(self):
        store = _started_store()
        pos   = _make_position(strategy_id="BS")
        store.build_and_store(pos)
        bundle = store.bundle_strategy("BS")
        assert bundle.count >= 1
        store.stop()

    def test_bundle_all(self):
        store = _started_store()
        for i in range(3):
            store.build_and_store(_make_position(f"STOCK{i}"))
        bundle = store.bundle_all()
        assert bundle.count == 3
        store.stop()

    def test_remove(self):
        store = _started_store()
        pos   = _make_position()
        store.build_and_store(pos)
        removed = store.remove(pos.position_id)
        assert len(removed) >= 1
        assert store.get_latest(pos.position_id) is None
        store.stop()

    def test_remove_not_found_raises(self):
        store = _started_store()
        with pytest.raises(SnapshotNotFoundError):
            store.remove("ghost")
        store.stop()

    def test_contains(self):
        store = _started_store()
        pos   = _make_position()
        assert store.contains(pos.position_id) is False
        store.build_and_store(pos)
        assert store.contains(pos.position_id) is True
        store.stop()

    def test_count(self):
        store = _started_store()
        assert store.count() == 0
        store.build_and_store(_make_position())
        assert store.count() == 1
        store.stop()

    def test_statistics_created_updated(self):
        store = _started_store()
        store.build_and_store(_make_position())
        stats = store.statistics()
        assert stats.snapshots_created >= 1
        store.stop()

    def test_statistics_returns_copy(self):
        store = _started_store()
        s1 = store.statistics()
        s2 = store.statistics()
        assert s1 is not s2
        store.stop()

    def test_events_populated_after_build(self):
        store = _started_store()
        store.build_and_store(_make_position())
        events = store.events()
        assert len(events) >= 1
        store.stop()

    def test_event_history_object(self):
        store = _started_store()
        assert isinstance(store.event_history(), SnapshotEventHistory)
        store.stop()

    def test_cache_accessor(self):
        store = _started_store()
        assert isinstance(store.cache(), PositionSnapshotCache)
        store.stop()

    def test_full_lifecycle(self):
        """Build → validate → publish → archive → remove."""
        store = _started_store()
        pos   = _make_position()
        snap  = store.build_and_store(pos)
        assert snap.is_valid

        pub   = store.publish(snap.snapshot_id)
        assert pub.is_published

        arc   = store.archive(pub.snapshot_id)
        assert arc.is_archived

        store.remove(pos.position_id)
        assert store.get_latest(pos.position_id) is None
        store.stop()

    def test_concurrency_safe_build_and_store(self):
        store   = _started_store(max_positions=200)
        errors  = []
        positions = [_make_position(f"STOCK{i}") for i in range(20)]

        def worker(pos):
            try:
                store.build_and_store(pos)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(p,)) for p in positions]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert store.count() == 20
        store.stop()

    def test_cache_populated_after_build(self):
        store = _started_store()
        pos   = _make_position()
        store.build_and_store(pos)
        cached = store.cache().get(pos.position_id)
        assert cached is not None
        assert cached.position_id == pos.position_id
        store.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 16. Regression guards
# ══════════════════════════════════════════════════════════════════════════════

class TestRegressionGuards:
    def test_snapshot_is_str_enum_status(self):
        assert SnapshotStatus.VALID == "VALID"

    def test_snapshot_is_frozen(self):
        """PositionSnapshot must be a frozen dataclass."""
        snap = _make_snapshot()
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            snap.position_id = "mutated"  # type: ignore[misc]

    def test_snapshot_not_lifecycle_aware(self):
        from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
        snap = _make_snapshot()
        assert not isinstance(snap, LifecycleAwareMixin)

    def test_builder_not_lifecycle_aware(self):
        from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
        b = PositionSnapshotBuilder()
        assert not isinstance(b, LifecycleAwareMixin)

    def test_validator_not_lifecycle_aware(self):
        from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
        v = SnapshotValidator()
        assert not isinstance(v, LifecycleAwareMixin)

    def test_store_registry_started_on_store_start(self):
        store = PositionSnapshotStore()
        store.start()
        # Registry must be running so build works
        pos = _make_position()
        snap = store.build_and_store(pos)
        assert snap is not None
        store.stop()

    def test_multiple_positions_independent(self):
        store = _started_store()
        p1    = _make_position("NIFTY50")
        p2    = _make_position("BANKNIFTY")
        store.build_and_store(p1)
        store.build_and_store(p2)
        assert store.get_latest(p1.position_id).instrument == "NIFTY50"
        assert store.get_latest(p2.position_id).instrument == "BANKNIFTY"
        store.stop()

    def test_status_transitions_produce_new_objects(self):
        snap     = _make_snapshot(status=SnapshotStatus.VALID.value)
        pub      = snap.as_published()
        assert snap.snapshot_id == pub.snapshot_id   # same snapshot
        assert snap.is_valid     is True              # original unchanged
        assert pub.is_published  is True

    def test_from_dict_to_dict_roundtrip_exact(self):
        snap  = _make_snapshot()
        snap2 = PositionSnapshot.from_dict(snap.to_dict())
        assert snap2.snapshot_id      == snap.snapshot_id
        assert snap2.snapshot_version == snap.snapshot_version
        assert snap2.position_id      == snap.position_id
        assert snap2.realized_pnl     == snap.realized_pnl

    def test_snapshot_version_independent_per_position(self):
        store = _started_store()
        p1    = _make_position("NIFTY50")
        p2    = _make_position("BANKNIFTY")
        store.build_and_store(p1)  # v1
        store.build_and_store(p1)  # v2
        store.build_and_store(p2)  # v1 for p2 (independent)
        assert store.get_latest(p2.position_id).snapshot_version == 1
        assert store.get_latest(p1.position_id).snapshot_version == 2
        store.stop()
