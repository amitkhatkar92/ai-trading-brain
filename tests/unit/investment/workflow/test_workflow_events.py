"""tests/unit/investment/workflow/test_workflow_events.py
Tests for WorkflowEvent and WorkflowEventPublisher.
"""
from __future__ import annotations

from typing import List
import pytest

from iios.investment.workflow.workflow_events import WorkflowEvent, WorkflowEventPublisher
from iios.investment.workflow.workflow_types import PipelineEventType, WorkflowStage


class TestWorkflowEvent:
    def test_frozen(self):
        ev = WorkflowEvent(
            event_type  = PipelineEventType.WORKFLOW_STARTED,
            workflow_id = "wf",
            request_id  = "req",
            stage       = None,
            emitted_at  = "iso",
        )
        with pytest.raises((AttributeError, TypeError)):
            ev.workflow_id = "new"  # type: ignore

    def test_to_dict(self):
        ev = WorkflowEvent(
            event_type  = PipelineEventType.STAGE_COMPLETED,
            workflow_id = "wf",
            request_id  = "req",
            stage       = WorkflowStage.MARKET,
            emitted_at  = "iso",
            payload     = {"duration_ms": 50.0},
        )
        d = ev.to_dict()
        assert d["event_type"] == "stage_completed"
        assert d["stage"]      == "market"
        assert d["payload"]["duration_ms"] == 50.0


class TestWorkflowEventPublisher:
    def test_register_and_receive(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        ev = WorkflowEvent(
            event_type=PipelineEventType.WORKFLOW_STARTED,
            workflow_id="w", request_id="r", stage=None, emitted_at="t",
        )
        pub.publish(ev)
        assert len(captured) == 1
        assert captured[0] is ev

    def test_unregister(self):
        captured: List[WorkflowEvent] = []
        cb  = lambda e: captured.append(e)
        pub = WorkflowEventPublisher()
        pub.register(cb)
        pub.unregister(cb)
        pub.emit_workflow_started("w", "r", "P")
        assert len(captured) == 0

    def test_callback_exception_does_not_propagate(self):
        pub = WorkflowEventPublisher()
        pub.register(lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        # Should not raise
        pub.emit_workflow_started("w", "r", "P")

    def test_emit_workflow_started(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_workflow_started("wf", "req", "P-1")
        assert captured[0].event_type == PipelineEventType.WORKFLOW_STARTED
        assert captured[0].payload["portfolio_id"] == "P-1"

    def test_emit_stage_started(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_stage_started("wf", "req", WorkflowStage.MARKET, attempt=2)
        assert captured[0].event_type == PipelineEventType.STAGE_STARTED
        assert captured[0].stage      == WorkflowStage.MARKET
        assert captured[0].payload["attempt"] == 2

    def test_emit_stage_completed(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_stage_completed("wf", "req", WorkflowStage.COMPANY, 55.0, "snap-1")
        assert captured[0].event_type == PipelineEventType.STAGE_COMPLETED
        assert captured[0].payload["snapshot_id"] == "snap-1"

    def test_emit_stage_retrying(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_stage_retrying("wf", "req", WorkflowStage.MARKET, 1, "timeout")
        assert captured[0].event_type == PipelineEventType.STAGE_RETRYING
        assert "timeout" in captured[0].payload["error"]

    def test_emit_stage_failed(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_stage_failed("wf", "req", WorkflowStage.MARKET, "crash")
        assert captured[0].event_type == PipelineEventType.STAGE_FAILED

    def test_emit_workflow_completed(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_workflow_completed("wf", "req", "P-1", 300.0, "snap-1")
        assert captured[0].event_type == PipelineEventType.WORKFLOW_COMPLETED

    def test_emit_workflow_failed(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_workflow_failed("wf", "req", WorkflowStage.MARKET, "fatal")
        assert captured[0].event_type == PipelineEventType.WORKFLOW_FAILED

    def test_emit_workflow_cancelled(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_workflow_cancelled("wf", "req")
        assert captured[0].event_type == PipelineEventType.WORKFLOW_CANCELLED

    def test_emit_snapshot_published(self):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        pub.emit_snapshot_published("wf", "req", "P-1", "snap-id")
        assert captured[0].event_type == PipelineEventType.PORTFOLIO_SNAPSHOT_PUBLISHED
        assert captured[0].payload["snapshot_id"] == "snap-id"

    def test_multiple_callbacks(self):
        captured1: List[WorkflowEvent] = []
        captured2: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured1.append(e))
        pub.register(lambda e: captured2.append(e))
        pub.emit_workflow_started("wf", "req", "P")
        assert len(captured1) == 1
        assert len(captured2) == 1

    def test_duplicate_register_ignored(self):
        captured: List[WorkflowEvent] = []
        cb  = lambda e: captured.append(e)
        pub = WorkflowEventPublisher()
        pub.register(cb)
        pub.register(cb)  # duplicate
        pub.emit_workflow_started("wf", "req", "P")
        assert len(captured) == 1  # only one delivery
