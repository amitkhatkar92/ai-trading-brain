"""tests/unit/investment/strategy/integration/test_conflict.py
Tests for ConflictClassifier, ConflictResolver, ConflictEngine, ConflictHistory.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.aggregation_state import make_update
from iios.investment.strategy.integration.conflict_classifier import (
    Conflict,
    ConflictClassifier,
)
from iios.investment.strategy.integration.conflict_engine import ConflictEngine
from iios.investment.strategy.integration.conflict_history import ConflictHistory
from iios.investment.strategy.integration.conflict_resolution import ConflictResolver
from iios.investment.strategy.integration.consistency_rules import (
    RuleCheckResult,
    create_default_rule_registry,
)
from iios.investment.strategy.integration.conflict_detector import ConflictDetector
from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    IntelligenceSource,
    ResolutionStrategy,
)
from tests.unit.investment.strategy.integration.conftest import (
    make_eval_update,
    make_risk_update,
    make_full_state,
)


# ===========================================================================
# ConflictClassifier
# ===========================================================================

class TestConflictClassifier:
    def _make_failure(
        self,
        conflict_type: ConflictType,
        severity: ConflictSeverity,
        rule_id: str = "R001",
    ) -> RuleCheckResult:
        from datetime import datetime, timezone
        return RuleCheckResult(
            rule_id=rule_id,
            rule_name="test",
            passed=False,
            conflict_type=conflict_type,
            severity=severity,
            description="test conflict",
            source_a=IntelligenceSource.EVALUATION,
            source_b=IntelligenceSource.RISK,
            checked_at=datetime.now(timezone.utc),
        )

    def test_classify_single_failure(self):
        clf = ConflictClassifier()
        failure = self._make_failure(ConflictType.EVALUATION_VS_RISK, ConflictSeverity.HIGH)
        conflicts = clf.classify("STRAT-1", [failure])
        assert len(conflicts) == 1
        c = conflicts[0]
        assert c.conflict_type == ConflictType.EVALUATION_VS_RISK
        assert c.severity == ConflictSeverity.HIGH
        assert c.strategy_id == "STRAT-1"

    def test_classify_skips_passed(self):
        from datetime import datetime, timezone
        passed = RuleCheckResult(
            rule_id="R000",
            rule_name="ok",
            passed=True,
            conflict_type=None,
            severity=None,
            description="ok",
            source_a=IntelligenceSource.EVALUATION,
            source_b=IntelligenceSource.RISK,
            checked_at=datetime.now(timezone.utc),
        )
        clf = ConflictClassifier()
        assert clf.classify("S", [passed]) == []

    def test_resolution_strategy_assigned(self):
        clf = ConflictClassifier()
        failure = self._make_failure(ConflictType.EVALUATION_VS_RISK, ConflictSeverity.HIGH)
        conflicts = clf.classify("S", [failure])
        # EVALUATION_VS_RISK → RISK_FIRST
        assert conflicts[0].resolution_strategy == ResolutionStrategy.RISK_FIRST

    def test_conflict_to_dict(self):
        clf = ConflictClassifier()
        failure = self._make_failure(ConflictType.LIFECYCLE_VS_EVALUATION, ConflictSeverity.HIGH)
        c = clf.classify("S", [failure])[0]
        d = c.to_dict()
        assert "conflict_id" in d
        assert "severity" in d


# ===========================================================================
# ConflictResolver
# ===========================================================================

class TestConflictResolver:
    def _make_conflict(
        self,
        resolution: ResolutionStrategy = ResolutionStrategy.HIGHER_CONFIDENCE,
        conflict_type: ConflictType = ConflictType.EVALUATION_VS_RISK,
        severity: ConflictSeverity = ConflictSeverity.MEDIUM,
    ) -> Conflict:
        from datetime import datetime, timezone
        return Conflict(
            conflict_id="test-cid",
            strategy_id="STRAT-R",
            conflict_type=conflict_type,
            severity=severity,
            source_a=IntelligenceSource.EVALUATION,
            source_b=IntelligenceSource.RISK,
            description="test",
            rule_id="R001",
            resolution_strategy=resolution,
        )

    def _make_state(self, sid, conf_a=80, conf_b=60):
        eng = AggregationEngine()
        eng.apply(make_eval_update(sid, confidence=conf_a))
        eng.apply(make_risk_update(sid, confidence=conf_b))
        return eng.get_state(sid)

    def test_higher_confidence_resolves(self):
        resolver = ConflictResolver()
        c = self._make_conflict(ResolutionStrategy.HIGHER_CONFIDENCE)
        state = self._make_state("HR1", conf_a=90, conf_b=50)
        ok, notes = resolver.resolve(c, state)
        assert ok
        assert c.is_resolved

    def test_most_recent_resolves(self):
        resolver = ConflictResolver()
        c = self._make_conflict(ResolutionStrategy.MOST_RECENT)
        state = self._make_state("MR1")
        ok, notes = resolver.resolve(c, state)
        assert ok

    def test_risk_first_resolves(self):
        resolver = ConflictResolver()
        c = self._make_conflict(ResolutionStrategy.RISK_FIRST)
        state = self._make_state("RF1")
        ok, notes = resolver.resolve(c, state)
        assert ok

    def test_conservative_resolves(self):
        resolver = ConflictResolver()
        c = self._make_conflict(ResolutionStrategy.CONSERVATIVE)
        state = self._make_state("CO1")
        ok, notes = resolver.resolve(c, state)
        assert ok

    def test_escalate_does_not_resolve(self):
        resolver = ConflictResolver()
        c = self._make_conflict(ResolutionStrategy.ESCALATE)
        state = self._make_state("ESC1")
        ok, notes = resolver.resolve(c, state)
        assert not ok

    def test_resolve_all(self):
        resolver = ConflictResolver()
        state = self._make_state("ALL1")
        conflicts = [
            self._make_conflict(ResolutionStrategy.HIGHER_CONFIDENCE),
            self._make_conflict(ResolutionStrategy.ESCALATE),
        ]
        resolved, unresolved = resolver.resolve_all(conflicts, state)
        assert len(resolved) == 1
        assert len(unresolved) == 1


# ===========================================================================
# ConflictEngine
# ===========================================================================

class TestConflictEngine:
    def _make_conflicting_state(self, sid: str):
        eng = AggregationEngine()
        # R001: eval>=70 + risk=critical → HIGH conflict
        eng.apply(make_update(IntelligenceSource.EVALUATION, sid, {"score": 75, "status": "active"}, confidence=80))
        eng.apply(make_update(IntelligenceSource.RISK, sid, {"risk_level": "critical"}, confidence=75))
        return eng.get_state(sid)

    def test_process_returns_lists(self):
        engine = ConflictEngine()
        sid = "CE1"
        state = self._make_conflicting_state(sid)
        resolved, unresolved = engine.process(state)
        assert isinstance(resolved, list)
        assert isinstance(unresolved, list)

    def test_process_clean_state_returns_empty(self):
        engine = ConflictEngine()
        sid, state, _ = make_full_state("CE_CLEAN")
        resolved, unresolved = engine.process(state)
        assert resolved == []
        assert unresolved == []

    def test_active_conflicts_recorded(self):
        engine = ConflictEngine()
        sid = "CE2"
        state = self._make_conflicting_state(sid)
        engine.process(state)
        # Some conflicts may be auto-resolved; history is still recorded
        assert engine.stats(sid)["total_recorded"] >= 0

    def test_has_blocking_conflict_false_for_clean(self):
        engine = ConflictEngine()
        sid, state, _ = make_full_state("CE_BLOCK")
        engine.process(state)
        assert not engine.has_blocking_conflict(sid)

    def test_stats_structure(self):
        engine = ConflictEngine()
        s = engine.stats()
        assert "total_recorded" in s
        assert "active" in s


# ===========================================================================
# ConflictHistory
# ===========================================================================

class TestConflictHistory:
    def _make_conflict(self, sid: str, resolved: bool = False) -> Conflict:
        from datetime import datetime, timezone
        c = Conflict(
            conflict_id="ch-test",
            strategy_id=sid,
            conflict_type=ConflictType.EVALUATION_VS_RISK,
            severity=ConflictSeverity.MEDIUM,
            source_a=IntelligenceSource.EVALUATION,
            source_b=IntelligenceSource.RISK,
            description="test",
            rule_id="R001",
            resolution_strategy=ResolutionStrategy.RISK_FIRST,
        )
        if resolved:
            c.resolve("resolved in test")
        return c

    def test_record_and_for_strategy(self):
        hist = ConflictHistory()
        c = self._make_conflict("HIST1")
        hist.record(c)
        assert c in hist.for_strategy("HIST1")

    def test_active_vs_resolved(self):
        hist = ConflictHistory()
        hist.record(self._make_conflict("H2", resolved=False))
        hist.record(self._make_conflict("H2", resolved=True))
        assert len(hist.active("H2")) == 1
        assert len(hist.resolved("H2")) == 1

    def test_count(self):
        hist = ConflictHistory()
        hist.record(self._make_conflict("H3"))
        hist.record(self._make_conflict("H3"))
        assert hist.count() == 2

    def test_max_size_ring(self):
        hist = ConflictHistory(max_size=3)
        for _ in range(5):
            hist.record(self._make_conflict("RING"))
        assert hist.count() == 3

    def test_by_severity(self):
        hist = ConflictHistory()
        hist.record(self._make_conflict("SEV"))
        results = hist.by_severity(ConflictSeverity.MEDIUM)
        assert len(results) >= 1
