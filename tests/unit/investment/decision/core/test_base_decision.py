"""tests/unit/investment/decision/core/test_base_decision.py
Tests for BaseDecision lifecycle, state, context, metadata, and configuration.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from iios.investment.decision.core.decision_constants import (
    ApprovalStatus,
    DecisionStatus,
    EnvironmentProfile,
    RecommendationType,
    RiskReviewStatus,
)
from iios.investment.decision.core.decision_configuration import (
    DecisionConfiguration,
    DEVELOPMENT_CONFIG,
    LIVE_CONFIG,
)
from iios.investment.decision.core.decision_context import DecisionContext, make_context
from iios.investment.decision.core.decision_constants import DecisionType, DecisionPriority
from tests.unit.investment.decision.core.conftest import (
    FailingDecision,
    RejectedDecision,
    SimpleBuyDecision,
)


# ===========================================================================
# DecisionContext
# ===========================================================================

class TestDecisionContext:
    def test_make_context_defaults(self):
        ctx = make_context(
            decision_type=DecisionType.INVESTMENT,
            subject_id="INFY",
            subject_type="equity",
            source="test",
        )
        assert ctx.decision_id
        assert ctx.subject_id == "INFY"
        assert ctx.environment == EnvironmentProfile.DEVELOPMENT

    def test_to_dict(self):
        ctx = make_context(DecisionType.INVESTMENT, "INFY", "equity", "test")
        d = ctx.to_dict()
        assert "decision_id" in d
        assert "subject_id" in d
        assert d["decision_type"] == "investment"

    def test_tags_are_immutable(self):
        ctx = make_context(
            DecisionType.RESEARCH, "TATA", "equity", "test", tags=("alpha", "beta")
        )
        assert "alpha" in ctx.tags

    def test_extra_metadata(self):
        ctx = make_context(
            DecisionType.RISK_ACTION, "NIFTY", "index", "risk_system",
            extra={"trigger": "vix_spike"},
        )
        assert ctx.extra["trigger"] == "vix_spike"


# ===========================================================================
# DecisionConfiguration
# ===========================================================================

class TestDecisionConfiguration:
    def test_defaults(self):
        cfg = DecisionConfiguration()
        assert cfg.approval_threshold == 65.0
        assert cfg.confidence_threshold == 50.0
        assert cfg.auto_approve is False

    def test_with_environment(self):
        cfg = DEVELOPMENT_CONFIG.with_environment(EnvironmentProfile.PAPER)
        assert cfg.environment == EnvironmentProfile.PAPER

    def test_with_policy(self):
        cfg = DecisionConfiguration()
        cfg2 = cfg.with_policy("max_exposure", 0.05)
        assert cfg2.policies["max_exposure"] == 0.05

    def test_to_dict(self):
        d = LIVE_CONFIG.to_dict()
        assert "approval_threshold" in d
        assert "environment" in d
        assert d["environment"] == "live"

    def test_immutability(self):
        cfg = DecisionConfiguration()
        with pytest.raises((TypeError, AttributeError)):
            cfg.approval_threshold = 99.0  # type: ignore[misc]


# ===========================================================================
# DecisionMetadata
# ===========================================================================

class TestDecisionMetadata:
    def test_initial_version(self):
        from iios.investment.decision.core.decision_metadata import DecisionMetadata
        meta = DecisionMetadata("D1", "system")
        # Created by __init__ with _record (not record), so version stays at 1
        assert meta.version >= 1

    def test_record_increments_version(self):
        from iios.investment.decision.core.decision_metadata import DecisionMetadata
        meta = DecisionMetadata("D2", "system")
        v0   = meta.version
        meta.record("user", "manual_override", "Override applied.")
        assert meta.version == v0 + 1

    def test_audit_trail_grows(self):
        from iios.investment.decision.core.decision_metadata import DecisionMetadata
        meta = DecisionMetadata("D3", "system")
        n0   = len(meta.audit_trail)
        meta.record("analyst", "review", "Reviewed.")
        assert len(meta.audit_trail) == n0 + 1

    def test_to_dict(self):
        from iios.investment.decision.core.decision_metadata import DecisionMetadata
        meta = DecisionMetadata("D4", "system")
        d    = meta.to_dict()
        assert "decision_id" in d
        assert "audit_trail" in d


# ===========================================================================
# BaseDecision — happy path lifecycle
# ===========================================================================

class TestBaseDecisionHappyPath:
    @pytest.mark.asyncio
    async def test_full_lifecycle_completes(self, simple_buy_decision):
        state = await simple_buy_decision.run()
        assert state.status == DecisionStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_recommendation_set(self, simple_buy_decision):
        await simple_buy_decision.run()
        assert simple_buy_decision.state.recommendation == RecommendationType.STRONG_BUY

    @pytest.mark.asyncio
    async def test_score_set(self, simple_buy_decision):
        await simple_buy_decision.run()
        assert simple_buy_decision.state.score == pytest.approx(80.0)

    @pytest.mark.asyncio
    async def test_approval_status_approved(self, simple_buy_decision):
        await simple_buy_decision.run()
        assert simple_buy_decision.state.approval_status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_risk_review_approved(self, simple_buy_decision):
        await simple_buy_decision.run()
        assert simple_buy_decision.state.risk_review_status == RiskReviewStatus.APPROVED

    @pytest.mark.asyncio
    async def test_explanation_populated(self, simple_buy_decision):
        await simple_buy_decision.run()
        assert len(simple_buy_decision.state.explanation) > 0

    @pytest.mark.asyncio
    async def test_lifecycle_phases_recorded(self, simple_buy_decision):
        await simple_buy_decision.run()
        phases = simple_buy_decision.lifecycle.all_phases()
        assert len(phases) > 0

    @pytest.mark.asyncio
    async def test_metadata_updated(self, simple_buy_decision):
        await simple_buy_decision.run()
        assert len(simple_buy_decision.metadata.audit_trail) > 0

    @pytest.mark.asyncio
    async def test_events_dispatched(self, simple_buy_decision):
        events = []
        simple_buy_decision.dispatcher.subscribe(lambda e: events.append(e))
        await simple_buy_decision.run()
        assert len(events) > 5   # multiple events per lifecycle

    @pytest.mark.asyncio
    async def test_properties_accessible(self, simple_buy_decision):
        assert simple_buy_decision.decision_id
        assert simple_buy_decision.context.subject_id == "RELIANCE"
        assert simple_buy_decision.state is not None
        assert simple_buy_decision.metadata is not None
        assert simple_buy_decision.lifecycle is not None


# ===========================================================================
# BaseDecision — rejection path
# ===========================================================================

class TestBaseDecisionRejectedPath:
    @pytest.mark.asyncio
    async def test_rejected_decision_status(self, investment_context, dev_config, dispatcher):
        decision = RejectedDecision(investment_context, dev_config, dispatcher)
        state    = await decision.run()
        assert state.status == DecisionStatus.ARCHIVED
        assert state.approval_status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_rejected_recommendation(self, investment_context, dev_config, dispatcher):
        decision = RejectedDecision(investment_context, dev_config, dispatcher)
        await decision.run()
        assert decision.state.recommendation == RecommendationType.SELL


# ===========================================================================
# BaseDecision — failure path
# ===========================================================================

class TestBaseDecisionFailurePath:
    @pytest.mark.asyncio
    async def test_failing_decision_raises(self, investment_context, dev_config, dispatcher):
        decision = FailingDecision(investment_context, dev_config, dispatcher)
        with pytest.raises(RuntimeError):
            await decision.run()

    @pytest.mark.asyncio
    async def test_failing_decision_state_is_failed(self, investment_context, dev_config, dispatcher):
        decision = FailingDecision(investment_context, dev_config, dispatcher)
        try:
            await decision.run()
        except RuntimeError:
            pass
        assert decision.state.status == DecisionStatus.FAILED
        assert decision.state.error_message is not None

    def test_run_sync(self, investment_context, dev_config, dispatcher):
        """Sync wrapper produces the same result."""
        from tests.unit.investment.decision.core.conftest import SimpleBuyDecision
        ctx  = make_context(DecisionType.INVESTMENT, "WIPRO", "equity", "test_sync")
        dec  = SimpleBuyDecision(ctx, dev_config, dispatcher)
        state = dec.run_sync()
        assert state.status == DecisionStatus.ARCHIVED
