"""tests/unit/investment/decision/evidence/test_timeline.py"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.decision.evidence.event_timeline import EventTimeline
from iios.investment.decision.evidence.evidence_constants import EvidenceEventType
from iios.investment.decision.evidence.historical_evidence import HistoricalEvidence
from iios.investment.decision.evidence.change_tracker import ChangeTracker
from iios.investment.decision.evidence.timeline_engine import TimelineEngine
from iios.investment.decision.evidence.evidence_constants import EvidenceValidationStatus


def _snap(decision_id, subject_id, items, quality=80.0):
    from iios.investment.decision.evidence.evidence_snapshot import build_snapshot
    from iios.investment.decision.evidence.evidence_package import EvidencePackage
    pkg = EvidencePackage(str(uuid.uuid4()), decision_id, subject_id, "equity")
    pkg.add_items(items)
    pkg.seal()
    return build_snapshot(pkg, items, EvidenceValidationStatus.PASSED, quality, 1,
                          datetime.now(timezone.utc))


# =========================== EventTimeline ===============================

class TestEventTimeline:
    def test_record_and_retrieve(self, decision_id):
        tl = EventTimeline()
        ev = tl.record_simple(EvidenceEventType.COLLECTION_STARTED, decision_id,
                              details={"subject": "TCS"})
        assert tl.count() == 1
        events = tl.for_decision(decision_id)
        assert len(events) == 1
        assert events[0] is ev

    def test_by_type(self, decision_id):
        tl = EventTimeline()
        tl.record_simple(EvidenceEventType.COLLECTION_STARTED, decision_id)
        tl.record_simple(EvidenceEventType.SNAPSHOT_PUBLISHED, decision_id)
        assert len(tl.by_type(EvidenceEventType.SNAPSHOT_PUBLISHED)) == 1

    def test_recent(self, decision_id):
        tl = EventTimeline()
        for _ in range(10):
            tl.record_simple(EvidenceEventType.COLLECTION_STARTED, decision_id)
        assert len(tl.recent(5)) == 5

    def test_max_size_rolls_over(self, decision_id):
        tl = EventTimeline(max_size=5)
        for _ in range(10):
            tl.record_simple(EvidenceEventType.COLLECTION_STARTED, decision_id)
        assert tl.count() == 5

    def test_to_dict(self, decision_id):
        tl = EventTimeline()
        ev = tl.record_simple(EvidenceEventType.COLLECTION_STARTED, decision_id)
        d  = ev.to_dict()
        assert "event_type" in d and "decision_id" in d


# =========================== HistoricalEvidence ==========================

class TestHistoricalEvidence:
    def test_record_and_get_history(self, market_item):
        hist = HistoricalEvidence()
        hist.record(market_item)
        items = hist.get_history(market_item.subject_id)
        assert market_item in items

    def test_filter_by_key(self, market_item, risk_item):
        hist = HistoricalEvidence()
        hist.record(market_item)
        hist.record(risk_item)
        items = hist.get_history(market_item.subject_id, key=market_item.key)
        assert all(i.key == market_item.key for i in items)

    def test_max_per_subject(self, market_item):
        hist = HistoricalEvidence(max_per_subject=3)
        for _ in range(5):
            hist.record(market_item)
        items = hist.get_history(market_item.subject_id)
        assert len(items) <= 3

    def test_known_subjects(self, market_item, risk_item):
        hist = HistoricalEvidence()
        hist.record(market_item)
        hist.record(risk_item)
        subjects = hist.known_subjects()
        assert market_item.subject_id in subjects


# =========================== ChangeTracker ===============================

class TestChangeTracker:
    def test_no_change(self, sample_items, decision_id, subject_id):
        snap = _snap(decision_id, subject_id, sample_items)
        tracker = ChangeTracker()
        report  = tracker.compare(snap, snap)
        assert not report.has_changes

    def test_detects_value_change(self, make_item, decision_id, subject_id):
        from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
        i1 = make_item("price", 100.0, EvidenceSourceType.MARKET,
                       decision_id=decision_id, subject_id=subject_id)
        i2 = make_item("price", 120.0, EvidenceSourceType.MARKET,
                       decision_id=decision_id, subject_id=subject_id)

        snap_old = _snap(decision_id, subject_id, [i1])
        snap_new = _snap(decision_id, subject_id, [i2])

        tracker  = ChangeTracker()
        report   = tracker.compare(snap_old, snap_new)
        assert report.has_changes
        assert len(report.value_changes) == 1
        vc = report.value_changes[0]
        assert vc.key == "price"
        assert vc.pct_change == pytest.approx(20.0)

    def test_quality_delta(self, sample_items, decision_id, subject_id):
        snap1 = _snap(decision_id, subject_id, sample_items, quality=70.0)
        snap2 = _snap(decision_id, subject_id, sample_items, quality=80.0)
        report = ChangeTracker().compare(snap1, snap2)
        assert report.quality_delta == pytest.approx(10.0)


# =========================== TimelineEngine ==============================

class TestTimelineEngine:
    def test_on_collection_started(self, decision_id, subject_id):
        eng = TimelineEngine()
        eng.on_collection_started(decision_id, subject_id)
        events = eng.events_for(decision_id)
        assert len(events) == 1
        assert events[0].event_type == EvidenceEventType.COLLECTION_STARTED

    def test_on_snapshot_no_change_report_first(self, sample_items, decision_id, subject_id):
        eng  = TimelineEngine()
        snap = _snap(decision_id, subject_id, sample_items)
        cr   = eng.on_snapshot_published(snap)
        assert cr is None   # first snapshot → no prior to compare

    def test_on_snapshot_change_report_second(self, sample_items, decision_id, subject_id):
        eng   = TimelineEngine()
        snap1 = _snap(decision_id, subject_id, sample_items, quality=70.0)
        snap2 = _snap(decision_id, subject_id, sample_items, quality=80.0)
        eng.on_snapshot_published(snap1)
        cr = eng.on_snapshot_published(snap2)
        assert cr is not None

    def test_stats(self, decision_id, subject_id, market_item):
        eng = TimelineEngine()
        eng.on_collection_started(decision_id, subject_id)
        eng.on_evidence_collected(decision_id, [market_item])
        s = eng.stats()
        assert s["timeline_events"] >= 2
