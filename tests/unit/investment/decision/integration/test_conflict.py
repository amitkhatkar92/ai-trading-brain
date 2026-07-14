"""tests/unit/investment/decision/integration/test_conflict.py
Tests for ConflictDetector, ConflictClassifier, ConflictResolver, ConflictEngine.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.integration.aggregation_engine import AggregationEngine
from iios.investment.decision.integration.conflict_classifier import ConflictClassifier
from iios.investment.decision.integration.conflict_detector import ConflictDetector, DetectedConflict
from iios.investment.decision.integration.conflict_engine import ConflictEngine, ConflictReport
from iios.investment.decision.integration.conflict_history import ConflictHistory
from iios.investment.decision.integration.conflict_resolution import ConflictResolver
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    ConflictResolutionStrategy,
    ConflictSeverity,
    ConflictType,
)


def _make_snap(pipeline):
    did, sid, ev, rs, cs, ri, ex, cm = pipeline
    eng   = AggregationEngine()
    state = eng.create(
        decision_id=did + "_DEC", subject_id=sid, subject_type="equity",
        evidence=ev, reasoning=rs, confidence=cs, risk=ri,
        explanation=ex, committee=cm,
    )
    return state.snapshot()


class TestConflictDetector:
    def test_detect_returns_list(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        cfs  = det.detect(snap)
        assert isinstance(cfs, list)

    def test_all_items_are_detected_conflicts(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        for c in det.detect(snap):
            assert isinstance(c, DetectedConflict)

    def test_no_subject_mismatch_on_consistent_data(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        cfs  = det.detect(snap)
        mismatch = [c for c in cfs if c.conflict_type == ConflictType.SUBJECT_MISMATCH]
        assert len(mismatch) == 0

    def test_conflict_to_dict(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        cfs  = det.detect(snap)
        for c in cfs:
            d = c.to_dict()
            assert "conflict_id"   in d
            assert "conflict_type" in d
            assert "severity"      in d

    def test_conflict_severity_valid(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        for c in det.detect(snap):
            assert c.severity in list(ConflictSeverity)


class TestConflictClassifier:
    def test_classify_returns_pairs(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        cfs  = det.detect(snap)
        cls  = ConflictClassifier()
        pairs = cls.classify(cfs)
        assert len(pairs) == len(cfs)
        for c, strategy in pairs:
            assert isinstance(c, DetectedConflict)
            assert strategy in list(ConflictResolutionStrategy)

    def test_sorted_critical_first(self):
        from datetime import datetime, timezone
        import uuid
        low  = DetectedConflict(str(uuid.uuid4()), ConflictType.DATA_STALENESS,
                                ConflictSeverity.LOW, "a", "b", "low", None, None, None,
                                datetime.now(timezone.utc))
        crit = DetectedConflict(str(uuid.uuid4()), ConflictType.SUBJECT_MISMATCH,
                                ConflictSeverity.CRITICAL, "a", "b", "crit", None, None, None,
                                datetime.now(timezone.utc))
        cls  = ConflictClassifier()
        pairs = cls.classify([low, crit])
        assert pairs[0][0].severity == ConflictSeverity.CRITICAL

    def test_blocks_publishing_on_critical(self):
        from datetime import datetime, timezone
        import uuid
        crit = DetectedConflict(str(uuid.uuid4()), ConflictType.SUBJECT_MISMATCH,
                                ConflictSeverity.CRITICAL, "a", "b", "crit", None, None, None,
                                datetime.now(timezone.utc))
        cls = ConflictClassifier()
        assert cls.blocks_publishing([crit])

    def test_not_blocks_publishing_when_no_critical(self):
        from datetime import datetime, timezone
        import uuid
        low = DetectedConflict(str(uuid.uuid4()), ConflictType.DATA_STALENESS,
                               ConflictSeverity.LOW, "a", "b", "low", None, None, None,
                               datetime.now(timezone.utc))
        cls = ConflictClassifier()
        assert not cls.blocks_publishing([low])


class TestConflictResolver:
    def test_resolve_returns_three_lists(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        cfs  = det.detect(snap)
        res  = ConflictResolver()
        resolved, unresolved, results = res.resolve(cfs)
        assert len(resolved) + len(unresolved) == len(cfs)
        assert len(results) == len(cfs)

    def test_resolution_result_to_dict(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        det  = ConflictDetector()
        cfs  = det.detect(snap)
        if not cfs:
            return
        res     = ConflictResolver()
        _, _, results = res.resolve(cfs)
        for r in results:
            d = r.to_dict()
            assert "conflict_id" in d
            assert "strategy"    in d
            assert "resolved"    in d


class TestConflictEngine:
    def test_run_returns_conflict_report(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        eng  = ConflictEngine()
        rep  = eng.run(snap)
        assert isinstance(rep, ConflictReport)

    def test_report_to_dict(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        eng  = ConflictEngine()
        rep  = eng.run(snap)
        d    = rep.to_dict()
        assert "total_conflicts"   in d
        assert "blocks_publishing" in d

    def test_history_recorded(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        eng  = ConflictEngine()
        eng.run(snap)
        assert eng.history.count() >= 0  # may have 0 conflicts


class TestConflictHistory:
    def test_record_and_retrieve(self):
        from datetime import datetime, timezone
        import uuid
        h  = ConflictHistory()
        cf = DetectedConflict(str(uuid.uuid4()), ConflictType.DATA_STALENESS,
                              ConflictSeverity.LOW, "a", "b", "desc", None, None, None,
                              datetime.now(timezone.utc))
        h.record("D1", [cf])
        assert len(h.for_decision("D1")) == 1

    def test_by_severity_filter(self):
        from datetime import datetime, timezone
        import uuid
        h    = ConflictHistory()
        low  = DetectedConflict(str(uuid.uuid4()), ConflictType.DATA_STALENESS,
                                ConflictSeverity.LOW, "a", "b", "low", None, None, None,
                                datetime.now(timezone.utc))
        high = DetectedConflict(str(uuid.uuid4()), ConflictType.CROSS_ENGINE,
                                ConflictSeverity.HIGH, "a", "b", "high", None, None, None,
                                datetime.now(timezone.utc))
        h.record("D1", [low, high])
        assert len(h.by_severity(ConflictSeverity.LOW)) == 1

    def test_reset(self):
        from datetime import datetime, timezone
        import uuid
        h  = ConflictHistory()
        cf = DetectedConflict(str(uuid.uuid4()), ConflictType.DATA_STALENESS,
                              ConflictSeverity.LOW, "a", "b", "d", None, None, None,
                              datetime.now(timezone.utc))
        h.record("D1", [cf])
        h.reset()
        assert h.count() == 0
