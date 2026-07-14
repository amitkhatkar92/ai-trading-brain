"""tests/unit/investment/strategy/debate/test_evidence.py"""
import pytest
from datetime import datetime, timezone, timedelta

from iios.investment.strategy.debate.debate_constants import (
    EvidenceSource, EvidenceReliability, EvidenceWeight,
)
from iios.investment.strategy.debate.evidence_registry import (
    Evidence, EvidenceRegistry, make_evidence,
)
from iios.investment.strategy.debate.evidence_score import (
    EvidenceScore, compute_evidence_score, _recency_score,
)
from iios.investment.strategy.debate.evidence_validator import (
    EvidenceValidator, ValidationResult,
)
from iios.investment.strategy.debate.evidence_collector import (
    EvidenceCollector,
)


class TestEvidenceScore:
    def test_compute_basic(self, session_id):
        score = compute_evidence_score(
            evidence_id="ev-001",
            raw_score=70.0,
            reliability=EvidenceReliability.HIGH,
            weight=EvidenceWeight.MEDIUM,
            relevance=0.8,
        )
        assert 0 <= score.weighted_score <= 100
        assert score.reliability == EvidenceReliability.HIGH.score

    def test_critical_weight_amplifies(self, session_id):
        s_crit = compute_evidence_score("e", 60.0, EvidenceReliability.HIGH,
                                        EvidenceWeight.CRITICAL, relevance=0.8)
        s_med  = compute_evidence_score("e", 60.0, EvidenceReliability.HIGH,
                                        EvidenceWeight.MEDIUM, relevance=0.8)
        assert s_crit.weighted_score > s_med.weighted_score

    def test_score_capped_at_100(self):
        score = compute_evidence_score(
            "e", 100.0, EvidenceReliability.VERIFIED,
            EvidenceWeight.CRITICAL, relevance=1.0,
        )
        assert score.weighted_score <= 100.0

    def test_recency_none_returns_neutral(self):
        r = _recency_score(None)
        assert r == 0.5

    def test_recency_fresh_is_1(self):
        r = _recency_score(datetime.now(timezone.utc))
        assert r > 0.9

    def test_recency_old_is_low(self):
        old = datetime.now(timezone.utc) - timedelta(hours=48)
        r   = _recency_score(old, decay_hours=24.0)
        assert r == 0.1

    def test_score_to_dict(self):
        score = compute_evidence_score("ev-1", 60.0, EvidenceReliability.MEDIUM,
                                       EvidenceWeight.LOW, relevance=0.5)
        d = score.to_dict()
        assert "evidence_id" in d
        assert "weighted_score" in d


class TestEvidenceRegistry:
    def test_add_and_count(self, session_id):
        reg = EvidenceRegistry(session_id)
        ev  = make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "tech",
                            "RSI", "RSI description", 70.0)
        reg.add(ev)
        assert reg.count() == 1

    def test_get(self, session_id):
        reg = EvidenceRegistry(session_id)
        ev  = make_evidence(session_id, EvidenceSource.MARKET_INTELLIGENCE, "market",
                            "Regime", "Bullish regime", 72.0)
        reg.add(ev)
        found = reg.get(ev.evidence_id)
        assert found is ev

    def test_by_source(self, evidence_registry):
        items = evidence_registry.by_source(EvidenceSource.TECHNICAL_ANALYSIS)
        assert len(items) >= 1

    def test_bullish(self, session_id):
        reg = EvidenceRegistry(session_id)
        reg.add(make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "t",
                              "Bullish", "Bull", 70.0))
        reg.add(make_evidence(session_id, EvidenceSource.RISK_INTELLIGENCE, "r",
                              "Bearish", "Bear", 30.0))
        assert len(reg.bullish()) == 1
        assert len(reg.bearish()) == 1

    def test_average_weighted_score(self, evidence_registry):
        avg = evidence_registry.average_weighted_score()
        assert 0 <= avg <= 100

    def test_add_all(self, session_id):
        reg   = EvidenceRegistry(session_id)
        items = [
            make_evidence(session_id, EvidenceSource.MARKET_INTELLIGENCE, "m", "A", "desc", 60.0),
            make_evidence(session_id, EvidenceSource.RISK_INTELLIGENCE, "r", "B", "desc", 40.0),
        ]
        reg.add_all(items)
        assert reg.count() == 2


class TestMakeEvidence:
    def test_auto_scores(self, session_id):
        ev = make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "tech",
                           "Signal", "Strong buy signal", 75.0)
        assert ev.score is not None
        assert ev.score.weighted_score > 0

    def test_raw_score_clamped(self, session_id):
        ev = make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "tech",
                           "X", "desc", 120.0)
        assert ev.raw_score == 100.0

    def test_to_dict(self, session_id):
        ev = make_evidence(session_id, EvidenceSource.MACRO_ANALYSIS, "macro",
                           "GDP", "GDP growth positive", 65.0)
        d = ev.to_dict()
        assert "evidence_id" in d
        assert "source" in d
        assert d["source"] == "macro_analysis"


class TestEvidenceValidator:
    def test_valid_evidence(self, session_id):
        ev  = make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "tech",
                            "RSI", "RSI signal", 70.0)
        val = EvidenceValidator()
        r   = val.validate(ev)
        assert r.is_valid

    def test_empty_title_invalid(self, session_id):
        ev  = make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "tech",
                            "", "Description", 70.0)
        val = EvidenceValidator()
        r   = val.validate(ev)
        assert not r.is_valid
        assert any("title" in i for i in r.issues)

    def test_validate_all_partitions(self, session_id):
        ev_valid  = make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "t",
                                   "Title", "desc", 70.0)
        ev_invalid = make_evidence(session_id, EvidenceSource.RISK_INTELLIGENCE, "r",
                                    "", "desc", 50.0)
        val        = EvidenceValidator()
        valid, rejected = val.validate_all([ev_valid, ev_invalid])
        assert len(valid) == 1
        assert len(rejected) == 1


class TestEvidenceCollector:
    def test_collect_from_context_preloaded(self, debate_context, session_id):
        from iios.investment.strategy.debate.evidence_registry import EvidenceRegistry
        debate_context.pre_loaded_evidence.append({
            "source":      "technical_analysis",
            "category":    "tech",
            "title":       "Pre-loaded",
            "description": "Pre-loaded evidence",
            "raw_score":   70.0,
            "reliability": "high",
            "weight":      "medium",
            "relevance":   0.8,
        })
        reg = EvidenceRegistry(session_id)
        col = EvidenceCollector()
        result = col.collect(debate_context, reg)
        assert result.collected >= 1

    def test_collect_no_adapters(self, debate_context, session_id):
        from iios.investment.strategy.debate.evidence_registry import EvidenceRegistry
        reg = EvidenceRegistry(session_id)
        col = EvidenceCollector()
        result = col.collect(debate_context, reg)
        # Should complete without error even with no adapters
        assert result.collected >= 0
        assert isinstance(result.errors, list)

    def test_collect_with_market_adapter(self, debate_context, session_id):
        from iios.investment.strategy.debate.evidence_registry import EvidenceRegistry

        class MockMarket:
            def get_market_summary(self, symbol):
                return {"regime": "bullish", "vix": 15.0}

        reg = EvidenceRegistry(session_id)
        col = EvidenceCollector(market_intelligence=MockMarket())
        result = col.collect(debate_context, reg)
        assert result.collected >= 2  # regime + vix evidence
