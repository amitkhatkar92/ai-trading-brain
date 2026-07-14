"""tests/unit/investment/decision/evidence/test_evidence_models.py"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType, EvidenceStatus,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item
from iios.investment.decision.evidence.evidence_package import EvidencePackage
from iios.investment.decision.evidence.evidence_statistics import EvidenceStatisticsTracker
from iios.investment.decision.evidence.evidence_history import EvidenceHistory


# ============================= EvidenceItem ==============================

class TestEvidenceItem:
    def test_make_item_defaults(self, market_item):
        i = market_item
        assert i.confidence >= 0
        assert 0.0 <= i.freshness_score <= 1.0
        assert i.evidence_id
        assert i.trace_id

    def test_item_is_immutable(self, market_item):
        with pytest.raises(Exception):
            market_item.key = "mutated"  # type: ignore

    def test_confidence_clamped(self, decision_id, subject_id, subject_type):
        item = make_evidence_item(
            decision_id=decision_id, source_type=EvidenceSourceType.MARKET,
            source_provider="p", subject_id=subject_id, subject_type=subject_type,
            category=EvidenceCategory.TECHNICAL, key="x", value=1,
            confidence=150.0, freshness_score=2.0,
        )
        assert item.confidence == 100.0
        assert item.freshness_score == 1.0

    def test_to_dict_has_all_keys(self, market_item):
        d = market_item.to_dict()
        for k in ("evidence_id", "decision_id", "source_type", "key", "value",
                  "confidence", "freshness_score", "priority", "trace_id"):
            assert k in d

    def test_age_seconds_non_negative(self, market_item):
        assert market_item.age_seconds >= 0

    def test_is_fresh_true_for_new_item(self, market_item):
        assert market_item.is_fresh is True

    def test_is_stale_false_for_new_item(self, market_item):
        assert market_item.is_stale is False


# ============================= EvidencePackage ===========================

class TestEvidencePackage:
    def _pkg(self, decision_id):
        return EvidencePackage(str(uuid.uuid4()), decision_id, "TCS", "equity")

    def test_add_item(self, market_item, decision_id):
        pkg = self._pkg(decision_id)
        pkg.add_item(market_item)
        assert pkg.item_count == 1

    def test_add_items(self, sample_items, decision_id):
        pkg = self._pkg(decision_id)
        pkg.add_items(sample_items)
        assert pkg.item_count == len(sample_items)

    def test_seal_prevents_more_adds(self, market_item, decision_id):
        pkg = self._pkg(decision_id)
        pkg.seal()
        with pytest.raises(RuntimeError):
            pkg.add_item(market_item)

    def test_seal_sets_status_complete(self, market_item, decision_id):
        pkg = self._pkg(decision_id)
        pkg.add_item(market_item)
        pkg.seal()
        assert pkg.status == EvidenceStatus.COMPLETE

    def test_seal_empty_is_partial(self, decision_id):
        pkg = self._pkg(decision_id)
        pkg.seal()
        assert pkg.status == EvidenceStatus.PARTIAL

    def test_by_source(self, sample_items, decision_id):
        pkg = self._pkg(decision_id)
        pkg.add_items(sample_items)
        mkt = pkg.by_source(EvidenceSourceType.MARKET)
        assert all(i.source_type == EvidenceSourceType.MARKET for i in mkt)

    def test_avg_confidence(self, sample_items, decision_id):
        pkg = self._pkg(decision_id)
        pkg.add_items(sample_items)
        assert 0.0 < pkg.avg_confidence() <= 100.0

    def test_to_dict(self, sample_items, decision_id):
        pkg = self._pkg(decision_id)
        pkg.add_items(sample_items)
        d = pkg.to_dict()
        assert d["item_count"] == len(sample_items)


# ============================= EvidenceHistory ===========================

class TestEvidenceHistory:
    def test_record_and_retrieve(self, sample_items, decision_id, subject_id, subject_type):
        from iios.investment.decision.evidence.evidence_snapshot import build_snapshot
        from iios.investment.decision.evidence.evidence_package import EvidencePackage
        from iios.investment.decision.evidence.evidence_constants import EvidenceValidationStatus

        pkg = EvidencePackage(str(uuid.uuid4()), decision_id, subject_id, subject_type)
        pkg.add_items(sample_items)
        pkg.seal()
        snap = build_snapshot(pkg, sample_items, EvidenceValidationStatus.PASSED, 82.5, 1,
                              datetime.now(timezone.utc))

        hist = EvidenceHistory()
        hist.record(snap)
        assert hist.count() == 1
        assert hist.get(snap.snapshot_id) is snap

    def test_for_subject(self, sample_items, decision_id, subject_id, subject_type):
        from iios.investment.decision.evidence.evidence_snapshot import build_snapshot
        from iios.investment.decision.evidence.evidence_package import EvidencePackage
        from iios.investment.decision.evidence.evidence_constants import EvidenceValidationStatus

        hist = EvidenceHistory()
        for _ in range(3):
            pkg = EvidencePackage(str(uuid.uuid4()), str(uuid.uuid4()), subject_id, subject_type)
            pkg.add_items(sample_items)
            pkg.seal()
            snap = build_snapshot(pkg, sample_items, EvidenceValidationStatus.PASSED, 80.0, 1,
                                  datetime.now(timezone.utc))
            hist.record(snap)

        assert len(hist.for_subject(subject_id)) == 3


# ============================= EvidenceStatisticsTracker =================

class TestEvidenceStatisticsTracker:
    def test_empty_tracker(self):
        tracker = EvidenceStatisticsTracker()
        s = tracker.summary()
        assert s.total_snapshots == 0

    def test_records_correctly(self, sample_items, decision_id, subject_id, subject_type):
        from iios.investment.decision.evidence.evidence_snapshot import build_snapshot
        from iios.investment.decision.evidence.evidence_package import EvidencePackage
        from iios.investment.decision.evidence.evidence_constants import EvidenceValidationStatus

        pkg = EvidencePackage(str(uuid.uuid4()), decision_id, subject_id, subject_type)
        pkg.add_items(sample_items)
        pkg.seal()
        snap = build_snapshot(pkg, sample_items, EvidenceValidationStatus.PASSED, 85.0, 1,
                              datetime.now(timezone.utc))

        tracker = EvidenceStatisticsTracker()
        tracker.record(snap)
        s = tracker.summary()
        assert s.total_snapshots == 1
        assert s.avg_quality == 85.0
