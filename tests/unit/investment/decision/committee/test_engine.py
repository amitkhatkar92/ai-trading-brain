"""tests/unit/investment/decision/committee/test_engine.py
Tests for DecisionCommitteeEngine — full lifecycle, query API, async, history.
"""
from __future__ import annotations

import asyncio

import pytest

from iios.investment.decision.committee.committee_constants import (
    CommitteePosition,
    CommitteeStatus,
)
from iios.investment.decision.committee.committee_report import CommitteeReport
from iios.investment.decision.committee.decision_committee_engine import (
    DecisionCommitteeEngine,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _run_sync(engine: DecisionCommitteeEngine, ctx, did=None, version=1):
    return engine.run_committee_sync(
        ctx.evidence, ctx.reasoning, ctx.confidence, ctx.risk, ctx.explanation,
        did or ctx.decision_id, version,
    )


# ─── lifecycle ────────────────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_start_stop(self):
        engine = DecisionCommitteeEngine()
        engine.start()
        assert engine.health().status == CommitteeStatus.READY
        engine.stop()
        assert engine.health().status == CommitteeStatus.STOPPED

    def test_double_start_safe(self):
        engine = DecisionCommitteeEngine()
        engine.start()
        engine.start()  # should not raise
        engine.stop()

    def test_stop_without_start_safe(self):
        engine = DecisionCommitteeEngine()
        engine.stop()  # should not raise

    def test_run_requires_started(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        engine.stop()
        with pytest.raises(RuntimeError):
            _run_sync(engine, rich_context)


# ─── synchronous API ──────────────────────────────────────────────────────────

class TestEngineSyncAPI:
    def test_run_returns_committee_report(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            r = _run_sync(engine, rich_context)
            assert isinstance(r, CommitteeReport)
        finally:
            engine.stop()

    def test_rich_position_not_none(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            r = _run_sync(engine, rich_context)
            assert r.position is not None
        finally:
            engine.stop()

    def test_minimal_returns_insufficient(self, minimal_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            r = _run_sync(engine, minimal_context)
            assert r.position == CommitteePosition.INSUFFICIENT_EVIDENCE
        finally:
            engine.stop()

    def test_stats_increments(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            _run_sync(engine, rich_context)
            assert engine.stats().total_sessions >= 2
        finally:
            engine.stop()

    def test_health_healthy_after_success(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            assert engine.health().is_healthy
        finally:
            engine.stop()


# ─── query API ────────────────────────────────────────────────────────────────

class TestEngineQueryAPI:
    def test_get_report_by_id(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            r = _run_sync(engine, rich_context)
            found = engine.get_report(r.report_id)
            assert found is not None
            assert found.report_id == r.report_id
        finally:
            engine.stop()

    def test_get_report_missing_returns_none(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            assert engine.get_report("nonexistent-id") is None
        finally:
            engine.stop()

    def test_get_by_decision(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            did = rich_context.decision_id
            r   = _run_sync(engine, rich_context, did)
            found = engine.get_by_decision(did)
            assert found is not None
            assert found.decision_id == did
        finally:
            engine.stop()

    def test_get_latest(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            latest = engine.get_latest(rich_context.subject_id)
            assert latest is not None
        finally:
            engine.stop()

    def test_get_history_non_empty(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            h = engine.get_history(rich_context.subject_id)
            assert len(h) >= 1
        finally:
            engine.stop()

    def test_recent(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            r = engine.recent(10)
            assert len(r) >= 1
        finally:
            engine.stop()

    def test_known_subjects(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            subjects = engine.known_subjects()
            assert rich_context.subject_id in subjects
        finally:
            engine.stop()

    def test_position_series(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            series = engine.position_series(rich_context.subject_id)
            assert len(series) >= 1
        finally:
            engine.stop()

    def test_score_series(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            series = engine.score_series(rich_context.subject_id)
            assert len(series) >= 1
        finally:
            engine.stop()


# ─── async API ────────────────────────────────────────────────────────────────

class TestEngineAsyncAPI:
    def test_run_async_returns_report(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            report = asyncio.run(
                engine.run_committee(
                    rich_context.evidence,
                    rich_context.reasoning,
                    rich_context.confidence,
                    rich_context.risk,
                    rich_context.explanation,
                    rich_context.decision_id,
                )
            )
            assert isinstance(report, CommitteeReport)
        finally:
            engine.stop()

    def test_async_increments_stats(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            asyncio.run(
                engine.run_committee(
                    rich_context.evidence,
                    rich_context.reasoning,
                    rich_context.confidence,
                    rich_context.risk,
                    rich_context.explanation,
                    rich_context.decision_id,
                )
            )
            assert engine.stats().total_sessions >= 1
        finally:
            engine.stop()


# ─── statistics ───────────────────────────────────────────────────────────────

class TestEngineStatistics:
    def test_initial_stats_zero(self):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            s = engine.stats()
            assert s.total_sessions == 0
        finally:
            engine.stop()

    def test_success_rate_after_runs(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            _run_sync(engine, rich_context)
            assert engine.stats().success_rate > 0.0
        finally:
            engine.stop()

    def test_stats_to_dict(self, rich_context):
        engine = DecisionCommitteeEngine()
        engine.start()
        try:
            _run_sync(engine, rich_context)
            d = engine.stats().to_dict()
            assert "total_sessions" in d
            assert "success_rate"   in d
        finally:
            engine.stop()
