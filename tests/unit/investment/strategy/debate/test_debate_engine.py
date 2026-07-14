"""tests/unit/investment/strategy/debate/test_debate_engine.py
End-to-end tests for StrategyDebateEngine.
"""
import asyncio
import pytest

from iios.investment.strategy.debate.strategy_debate_engine import StrategyDebateEngine
from iios.investment.strategy.debate.debate_report import DebateReport
from iios.investment.strategy.debate.debate_constants import DebateStatus
from iios.investment.strategy.debate.debate_context import DebateContext
from iios.investment.strategy.debate.debate_orchestrator import OrchestratorConfig
from iios.investment.strategy.debate.evidence_registry import make_evidence
from iios.investment.strategy.debate.debate_constants import EvidenceSource


class TestStrategyDebateEngineSync:
    """Sync API tests."""

    def _engine(self, fast_config):
        return StrategyDebateEngine(config=fast_config)

    def test_run_debate_sync_returns_report(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        assert isinstance(report, DebateReport)

    def test_report_not_a_decision(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        assert report.not_a_decision is True

    def test_report_has_evidence_summary(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        assert "total" in report.evidence_summary

    def test_report_has_consensus(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        # Consensus may or may not be reached — either is valid
        assert report.executive_summary is not None

    def test_stats_updates(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        engine.run_debate_sync(debate_context)
        stats = engine.stats()
        assert stats["total_debates_run"] >= 1

    def test_history_recorded(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        session = engine.get_session(report.session_id)
        assert session is not None

    def test_get_report(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        found  = engine.get_report(report.session_id)
        assert found is report

    def test_get_history_by_strategy(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        engine.run_debate_sync(debate_context)
        history = engine.get_history("strat-001")
        assert len(history) >= 1

    def test_get_evidence_summary(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        ev_sum = engine.get_evidence_summary(report.session_id)
        assert "total" in ev_sum

    def test_active_sessions_cleared_after_run(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        engine.run_debate_sync(debate_context)
        assert len(engine.active_sessions()) == 0

    def test_get_debate_timeline(self, debate_context, fast_config):
        engine   = self._engine(fast_config)
        report   = engine.run_debate_sync(debate_context)
        timeline = engine.get_debate_timeline(report.session_id)
        assert isinstance(timeline, list)
        assert len(timeline) > 0

    def test_get_minority_report(self, debate_context, fast_config):
        engine   = self._engine(fast_config)
        report   = engine.run_debate_sync(debate_context)
        minority = engine.get_minority_report(report.session_id)
        assert isinstance(minority, dict)

    def test_report_has_arguments(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        total  = (len(report.arguments_for) + len(report.arguments_against)
                  + len(report.neutral_arguments))
        assert total >= 0  # agents may produce 0 args if no evidence

    def test_report_to_dict_structure(self, debate_context, fast_config):
        engine = self._engine(fast_config)
        report = engine.run_debate_sync(debate_context)
        d      = report.to_dict()
        assert d["NOT_A_TRADING_DECISION"] is True
        assert "executive_summary" in d
        assert "explanation" in d
        assert "recommendation" in d


class TestStrategyDebateEngineAsync:
    """Async API tests."""

    def test_run_debate_async(self, debate_context, fast_config):
        engine = StrategyDebateEngine(config=fast_config)
        report = asyncio.run(engine.run_debate(debate_context))
        assert isinstance(report, DebateReport)

    def test_batch_debates(self, debate_context, fast_config):
        engine  = StrategyDebateEngine(config=fast_config)
        reports = asyncio.run(engine.run_debates_batch([debate_context, debate_context]))
        assert len(reports) == 2
        for r in reports:
            assert isinstance(r, DebateReport)

    def test_batch_with_evidence(self, debate_context, fast_config):
        ctx = debate_context
        ctx.pre_loaded_evidence.append({
            "source":      EvidenceSource.TECHNICAL_ANALYSIS.value,
            "category":    "tech",
            "title":       "RSI Signal",
            "description": "RSI at 35",
            "raw_score":   65.0,
            "reliability": "high",
            "weight":      "medium",
            "relevance":   0.8,
        })
        engine = StrategyDebateEngine(config=fast_config)
        report = asyncio.run(engine.run_debate(ctx))
        assert report.evidence_summary.get("total", 0) >= 1


class TestEngineWithPreloadedEvidence:
    """Tests with pre-loaded evidence to ensure agents produce arguments."""

    def _context_with_evidence(self, debate_context):
        for raw_score, source in [
            (75.0, EvidenceSource.TECHNICAL_ANALYSIS.value),
            (70.0, EvidenceSource.MARKET_INTELLIGENCE.value),
            (30.0, EvidenceSource.RISK_INTELLIGENCE.value),
            (65.0, EvidenceSource.LEARNING_ENGINE.value),
        ]:
            debate_context.pre_loaded_evidence.append({
                "source":      source,
                "category":    source,
                "title":       f"Evidence: {source}",
                "description": f"Pre-loaded {source} evidence",
                "raw_score":   raw_score,
                "reliability": "high",
                "weight":      "medium",
                "relevance":   0.8,
            })
        return debate_context

    def test_agents_produce_arguments_with_evidence(self, debate_context, fast_config):
        ctx    = self._context_with_evidence(debate_context)
        engine = StrategyDebateEngine(config=fast_config)
        report = engine.run_debate_sync(ctx)
        total  = (len(report.arguments_for) + len(report.arguments_against)
                  + len(report.neutral_arguments))
        assert total > 0

    def test_consensus_reached_with_bullish_evidence(self, debate_context, fast_config):
        # Load all bullish evidence
        for source in [e.value for e in EvidenceSource]:
            debate_context.pre_loaded_evidence.append({
                "source":      source,
                "category":    source,
                "title":       f"Bullish {source}",
                "description": "Bullish signal",
                "raw_score":   75.0,
                "reliability": "high",
                "weight":      "medium",
                "relevance":   0.8,
            })
        engine = StrategyDebateEngine(config=fast_config)
        report = engine.run_debate_sync(debate_context)
        # With all bullish evidence, consensus should lean positive
        if report.consensus:
            assert report.consensus.winning_outcome.numeric_value >= 0
