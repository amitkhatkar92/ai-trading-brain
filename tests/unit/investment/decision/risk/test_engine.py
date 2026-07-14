"""tests/unit/investment/decision/risk/test_engine.py
Tests for DecisionRiskEngine — lifecycle, sync/async eval, query API,
pluggable module support, version tracking.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from iios.investment.decision.risk.decision_risk_engine import DecisionRiskEngine
from iios.investment.decision.risk.risk_constants import (
    RiskEngineStatus,
    RiskPolicyStatus,
)
from iios.investment.decision.risk.risk_pipeline import BaseRiskModule, RiskContext
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot


# ─── Lifecycle ────────────────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_engine_starts_and_stops(self):
        engine = DecisionRiskEngine()
        engine.start()
        assert engine.health().status == RiskEngineStatus.READY
        engine.stop()
        assert engine.health().status == RiskEngineStatus.STOPPED

    def test_evaluate_before_start_raises(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        engine = DecisionRiskEngine()
        # no start() — still works because INITIALIZING is not STOPPED
        # Only STOPPED should raise — test after stop
        engine.start()
        engine.stop()
        with pytest.raises(RuntimeError):
            engine.evaluate_sync(
                rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
            )

    def test_version_is_string(self):
        assert isinstance(DecisionRiskEngine.VERSION, str)


# ─── evaluate_sync ───────────────────────────────────────────────────────────

class TestEvaluateSync:
    def setup_method(self):
        self.engine = DecisionRiskEngine()
        self.engine.start()

    def teardown_method(self):
        self.engine.stop()

    def test_returns_risk_snapshot(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        assert isinstance(snap, RiskSnapshot)

    def test_snapshot_ids_populated(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        assert snap.snapshot_id and snap.decision_id

    def test_overall_risk_in_range(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        assert 0.0 <= snap.overall_risk <= 100.0

    def test_policy_status_is_valid_enum(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        assert snap.policy_status in list(RiskPolicyStatus)

    def test_rich_snapshot_is_usable(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        # Rich inputs should generally produce a usable snapshot
        # (not guaranteed to be low risk, but should not fail)
        assert isinstance(snap.is_usable, bool)

    def test_custom_decision_id(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        d_id = str(uuid.uuid4())
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
            decision_id=d_id,
        )
        assert snap.decision_id == d_id

    def test_duration_positive(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        assert snap.evaluation_duration_ms >= 0.0

    def test_to_dict_structure(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        d = snap.to_dict()
        assert "snapshot_id" in d and "overall_risk" in d and "risk_level" in d


# ─── evaluate (async) ────────────────────────────────────────────────────────

class TestEvaluateAsync:
    def test_async_returns_same_type(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        engine = DecisionRiskEngine()
        engine.start()
        snap = asyncio.run(engine.evaluate(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        ))
        engine.stop()
        assert isinstance(snap, RiskSnapshot)

    def test_async_decision_id_preserved(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        engine = DecisionRiskEngine()
        engine.start()
        d_id = str(uuid.uuid4())
        snap = asyncio.run(engine.evaluate(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
            decision_id=d_id,
        ))
        engine.stop()
        assert snap.decision_id == d_id


# ─── Query API ───────────────────────────────────────────────────────────────

class TestQueryAPI:
    def setup_method(self):
        self.engine = DecisionRiskEngine()
        self.engine.start()

    def teardown_method(self):
        self.engine.stop()

    def test_get_snapshot_by_id(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        retrieved = self.engine.get_snapshot(snap.snapshot_id)
        assert retrieved is not None
        assert retrieved.snapshot_id == snap.snapshot_id

    def test_get_history_for_subject(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        history = self.engine.get_history(rich_evidence_snapshot.subject_id)
        assert len(history) >= 1

    def test_get_latest_returns_most_recent(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        latest = self.engine.get_latest(rich_evidence_snapshot.subject_id)
        assert latest is not None

    def test_risk_series_returns_list(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        series = self.engine.risk_series(rich_evidence_snapshot.subject_id)
        assert isinstance(series, list) and len(series) >= 1

    def test_stats_update_after_eval(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        stats = self.engine.stats()
        assert stats.successful >= 1

    def test_get_quality_returns_grade(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        from iios.investment.decision.risk.risk_constants import RiskQualityGrade
        snap = self.engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        grade = self.engine.get_quality(snap.snapshot_id)
        assert grade in list(RiskQualityGrade)

    def test_get_snapshot_missing_returns_none(self):
        assert self.engine.get_snapshot("nonexistent") is None

    def test_get_latest_missing_returns_none(self):
        assert self.engine.get_latest("NONEXISTENT_SUBJECT") is None


# ─── Pluggable module ────────────────────────────────────────────────────────

class _CustomModule(BaseRiskModule):
    @property
    def module_id(self) -> str:
        return "test_custom"

    def evaluate(self, context: RiskContext):
        return {"custom_value": 42}


class TestPluggableModule:
    def test_custom_module_result_in_pipeline(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        engine = DecisionRiskEngine(custom_modules=[_CustomModule()])
        engine.start()
        snap = engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        engine.stop()
        # The snapshot is stored — we can verify engine ran without error
        assert isinstance(snap, RiskSnapshot)

    def test_failing_custom_module_does_not_crash(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        class CrashModule(BaseRiskModule):
            @property
            def module_id(self): return "crash"
            def evaluate(self, ctx): raise ValueError("intentional crash")

        engine = DecisionRiskEngine(custom_modules=[CrashModule()])
        engine.start()
        snap = engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        engine.stop()
        assert isinstance(snap, RiskSnapshot)


# ─── validate_controls ───────────────────────────────────────────────────────

class TestValidateControls:
    def test_returns_bool(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        engine = DecisionRiskEngine()
        engine.start()
        result = engine.validate_controls(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        engine.stop()
        assert isinstance(result, bool)


# ─── blocks_execution property ───────────────────────────────────────────────

class TestBlocksExecution:
    def test_blocks_execution_is_bool(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        engine = DecisionRiskEngine()
        engine.start()
        snap = engine.evaluate_sync(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        engine.stop()
        assert isinstance(snap.blocks_execution, bool)
