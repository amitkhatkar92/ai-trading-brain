"""tests/unit/investment/workflow/test_workflow_context.py
Tests for WorkflowParameters and WorkflowEngines.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from iios.investment.workflow.workflow_context import WorkflowEngines, WorkflowParameters


class TestWorkflowParameters:
    def test_defaults(self):
        p = WorkflowParameters()
        assert p.max_retries >= 0
        assert p.retry_delay_sec >= 0.0
        assert p.stage_timeout_sec > 0.0
        assert p.publish_portfolio_snapshot is True

    def test_custom_values(self):
        p = WorkflowParameters(max_retries=3, retry_delay_sec=1.0, stage_timeout_sec=60.0)
        assert p.max_retries == 3
        assert p.retry_delay_sec == 1.0
        assert p.stage_timeout_sec == 60.0

    def test_frozen(self):
        p = WorkflowParameters()
        with pytest.raises((AttributeError, TypeError)):
            p.max_retries = 99  # type: ignore

    def test_invalid_max_retries(self):
        with pytest.raises(ValueError):
            WorkflowParameters(max_retries=-1)

    def test_invalid_timeout(self):
        with pytest.raises(ValueError):
            WorkflowParameters(stage_timeout_sec=0.0)

    def test_invalid_delay(self):
        with pytest.raises(ValueError):
            WorkflowParameters(retry_delay_sec=-0.1)

    def test_to_dict(self):
        p = WorkflowParameters()
        d = p.to_dict()
        assert "max_retries" in d
        assert "stage_timeout_sec" in d
        assert "publish_portfolio_snapshot" in d

    def test_skip_flags(self):
        p = WorkflowParameters(
            skip_company_stage=True,
            skip_strategy_stage=True,
            skip_decision_stage=True,
        )
        assert p.skip_company_stage
        assert p.skip_strategy_stage
        assert p.skip_decision_stage

    def test_quality_gates_default_zero(self):
        p = WorkflowParameters()
        assert p.min_quality_market == 0.0
        assert p.min_quality_portfolio == 0.0


class TestWorkflowEngines:
    def test_all_none_by_default(self):
        e = WorkflowEngines()
        assert e.market_engine   is None
        assert e.company_engine  is None
        assert e.strategy_engine is None
        assert e.decision_engine is None
        assert e.portfolio_engine is None

    def test_inject_custom_engines(self):
        m = MagicMock()
        e = WorkflowEngines(market_engine=m)
        assert e.market_engine is m

    def test_event_callback_accepted(self):
        cb = lambda t, d: None
        e  = WorkflowEngines(event_callback=cb)
        assert e.event_callback is cb

    def test_ensure_defaults_creates_engines(self):
        """ensure_defaults() lazily creates engines when None."""
        e = WorkflowEngines()
        e.ensure_defaults()
        assert e.market_engine   is not None
        assert e.company_engine  is not None
        assert e.strategy_engine is not None
        assert e.decision_engine is not None
        assert e.portfolio_engine is not None

    def test_ensure_defaults_respects_injected(self):
        mock_eng = MagicMock()
        e = WorkflowEngines(market_engine=mock_eng)
        e.ensure_defaults()
        assert e.market_engine is mock_eng  # not replaced
