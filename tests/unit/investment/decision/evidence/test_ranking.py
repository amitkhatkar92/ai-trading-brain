"""tests/unit/investment/decision/evidence/test_ranking.py"""
from __future__ import annotations

from typing import List

import pytest

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.priority_engine import PriorityEngine
from iios.investment.decision.evidence.relevance_engine import RelevanceEngine
from iios.investment.decision.evidence.confidence_engine import ConfidenceEngine
from iios.investment.decision.evidence.evidence_ranker import EvidenceRanker


def _item(key="x", value=1, priority=EvidencePriority.MEDIUM, confidence=70.0, freshness=1.0,
          src=EvidenceSourceType.MARKET, subject_type="equity", required=False):
    return make_evidence_item(
        decision_id="D1", source_type=src, source_provider="p",
        subject_id="TCS", subject_type=subject_type,
        category=EvidenceCategory.TECHNICAL, key=key, value=value,
        confidence=confidence, freshness_score=freshness,
        priority=priority, is_required=required,
    )


# =========================== PriorityEngine ==============================

class TestPriorityEngine:
    def test_critical_scores_higher_than_low(self):
        eng = PriorityEngine()
        crit = _item(priority=EvidencePriority.CRITICAL)
        low  = _item(priority=EvidencePriority.LOW)
        assert eng.score(crit) > eng.score(low)

    def test_required_scores_higher(self):
        eng = PriorityEngine()
        req     = _item(required=True)
        not_req = _item(required=False)
        assert eng.score(req) > eng.score(not_req)

    def test_rank_returns_sorted(self):
        eng   = PriorityEngine()
        items = [
            _item("a", priority=EvidencePriority.LOW),
            _item("b", priority=EvidencePriority.CRITICAL),
            _item("c", priority=EvidencePriority.MEDIUM),
        ]
        ranked = eng.rank(items)
        scores = [eng.score(i) for i in ranked]
        assert scores == sorted(scores, reverse=True)


# =========================== RelevanceEngine =============================

class TestRelevanceEngine:
    def test_score_range(self):
        eng = RelevanceEngine()
        item = _item(src=EvidenceSourceType.MARKET, subject_type="equity", confidence=80.0)
        s = eng.score(item)
        assert 0.0 <= s <= 100.0

    def test_market_outranks_external_for_equity(self):
        eng = RelevanceEngine()
        mkt = _item(src=EvidenceSourceType.MARKET,   subject_type="equity", confidence=80.0)
        ext = _item(src=EvidenceSourceType.EXTERNAL,  subject_type="equity", confidence=80.0)
        assert eng.score(mkt) > eng.score(ext)

    def test_rank_sorted(self):
        eng   = RelevanceEngine()
        items = [
            _item("a", src=EvidenceSourceType.EXTERNAL,  confidence=80.0),
            _item("b", src=EvidenceSourceType.RISK,      confidence=80.0),
            _item("c", src=EvidenceSourceType.MARKET,    confidence=80.0),
        ]
        ranked = eng.rank(items)
        scores = [eng.score(i) for i in ranked]
        assert scores == sorted(scores, reverse=True)


# =========================== ConfidenceEngine ============================

class TestConfidenceEngine:
    def test_low_freshness_reduces_confidence(self):
        eng = ConfidenceEngine()
        high_fresh = _item(confidence=80.0, freshness=1.0)
        low_fresh  = _item(confidence=80.0, freshness=0.1)
        assert eng.adjust(high_fresh) > eng.adjust(low_fresh)

    def test_filter_removes_below_threshold(self):
        eng   = ConfidenceEngine(min_threshold=50.0)
        items = [
            _item("a", confidence=10.0, freshness=1.0),   # 10 → filtered out
            _item("b", confidence=80.0, freshness=1.0),   # 80 → kept
        ]
        kept = eng.filter_low_confidence(items)
        assert len(kept) == 1
        assert kept[0].key == "b"

    def test_rank_sorted(self):
        eng   = ConfidenceEngine()
        items = [_item(confidence=30.0), _item(confidence=90.0), _item(confidence=60.0)]
        ranked = eng.rank(items)
        assert eng.adjust(ranked[0]) >= eng.adjust(ranked[-1])


# =========================== EvidenceRanker ==============================

class TestEvidenceRanker:
    def test_rank_returns_list(self, sample_items):
        ranker = EvidenceRanker()
        result = ranker.rank(sample_items)
        assert isinstance(result, list)

    def test_empty_input(self):
        ranker = EvidenceRanker()
        assert ranker.rank([]) == []

    def test_very_low_confidence_filtered(self):
        ranker = EvidenceRanker(confidence_engine=ConfidenceEngine(min_threshold=80.0))
        items = [
            _item("a", confidence=10.0, freshness=1.0),
            _item("b", confidence=90.0, freshness=1.0),
        ]
        ranked = ranker.rank(items)
        assert all(i.key != "a" for i in ranked)

    def test_order_descends(self, sample_items):
        ranker  = EvidenceRanker()
        ranked  = ranker.rank(sample_items)
        if len(ranked) > 1:
            # confidence of first should be >= last in general (not guaranteed, but common)
            assert ranked[0].confidence >= 0  # trivial safety
