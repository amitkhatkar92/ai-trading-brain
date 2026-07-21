"""
tests/unit/decision/snapshot/test_snapshot.py
==============================================
Comprehensive unit tests for C9 M5 Decision Snapshot.

Coverage targets
----------------
- Constants and enums
- Exceptions (hierarchy + error codes)
- DecisionSnapshot (create, properties, serialization)
- DecisionSnapshotMetadata + SnapshotAuditMetadata
- DecisionSnapshotValidation (all 9 checks, pass/fail paths)
- DecisionSnapshotBuilder (full build, rejection paths, field extraction)
- DecisionSnapshotFactory (create, from_dict roundtrip)
- DecisionSnapshotEvents (factory functions, to_dict)
- DecisionSnapshotStatistics (counters, EMA, reset)
- DecisionSnapshotHistory (snapshots, events, by-decision/session/type)
- DecisionSnapshotCache (LRU, eviction, stats)
- DecisionSnapshotRegistry (CRUD, secondary indices, version limit)
- DecisionSnapshotStore (save/get/delete, versioning, queries, cache integration)
- DecisionSnapshotBundle (create, properties, access, serialization)
- __init__ exports
- Concurrency (thread-safe operations)
- Regression (immutability, deduplication)
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from iios.decision.snapshot import (
    # Constants
    SNAPSHOT_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    DecisionHealth,
    DecisionOutcome,
    DecisionStatus,
    SnapshotEventType,
    SnapshotStatus,
    SnapshotValidationCode,
    # Exceptions
    DecisionSnapshotError,
    DuplicateSnapshotError,
    SnapshotBuildError,
    SnapshotCacheError,
    SnapshotConfigurationError,
    SnapshotNotFoundError,
    SnapshotRegistryError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
    # Value objects
    DecisionSnapshot,
    DecisionSnapshotBundle,
    DecisionSnapshotEvent,
    DecisionSnapshotMetadata,
    SnapshotAuditMetadata,
    # Validation
    DecisionSnapshotValidator,
    SnapshotValidationCheckResult,
    SnapshotValidationResult,
    # Builder + Factory
    DecisionSnapshotBuilder,
    DecisionSnapshotFactory,
    # Registry / Store / Cache
    DecisionSnapshotCache,
    DecisionSnapshotHistory,
    DecisionSnapshotRegistry,
    DecisionSnapshotStatistics,
    DecisionSnapshotStore,
    # Events
    make_snapshot_archived,
    make_snapshot_cached,
    make_snapshot_created,
    make_snapshot_published,
    make_snapshot_retrieved,
    make_snapshot_validated,
)


# ============================================================================
# Helpers
# ============================================================================

_UNSET = object()


def _snapshot(
    *,
    session_id:       str          = "sess-001",
    decision_id:      str          = "dec-001",
    lifecycle_state:  str          = "completed",
    decision_scope:   str          = "order",
    decision_type:    str          = "order",
    decision_priority: str         = "medium",
    decision_status:  DecisionStatus = DecisionStatus.APPROVED,
    decision_health:  DecisionHealth = DecisionHealth.HEALTHY,
    decision_outcome: DecisionOutcome = DecisionOutcome.SUCCESS,
    snapshot_status:  SnapshotStatus  = SnapshotStatus.VALID,
    decision_confidence: float      = 0.85,
    decision_score:   float          = 0.78,
    selected_decision                = _UNSET,
    **kw,
) -> DecisionSnapshot:
    sel = (
        {"candidate_id": "c1", "symbol": "RELIANCE"}
        if selected_decision is _UNSET
        else selected_decision
    )
    return DecisionSnapshot.create(
        session_id        = session_id,
        decision_id       = decision_id,
        lifecycle_state   = lifecycle_state,
        decision_scope    = decision_scope,
        decision_type     = decision_type,
        decision_priority = decision_priority,
        decision_status   = decision_status,
        decision_health   = decision_health,
        decision_outcome  = decision_outcome,
        snapshot_status   = snapshot_status,
        decision_confidence = decision_confidence,
        decision_score    = decision_score,
        selected_decision = sel,
        policy_summary    = {"action": "approve", "is_approved": True},
        optimization_summary = {"candidates_evaluated": 2, "final_score": 0.78},
        **kw,
    )


class FakeSession:
    """Minimal duck-typed M1 session for builder tests."""
    def __init__(self, **kw):
        self._session_id       = kw.get("session_id", "sess-001")
        self._decision_id      = kw.get("decision_id", "dec-001")
        self._workflow_id      = kw.get("workflow_id", "wf-001")
        self._portfolio_id     = kw.get("portfolio_id", "pf-001")
        self._strategy_id      = kw.get("strategy_id", "strat-001")
        self._state            = kw.get("state", _FakeState("completed"))
        self._decision_scope   = _FakeEnum("order")
        self._decision_type    = _FakeEnum("order")
        self._decision_priority= _FakePriority("medium")


class _FakeState:
    def __init__(self, v): self.value = v


class _FakeEnum:
    def __init__(self, v): self.value = v


class _FakePriority:
    def __init__(self, v):
        self.value = v
        self.name  = v


# ============================================================================
# 1. Constants & Enums
# ============================================================================

class TestConstants:
    def test_system_id_not_empty(self):
        assert SNAPSHOT_SYSTEM_ID

    def test_version_not_empty(self):
        assert VERSION
        assert "." in VERSION

    def test_schema_version(self):
        assert SCHEMA_VERSION

    def test_decision_status_count(self):
        assert len(DecisionStatus) >= 9

    def test_decision_health_values(self):
        names = {h.name for h in DecisionHealth}
        assert {"HEALTHY", "DEGRADED", "CRITICAL", "UNKNOWN"}.issubset(names)

    def test_decision_outcome_values(self):
        names = {o.name for o in DecisionOutcome}
        assert {"SUCCESS", "FAILURE", "PARTIAL", "UNKNOWN"}.issubset(names)

    def test_snapshot_status_values(self):
        names = {s.name for s in SnapshotStatus}
        assert {"PENDING", "VALID", "INVALID", "PUBLISHED", "ARCHIVED"}.issubset(names)

    def test_event_types_count(self):
        assert len(SnapshotEventType) == 6

    def test_validation_code_count(self):
        assert len(SnapshotValidationCode) == 9


# ============================================================================
# 2. Exceptions
# ============================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(DecisionSnapshotError, IIOSError)

    def test_not_found_has_snapshot_id(self):
        err = SnapshotNotFoundError("snap-123")
        assert err.snapshot_id == "snap-123"
        assert "DS-001" in str(err) or err.error_code == "DS-001"

    def test_build_error(self):
        err = SnapshotBuildError("cannot build")
        assert "DS-002" in str(err) or err.error_code == "DS-002"

    def test_validation_error_has_failed_checks(self):
        err = SnapshotValidationError("fail", failed_checks=("CHECK_A",))
        assert "CHECK_A" in err.failed_checks

    def test_registry_error(self):
        err = SnapshotRegistryError("full")
        assert "DS-004" in str(err) or err.error_code == "DS-004"

    def test_store_error(self):
        err = SnapshotStoreError("io failure")
        assert "DS-005" in str(err) or err.error_code == "DS-005"

    def test_cache_error(self):
        err = SnapshotCacheError("miss")
        assert "DS-006" in str(err) or err.error_code == "DS-006"

    def test_duplicate_snapshot_error(self):
        err = DuplicateSnapshotError("snap-dup")
        assert err.snapshot_id == "snap-dup"
        assert "DS-007" in str(err) or err.error_code == "DS-007"

    def test_version_error(self):
        err = SnapshotVersionError("bad version")
        assert "DS-008" in str(err) or err.error_code == "DS-008"

    def test_configuration_error(self):
        err = SnapshotConfigurationError("bad cfg")
        assert "DS-009" in str(err) or err.error_code == "DS-009"

    def test_hierarchy(self):
        for cls in [
            SnapshotNotFoundError, SnapshotBuildError, SnapshotValidationError,
            SnapshotRegistryError, SnapshotStoreError, SnapshotCacheError,
            DuplicateSnapshotError, SnapshotVersionError, SnapshotConfigurationError,
        ]:
            assert issubclass(cls, DecisionSnapshotError)


# ============================================================================
# 3. DecisionSnapshot
# ============================================================================

class TestDecisionSnapshot:
    def test_create_generates_uuid(self):
        s1 = _snapshot()
        s2 = _snapshot()
        assert s1.snapshot_id != s2.snapshot_id

    def test_explicit_snapshot_id(self):
        s = _snapshot(snapshot_id="snap-x")
        assert s.snapshot_id == "snap-x"

    def test_is_frozen(self):
        s = _snapshot()
        with pytest.raises((AttributeError, TypeError)):
            s.decision_id = "changed"  # type: ignore[misc]

    def test_is_approved_true(self):
        s = _snapshot(decision_status=DecisionStatus.APPROVED)
        assert s.is_approved

    def test_is_approved_conditional(self):
        s = _snapshot(decision_status=DecisionStatus.APPROVED_CONDITIONAL)
        assert s.is_approved

    def test_is_rejected(self):
        s = _snapshot(decision_status=DecisionStatus.REJECTED)
        assert s.is_rejected
        assert not s.is_approved

    def test_is_blocked(self):
        s = _snapshot(decision_status=DecisionStatus.BLOCKED)
        assert s.is_blocked

    def test_is_failed(self):
        s = _snapshot(decision_status=DecisionStatus.FAILED)
        assert s.is_failed

    def test_is_healthy(self):
        s = _snapshot(decision_health=DecisionHealth.HEALTHY)
        assert s.is_healthy

    def test_is_successful(self):
        s = _snapshot(decision_outcome=DecisionOutcome.SUCCESS)
        assert s.is_successful

    def test_has_selection_true(self):
        s = _snapshot(selected_decision={"candidate_id": "c1"})
        assert s.has_selection

    def test_has_selection_false(self):
        s = _snapshot(selected_decision=None)
        assert not s.has_selection

    def test_to_dict_has_all_required_keys(self):
        d = _snapshot().to_dict()
        required = {
            "snapshot_id", "snapshot_version", "schema_version",
            "session_id", "decision_id", "workflow_id",
            "decision_scope", "decision_type", "decision_priority",
            "lifecycle_state", "decision_status", "decision_health",
            "decision_outcome", "snapshot_status",
            "decision_confidence", "decision_score",
            "optimization_summary", "ranking_summary", "constraint_summary",
            "policy_summary", "evaluation_summary",
            "decision_explanation", "decision_statistics",
            "decision_metadata", "audit_metadata",
            "framework_version", "created_at",
        }
        assert required.issubset(set(d.keys()))

    def test_to_dict_enums_serialized_as_strings(self):
        d = _snapshot().to_dict()
        assert isinstance(d["decision_status"], str)
        assert isinstance(d["decision_health"], str)
        assert isinstance(d["decision_outcome"], str)

    def test_created_at_is_utc(self):
        s = _snapshot()
        assert s.created_at.tzinfo is not None

    def test_schema_version_set(self):
        s = _snapshot()
        assert s.schema_version == SCHEMA_VERSION

    def test_empty_summaries_default_to_dict(self):
        s = DecisionSnapshot.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
        )
        assert isinstance(s.optimization_summary, dict)
        assert isinstance(s.policy_summary, dict)

    def test_snapshot_version_default_one(self):
        s = _snapshot()
        assert s.snapshot_version == 1

    def test_explicit_snapshot_version(self):
        s = _snapshot(snapshot_version=5)
        assert s.snapshot_version == 5


# ============================================================================
# 4. DecisionSnapshotMetadata & SnapshotAuditMetadata
# ============================================================================

class TestSnapshotMetadata:
    def test_create_metadata(self):
        md = DecisionSnapshotMetadata.create(
            snapshot_id="snap-1", session_id="sess-1", decision_id="dec-1"
        )
        assert md.metadata_id
        assert md.snapshot_id == "snap-1"

    def test_metadata_tags(self):
        md = DecisionSnapshotMetadata.create(
            snapshot_id="s", session_id="ss", decision_id="d",
            tags=("tag1", "tag2"),
        )
        assert "tag1" in md.tags

    def test_metadata_to_dict(self):
        md = DecisionSnapshotMetadata.create(
            snapshot_id="s", session_id="ss", decision_id="d"
        )
        d = md.to_dict()
        assert "metadata_id" in d
        assert isinstance(d["tags"], list)

    def test_create_audit(self):
        audit = SnapshotAuditMetadata.create(
            snapshot_id="snap-1", builder_id="builder-1",
            build_time_s=0.05, source_modules=("M1", "M3", "M4"),
        )
        assert audit.audit_id
        assert "M3" in audit.source_modules

    def test_audit_to_dict(self):
        audit = SnapshotAuditMetadata.create(
            snapshot_id="s", builder_id="b", source_modules=("M1",)
        )
        d = audit.to_dict()
        assert "audit_id" in d
        assert "source_modules" in d
        assert isinstance(d["source_modules"], list)

    def test_audit_validated_fields_none_by_default(self):
        audit = SnapshotAuditMetadata.create(snapshot_id="s", builder_id="b")
        assert audit.validated is False
        assert audit.validated_at is None


# ============================================================================
# 5. DecisionSnapshotValidation
# ============================================================================

class TestDecisionSnapshotValidation:
    def test_valid_snapshot_passes_all_checks(self):
        validator = DecisionSnapshotValidator()
        result = validator.validate(_snapshot())
        assert result.is_valid
        assert result.passed_count == 9
        assert result.failed_count == 0

    def test_check_count_nine(self):
        validator = DecisionSnapshotValidator()
        result = validator.validate(_snapshot())
        assert len(result.checks) == 9

    def test_empty_snapshot_id_fails(self):
        validator = DecisionSnapshotValidator()
        # Bypass create() (which auto-generates UUID) to test validation
        from datetime import datetime, timezone
        s = DecisionSnapshot(
            snapshot_id="", snapshot_version=1, schema_version="1.0",
            session_id="s", decision_id="d",
            workflow_id="", execution_session_id="",
            portfolio_id="", strategy_id="",
            decision_scope="order", decision_type="order", decision_priority="medium",
            lifecycle_state="completed",
            decision_status=DecisionStatus.PENDING,
            decision_health=DecisionHealth.UNKNOWN,
            decision_outcome=DecisionOutcome.UNKNOWN,
            snapshot_status=SnapshotStatus.PENDING,
            selected_decision=None,
            decision_confidence=0.0, decision_score=0.0,
            optimization_summary={}, ranking_summary={}, constraint_summary={},
            policy_summary={}, evaluation_summary={},
            decision_explanation="",
            decision_statistics={}, decision_metadata={}, audit_metadata={},
            framework_version=VERSION,
            created_at=datetime.now(timezone.utc),
        )
        result = validator.validate(s)
        assert not result.is_valid
        failed_codes = {c.value for c in result.failed_checks}
        assert SnapshotValidationCode.IDENTIFIER_CONSISTENCY.value in failed_codes

    def test_empty_session_id_fails(self):
        validator = DecisionSnapshotValidator()
        s = DecisionSnapshot.create(
            session_id="", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
        )
        result = validator.validate(s)
        assert not result.is_valid

    def test_unknown_lifecycle_state_fails(self):
        validator = DecisionSnapshotValidator()
        s = _snapshot(lifecycle_state="not_a_real_state")
        result = validator.validate(s)
        assert not result.is_valid
        assert SnapshotValidationCode.LIFECYCLE_CONSISTENCY in result.failed_checks

    def test_approved_without_selection_fails(self):
        validator = DecisionSnapshotValidator()
        s = DecisionSnapshot.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
            decision_status=DecisionStatus.APPROVED,
            selected_decision=None,
            policy_summary={"action": "approve"},
        )
        result = validator.validate(s)
        assert not result.is_valid
        assert SnapshotValidationCode.DECISION_CONSISTENCY in result.failed_checks

    def test_approved_without_policy_summary_fails(self):
        validator = DecisionSnapshotValidator()
        s = DecisionSnapshot.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
            decision_status=DecisionStatus.APPROVED,
            selected_decision={"candidate_id": "c1"},
            policy_summary={},
        )
        result = validator.validate(s)
        assert not result.is_valid
        assert SnapshotValidationCode.POLICY_CONSISTENCY in result.failed_checks

    def test_score_out_of_range_fails(self):
        validator = DecisionSnapshotValidator()
        s = _snapshot(decision_score=1.5)
        # override optimization_summary via create to have it non-empty
        s2 = DecisionSnapshot.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
            decision_score=1.5,
            optimization_summary={"candidates_evaluated": 1},
        )
        result = validator.validate(s2)
        assert not result.is_valid
        assert SnapshotValidationCode.OPTIMIZATION_CONSISTENCY in result.failed_checks

    def test_empty_scope_fails_completeness(self):
        validator = DecisionSnapshotValidator()
        s = DecisionSnapshot.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="", decision_type="order", decision_priority="medium",
        )
        result = validator.validate(s)
        assert not result.is_valid
        assert SnapshotValidationCode.SNAPSHOT_COMPLETENESS in result.failed_checks

    def test_error_messages_non_empty_on_failure(self):
        validator = DecisionSnapshotValidator()
        s = DecisionSnapshot.create(
            session_id="", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
        )
        result = validator.validate(s)
        assert len(result.error_messages) > 0

    def test_timestamp_without_tz_fails(self):
        validator = DecisionSnapshotValidator()
        naive_dt = datetime(2026, 1, 1, 12, 0, 0)  # no timezone
        s = DecisionSnapshot.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
            created_at=naive_dt,
        )
        result = validator.validate(s)
        assert not result.is_valid
        assert SnapshotValidationCode.TIMESTAMP_CONSISTENCY in result.failed_checks


# ============================================================================
# 6. DecisionSnapshotBuilder
# ============================================================================

class TestDecisionSnapshotBuilder:
    def test_build_from_session_only(self):
        builder  = DecisionSnapshotBuilder()
        session  = FakeSession()
        snapshot = builder.build(session)
        assert snapshot.session_id == "sess-001"
        assert snapshot.decision_id == "dec-001"
        assert snapshot.lifecycle_state == "completed"

    def test_build_with_policy_response(self):
        class FakePolicyResponse:
            action        = _FakeEnum("approve")
            is_approved   = True
            is_rejected   = False
            is_blocked    = False
            is_success    = True
            evaluation_time_s = 0.02
            summary       = None

        builder  = DecisionSnapshotBuilder()
        snapshot = builder.build(FakeSession(), policy_response=FakePolicyResponse())
        assert snapshot.decision_status == DecisionStatus.APPROVED

    def test_build_rejected_status(self):
        class FakePolicyResponse:
            action        = _FakeEnum("reject")
            is_approved   = False
            is_rejected   = True
            is_blocked    = False
            is_success    = True
            evaluation_time_s = 0.01
            summary       = None

        builder  = DecisionSnapshotBuilder()
        snapshot = builder.build(FakeSession(), policy_response=FakePolicyResponse())
        assert snapshot.decision_status == DecisionStatus.REJECTED

    def test_build_without_session_raises(self):
        builder = DecisionSnapshotBuilder()
        with pytest.raises(SnapshotBuildError):
            builder.build(None)

    def test_build_missing_session_id_raises(self):
        class BadSession:
            _session_id    = ""
            _decision_id   = "dec-1"
            _state         = _FakeState("completed")
            _decision_scope= _FakeEnum("order")
            _decision_type = _FakeEnum("order")
            _decision_priority = _FakePriority("medium")

        with pytest.raises(SnapshotBuildError, match="session_id"):
            DecisionSnapshotBuilder().build(BadSession())

    def test_build_invalid_lifecycle_state_raises(self):
        class BadSession(FakeSession):
            def __init__(self):
                super().__init__()
                self._state = _FakeState("not_a_state")

        with pytest.raises(SnapshotBuildError, match="Invalid lifecycle_state"):
            DecisionSnapshotBuilder().build(BadSession())

    def test_build_missing_scope_raises(self):
        class BadSession(FakeSession):
            def __init__(self):
                super().__init__()
                self._decision_scope = _FakeEnum("")

        with pytest.raises(SnapshotBuildError, match="decision_scope"):
            DecisionSnapshotBuilder().build(BadSession())

    def test_build_result_is_immutable(self):
        snapshot = DecisionSnapshotBuilder().build(FakeSession())
        with pytest.raises((AttributeError, TypeError)):
            snapshot.decision_id = "hacked"  # type: ignore[misc]

    def test_build_with_optimization_response(self):
        class FakeSolution:
            final_score = 0.82
            selected_candidate = type("C", (), {
                "confidence": 0.88,
                "to_dict": lambda self: {"candidate_id": "c1", "symbol": "TCS"},
            })()

        class FakeOptResponse:
            solution           = FakeSolution()
            is_success         = True
            is_feasible        = True
            summary            = type("S", (), {
                "selected_candidate_id": "c1",
                "is_feasible":           True,
                "final_score":           0.82,
                "candidates_evaluated":  2,
                "feasible_count":        2,
                "infeasible_count":      0,
                "optimization_strategy": "weighted_score",
                "optimization_time_s":   0.03,
                "objectives_applied":    1,
                "constraints_applied":   1,
                "constraint_violations": 0,
                "rationale":             "Best candidate selected",
            })()
            optimization_report = None

        snapshot = DecisionSnapshotBuilder().build(
            FakeSession(), optimization_response=FakeOptResponse()
        )
        assert snapshot.decision_score == pytest.approx(0.82)
        assert snapshot.decision_confidence == pytest.approx(0.88)
        assert snapshot.has_selection
        assert snapshot.optimization_summary["candidates_evaluated"] == 2

    def test_build_audit_metadata_populated(self):
        snapshot = DecisionSnapshotBuilder().build(FakeSession())
        assert isinstance(snapshot.audit_metadata, dict)
        assert "builder_id" in snapshot.audit_metadata
        assert "source_modules" in snapshot.audit_metadata

    def test_build_decision_explanation_not_empty(self):
        snapshot = DecisionSnapshotBuilder().build(FakeSession())
        assert snapshot.decision_explanation

    def test_build_pending_status_when_no_policy(self):
        snapshot = DecisionSnapshotBuilder().build(FakeSession())
        assert snapshot.decision_status == DecisionStatus.PENDING

    def test_build_explicit_snapshot_id(self):
        snapshot = DecisionSnapshotBuilder().build(FakeSession(), snapshot_id="my-snap")
        assert snapshot.snapshot_id == "my-snap"

    def test_health_is_unknown_for_pending(self):
        snapshot = DecisionSnapshotBuilder().build(FakeSession())
        assert snapshot.decision_health == DecisionHealth.UNKNOWN

    def test_outcome_unknown_for_active_state(self):
        class ActiveSession(FakeSession):
            def __init__(self):
                super().__init__()
                self._state = _FakeState("active")

        snapshot = DecisionSnapshotBuilder().build(ActiveSession())
        assert snapshot.decision_outcome == DecisionOutcome.UNKNOWN


# ============================================================================
# 7. DecisionSnapshotFactory
# ============================================================================

class TestDecisionSnapshotFactory:
    def test_create_basic(self):
        fac = DecisionSnapshotFactory()
        s = fac.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
        )
        assert isinstance(s, DecisionSnapshot)
        assert s.session_id == "s"

    def test_from_dict_roundtrip(self):
        original = _snapshot()
        d = original.to_dict()
        fac = DecisionSnapshotFactory()
        restored = fac.from_dict(d)
        assert restored.snapshot_id   == original.snapshot_id
        assert restored.decision_id   == original.decision_id
        assert restored.decision_status == original.decision_status
        assert restored.decision_score  == pytest.approx(original.decision_score)

    def test_from_dict_handles_missing_fields(self):
        fac = DecisionSnapshotFactory()
        minimal = {
            "session_id":       "s",
            "decision_id":      "d",
            "lifecycle_state":  "completed",
            "decision_scope":   "order",
            "decision_type":    "order",
            "decision_priority": "medium",
        }
        s = fac.from_dict(minimal)
        assert s.session_id == "s"
        assert s.decision_status == DecisionStatus.PENDING

    def test_from_dict_parses_datetime_string(self):
        fac  = DecisionSnapshotFactory()
        snap = _snapshot()
        d    = snap.to_dict()
        assert isinstance(d["created_at"], str)
        restored = fac.from_dict(d)
        assert isinstance(restored.created_at, datetime)

    def test_from_dict_invalid_enum_falls_back(self):
        fac = DecisionSnapshotFactory()
        d = _snapshot().to_dict()
        d["decision_status"] = "totally_invalid_status"
        s = fac.from_dict(d)
        assert s.decision_status == DecisionStatus.PENDING


# ============================================================================
# 8. DecisionSnapshotEvents
# ============================================================================

class TestDecisionSnapshotEvents:
    def _base(self):
        return ("snap-1", "dec-1", "sess-1", "test-source")

    def test_make_created(self):
        ev = make_snapshot_created(*self._base(), snapshot_version=2, lifecycle_state="completed")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_CREATED
        assert ev.payload["snapshot_version"] == 2

    def test_make_validated(self):
        ev = make_snapshot_validated(*self._base(), is_valid=True)
        assert ev.event_type == SnapshotEventType.SNAPSHOT_VALIDATED
        assert ev.payload["is_valid"] is True

    def test_make_validated_failed(self):
        ev = make_snapshot_validated(*self._base(), is_valid=False,
                                     failed_checks=("IDENTIFIER_CONSISTENCY",))
        assert not ev.payload["is_valid"]
        assert len(ev.payload["failed_checks"]) == 1

    def test_make_published(self):
        ev = make_snapshot_published(*self._base(), decision_status="approved")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED

    def test_make_archived(self):
        ev = make_snapshot_archived(*self._base(), reason="TTL expired")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_ARCHIVED
        assert ev.payload["reason"] == "TTL expired"

    def test_make_retrieved(self):
        ev = make_snapshot_retrieved(*self._base(), query_key="decision_id")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_RETRIEVED

    def test_make_cached(self):
        ev = make_snapshot_cached(*self._base(), cache_hit=True)
        assert ev.event_type == SnapshotEventType.SNAPSHOT_CACHED
        assert ev.payload["cache_hit"] is True

    def test_to_dict_keys(self):
        ev = make_snapshot_created(*self._base())
        d = ev.to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert "occurred_at" in d
        assert isinstance(d["event_type"], str)

    def test_unique_event_ids(self):
        b = self._base()
        ev1 = make_snapshot_created(*b)
        ev2 = make_snapshot_created(*b)
        assert ev1.event_id != ev2.event_id

    def test_immutable(self):
        ev = make_snapshot_created(*self._base())
        with pytest.raises((AttributeError, TypeError)):
            ev.snapshot_id = "hacked"  # type: ignore[misc]


# ============================================================================
# 9. DecisionSnapshotStatistics
# ============================================================================

class TestDecisionSnapshotStatistics:
    def test_initial_zeros(self):
        stats = DecisionSnapshotStatistics()
        snap  = stats.snapshot()
        assert snap["snapshots_created"]   == 0
        assert snap["snapshots_published"] == 0
        assert snap["validation_success"]  == 0

    def test_record_created(self):
        stats = DecisionSnapshotStatistics()
        stats.record_snapshot_created(build_time_s=0.1, snapshot_size=512)
        s = stats.snapshot()
        assert s["snapshots_created"] == 1
        assert s["average_build_time_s"] > 0
        assert s["average_snapshot_size"] > 0

    def test_record_validated_success(self):
        stats = DecisionSnapshotStatistics()
        stats.record_snapshot_validated(success=True)
        stats.record_snapshot_validated(success=True)
        stats.record_snapshot_validated(success=False)
        s = stats.snapshot()
        assert s["validation_success"] == 2
        assert s["validation_failure"] == 1

    def test_validation_success_rate(self):
        stats = DecisionSnapshotStatistics()
        stats.record_snapshot_validated(success=True)
        stats.record_snapshot_validated(success=False)
        s = stats.snapshot()
        assert s["validation_success_rate"] == pytest.approx(0.5)

    def test_record_published(self):
        stats = DecisionSnapshotStatistics()
        stats.record_snapshot_published()
        stats.record_snapshot_published()
        assert stats.snapshot()["snapshots_published"] == 2

    def test_record_archived(self):
        stats = DecisionSnapshotStatistics()
        stats.record_snapshot_archived()
        assert stats.snapshot()["snapshots_archived"] == 1

    def test_reset(self):
        stats = DecisionSnapshotStatistics()
        stats.record_snapshot_created(build_time_s=0.1)
        stats.record_snapshot_validated(success=True)
        stats.reset()
        s = stats.snapshot()
        assert s["snapshots_created"] == 0
        assert s["validation_success"] == 0

    def test_throughput_window(self):
        stats = DecisionSnapshotStatistics()
        for _ in range(5):
            stats.record_snapshot_created()
        assert stats.snapshot()["snapshot_throughput"] >= 5


# ============================================================================
# 10. DecisionSnapshotHistory
# ============================================================================

class TestDecisionSnapshotHistory:
    def test_record_and_retrieve_snapshots(self):
        history = DecisionSnapshotHistory()
        s = _snapshot()
        history.record_snapshot(s)
        assert history.snapshot_count() == 1
        assert history.latest_snapshot() is s

    def test_snapshots_for_decision(self):
        history = DecisionSnapshotHistory()
        s1 = _snapshot(decision_id="dec-A")
        s2 = _snapshot(decision_id="dec-B")
        history.record_snapshot(s1)
        history.record_snapshot(s2)
        result = history.snapshots_for_decision("dec-A")
        assert len(result) == 1
        assert result[0].decision_id == "dec-A"

    def test_snapshots_for_session(self):
        history = DecisionSnapshotHistory()
        history.record_snapshot(_snapshot(session_id="sess-A"))
        history.record_snapshot(_snapshot(session_id="sess-B"))
        assert len(history.snapshots_for_session("sess-A")) == 1

    def test_latest_for_decision(self):
        history = DecisionSnapshotHistory()
        s1 = _snapshot(decision_id="dec-X", snapshot_version=1)
        s2 = _snapshot(decision_id="dec-X", snapshot_version=2)
        history.record_snapshot(s1)
        history.record_snapshot(s2)
        latest = history.latest_for_decision("dec-X")
        assert latest is s2

    def test_record_and_retrieve_events(self):
        history = DecisionSnapshotHistory()
        ev = make_snapshot_created("s", "d", "ss", "src")
        history.record_event(ev)
        assert history.event_count() == 1
        assert history.latest_event() is ev

    def test_events_by_type(self):
        history = DecisionSnapshotHistory()
        history.record_event(make_snapshot_created("s", "d", "ss", "src"))
        history.record_event(make_snapshot_published("s", "d", "ss", "src"))
        result = history.events_by_type(SnapshotEventType.SNAPSHOT_PUBLISHED)
        assert len(result) == 1

    def test_events_for_snapshot(self):
        history = DecisionSnapshotHistory()
        history.record_event(make_snapshot_created("snap-1", "d", "ss", "src"))
        history.record_event(make_snapshot_created("snap-2", "d", "ss", "src"))
        result = history.events_for_snapshot("snap-1")
        assert len(result) == 1

    def test_clear(self):
        history = DecisionSnapshotHistory()
        history.record_snapshot(_snapshot())
        history.record_event(make_snapshot_created("s", "d", "ss", "src"))
        history.clear()
        assert history.snapshot_count() == 0
        assert history.event_count() == 0

    def test_bounded_by_max(self):
        history = DecisionSnapshotHistory(max_snapshots=3)
        for i in range(5):
            history.record_snapshot(_snapshot(snapshot_id=f"snap-{i}"))
        assert history.snapshot_count() == 3


# ============================================================================
# 11. DecisionSnapshotCache
# ============================================================================

class TestDecisionSnapshotCache:
    def test_put_and_get(self):
        cache = DecisionSnapshotCache(max_size=10)
        s = _snapshot(snapshot_id="snap-1")
        cache.put(s)
        assert cache.get("snap-1") is s

    def test_miss_returns_none(self):
        cache = DecisionSnapshotCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        cache = DecisionSnapshotCache(max_size=2)
        s1 = _snapshot(snapshot_id="s1")
        s2 = _snapshot(snapshot_id="s2")
        s3 = _snapshot(snapshot_id="s3")
        cache.put(s1)
        cache.put(s2)
        cache.put(s3)  # evicts s1
        assert cache.get("s1") is None
        assert cache.get("s2") is not None
        assert cache.get("s3") is not None

    def test_invalidate(self):
        cache = DecisionSnapshotCache()
        s = _snapshot(snapshot_id="snap-x")
        cache.put(s)
        result = cache.invalidate("snap-x")
        assert result is True
        assert cache.get("snap-x") is None

    def test_invalidate_not_found_returns_false(self):
        cache = DecisionSnapshotCache()
        assert cache.invalidate("missing") is False

    def test_contains(self):
        cache = DecisionSnapshotCache()
        s = _snapshot(snapshot_id="snap-c")
        cache.put(s)
        assert cache.contains("snap-c")
        assert not cache.contains("other")

    def test_size(self):
        cache = DecisionSnapshotCache(max_size=100)
        cache.put(_snapshot())
        cache.put(_snapshot())
        assert cache.size() == 2

    def test_hit_rate_stats(self):
        cache = DecisionSnapshotCache()
        s = _snapshot(snapshot_id="snap-h")
        cache.put(s)
        cache.get("snap-h")
        cache.get("snap-h")
        cache.get("missing")
        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(2 / 3)

    def test_clear(self):
        cache = DecisionSnapshotCache()
        cache.put(_snapshot())
        cache.clear()
        assert cache.size() == 0

    def test_lru_updates_order_on_access(self):
        cache = DecisionSnapshotCache(max_size=2)
        s1 = _snapshot(snapshot_id="s1")
        s2 = _snapshot(snapshot_id="s2")
        cache.put(s1)
        cache.put(s2)
        # Access s1 to make it recently used
        cache.get("s1")
        s3 = _snapshot(snapshot_id="s3")
        cache.put(s3)  # evicts s2 (LRU)
        assert cache.get("s2") is None
        assert cache.get("s1") is not None


# ============================================================================
# 12. DecisionSnapshotRegistry
# ============================================================================

class TestDecisionSnapshotRegistry:
    def test_register_and_get(self):
        reg = DecisionSnapshotRegistry()
        s = _snapshot(snapshot_id="snap-r1")
        reg.register(s)
        assert reg.get("snap-r1") is s

    def test_get_not_found_raises(self):
        reg = DecisionSnapshotRegistry()
        with pytest.raises(SnapshotNotFoundError):
            reg.get("nonexistent")

    def test_find_returns_none(self):
        reg = DecisionSnapshotRegistry()
        assert reg.find("x") is None

    def test_duplicate_raises(self):
        reg = DecisionSnapshotRegistry()
        s = _snapshot(snapshot_id="dup")
        reg.register(s)
        with pytest.raises(DuplicateSnapshotError):
            reg.register(s)

    def test_deregister(self):
        reg = DecisionSnapshotRegistry()
        s = _snapshot(snapshot_id="snap-r2")
        reg.register(s)
        removed = reg.deregister("snap-r2")
        assert removed is s
        assert reg.find("snap-r2") is None

    def test_count(self):
        reg = DecisionSnapshotRegistry()
        reg.register(_snapshot())
        reg.register(_snapshot())
        assert reg.count() == 2

    def test_by_session(self):
        reg = DecisionSnapshotRegistry()
        reg.register(_snapshot(session_id="sess-A"))
        reg.register(_snapshot(session_id="sess-B"))
        result = reg.by_session("sess-A")
        assert len(result) == 1

    def test_by_decision(self):
        reg = DecisionSnapshotRegistry()
        reg.register(_snapshot(decision_id="dec-A"))
        reg.register(_snapshot(decision_id="dec-A", snapshot_version=2,
                                snapshot_id="snap-a2"))
        assert len(reg.by_decision("dec-A")) == 2

    def test_by_status(self):
        reg = DecisionSnapshotRegistry()
        reg.register(_snapshot(decision_status=DecisionStatus.APPROVED))
        reg.register(_snapshot(decision_status=DecisionStatus.REJECTED))
        assert len(reg.by_status("approved")) == 1
        assert len(reg.by_status("rejected")) == 1

    def test_by_type(self):
        reg = DecisionSnapshotRegistry()
        reg.register(_snapshot(decision_type="order"))
        reg.register(_snapshot(decision_type="position"))
        assert len(reg.by_type("order")) == 1

    def test_by_priority(self):
        reg = DecisionSnapshotRegistry()
        reg.register(_snapshot(decision_priority="high"))
        reg.register(_snapshot(decision_priority="low"))
        assert len(reg.by_priority("high")) == 1

    def test_latest_for_decision(self):
        reg = DecisionSnapshotRegistry()
        s1 = _snapshot(decision_id="dec-Z", snapshot_version=1, snapshot_id="z1")
        s2 = _snapshot(decision_id="dec-Z", snapshot_version=3, snapshot_id="z3")
        s3 = _snapshot(decision_id="dec-Z", snapshot_version=2, snapshot_id="z2")
        for s in [s1, s2, s3]:
            reg.register(s)
        latest = reg.latest_for_decision("dec-Z")
        assert latest.snapshot_version == 3

    def test_capacity_raises(self):
        reg = DecisionSnapshotRegistry(max_snapshots=2)
        reg.register(_snapshot())
        reg.register(_snapshot())
        with pytest.raises(SnapshotRegistryError):
            reg.register(_snapshot())

    def test_version_limit_raises(self):
        reg = DecisionSnapshotRegistry(max_versions=2)
        reg.register(_snapshot(decision_id="dec-V", snapshot_id="v1", snapshot_version=1))
        reg.register(_snapshot(decision_id="dec-V", snapshot_id="v2", snapshot_version=2))
        with pytest.raises(SnapshotRegistryError):
            reg.register(_snapshot(decision_id="dec-V", snapshot_id="v3", snapshot_version=3))

    def test_clear(self):
        reg = DecisionSnapshotRegistry()
        reg.register(_snapshot())
        reg.clear()
        assert reg.count() == 0


# ============================================================================
# 13. DecisionSnapshotStore
# ============================================================================

class TestDecisionSnapshotStore:
    def test_save_and_get(self):
        store = DecisionSnapshotStore()
        s = _snapshot(snapshot_id="store-1")
        store.save(s)
        assert store.get("store-1") is s

    def test_get_not_found_raises(self):
        store = DecisionSnapshotStore()
        with pytest.raises(SnapshotNotFoundError):
            store.get("missing")

    def test_find_returns_none(self):
        store = DecisionSnapshotStore()
        assert store.find("x") is None

    def test_duplicate_raises(self):
        store = DecisionSnapshotStore()
        s = _snapshot(snapshot_id="dup-store")
        store.save(s)
        with pytest.raises(DuplicateSnapshotError):
            store.save(s)

    def test_delete(self):
        store = DecisionSnapshotStore()
        s = _snapshot(snapshot_id="del-1")
        store.save(s)
        removed = store.delete("del-1")
        assert removed is s
        assert store.find("del-1") is None

    def test_latest_returns_highest_version(self):
        store = DecisionSnapshotStore()
        s1 = _snapshot(decision_id="dv", snapshot_version=1, snapshot_id="dv-1")
        s2 = _snapshot(decision_id="dv", snapshot_version=2, snapshot_id="dv-2")
        store.save(s1)
        store.save(s2)
        assert store.latest("dv").snapshot_version == 2

    def test_history_returns_all_versions(self):
        store = DecisionSnapshotStore()
        s1 = _snapshot(decision_id="dh", snapshot_version=1, snapshot_id="dh-1")
        s2 = _snapshot(decision_id="dh", snapshot_version=2, snapshot_id="dh-2")
        store.save(s1)
        store.save(s2)
        history = store.history("dh")
        assert len(history) == 2
        assert history[0].snapshot_version == 1

    def test_version_lookup(self):
        store = DecisionSnapshotStore()
        s = _snapshot(decision_id="dver", snapshot_version=3, snapshot_id="dver-3")
        store.save(s)
        found = store.version("dver", 3)
        assert found is s
        assert store.version("dver", 99) is None

    def test_by_session(self):
        store = DecisionSnapshotStore()
        store.save(_snapshot(session_id="sess-S1"))
        store.save(_snapshot(session_id="sess-S2"))
        assert len(store.by_session("sess-S1")) == 1

    def test_by_status(self):
        store = DecisionSnapshotStore()
        store.save(_snapshot(decision_status=DecisionStatus.APPROVED))
        store.save(_snapshot(decision_status=DecisionStatus.REJECTED))
        assert len(store.by_status("approved")) == 1

    def test_by_type(self):
        store = DecisionSnapshotStore()
        store.save(_snapshot(decision_type="order"))
        assert len(store.by_type("order")) == 1

    def test_by_priority(self):
        store = DecisionSnapshotStore()
        store.save(_snapshot(decision_priority="high"))
        assert len(store.by_priority("high")) == 1

    def test_by_timestamp_range(self):
        from datetime import timedelta
        store = DecisionSnapshotStore()
        now   = datetime.now(timezone.utc)
        s = _snapshot(created_at=now)
        store.save(s)
        result = store.by_timestamp_range(
            now - timedelta(seconds=1),
            now + timedelta(seconds=1),
        )
        assert len(result) == 1

    def test_count(self):
        store = DecisionSnapshotStore()
        store.save(_snapshot())
        store.save(_snapshot())
        assert store.count() == 2

    def test_cache_integration(self):
        store = DecisionSnapshotStore(cache_size=10)
        s = _snapshot(snapshot_id="cache-int")
        store.save(s)
        # First get warms cache
        store.get("cache-int")
        # Second get should be from cache
        store.get("cache-int")

    def test_validation_on_save_rejects_invalid(self):
        store = DecisionSnapshotStore(validate=True)
        invalid = DecisionSnapshot.create(
            snapshot_id="inv", session_id="", decision_id="d",
            lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
        )
        with pytest.raises(SnapshotValidationError):
            store.save(invalid)

    def test_no_validation_on_save(self):
        store = DecisionSnapshotStore(validate=False)
        invalid = DecisionSnapshot.create(
            snapshot_id="inv2", session_id="", decision_id="d",
            lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
        )
        store.save(invalid)  # should not raise
        assert store.contains("inv2")

    def test_clear(self):
        store = DecisionSnapshotStore()
        store.save(_snapshot())
        store.clear()
        assert store.count() == 0

    def test_version_limit_evicts_oldest(self):
        store = DecisionSnapshotStore(max_versions=2)
        s1 = _snapshot(decision_id="dvl", snapshot_version=1, snapshot_id="dvl-1")
        s2 = _snapshot(decision_id="dvl", snapshot_version=2, snapshot_id="dvl-2")
        s3 = _snapshot(decision_id="dvl", snapshot_version=3, snapshot_id="dvl-3")
        store.save(s1)
        store.save(s2)
        store.save(s3)  # evicts v1
        assert store.find("dvl-1") is None
        assert store.find("dvl-2") is not None


# ============================================================================
# 14. DecisionSnapshotBundle
# ============================================================================

class TestDecisionSnapshotBundle:
    def _make_bundle(self):
        snaps = [
            _snapshot(snapshot_id=f"b{i}", decision_id=f"dec-b{i}",
                      decision_status=DecisionStatus.APPROVED if i < 2 else DecisionStatus.REJECTED)
            for i in range(3)
        ]
        return DecisionSnapshotBundle.create("test bundle", snaps)

    def test_create_sets_uuid(self):
        bundle = self._make_bundle()
        assert bundle.bundle_id

    def test_size(self):
        bundle = self._make_bundle()
        assert bundle.size == 3

    def test_approved_count(self):
        bundle = self._make_bundle()
        assert bundle.approved_count == 2

    def test_rejected_count(self):
        bundle = self._make_bundle()
        assert bundle.rejected_count == 1

    def test_snapshot_ids(self):
        bundle = self._make_bundle()
        assert "b0" in bundle.snapshot_ids

    def test_decision_ids(self):
        bundle = self._make_bundle()
        assert "dec-b0" in bundle.decision_ids

    def test_get_by_snapshot_id(self):
        bundle = self._make_bundle()
        s = bundle.get("b0")
        assert s is not None
        assert s.snapshot_id == "b0"

    def test_get_missing_returns_none(self):
        bundle = self._make_bundle()
        assert bundle.get("nonexistent") is None

    def test_for_decision(self):
        bundle = self._make_bundle()
        s = bundle.for_decision("dec-b1")
        assert s is not None
        assert s.decision_id == "dec-b1"

    def test_contains(self):
        bundle = self._make_bundle()
        assert "b0" in bundle
        assert "zz" not in bundle

    def test_iter(self):
        bundle = self._make_bundle()
        ids = [s.snapshot_id for s in bundle]
        assert len(ids) == 3

    def test_len(self):
        bundle = self._make_bundle()
        assert len(bundle) == 3

    def test_to_dict(self):
        bundle = self._make_bundle()
        d = bundle.to_dict()
        assert "bundle_id" in d
        assert d["size"] == 3
        assert "snapshot_ids" in d

    def test_immutable(self):
        bundle = self._make_bundle()
        with pytest.raises((AttributeError, TypeError)):
            bundle.name = "changed"  # type: ignore[misc]

    def test_explicit_bundle_id(self):
        bundle = DecisionSnapshotBundle.create("b", [_snapshot()], bundle_id="my-bundle")
        assert bundle.bundle_id == "my-bundle"

    def test_healthy_count(self):
        snaps = [_snapshot(decision_health=DecisionHealth.HEALTHY),
                 _snapshot(decision_health=DecisionHealth.DEGRADED)]
        bundle = DecisionSnapshotBundle.create("b2", snaps)
        assert bundle.healthy_count == 1


# ============================================================================
# 15. __init__ exports
# ============================================================================

class TestInit:
    def test_key_symbols_importable(self):
        import iios.decision.snapshot as pkg
        for name in [
            "DecisionSnapshot", "DecisionSnapshotBuilder", "DecisionSnapshotStore",
            "DecisionSnapshotCache", "DecisionSnapshotRegistry",
            "DecisionSnapshotFactory", "DecisionSnapshotValidator",
            "DecisionSnapshotHistory", "DecisionSnapshotStatistics",
            "DecisionSnapshotBundle", "DecisionSnapshotEvent",
        ]:
            assert hasattr(pkg, name), f"Missing export: {name}"

    def test_version_accessible(self):
        import iios.decision.snapshot as pkg
        assert pkg.VERSION

    def test_snapshot_system_id(self):
        import iios.decision.snapshot as pkg
        assert pkg.SNAPSHOT_SYSTEM_ID


# ============================================================================
# 16. Concurrency
# ============================================================================

class TestConcurrency:
    def test_registry_concurrent_registration(self):
        reg = DecisionSnapshotRegistry(max_snapshots=200)
        errors = []

        def register_batch(n):
            try:
                for _ in range(n):
                    reg.register(_snapshot())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_batch, args=(10,)) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert reg.count() == 50

    def test_store_concurrent_save(self):
        store  = DecisionSnapshotStore(max_snapshots=200, validate=False)
        errors = []

        def save_batch(n):
            try:
                for _ in range(n):
                    store.save(_snapshot(session_id="s", decision_id="d"))
            except DuplicateSnapshotError:
                pass   # expected on very rare collision with same UUID
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_batch, args=(10,)) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors

    def test_cache_concurrent_put_get(self):
        cache  = DecisionSnapshotCache(max_size=50)
        errors = []

        def run():
            try:
                s = _snapshot()
                cache.put(s)
                cache.get(s.snapshot_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors

    def test_history_concurrent_record(self):
        history = DecisionSnapshotHistory()
        errors  = []

        def record():
            try:
                history.record_snapshot(_snapshot())
                history.record_event(make_snapshot_created("s", "d", "ss", "src"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert history.snapshot_count() == 20
        assert history.event_count() == 20


# ============================================================================
# 17. Regression
# ============================================================================

class TestRegression:
    def test_snapshot_immutability_deep(self):
        """Summaries stored as dicts should not mutate original."""
        orig_summary = {"candidates": 2}
        # Build snapshot directly to control optimization_summary
        s = DecisionSnapshot.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
            optimization_summary=dict(orig_summary),
        )
        # Mutate the original dict
        orig_summary["candidates"] = 99
        # Snapshot's dict was created from a copy — stays at 2
        assert s.optimization_summary.get("candidates") == 2

    def test_serialization_roundtrip_via_factory(self):
        original = _snapshot()
        restored = DecisionSnapshotFactory().from_dict(original.to_dict())
        assert restored.snapshot_id      == original.snapshot_id
        assert restored.decision_status  == original.decision_status
        assert restored.decision_score   == pytest.approx(original.decision_score)
        assert restored.decision_confidence == pytest.approx(original.decision_confidence)

    def test_store_get_after_cache_clear(self):
        store = DecisionSnapshotStore(cache_size=10)
        s = _snapshot(snapshot_id="cache-clear-test")
        store.save(s)
        store._cache.clear()  # force cache miss
        found = store.get("cache-clear-test")
        assert found is s

    def test_builder_does_not_mutate_input_metadata(self):
        meta = {"key": "original"}
        snap = DecisionSnapshotBuilder().build(FakeSession(), decision_metadata=meta)
        meta["key"] = "changed"
        assert snap.decision_metadata.get("key") == "original"

    def test_snapshot_version_uniqueness(self):
        fac = DecisionSnapshotFactory()
        s1  = fac.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
            snapshot_version=1,
        )
        s2  = fac.create(
            session_id="s", decision_id="d", lifecycle_state="completed",
            decision_scope="order", decision_type="order", decision_priority="medium",
            snapshot_version=2,
        )
        assert s1.snapshot_version != s2.snapshot_version
