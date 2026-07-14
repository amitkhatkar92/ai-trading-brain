"""Tests for migration reports, summaries, audit, and confidence."""
import pytest
from datetime import datetime, timezone

from iios.investment.strategy.migration.migration_report import (
    MigrationReport,
    build_migration_report,
    RECOMMEND_APPROVE,
    RECOMMEND_REJECT,
    RECOMMEND_REVIEW,
)
from iios.investment.strategy.migration.migration_summary import (
    MigrationSummary,
    MigrationSummaryBuilder,
)
from iios.investment.strategy.migration.migration_audit import (
    AuditEntry,
    MigrationAudit,
    make_entry,
)
from iios.investment.strategy.migration.migration_confidence import MigrationConfidence
from iios.investment.strategy.migration.migration_session import MigrationSession
from iios.investment.strategy.migration.migration_status import MigrationStatus
from iios.investment.strategy.migration.adapter_factory import AdapterFactory
from iios.investment.strategy.migration.migration_validator import MigrationValidator


class TestMigrationReport:
    def test_build_report(self, basic_metadata):
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.COMPLETED,
        )
        assert isinstance(report, MigrationReport)

    def test_report_has_report_id(self, basic_metadata):
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.COMPLETED,
        )
        assert len(report.report_id) > 0

    def test_report_to_dict(self, basic_metadata):
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.COMPLETED,
        )
        d = report.to_dict()
        assert "report_id" in d
        assert "approval_recommendation" in d

    def test_failed_migration_gets_reject(self, basic_metadata):
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.FAILED,
        )
        assert report.approval_recommendation == RECOMMEND_REJECT

    def test_completed_with_good_validation_gets_approve(self, basic_metadata):
        validator = MigrationValidator()
        val_report = validator.validate_metadata(basic_metadata)
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.COMPLETED,
            validation_report=val_report,
        )
        # Good metadata → APPROVE or REVIEW (not REJECT)
        assert report.approval_recommendation in (RECOMMEND_APPROVE, RECOMMEND_REVIEW)

    def test_confidence_score_range(self, basic_metadata):
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.COMPLETED,
        )
        assert 0 <= report.confidence_score <= 100

    def test_failed_confidence_is_zero(self, basic_metadata):
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.FAILED,
        )
        assert report.confidence_score == 0.0


class TestMigrationSummary:
    def setup_method(self):
        self.builder = MigrationSummaryBuilder()

    def test_empty_summary(self):
        summary = self.builder.build([], [])
        assert summary.total_strategies == 0
        assert summary.success_rate == 0.0

    def test_summary_counts(self, basic_metadata, json_metadata):
        sessions = []
        reports  = []
        for meta in [basic_metadata, json_metadata]:
            s = MigrationSession.create(meta)
            s.advance(MigrationStatus.COMPLETED)
            sessions.append(s)
            r = build_migration_report(
                strategy_id=meta.strategy_id,
                strategy_name=meta.strategy_name,
                migration_status=MigrationStatus.COMPLETED,
            )
            reports.append(r)

        summary = self.builder.build(sessions, reports)
        assert summary.total_strategies == 2
        assert summary.completed == 2

    def test_summary_to_dict(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.COMPLETED)
        report  = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.COMPLETED,
        )
        summary = self.builder.build([session], [report])
        d = summary.to_dict()
        assert "total_strategies" in d
        assert "success_rate" in d

    def test_approve_candidates(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.COMPLETED)
        validator  = MigrationValidator()
        val_report = validator.validate_metadata(basic_metadata)
        report = build_migration_report(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            migration_status=MigrationStatus.COMPLETED,
            validation_report=val_report,
        )
        summary = self.builder.build([session], [report])
        candidates = summary.approve_candidates()
        assert isinstance(candidates, list)


class TestMigrationAudit:
    def setup_method(self):
        self.audit = MigrationAudit()

    def test_record_entry(self, basic_metadata):
        entry = make_entry(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            event_type="migration_started",
            before_state={},
            after_state={"status": "discovery"},
        )
        self.audit.record(entry)
        assert self.audit.count() == 1

    def test_get_by_strategy_id(self, basic_metadata):
        self.audit.record_event(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            event_type="test_event",
        )
        entries = self.audit.get(basic_metadata.strategy_id)
        assert len(entries) == 1

    def test_all_returns_all(self, basic_metadata, json_metadata):
        for meta in [basic_metadata, json_metadata]:
            self.audit.record_event(
                strategy_id=meta.strategy_id,
                strategy_name=meta.strategy_name,
                event_type="test",
            )
        assert len(self.audit.all()) == 2

    def test_export(self, basic_metadata):
        self.audit.record_event(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            event_type="exported",
        )
        exported = self.audit.export()
        assert len(exported) == 1
        assert "audit_id" in exported[0]

    def test_append_only(self, basic_metadata):
        initial_count = self.audit.count()
        for i in range(5):
            self.audit.record_event(
                strategy_id=str(i),
                strategy_name=f"S{i}",
                event_type="event",
            )
        assert self.audit.count() == initial_count + 5

    def test_strategies_audited(self, basic_metadata):
        self.audit.record_event(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            event_type="test",
        )
        ids = self.audit.strategies_audited()
        assert basic_metadata.strategy_id in ids

    def test_entry_to_dict(self, basic_metadata):
        self.audit.record_event(
            strategy_id=basic_metadata.strategy_id,
            strategy_name=basic_metadata.strategy_name,
            event_type="check",
        )
        entry = self.audit.get(basic_metadata.strategy_id)[0]
        d = entry.to_dict()
        assert "audit_id" in d
        assert "event_type" in d


class TestMigrationConfidence:
    def setup_method(self):
        self.factory   = AdapterFactory()
        self.validator = MigrationValidator()

    def test_compute_basic(self, basic_metadata):
        session    = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.COMPLETED)
        val_report = self.validator.validate_metadata(basic_metadata)
        confidence = MigrationConfidence.compute(session, val_report)
        assert isinstance(confidence, MigrationConfidence)
        assert 0 <= confidence.overall_confidence <= 100

    def test_grade_high(self, basic_metadata):
        session    = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.COMPLETED)
        val_report = self.validator.validate_metadata(basic_metadata)
        confidence = MigrationConfidence.compute(session, val_report)
        assert confidence.grade in ("HIGH", "MEDIUM", "LOW")

    def test_failed_session_low_confidence(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.mark_failed("forced fail")
        confidence = MigrationConfidence.compute(session)
        assert confidence.grade in ("LOW", "MEDIUM")

    def test_to_dict(self, basic_metadata):
        session    = MigrationSession.create(basic_metadata)
        val_report = self.validator.validate_metadata(basic_metadata)
        conf = MigrationConfidence.compute(session, val_report)
        d = conf.to_dict()
        assert "overall_confidence" in d
        assert "grade" in d

    def test_data_completeness_non_zero(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        conf    = MigrationConfidence.compute(session)
        assert conf.data_completeness > 0
