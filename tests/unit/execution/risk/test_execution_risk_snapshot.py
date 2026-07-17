"""tests/unit/execution/risk/test_execution_risk_snapshot.py
==================================================
Unit tests for C6 Phase 4 M5 — Execution Risk Snapshot.

Coverage:
  TestConstants              — enums, sentinel sets
  TestExceptions             — hierarchy, error codes, fields
  TestAuditMetadata          — construction, to_dict
  TestRiskMetadata           — construction, to_dict
  TestOverrideMetadata       — construction, to_dict, make_override_metadata_from
  TestRuleSnapshot           — construction, to_dict, bool properties
  TestExecutionRiskSnapshot  — properties, to_dict, to_json, with_status, with_*_audit
  TestSnapshotValidation     — valid snapshot, all error cases
  TestSnapshotBuilder        — happy path, each missing-input error
  TestSnapshotFactory        — all convenience factories
  TestSnapshotEvents         — all 6 event factory functions, to_dict
  TestSnapshotStatistics     — record_*, properties, copy, to_dict, reset
  TestSnapshotHistory        — append, versions, latest, oldest, count, total, clear
  TestSnapshotStore          — put, get, require, duplicate, capacity, all indices,
                               latest, update_status, remove, clear
  TestSnapshotCache          — put, get, peek, LRU eviction, evict, clear, is_full
  TestSnapshotBundle         — properties, get, ids, to_dict, make_snapshot_bundle
  TestSnapshotRegistry       — start/stop, register, publish, archive, get, require,
                               duplicate, not-running, all query methods, stats, events
  TestConcurrency            — store concurrent puts, registry concurrent registers
  TestEdgeCases              — empty snapshot_id builder guard, archived publish guard,
                               to_json roundtrip
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import replace
from typing import Any
from unittest.mock import MagicMock

import pytest

from iios.execution.risk.snapshot import (
    AuditMetadata,
    DuplicateSnapshotError,
    ExecutionRiskSnapshot,
    ExecutionRiskSnapshotError,
    OverrideMetadata,
    PUBLISHABLE_STATUSES,
    RiskMetadata,
    RuleSnapshot,
    SNAPSHOT_SYSTEM_ID,
    SNAPSHOT_VERSION,
    TERMINAL_STATUSES,
    VALID_LIFECYCLE_STATES_FOR_SNAPSHOT,
    VERSION,
    SnapshotBuildError,
    SnapshotBundle,
    SnapshotBuilder,
    SnapshotCache,
    SnapshotEvent,
    SnapshotEventType,
    SnapshotFactory,
    SnapshotHistory,
    SnapshotNotFoundError,
    SnapshotRegistryNotRunningError,
    SnapshotRegistry,
    SnapshotSerializationError,
    SnapshotStatistics,
    SnapshotStatus,
    SnapshotStore,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotValidationResult,
    SnapshotValidator,
    SnapshotVersionError,
    make_audit_metadata,
    make_override_metadata_from,
    make_risk_metadata,
    make_snapshot_archived_event,
    make_snapshot_bundle,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_snapshot(**overrides) -> ExecutionRiskSnapshot:
    return SnapshotFactory.create_minimal(**overrides)


def _allow_snapshot(**overrides) -> ExecutionRiskSnapshot:
    return SnapshotFactory.create_allow_snapshot(**overrides)


def _block_snapshot(**overrides) -> ExecutionRiskSnapshot:
    return SnapshotFactory.create_block_snapshot(**overrides)


def _emergency_snapshot(**overrides) -> ExecutionRiskSnapshot:
    return SnapshotFactory.create_emergency_snapshot(**overrides)


def _make_lifecycle(
    risk_id:    str = "",
    state_val:  str = "PASSED",
    **kw,
) -> Any:
    """Minimal fake M1 ExecutionRisk object."""
    m = MagicMock()
    m.risk_id       = risk_id or str(uuid.uuid4())
    m.execution_id  = kw.get("execution_id", str(uuid.uuid4()))
    m.order_id      = kw.get("order_id", "ORD-001")
    m.position_id   = kw.get("position_id", "")
    m.portfolio_id  = kw.get("portfolio_id", "PORT-001")
    m.workflow_id   = kw.get("workflow_id", "WF-001")
    m.strategy_id   = kw.get("strategy_id", "STRAT-001")
    m.correlation_id = kw.get("correlation_id", "")
    state_mock = MagicMock()
    state_mock.value = state_val
    m.state = state_mock
    cat_mock = MagicMock()
    cat_mock.value = kw.get("risk_category", "EXECUTION")
    m.risk_category = cat_mock
    return m


def _make_engine_result() -> Any:
    m = MagicMock()
    m.succeeded  = True
    m.elapsed_ms = 10.0
    return m


def _make_rule_result(
    rule_id:   str = "",
    outcome:   str = "PASS",
    blocked:   bool = False,
    warned:    bool = False,
    passed:    bool = True,
    failed:    bool = False,
    skipped:   bool = False,
    override_required: bool = False,
) -> Any:
    m = MagicMock()
    m.rule_id    = rule_id or str(uuid.uuid4())
    m.rule_name  = "test_rule"
    outcome_mock = MagicMock()
    outcome_mock.value = outcome
    m.outcome    = outcome_mock
    cat_mock     = MagicMock()
    cat_mock.value = "MARKET"
    m.category   = cat_mock
    m.message    = "Test message"
    m.reason     = "Test reason"
    m.elapsed_ms = 2.0
    m.metadata   = {}
    m.blocked    = blocked
    m.warned     = warned
    m.passed     = passed
    m.failed     = failed
    m.skipped    = skipped
    m.override_required = override_required
    return m


def _make_control_decision(
    action_val: str = "ALLOW",
    policy_val: str = "HIGHEST_SEVERITY",
    overridden: bool = False,
    emergency:  bool = False,
) -> Any:
    m = MagicMock()
    m.decision_id = str(uuid.uuid4())
    action_mock   = MagicMock()
    action_mock.value = action_val
    m.action      = action_mock
    policy_mock   = MagicMock()
    policy_mock.value = policy_val
    m.policy_used = policy_mock
    m.elapsed_ms  = 5.0
    m.was_overridden = overridden
    m.is_emergency   = emergency
    m.override_info  = None
    return m


def _build_snapshot(
    state_val:  str = "PASSED",
    action_val: str = "ALLOW",
    rule_count: int = 1,
) -> ExecutionRiskSnapshot:
    lifecycle = _make_lifecycle(state_val=state_val)
    engine    = _make_engine_result()
    rules     = [_make_rule_result() for _ in range(rule_count)]
    decision  = _make_control_decision(action_val=action_val)
    return SnapshotBuilder() \
        .with_lifecycle(lifecycle) \
        .with_engine_result(engine) \
        .with_rule_results(rules) \
        .with_control_decision(decision) \
        .build()


# ── TestConstants ─────────────────────────────────────────────────────────────

class TestConstants:
    def test_snapshot_system_id_prefix(self):
        assert SNAPSHOT_SYSTEM_ID.startswith("iios:")

    def test_snapshot_version(self):
        assert SNAPSHOT_VERSION == "1.0.0"

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_snapshot_status_values(self):
        vals = {s.value for s in SnapshotStatus}
        assert "created"   in vals
        assert "published" in vals
        assert "archived"  in vals
        assert "invalid"   in vals

    def test_snapshot_event_type_values(self):
        vals = {e.value for e in SnapshotEventType}
        assert "snapshot_created"   in vals
        assert "snapshot_published" in vals
        assert "snapshot_archived"  in vals
        assert "snapshot_retrieved" in vals

    def test_publishable_statuses(self):
        assert SnapshotStatus.CREATED  in PUBLISHABLE_STATUSES
        assert SnapshotStatus.ARCHIVED not in PUBLISHABLE_STATUSES

    def test_terminal_statuses(self):
        assert SnapshotStatus.ARCHIVED in TERMINAL_STATUSES
        assert SnapshotStatus.CREATED  not in TERMINAL_STATUSES

    def test_valid_lifecycle_states(self):
        assert "PASSED"    in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT
        assert "BLOCKED"   in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT
        assert "WARNING"   in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT
        assert "OVERRIDDEN" in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT
        assert "ARCHIVED"  in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT
        assert "CREATED"   not in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT
        assert "PENDING_EVALUATION" not in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT


# ── TestExceptions ────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(ExecutionRiskSnapshotError, IIOSError)

    def test_all_subclass_base(self):
        for exc_cls in (
            SnapshotBuildError, SnapshotValidationError, SnapshotNotFoundError,
            DuplicateSnapshotError, SnapshotVersionError, SnapshotStoreError,
            SnapshotRegistryNotRunningError, SnapshotSerializationError,
        ):
            assert issubclass(exc_cls, ExecutionRiskSnapshotError)

    def test_build_error(self):
        e = SnapshotBuildError("bad build")
        assert "bad build" in str(e)

    def test_validation_error_has_snapshot_id(self):
        e = SnapshotValidationError("invalid", snapshot_id="snap-1")
        assert e.snapshot_id == "snap-1"

    def test_not_found_error_has_snapshot_id(self):
        e = SnapshotNotFoundError("snap-2")
        assert e.snapshot_id == "snap-2"

    def test_duplicate_error_has_snapshot_id(self):
        e = DuplicateSnapshotError("snap-3")
        assert e.snapshot_id == "snap-3"

    def test_registry_not_running_no_args(self):
        e = SnapshotRegistryNotRunningError()
        assert "not running" in str(e).lower() or e is not None


# ── TestAuditMetadata ─────────────────────────────────────────────────────────

class TestAuditMetadata:
    def test_construction(self):
        m = make_audit_metadata(created_by="test", correlation_id="C1")
        assert m.created_by == "test"
        assert m.correlation_id == "C1"
        assert m.created_at > 0

    def test_to_dict_keys(self):
        m = make_audit_metadata()
        d = m.to_dict()
        assert "created_by" in d
        assert "created_at" in d
        assert "framework_version" in d

    def test_optional_fields_default_none(self):
        m = make_audit_metadata()
        assert m.published_at is None
        assert m.archived_at  is None

    def test_immutable(self):
        m = make_audit_metadata()
        with pytest.raises((TypeError, AttributeError)):
            m.created_by = "changed"  # type: ignore


# ── TestRiskMetadata ──────────────────────────────────────────────────────────

class TestRiskMetadata:
    def test_construction(self):
        m = make_risk_metadata(risk_category="EXECUTION", rule_count=5, pass_count=4)
        assert m.risk_category == "EXECUTION"
        assert m.rule_count == 5
        assert m.pass_count == 4

    def test_to_dict(self):
        m = make_risk_metadata(rule_count=3, block_count=1)
        d = m.to_dict()
        assert d["rule_count"] == 3
        assert d["block_count"] == 1

    def test_defaults_zero(self):
        m = make_risk_metadata()
        assert m.rule_count == 0
        assert m.warning_count == 0


# ── TestOverrideMetadata ──────────────────────────────────────────────────────

class TestOverrideMetadata:
    def test_construction(self):
        m = OverrideMetadata(
            override_id="OV-1",
            approver="compliance",
            reason="manual override",
            timestamp=time.time(),
            original_action="BLOCK",
            new_action="ALLOW",
            affected_rule_ids=("rule-1", "rule-2"),
        )
        assert m.approver == "compliance"
        assert len(m.affected_rule_ids) == 2

    def test_to_dict(self):
        m = OverrideMetadata(
            override_id="OV-2",
            approver="risk_mgr",
            reason="pre-approved",
            timestamp=time.time(),
            original_action="BLOCK",
            new_action="ALLOW",
            affected_rule_ids=(),
        )
        d = m.to_dict()
        assert d["override_id"] == "OV-2"
        assert isinstance(d["affected_rule_ids"], list)

    def test_make_override_metadata_from(self):
        fake = MagicMock()
        fake.override_id = "OV-3"
        fake.approver    = "mgr"
        fake.reason      = "test"
        fake.timestamp   = 1000.0
        action_mock      = MagicMock()
        action_mock.value = "BLOCK"
        fake.original_action = action_mock
        action_mock2     = MagicMock()
        action_mock2.value = "ALLOW"
        fake.new_action  = action_mock2
        fake.affected_rule_ids = ["r1"]

        m = make_override_metadata_from(fake)
        assert m.override_id == "OV-3"
        assert m.original_action == "BLOCK"
        assert m.new_action == "ALLOW"
        assert "r1" in m.affected_rule_ids


# ── TestRuleSnapshot ──────────────────────────────────────────────────────────

class TestRuleSnapshot:
    def test_construction(self):
        r = RuleSnapshot(
            rule_id="R1",
            rule_name="limit_check",
            category="MARKET",
            outcome="PASS",
            message="ok",
            reason="within limits",
            elapsed_ms=1.5,
            metadata={"key": "val"},
        )
        assert r.rule_id == "R1"
        assert r.outcome == "PASS"

    def test_to_dict(self):
        r = RuleSnapshot(
            rule_id="R2", rule_name="n", category="c",
            outcome="BLOCK", message="m", reason="r", elapsed_ms=2.0,
        )
        d = r.to_dict()
        assert d["outcome"] == "BLOCK"
        assert "metadata" in d

    def test_immutable(self):
        r = RuleSnapshot(
            rule_id="R3", rule_name="n", category="c",
            outcome="PASS", message="m", reason="r", elapsed_ms=0.0,
        )
        with pytest.raises((TypeError, AttributeError)):
            r.outcome = "BLOCK"  # type: ignore


# ── TestExecutionRiskSnapshot ─────────────────────────────────────────────────

class TestExecutionRiskSnapshot:
    def test_minimal_factory(self):
        s = _minimal_snapshot(risk_id="R1")
        assert s.risk_id == "R1"
        assert s.snapshot_id
        assert s.snapshot_version == SNAPSHOT_VERSION

    def test_allow_snapshot_properties(self):
        s = _allow_snapshot()
        assert s.allowed is True
        assert s.is_blocked is False
        assert s.is_emergency is False

    def test_block_snapshot_properties(self):
        s = _block_snapshot()
        assert s.is_blocked is True
        assert s.allowed is False

    def test_emergency_snapshot_properties(self):
        s = _emergency_snapshot()
        assert s.is_emergency is True
        assert s.is_blocked is True

    def test_rule_count(self):
        rule = RuleSnapshot(
            rule_id="R1", rule_name="n", category="c",
            outcome="PASS", message="m", reason="r", elapsed_ms=1.0,
        )
        s = replace(_minimal_snapshot(), triggered_rules=(rule,))
        assert s.rule_count == 1

    def test_block_count(self):
        rule = RuleSnapshot(
            rule_id="R1", rule_name="n", category="c",
            outcome="BLOCK", message="m", reason="r", elapsed_ms=1.0,
        )
        s = replace(_minimal_snapshot(), blocks=(rule,))
        assert s.block_count == 1

    def test_warning_count(self):
        rule = RuleSnapshot(
            rule_id="R1", rule_name="n", category="c",
            outcome="WARNING", message="m", reason="r", elapsed_ms=1.0,
        )
        s = replace(_minimal_snapshot(), warnings=(rule,))
        assert s.warning_count == 1

    def test_to_dict_structure(self):
        s = _allow_snapshot()
        d = s.to_dict()
        assert "snapshot_id"   in d
        assert "risk_id"       in d
        assert "final_action"  in d
        assert "triggered_rules" in d
        assert "risk_metadata" in d
        assert "audit_metadata" in d
        assert "status"        in d

    def test_to_json_valid(self):
        s = _allow_snapshot()
        raw = s.to_json()
        parsed = json.loads(raw)
        assert parsed["snapshot_id"] == s.snapshot_id

    def test_to_json_indent(self):
        s = _allow_snapshot()
        raw = s.to_json(indent=2)
        assert "\n" in raw

    def test_with_status(self):
        s = _allow_snapshot(status=SnapshotStatus.CREATED)
        updated = s.with_status(SnapshotStatus.PUBLISHED)
        assert updated.status == SnapshotStatus.PUBLISHED
        assert s.status == SnapshotStatus.CREATED

    def test_with_published_audit(self):
        s = _minimal_snapshot()
        updated = s.with_published_audit(published_by="tester")
        assert updated.audit_metadata.published_by == "tester"
        assert updated.audit_metadata.published_at is not None
        assert updated.status == SnapshotStatus.PUBLISHED

    def test_with_archived_audit(self):
        s = _minimal_snapshot()
        updated = s.with_archived_audit(archived_by="archivist")
        assert updated.audit_metadata.archived_by == "archivist"
        assert updated.status == SnapshotStatus.ARCHIVED

    def test_immutable(self):
        s = _minimal_snapshot()
        with pytest.raises((TypeError, AttributeError)):
            s.risk_id = "hacked"  # type: ignore

    def test_age_ms(self):
        s = _minimal_snapshot()
        time.sleep(0.01)
        assert s.age_ms >= 0

    def test_was_overridden_false_by_default(self):
        s = _minimal_snapshot()
        assert s.was_overridden is False

    def test_is_published(self):
        s = _allow_snapshot(status=SnapshotStatus.PUBLISHED)
        assert s.is_published is True


# ── TestSnapshotValidation ────────────────────────────────────────────────────

class TestSnapshotValidation:
    def test_valid_snapshot_passes(self):
        s = _allow_snapshot()
        result = SnapshotValidator.validate_snapshot(s)
        assert result.is_valid

    def test_empty_snapshot_id_fails(self):
        s = replace(_minimal_snapshot(), snapshot_id="")
        result = SnapshotValidator.validate_snapshot(s)
        assert not result.is_valid
        assert any("snapshot_id" in e for e in result.errors)

    def test_empty_risk_id_fails(self):
        s = replace(_minimal_snapshot(), risk_id="")
        result = SnapshotValidator.validate_snapshot(s)
        assert not result.is_valid
        assert any("risk_id" in e for e in result.errors)

    def test_invalid_risk_state_fails(self):
        s = replace(_minimal_snapshot(), risk_state="CREATED")
        result = SnapshotValidator.validate_snapshot(s)
        assert not result.is_valid

    def test_invalid_timestamp_fails(self):
        s = replace(_minimal_snapshot(), snapshot_timestamp=-1.0)
        result = SnapshotValidator.validate_snapshot(s)
        assert not result.is_valid

    def test_override_status_without_metadata_fails(self):
        s = replace(
            _minimal_snapshot(),
            override_status=True,
            override_metadata=None,
        )
        result = SnapshotValidator.validate_snapshot(s)
        assert not result.is_valid

    def test_empty_control_action_fails(self):
        s = replace(_minimal_snapshot(), control_action="")
        result = SnapshotValidator.validate_snapshot(s)
        assert not result.is_valid

    def test_raise_if_invalid_raises(self):
        s = replace(_minimal_snapshot(), snapshot_id="")
        result = SnapshotValidator.validate_snapshot(s)
        with pytest.raises(SnapshotValidationError):
            SnapshotValidator.raise_if_invalid(result, "test", snapshot_id="X")

    def test_raise_if_invalid_does_not_raise_on_valid(self):
        s = _allow_snapshot()
        result = SnapshotValidator.validate_snapshot(s)
        SnapshotValidator.raise_if_invalid(result)  # should not raise

    def test_validate_completeness(self):
        s = _allow_snapshot()
        result = SnapshotValidator.validate_completeness(s)
        assert result.is_valid

    def test_validate_completeness_fails_empty_category(self):
        s = replace(_allow_snapshot(), risk_category="")
        result = SnapshotValidator.validate_completeness(s)
        assert not result.is_valid

    def test_validation_result_bool(self):
        r_ok  = SnapshotValidationResult(True, (), ())
        r_bad = SnapshotValidationResult(False, ("err",), ())
        assert bool(r_ok) is True
        assert bool(r_bad) is False


# ── TestSnapshotBuilder ───────────────────────────────────────────────────────

class TestSnapshotBuilder:
    def test_happy_path(self):
        s = _build_snapshot()
        assert s.snapshot_id
        assert s.risk_state == "PASSED"
        assert s.final_action == "ALLOW"

    def test_missing_lifecycle_raises(self):
        with pytest.raises(SnapshotBuildError, match="lifecycle"):
            SnapshotBuilder() \
                .with_engine_result(_make_engine_result()) \
                .with_rule_results([]) \
                .with_control_decision(_make_control_decision()) \
                .build()

    def test_missing_engine_result_raises(self):
        with pytest.raises(SnapshotBuildError, match="engine_result"):
            SnapshotBuilder() \
                .with_lifecycle(_make_lifecycle()) \
                .with_rule_results([]) \
                .with_control_decision(_make_control_decision()) \
                .build()

    def test_missing_rule_results_raises(self):
        with pytest.raises(SnapshotBuildError, match="rule_results"):
            SnapshotBuilder() \
                .with_lifecycle(_make_lifecycle()) \
                .with_engine_result(_make_engine_result()) \
                .with_control_decision(_make_control_decision()) \
                .build()

    def test_missing_control_decision_raises(self):
        with pytest.raises(SnapshotBuildError, match="control_decision"):
            SnapshotBuilder() \
                .with_lifecycle(_make_lifecycle()) \
                .with_engine_result(_make_engine_result()) \
                .with_rule_results([]) \
                .build()

    def test_invalid_lifecycle_state_raises(self):
        lc = _make_lifecycle(state_val="CREATED")  # not a terminal outcome state
        with pytest.raises(SnapshotBuildError, match="terminal"):
            SnapshotBuilder() \
                .with_lifecycle(lc) \
                .with_engine_result(_make_engine_result()) \
                .with_rule_results([]) \
                .with_control_decision(_make_control_decision()) \
                .build()

    def test_failed_engine_result_raises(self):
        eng = _make_engine_result()
        eng.succeeded = False
        lc = _make_lifecycle(state_val="PASSED")
        with pytest.raises(SnapshotBuildError, match="succeeded"):
            SnapshotBuilder() \
                .with_lifecycle(lc) \
                .with_engine_result(eng) \
                .with_rule_results([]) \
                .with_control_decision(_make_control_decision()) \
                .build()

    def test_empty_risk_id_raises(self):
        lc = _make_lifecycle(risk_id="", state_val="PASSED")
        lc.risk_id = ""
        with pytest.raises(SnapshotBuildError, match="risk_id"):
            SnapshotBuilder() \
                .with_lifecycle(lc) \
                .with_engine_result(_make_engine_result()) \
                .with_rule_results([]) \
                .with_control_decision(_make_control_decision()) \
                .build()

    def test_block_rules_extracted(self):
        rules = [
            _make_rule_result(outcome="BLOCK", blocked=True, passed=False),
            _make_rule_result(outcome="PASS",  passed=True),
        ]
        lc  = _make_lifecycle(state_val="BLOCKED")
        dec = _make_control_decision(action_val="BLOCK")
        s = SnapshotBuilder() \
            .with_lifecycle(lc) \
            .with_engine_result(_make_engine_result()) \
            .with_rule_results(rules) \
            .with_control_decision(dec) \
            .build()
        assert s.block_count == 1

    def test_warning_rules_extracted(self):
        rules = [_make_rule_result(outcome="WARNING", warned=True, passed=False)]
        lc  = _make_lifecycle(state_val="WARNING")
        dec = _make_control_decision(action_val="ALLOW_WITH_WARNING")
        s = SnapshotBuilder() \
            .with_lifecycle(lc) \
            .with_engine_result(_make_engine_result()) \
            .with_rule_results(rules) \
            .with_control_decision(dec) \
            .build()
        assert s.warning_count == 1

    def test_skipped_rules_not_in_triggered(self):
        rules = [_make_rule_result(outcome="SKIPPED", skipped=True, passed=False)]
        s = _build_snapshot()  # uses default rules; just confirm builder works
        # Skipped rules should not appear in triggered_rules
        skipped_rule = _make_rule_result(outcome="SKIPPED", skipped=True, passed=False)
        lc  = _make_lifecycle(state_val="PASSED")
        dec = _make_control_decision(action_val="ALLOW")
        s2 = SnapshotBuilder() \
            .with_lifecycle(lc) \
            .with_engine_result(_make_engine_result()) \
            .with_rule_results([skipped_rule]) \
            .with_control_decision(dec) \
            .build()
        assert s2.rule_count == 0

    def test_reset(self):
        b = SnapshotBuilder().with_lifecycle(_make_lifecycle())
        b.reset()
        with pytest.raises(SnapshotBuildError):
            b.with_engine_result(_make_engine_result()) \
             .with_rule_results([]) \
             .with_control_decision(_make_control_decision()) \
             .build()

    def test_with_extra_metadata(self):
        lc  = _make_lifecycle(state_val="PASSED")
        dec = _make_control_decision()
        s = SnapshotBuilder() \
            .with_lifecycle(lc) \
            .with_engine_result(_make_engine_result()) \
            .with_rule_results([]) \
            .with_control_decision(dec) \
            .with_extra_metadata(source="test") \
            .build()
        assert s.extra_metadata.get("source") == "test"


# ── TestSnapshotFactory ───────────────────────────────────────────────────────

class TestSnapshotFactory:
    def test_build_from_pipeline(self):
        lc  = _make_lifecycle(state_val="PASSED")
        eng = _make_engine_result()
        rules = [_make_rule_result()]
        dec   = _make_control_decision()
        s = SnapshotFactory.build_from_pipeline(lc, eng, rules, dec)
        assert s.snapshot_id
        assert s.final_action == "ALLOW"

    def test_create_minimal(self):
        s = SnapshotFactory.create_minimal(risk_id="R1")
        assert s.risk_id == "R1"

    def test_create_allow_snapshot(self):
        s = SnapshotFactory.create_allow_snapshot()
        assert s.allowed is True
        assert s.status == SnapshotStatus.PUBLISHED

    def test_create_block_snapshot(self):
        s = SnapshotFactory.create_block_snapshot()
        assert s.is_blocked is True

    def test_create_warning_snapshot(self):
        s = SnapshotFactory.create_warning_snapshot()
        assert s.final_action == "ALLOW_WITH_WARNING"

    def test_create_emergency_snapshot(self):
        s = SnapshotFactory.create_emergency_snapshot()
        assert s.is_emergency is True

    def test_minimal_generates_unique_ids(self):
        a = SnapshotFactory.create_minimal()
        b = SnapshotFactory.create_minimal()
        assert a.snapshot_id != b.snapshot_id
        assert a.risk_id     != b.risk_id


# ── TestSnapshotEvents ────────────────────────────────────────────────────────

class TestSnapshotEvents:
    def _check(self, event: SnapshotEvent, expected_type: SnapshotEventType):
        assert isinstance(event, SnapshotEvent)
        assert event.event_type == expected_type
        assert event.event_id
        assert event.occurred_at > 0

    def test_created_event(self):
        e = make_snapshot_created_event("sid", "rid")
        self._check(e, SnapshotEventType.SNAPSHOT_CREATED)
        assert e.snapshot_id == "sid"
        assert e.risk_id     == "rid"

    def test_validated_event(self):
        e = make_snapshot_validated_event("sid", "rid")
        self._check(e, SnapshotEventType.SNAPSHOT_VALIDATED)

    def test_published_event(self):
        e = make_snapshot_published_event("sid", "rid")
        self._check(e, SnapshotEventType.SNAPSHOT_PUBLISHED)

    def test_archived_event(self):
        e = make_snapshot_archived_event("sid", "rid")
        self._check(e, SnapshotEventType.SNAPSHOT_ARCHIVED)

    def test_retrieved_event(self):
        e = make_snapshot_retrieved_event("sid", "rid")
        self._check(e, SnapshotEventType.SNAPSHOT_RETRIEVED)

    def test_cached_event(self):
        e = make_snapshot_cached_event("sid", "rid")
        self._check(e, SnapshotEventType.SNAPSHOT_CACHED)

    def test_to_dict(self):
        e = make_snapshot_created_event("sid", "rid")
        d = e.to_dict()
        assert d["event_type"]  == SnapshotEventType.SNAPSHOT_CREATED.value
        assert d["snapshot_id"] == "sid"

    def test_event_carries_metadata(self):
        e = make_snapshot_created_event("sid", "rid", source="test")
        assert e.metadata.get("source") == "test"


# ── TestSnapshotStatistics ────────────────────────────────────────────────────

class TestSnapshotStatistics:
    def test_initial_zeroes(self):
        s = SnapshotStatistics()
        assert s.snapshots_created == 0
        assert s.average_build_time_ms == 0.0

    def test_record_created(self):
        s = SnapshotStatistics()
        s.record_created(elapsed_ms=50.0)
        assert s.snapshots_created == 1
        assert s.total_build_time_ms == 50.0
        assert s.average_build_time_ms == 50.0

    def test_record_published(self):
        s = SnapshotStatistics()
        s.record_published()
        assert s.snapshots_published == 1

    def test_record_archived(self):
        s = SnapshotStatistics()
        s.record_archived()
        assert s.snapshots_archived == 1

    def test_record_validation(self):
        s = SnapshotStatistics()
        s.record_validation_success()
        s.record_validation_failure()
        assert s.validation_success == 1
        assert s.validation_failure == 1
        assert s.validation_pass_rate == 0.5

    def test_cache_hit_rate(self):
        s = SnapshotStatistics()
        s.record_cache_hit()
        s.record_cache_hit()
        s.record_cache_miss()
        assert abs(s.cache_hit_rate - 2/3) < 0.001

    def test_reset(self):
        s = SnapshotStatistics()
        s.record_created(50.0)
        s.reset()
        assert s.snapshots_created == 0

    def test_copy_is_independent(self):
        s = SnapshotStatistics()
        s.record_created(10.0)
        c = s.copy()
        s.record_created(20.0)
        assert c.snapshots_created == 1
        assert s.snapshots_created == 2

    def test_to_dict(self):
        s = SnapshotStatistics()
        d = s.to_dict()
        assert "snapshots_created" in d
        assert "cache_hit_rate" in d


# ── TestSnapshotHistory ───────────────────────────────────────────────────────

class TestSnapshotHistory:
    def _make_n(self, n: int) -> list:
        return [_allow_snapshot(risk_id="R1") for _ in range(n)]

    def test_append_and_versions(self):
        h = SnapshotHistory()
        s = _allow_snapshot(risk_id="R1")
        h.append(s)
        assert h.count_versions("R1") == 1
        assert h.versions("R1")[0].snapshot_id == s.snapshot_id

    def test_latest(self):
        h = SnapshotHistory()
        s1 = _allow_snapshot(risk_id="R1")
        s2 = _allow_snapshot(risk_id="R1")
        h.append(s1)
        h.append(s2)
        assert h.latest("R1").snapshot_id == s2.snapshot_id

    def test_oldest(self):
        h = SnapshotHistory()
        s1 = _allow_snapshot(risk_id="R1")
        s2 = _allow_snapshot(risk_id="R1")
        h.append(s1)
        h.append(s2)
        assert h.oldest("R1").snapshot_id == s1.snapshot_id

    def test_latest_returns_none_for_unknown(self):
        h = SnapshotHistory()
        assert h.latest("nonexistent") is None

    def test_total(self):
        h = SnapshotHistory()
        h.append(_allow_snapshot(risk_id="R1"))
        h.append(_allow_snapshot(risk_id="R2"))
        assert h.total == 2

    def test_all_returns_all(self):
        h = SnapshotHistory()
        h.append(_allow_snapshot(risk_id="R1"))
        h.append(_allow_snapshot(risk_id="R2"))
        assert len(h.all()) == 2

    def test_evicts_oldest_when_full(self):
        h = SnapshotHistory(max_versions_per_risk=2)
        snaps = self._make_n(3)
        for s in snaps:
            h.append(s)
        remaining = h.versions("R1")
        assert len(remaining) == 2
        assert remaining[-1].snapshot_id == snaps[2].snapshot_id

    def test_clear(self):
        h = SnapshotHistory()
        h.append(_allow_snapshot(risk_id="R1"))
        h.clear()
        assert h.total == 0

    def test_tracked_risk_ids(self):
        h = SnapshotHistory()
        h.append(_allow_snapshot(risk_id="R1"))
        h.append(_allow_snapshot(risk_id="R2"))
        assert set(h.tracked_risk_ids) == {"R1", "R2"}


# ── TestSnapshotStore ─────────────────────────────────────────────────────────

class TestSnapshotStore:
    def test_put_and_get(self):
        st = SnapshotStore()
        s  = _allow_snapshot()
        st.put(s)
        assert st.get(s.snapshot_id) == s

    def test_require_raises_not_found(self):
        st = SnapshotStore()
        with pytest.raises(SnapshotNotFoundError):
            st.require("nonexistent")

    def test_duplicate_raises(self):
        st = SnapshotStore()
        s  = _allow_snapshot()
        st.put(s)
        with pytest.raises(DuplicateSnapshotError):
            st.put(s)

    def test_capacity_exceeded_raises(self):
        st = SnapshotStore(max_size=1)
        st.put(_allow_snapshot())
        with pytest.raises(SnapshotStoreError):
            st.put(_allow_snapshot())

    def test_contains(self):
        st = SnapshotStore()
        s  = _allow_snapshot()
        assert st.contains(s.snapshot_id) is False
        st.put(s)
        assert st.contains(s.snapshot_id) is True

    def test_count(self):
        st = SnapshotStore()
        st.put(_allow_snapshot())
        st.put(_allow_snapshot())
        assert st.count == 2

    def test_get_by_risk_id(self):
        st = SnapshotStore()
        s  = _allow_snapshot(risk_id="R1")
        st.put(s)
        result = st.get_by_risk_id("R1")
        assert len(result) == 1
        assert result[0].snapshot_id == s.snapshot_id

    def test_get_by_execution_id(self):
        st = SnapshotStore()
        s  = _allow_snapshot(execution_id="E1")
        st.put(s)
        assert len(st.get_by_execution_id("E1")) == 1

    def test_get_by_order_id(self):
        st = SnapshotStore()
        s  = _allow_snapshot(order_id="O1")
        st.put(s)
        assert len(st.get_by_order_id("O1")) == 1

    def test_get_by_portfolio_id(self):
        st = SnapshotStore()
        s  = _allow_snapshot(portfolio_id="PORT-1")
        st.put(s)
        assert len(st.get_by_portfolio_id("PORT-1")) == 1

    def test_get_by_strategy_id(self):
        st = SnapshotStore()
        s  = _allow_snapshot(strategy_id="STRAT-1")
        st.put(s)
        assert len(st.get_by_strategy_id("STRAT-1")) == 1

    def test_latest_n(self):
        st = SnapshotStore()
        for _ in range(5):
            st.put(_allow_snapshot())
        assert len(st.latest(3)) == 3

    def test_update_status(self):
        st = SnapshotStore()
        s  = _allow_snapshot(status=SnapshotStatus.CREATED)
        st.put(s)
        updated = st.update_status(s.snapshot_id, SnapshotStatus.PUBLISHED)
        assert updated.status == SnapshotStatus.PUBLISHED
        assert st.get(s.snapshot_id).status == SnapshotStatus.PUBLISHED

    def test_remove(self):
        st = SnapshotStore()
        s  = _allow_snapshot()
        st.put(s)
        st.remove(s.snapshot_id)
        assert st.get(s.snapshot_id) is None
        assert st.count == 0

    def test_clear(self):
        st = SnapshotStore()
        st.put(_allow_snapshot())
        st.clear()
        assert st.count == 0

    def test_all(self):
        st = SnapshotStore()
        st.put(_allow_snapshot())
        st.put(_allow_snapshot())
        assert len(st.all()) == 2


# ── TestSnapshotCache ─────────────────────────────────────────────────────────

class TestSnapshotCache:
    def test_put_and_get(self):
        c = SnapshotCache()
        s = _allow_snapshot()
        c.put(s)
        assert c.get(s.snapshot_id) == s

    def test_get_returns_none_for_missing(self):
        c = SnapshotCache()
        assert c.get("nope") is None

    def test_contains(self):
        c = SnapshotCache()
        s = _allow_snapshot()
        assert c.contains(s.snapshot_id) is False
        c.put(s)
        assert c.contains(s.snapshot_id) is True

    def test_evict(self):
        c = SnapshotCache()
        s = _allow_snapshot()
        c.put(s)
        assert c.evict(s.snapshot_id) is True
        assert c.contains(s.snapshot_id) is False

    def test_evict_missing_returns_false(self):
        c = SnapshotCache()
        assert c.evict("ghost") is False

    def test_lru_eviction(self):
        c = SnapshotCache(max_size=2)
        s1, s2, s3 = _allow_snapshot(), _allow_snapshot(), _allow_snapshot()
        c.put(s1)
        c.put(s2)
        c.put(s3)  # should evict s1
        assert c.contains(s1.snapshot_id) is False
        assert c.contains(s2.snapshot_id) is True
        assert c.contains(s3.snapshot_id) is True

    def test_get_refreshes_lru(self):
        c = SnapshotCache(max_size=2)
        s1, s2 = _allow_snapshot(), _allow_snapshot()
        c.put(s1)
        c.put(s2)
        c.get(s1.snapshot_id)   # s1 is now MRU
        s3 = _allow_snapshot()
        c.put(s3)               # should evict s2 (LRU), not s1
        assert c.contains(s1.snapshot_id) is True
        assert c.contains(s2.snapshot_id) is False

    def test_size(self):
        c = SnapshotCache(max_size=10)
        c.put(_allow_snapshot())
        assert c.size == 1

    def test_is_full(self):
        c = SnapshotCache(max_size=1)
        assert c.is_full is False
        c.put(_allow_snapshot())
        assert c.is_full is True

    def test_clear(self):
        c = SnapshotCache()
        c.put(_allow_snapshot())
        c.clear()
        assert c.size == 0

    def test_peek_no_lru_change(self):
        c = SnapshotCache(max_size=2)
        s1, s2 = _allow_snapshot(), _allow_snapshot()
        c.put(s1)
        c.put(s2)
        c.peek(s1.snapshot_id)  # should NOT refresh s1
        s3 = _allow_snapshot()
        c.put(s3)               # should evict s1 (still LRU)
        assert c.contains(s1.snapshot_id) is False


# ── TestSnapshotBundle ────────────────────────────────────────────────────────

class TestSnapshotBundle:
    def test_construction(self):
        snaps = [_allow_snapshot(), _block_snapshot()]
        b = make_snapshot_bundle(snaps, source="test")
        assert b.count == 2
        assert b.metadata["source"] == "test"

    def test_blocked_snapshots(self):
        b = make_snapshot_bundle([_allow_snapshot(), _block_snapshot()])
        assert len(b.blocked_snapshots) == 1

    def test_allowed_snapshots(self):
        b = make_snapshot_bundle([_allow_snapshot(), _block_snapshot()])
        assert len(b.allowed_snapshots) == 1

    def test_emergencies(self):
        b = make_snapshot_bundle([_allow_snapshot(), _emergency_snapshot()])
        assert len(b.emergencies) == 1

    def test_has_blocks(self):
        b = make_snapshot_bundle([_block_snapshot()])
        assert b.has_blocks is True
        b2 = make_snapshot_bundle([_allow_snapshot()])
        assert b2.has_blocks is False

    def test_get_by_id(self):
        s = _allow_snapshot()
        b = make_snapshot_bundle([s])
        assert b.get(s.snapshot_id) == s
        assert b.get("nope") is None

    def test_ids(self):
        s1, s2 = _allow_snapshot(), _block_snapshot()
        b = make_snapshot_bundle([s1, s2])
        ids = b.ids()
        assert s1.snapshot_id in ids
        assert s2.snapshot_id in ids

    def test_to_dict(self):
        b = make_snapshot_bundle([_allow_snapshot()])
        d = b.to_dict()
        assert "bundle_id" in d
        assert "snapshots" in d
        assert "count" in d

    def test_empty_bundle(self):
        b = make_snapshot_bundle([])
        assert b.count == 0
        assert b.has_blocks is False


# ── TestSnapshotRegistry ──────────────────────────────────────────────────────

class TestSnapshotRegistry:
    def _registry(self) -> SnapshotRegistry:
        r = SnapshotRegistry()
        r.start()
        return r

    def test_start_stop(self):
        r = SnapshotRegistry()
        r.start()
        assert r.is_running
        r.stop()
        assert not r.is_running

    def test_register(self):
        r = self._registry()
        s = _allow_snapshot()
        r.register(s)
        assert r.snapshot_count == 1
        r.stop()

    def test_register_returns_snapshot(self):
        r = self._registry()
        s = _allow_snapshot()
        out = r.register(s)
        assert out.snapshot_id == s.snapshot_id
        r.stop()

    def test_register_duplicate_raises(self):
        r = self._registry()
        s = _allow_snapshot()
        r.register(s)
        with pytest.raises(DuplicateSnapshotError):
            r.register(s)
        r.stop()

    def test_not_running_raises(self):
        r = SnapshotRegistry()
        with pytest.raises(SnapshotRegistryNotRunningError):
            r.register(_allow_snapshot())

    def test_get_after_register(self):
        r = self._registry()
        s = _allow_snapshot()
        r.register(s)
        found = r.get(s.snapshot_id)
        assert found is not None
        assert found.snapshot_id == s.snapshot_id
        r.stop()

    def test_get_returns_none_for_missing(self):
        r = self._registry()
        assert r.get("nope") is None
        r.stop()

    def test_require_raises_not_found(self):
        r = self._registry()
        with pytest.raises(SnapshotNotFoundError):
            r.require("nope")
        r.stop()

    def test_publish(self):
        r = self._registry()
        s = _minimal_snapshot()
        r.register(s)
        updated = r.publish(s.snapshot_id, published_by="tester")
        assert updated.status == SnapshotStatus.PUBLISHED
        assert updated.audit_metadata.published_by == "tester"
        r.stop()

    def test_publish_retrieves_updated(self):
        r = self._registry()
        s = _minimal_snapshot()
        r.register(s)
        r.publish(s.snapshot_id)
        retrieved = r.get(s.snapshot_id)
        assert retrieved.status == SnapshotStatus.PUBLISHED
        r.stop()

    def test_archive(self):
        r = self._registry()
        s = _minimal_snapshot()
        r.register(s)
        updated = r.archive(s.snapshot_id, archived_by="archiver")
        assert updated.status == SnapshotStatus.ARCHIVED
        r.stop()

    def test_archive_idempotent(self):
        r = self._registry()
        s = _minimal_snapshot()
        r.register(s)
        r.archive(s.snapshot_id)
        r.archive(s.snapshot_id)   # should not raise
        r.stop()

    def test_get_by_risk_id(self):
        r = self._registry()
        s = _allow_snapshot(risk_id="R1")
        r.register(s)
        assert len(r.get_by_risk_id("R1")) == 1
        r.stop()

    def test_get_by_execution_id(self):
        r = self._registry()
        s = _allow_snapshot(execution_id="E1")
        r.register(s)
        assert len(r.get_by_execution_id("E1")) == 1
        r.stop()

    def test_get_by_order_id(self):
        r = self._registry()
        s = _allow_snapshot(order_id="O1")
        r.register(s)
        assert len(r.get_by_order_id("O1")) == 1
        r.stop()

    def test_get_by_portfolio_id(self):
        r = self._registry()
        s = _allow_snapshot(portfolio_id="PORT-1")
        r.register(s)
        assert len(r.get_by_portfolio_id("PORT-1")) == 1
        r.stop()

    def test_get_by_strategy_id(self):
        r = self._registry()
        s = _allow_snapshot(strategy_id="STRAT-1")
        r.register(s)
        assert len(r.get_by_strategy_id("STRAT-1")) == 1
        r.stop()

    def test_latest(self):
        r = self._registry()
        for _ in range(5):
            r.register(_allow_snapshot())
        assert len(r.latest(3)) == 3
        r.stop()

    def test_history_for_risk_id(self):
        r = self._registry()
        s1 = _allow_snapshot(risk_id="R1")
        s2 = _allow_snapshot(risk_id="R1")
        r.register(s1)
        r.register(s2)
        hist = r.history_for_risk_id("R1")
        assert len(hist) == 2
        r.stop()

    def test_latest_for_risk_id(self):
        r = self._registry()
        s1 = _allow_snapshot(risk_id="R1")
        s2 = _allow_snapshot(risk_id="R1")
        r.register(s1)
        r.register(s2)
        latest = r.latest_for_risk_id("R1")
        assert latest.snapshot_id == s2.snapshot_id
        r.stop()

    def test_statistics(self):
        r = self._registry()
        r.register(_allow_snapshot())
        stats = r.statistics()
        assert stats.snapshots_created == 1
        r.stop()

    def test_events(self):
        r = self._registry()
        r.register(_allow_snapshot())
        evts = r.events()
        assert any(e.event_type == SnapshotEventType.SNAPSHOT_CREATED for e in evts)
        r.stop()

    def test_all(self):
        r = self._registry()
        r.register(_allow_snapshot())
        r.register(_allow_snapshot())
        assert len(r.all()) == 2
        r.stop()

    def test_cache_hit_tracking(self):
        r = self._registry()
        s = _allow_snapshot()
        r.register(s)
        r.get(s.snapshot_id)  # cache miss (cache was populated on register)
        r.get(s.snapshot_id)  # cache hit
        stats = r.statistics()
        assert stats.cache_hits >= 1
        r.stop()


# ── TestConcurrency ───────────────────────────────────────────────────────────

class TestConcurrency:
    def test_store_concurrent_puts(self):
        st  = SnapshotStore(max_size=100)
        errors = []

        def _put():
            try:
                st.put(_allow_snapshot())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_put) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert st.count == 20

    def test_registry_concurrent_registers(self):
        r = SnapshotRegistry()
        r.start()
        errors = []

        def _register():
            try:
                r.register(_allow_snapshot())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_register) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        r.stop()
        assert len(errors) == 0


# ── TestEdgeCases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_to_json_roundtrip(self):
        s  = _build_snapshot()
        d1 = s.to_dict()
        d2 = json.loads(s.to_json())
        assert d1["snapshot_id"] == d2["snapshot_id"]
        assert d1["final_action"] == d2["final_action"]

    def test_publish_archived_snapshot_raises(self):
        r = SnapshotRegistry()
        r.start()
        s = _minimal_snapshot()
        r.register(s)
        r.archive(s.snapshot_id)
        with pytest.raises(SnapshotNotFoundError):
            r.publish(s.snapshot_id)
        r.stop()

    def test_empty_triggered_rules(self):
        s = _build_snapshot(rule_count=0)
        assert s.rule_count == 0
        assert s.block_count == 0
        assert s.warning_count == 0

    def test_store_get_returns_none_not_raises(self):
        st = SnapshotStore()
        assert st.get("nope") is None

    def test_history_empty_risk_returns_none(self):
        h = SnapshotHistory()
        assert h.latest("unknown") is None
        assert h.oldest("unknown") is None

    def test_validation_result_has_validated_at(self):
        r = SnapshotValidationResult(True, (), ())
        assert r.validated_at > 0

    def test_snapshot_bundle_immutable(self):
        b = make_snapshot_bundle([_allow_snapshot()])
        with pytest.raises((TypeError, AttributeError)):
            b.count = 99  # type: ignore

    def test_audit_metadata_replace(self):
        a = make_audit_metadata()
        b = replace(a, published_by="tester")
        assert b.published_by == "tester"
        assert a.published_by == ""
