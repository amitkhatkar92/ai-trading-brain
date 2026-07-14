"""tests/unit/investment/decision/evidence/test_validation.py"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType, EvidenceValidationStatus,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item
from iios.investment.decision.evidence.freshness_validator import FreshnessValidator
from iios.investment.decision.evidence.consistency_checker import ConsistencyChecker
from iios.investment.decision.evidence.coverage_validator import CoverageValidator
from iios.investment.decision.evidence.evidence_validator import EvidenceValidator


def _ev_item(key="price", value=100.0, src=EvidenceSourceType.MARKET,
             confidence=80.0, freshness=1.0, decision_id="D1", subject_id="X"):
    return make_evidence_item(
        decision_id=decision_id, source_type=src,
        source_provider="p", subject_id=subject_id, subject_type="equity",
        category=EvidenceCategory.TECHNICAL, key=key, value=value,
        confidence=confidence, freshness_score=freshness,
    )


# ========================== FreshnessValidator ===========================

class TestFreshnessValidator:
    def test_fresh_item_stays_fresh(self):
        v = FreshnessValidator()
        item = _ev_item(freshness=1.0)
        refreshed, report = v.validate([item])
        assert report.avg_freshness > 0.9

    def test_old_item_decays(self):
        v = FreshnessValidator(warn_seconds=1, stale_seconds=2)
        old_ts = datetime.now(timezone.utc) - timedelta(seconds=10)
        item = make_evidence_item(
            decision_id="D1", source_type=EvidenceSourceType.MARKET,
            source_provider="p", subject_id="X", subject_type="equity",
            category=EvidenceCategory.TECHNICAL, key="old",
            value=1, timestamp=old_ts,
        )
        refreshed, report = v.validate([item])
        assert refreshed[0].freshness_score == 0.0
        assert report.stale == 1

    def test_fresh_item_is_acceptable(self):
        v = FreshnessValidator()
        _, report = v.validate([_ev_item(freshness=1.0)])
        assert report.is_acceptable is True

    def test_empty_items(self):
        v = FreshnessValidator()
        refreshed, report = v.validate([])
        assert report.total == 0
        assert report.avg_freshness == 0.0


# ========================== ConsistencyChecker ===========================

class TestConsistencyChecker:
    def test_no_conflicts_same_key_same_value(self):
        checker = ConsistencyChecker(tolerance_pct=5.0)
        items = [_ev_item("pe", 22.0), _ev_item("pe", 22.5)]
        report = checker.check(items)
        assert report.conflict_count == 0

    def test_conflict_detected(self):
        checker = ConsistencyChecker(tolerance_pct=5.0)
        items = [_ev_item("pe", 10.0), _ev_item("pe", 50.0)]
        report = checker.check(items)
        assert report.conflict_count > 0
        assert report.consistency_score < 100.0

    def test_non_numeric_values_skipped(self):
        checker = ConsistencyChecker()
        items = [_ev_item("sector", "IT"), _ev_item("sector", "FMCG")]
        report = checker.check(items)
        assert report.conflict_count == 0

    def test_empty_is_acceptable(self):
        report = ConsistencyChecker().check([])
        assert report.is_acceptable is True


# ========================== CoverageValidator ============================

class TestCoverageValidator:
    def test_missing_required_gives_insufficient(self):
        v = CoverageValidator()
        items = [_ev_item(src=EvidenceSourceType.COMPANY)]   # MARKET and RISK missing
        report = v.validate(items)
        assert report.validation_status == EvidenceValidationStatus.INSUFFICIENT

    def test_required_present_passes(self):
        v = CoverageValidator()
        items = [
            _ev_item(src=EvidenceSourceType.MARKET),
            _ev_item(src=EvidenceSourceType.RISK),
        ]
        report = v.validate(items)
        assert report.validation_status != EvidenceValidationStatus.INSUFFICIENT

    def test_coverage_fraction_range(self):
        v = CoverageValidator()
        items = [_ev_item(src=EvidenceSourceType.MARKET), _ev_item(src=EvidenceSourceType.RISK)]
        report = v.validate(items)
        assert 0.0 <= report.coverage_fraction <= 1.0


# ========================== EvidenceValidator (orchestrator) =============

class TestEvidenceValidator:
    def _all_items(self, decision_id="D1"):
        return [
            _ev_item("price",  100.0, EvidenceSourceType.MARKET,   decision_id=decision_id),
            _ev_item("risk",    45.0, EvidenceSourceType.RISK,      decision_id=decision_id),
            _ev_item("pe",      22.0, EvidenceSourceType.COMPANY,   decision_id=decision_id),
            _ev_item("signal",  70.0, EvidenceSourceType.STRATEGY,  decision_id=decision_id),
            _ev_item("news",    60.0, EvidenceSourceType.KNOWLEDGE, decision_id=decision_id),
            _ev_item("target", 120.0, EvidenceSourceType.RESEARCH,  decision_id=decision_id),
        ]

    def test_valid_items_pass(self, decision_id):
        v = EvidenceValidator()
        result = v.validate(self._all_items(decision_id))
        assert result.overall.allows_publishing

    def test_to_dict_structure(self, decision_id):
        v = EvidenceValidator()
        result = v.validate(self._all_items(decision_id))
        d = result.to_dict()
        assert "overall" in d
        assert "freshness" in d
        assert "consistency" in d
        assert "coverage" in d

    def test_refreshed_items_returned(self, decision_id):
        v = EvidenceValidator()
        items = self._all_items(decision_id)
        result = v.validate(items)
        assert len(result.refreshed_items) == len(items)

    def test_insufficient_when_no_required(self):
        v = EvidenceValidator()
        items = [_ev_item(src=EvidenceSourceType.KNOWLEDGE)]
        result = v.validate(items)
        assert result.overall == EvidenceValidationStatus.INSUFFICIENT
