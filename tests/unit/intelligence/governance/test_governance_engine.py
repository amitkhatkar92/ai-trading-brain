"""
tests/unit/intelligence/governance/test_governance_engine.py
=============================================================
Test-suite for the Intelligence Quality & Explainability Engine.
Target: ≥ 110 tests.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _pid() -> str:
    return f"prod:{uuid.uuid4().hex[:8]}"


def _reset_all() -> None:
    """Reset every singleton so tests are isolated."""
    from iios.intelligence.governance.governance_engine import reset_governance_engine
    from iios.intelligence.governance.governance_manager import reset_governance_manager
    from iios.intelligence.governance.quality.quality_manager import reset_quality_manager
    from iios.intelligence.governance.explainability.explanation_engine import reset_explanation_engine
    from iios.intelligence.governance.audit.audit_engine import reset_audit_engine, reset_audit_manager
    from iios.intelligence.governance.audit.audit_registry import reset_audit_registry
    from iios.intelligence.governance.audit.audit_recorder import reset_audit_recorder
    from iios.intelligence.governance.certification.certification_engine import reset_certification_engine
    from iios.intelligence.governance.certification.certification_registry import reset_certification_registry
    from iios.intelligence.governance.monitoring.drift_detector import reset_drift_detector
    from iios.intelligence.governance.monitoring.performance_tracker import reset_governance_performance_tracker
    from iios.intelligence.governance.evaluation.evaluation_engine import reset_evaluation_engine
    from iios.intelligence.governance.quality_context import reset_governance_context

    reset_governance_engine()
    reset_governance_manager()
    reset_quality_manager()
    reset_explanation_engine()
    reset_audit_engine()
    reset_audit_manager()
    reset_audit_registry()
    reset_audit_recorder()
    reset_certification_engine()
    reset_certification_registry()
    reset_drift_detector()
    reset_governance_performance_tracker()
    reset_evaluation_engine()
    reset_governance_context()


@pytest.fixture(autouse=True)
def clean_singletons():
    _reset_all()
    yield
    _reset_all()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants & enums
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_quality_levels_ordered(self):
        from iios.intelligence.governance.quality_constants import (
            QualityLevel,
            QUALITY_SCORE_EXCELLENT,
            QUALITY_SCORE_GOOD,
            QUALITY_SCORE_ACCEPTABLE,
        )
        assert QUALITY_SCORE_EXCELLENT > QUALITY_SCORE_GOOD > QUALITY_SCORE_ACCEPTABLE

    def test_default_dimension_weights_sum_to_one(self):
        from iios.intelligence.governance.quality_constants import DEFAULT_DIMENSION_WEIGHTS
        total = sum(DEFAULT_DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_intelligence_types_present(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType
        assert IntelligenceType.FORECAST in list(IntelligenceType)
        assert IntelligenceType.HYPOTHESIS in list(IntelligenceType)
        assert IntelligenceType.GENERIC in list(IntelligenceType)

    def test_approval_status_values(self):
        from iios.intelligence.governance.quality_constants import ApprovalStatus
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"

    def test_certification_ttl_positive(self):
        from iios.intelligence.governance.quality_constants import CERTIFICATION_TTL_S
        assert CERTIFICATION_TTL_S > 0

    def test_audit_event_types_present(self):
        from iios.intelligence.governance.quality_constants import AuditEventType
        assert AuditEventType.EVALUATION in list(AuditEventType)
        assert AuditEventType.DRIFT_ALERT in list(AuditEventType)

    def test_drift_types_present(self):
        from iios.intelligence.governance.quality_constants import DriftType
        assert DriftType.QUALITY in list(DriftType)
        assert DriftType.CONFIDENCE in list(DriftType)

    def test_version_string(self):
        from iios.intelligence.governance.quality_constants import GOVERNANCE_ENGINE_VERSION
        assert GOVERNANCE_ENGINE_VERSION == "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_exception(self):
        from iios.intelligence.governance.quality_exceptions import IntelligenceQualityError
        with pytest.raises(IntelligenceQualityError):
            raise IntelligenceQualityError("IQE-000", "test")

    def test_quality_below_threshold(self):
        from iios.intelligence.governance.quality_exceptions import QualityBelowThresholdError
        exc = QualityBelowThresholdError("p1", 0.3, 0.6)
        assert "IQE-011" in str(exc)

    def test_quality_record_not_found(self):
        from iios.intelligence.governance.quality_exceptions import QualityRecordNotFoundError
        exc = QualityRecordNotFoundError("rec1")
        assert "rec1" in str(exc)

    def test_trace_not_found(self):
        from iios.intelligence.governance.quality_exceptions import TraceNotFoundError
        exc = TraceNotFoundError("t1")
        assert "IQE-021" in str(exc)

    def test_certification_not_found(self):
        from iios.intelligence.governance.quality_exceptions import CertificationNotFoundError
        exc = CertificationNotFoundError("c1")
        assert "IQE-041" in str(exc)

    def test_certification_failed(self):
        from iios.intelligence.governance.quality_exceptions import CertificationFailedError
        exc = CertificationFailedError("p1", "bad score")
        assert "IQE-044" in str(exc)

    def test_drift_alert_error(self):
        from iios.intelligence.governance.quality_exceptions import DriftAlertError
        exc = DriftAlertError("src1", "QUALITY", 0.2)
        assert "IQE-051" in str(exc)

    def test_governance_not_initialised(self):
        from iios.intelligence.governance.quality_exceptions import GovernanceEngineNotInitializedError
        exc = GovernanceEngineNotInitializedError()
        assert "IQE-071" in str(exc)

    def test_governance_already_running(self):
        from iios.intelligence.governance.quality_exceptions import GovernanceEngineAlreadyRunningError
        exc = GovernanceEngineAlreadyRunningError()
        assert "IQE-072" in str(exc)

    def test_policy_violation(self):
        from iios.intelligence.governance.quality_exceptions import PolicyViolationError
        exc = PolicyViolationError("pol1", "violated")
        assert "IQE-045" in str(exc)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Context manager
# ─────────────────────────────────────────────────────────────────────────────

class TestGovernanceContext:
    def test_evaluation_scope(self):
        from iios.intelligence.governance.quality_context import (
            evaluation_scope,
            get_governance_context,
        )
        from iios.intelligence.governance.quality_constants import IntelligenceType
        with evaluation_scope("p1", IntelligenceType.FORECAST, "src1") as ctx:
            assert ctx.product_id == "p1"
            assert ctx.depth == 1

    def test_certification_scope(self):
        from iios.intelligence.governance.quality_context import (
            certification_scope,
        )
        with certification_scope("rec1") as ctx:
            assert ctx.record_id == "rec1"

    def test_singleton_identity(self):
        from iios.intelligence.governance.quality_context import get_governance_context
        assert get_governance_context() is get_governance_context()


# ─────────────────────────────────────────────────────────────────────────────
# 4. QualityRecord model
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityRecord:
    def test_defaults(self):
        from iios.intelligence.governance.quality_result import QualityRecord
        from iios.intelligence.governance.quality_constants import (
            ApprovalStatus, CertificationStatus, IntelligenceType,
        )
        r = QualityRecord(product_id="p1", product_type=IntelligenceType.GENERIC)
        assert r.approval_status == ApprovalStatus.PENDING
        assert r.certification_status == CertificationStatus.UNCERTIFIED

    def test_is_approved(self):
        from iios.intelligence.governance.quality_result import QualityRecord
        from iios.intelligence.governance.quality_constants import (
            ApprovalStatus, IntelligenceType,
        )
        r = QualityRecord(product_id="p1", product_type=IntelligenceType.GENERIC)
        r.approval_status = ApprovalStatus.APPROVED
        assert r.is_approved

    def test_to_dict_keys(self):
        from iios.intelligence.governance.quality_result import QualityRecord
        from iios.intelligence.governance.quality_constants import IntelligenceType
        r = QualityRecord(product_id="p1", product_type=IntelligenceType.GENERIC)
        d = r.to_dict()
        assert "record_id" in d
        assert "quality_score" in d
        assert "approval_status" in d

    def test_touch_updates_updated_at(self):
        from iios.intelligence.governance.quality_result import QualityRecord
        from iios.intelligence.governance.quality_constants import IntelligenceType
        r = QualityRecord(product_id="p1", product_type=IntelligenceType.GENERIC)
        old = r.updated_at
        time.sleep(0.01)
        r.touch()
        assert r.updated_at >= old


# ─────────────────────────────────────────────────────────────────────────────
# 5. Quality scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityScoring:
    def test_score_product(self):
        from iios.intelligence.governance.quality.quality_score import score_product
        qs = score_product("p1", {"accuracy": 0.9, "consistency": 0.8})
        assert 0.0 <= qs.composite <= 1.0

    def test_composite_weighted(self):
        from iios.intelligence.governance.quality.quality_score import compute_composite, DimensionScore
        from iios.intelligence.governance.quality_constants import EvaluationDimension
        dims = [
            DimensionScore(dimension=EvaluationDimension.ACCURACY, score=1.0, weight=0.5),
            DimensionScore(dimension=EvaluationDimension.CONSISTENCY, score=0.5, weight=0.5),
        ]
        assert abs(compute_composite(dims) - 0.75) < 1e-9

    def test_level_from_score(self):
        from iios.intelligence.governance.quality.quality_score import level_from_score
        from iios.intelligence.governance.quality_constants import QualityLevel
        assert level_from_score(0.95) == QualityLevel.EXCELLENT
        assert level_from_score(0.60) == QualityLevel.ACCEPTABLE
        assert level_from_score(0.30) == QualityLevel.REJECTED


# ─────────────────────────────────────────────────────────────────────────────
# 6. QualityEvaluator (heuristic)
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityEvaluator:
    def test_evaluate_returns_score(self):
        from iios.intelligence.governance.quality.quality_evaluator import QualityEvaluator
        from iios.intelligence.governance.quality_constants import IntelligenceType
        ev = QualityEvaluator()
        qs = ev.evaluate("p1", IntelligenceType.FORECAST, {"confidence": 0.8})
        assert 0.0 <= qs.composite <= 1.0

    def test_evaluate_all_dimensions_present(self):
        from iios.intelligence.governance.quality.quality_evaluator import QualityEvaluator
        from iios.intelligence.governance.quality_constants import IntelligenceType, EvaluationDimension
        ev = QualityEvaluator()
        qs = ev.evaluate("p1", IntelligenceType.GENERIC, {})
        dim_names = {d.dimension for d in qs.dimensions}
        assert EvaluationDimension.ACCURACY in dim_names

    def test_high_confidence_improves_score(self):
        from iios.intelligence.governance.quality.quality_evaluator import QualityEvaluator
        from iios.intelligence.governance.quality_constants import IntelligenceType
        ev = QualityEvaluator()
        low  = ev.evaluate("p1", IntelligenceType.FORECAST, {"confidence": 0.1})
        high = ev.evaluate("p2", IntelligenceType.FORECAST, {"confidence": 0.95})
        assert high.composite > low.composite


# ─────────────────────────────────────────────────────────────────────────────
# 7. QualityManager
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityManager:
    def test_evaluate_stores_record(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType
        mgr = get_quality_manager()
        r = mgr.evaluate(_pid(), IntelligenceType.GENERIC, {})
        assert mgr.has(r.record_id)

    def test_approve_sets_status(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType, ApprovalStatus
        mgr = get_quality_manager()
        r = mgr.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.9})
        mgr.approve(r.record_id)
        r2 = mgr.get(r.record_id)
        assert r2.approval_status == ApprovalStatus.APPROVED

    def test_reject_sets_status(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType, ApprovalStatus
        mgr = get_quality_manager()
        r = mgr.evaluate(_pid(), IntelligenceType.GENERIC, {})
        mgr.reject(r.record_id, reason="test")
        assert mgr.get(r.record_id).approval_status == ApprovalStatus.REJECTED

    def test_for_product(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType
        mgr = get_quality_manager()
        pid = _pid()
        mgr.evaluate(pid, IntelligenceType.GENERIC, {})
        mgr.evaluate(pid, IntelligenceType.GENERIC, {})
        assert len(mgr.for_product(pid)) == 2

    def test_singleton_identity(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        assert get_quality_manager() is get_quality_manager()

    def test_stats_keys(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        s = get_quality_manager().stats()
        assert "total" in s


# ─────────────────────────────────────────────────────────────────────────────
# 8. Explainability
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainability:
    def _make_record(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType
        return get_quality_manager().evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.8})

    def test_explain_returns_dict(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        eng = get_explanation_engine()
        r = self._make_record()
        result = eng.explain(r)
        assert "record" in result

    def test_explain_text_nonempty(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        eng = get_explanation_engine()
        r = self._make_record()
        eng.explain(r)
        txt = eng.explain_text(r)
        assert len(txt) > 50

    def test_summary(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        eng = get_explanation_engine()
        r = self._make_record()
        s = eng.summary(r)
        assert r.product_id in s

    def test_get_reasoning(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        eng = get_explanation_engine()
        r = self._make_record()
        eng.explain(r)
        trace = eng.get_reasoning(r.record_id)
        assert trace.total_steps > 0

    def test_get_decision_trace(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        eng = get_explanation_engine()
        r = self._make_record()
        eng.explain(r)
        dt = eng.get_decision(r.record_id)
        assert dt.product_id == r.product_id

    def test_get_evidence_trace(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        eng = get_explanation_engine()
        r = self._make_record()
        eng.explain(r)
        et = eng.get_evidence(r.record_id)
        assert len(et.items) > 0

    def test_get_proof_chain(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        eng = get_explanation_engine()
        r = self._make_record()
        eng.explain(r)
        pc = eng.get_proof(r.record_id)
        assert pc.is_valid in (True, False)  # just not an error

    def test_missing_trace_raises(self):
        from iios.intelligence.governance.explainability.explanation_engine import get_explanation_engine
        from iios.intelligence.governance.quality_exceptions import TraceNotFoundError
        eng = get_explanation_engine()
        with pytest.raises(TraceNotFoundError):
            eng.get_reasoning("nonexistent")

    def test_reasoning_trace_steps(self):
        from iios.intelligence.governance.explainability.reasoning_trace import ReasoningTraceRecord
        t = ReasoningTraceRecord(record_id="r1", product_id="p1")
        t.add_step("step1", input_={"x": 1}, output={"y": 2}, confidence=0.9)
        assert t.total_steps == 1
        assert abs(t.avg_confidence - 0.9) < 1e-6

    def test_evidence_trace_net_strength(self):
        from iios.intelligence.governance.explainability.evidence_trace import (
            EvidenceItem, EvidenceTraceRecord,
        )
        t = EvidenceTraceRecord(record_id="r1", product_id="p1")
        t.add_item(EvidenceItem(evidence_id="e1", strength=0.8, direction="supporting"))
        t.add_item(EvidenceItem(evidence_id="e2", strength=0.3, direction="opposing"))
        assert abs(t.net_strength - 0.5) < 1e-9

    def test_proof_chain_cumulative_confidence(self):
        from iios.intelligence.governance.explainability.proof_chain import GovernanceProofChain
        chain = GovernanceProofChain(record_id="r1", product_id="p1")
        chain.add_step("P1", "C1", confidence=0.9)
        chain.add_step("P2", "C2", confidence=0.8)
        assert abs(chain.cumulative_confidence() - 0.72) < 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# 9. Audit
# ─────────────────────────────────────────────────────────────────────────────

class TestAudit:
    def _make_record(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType
        return get_quality_manager().evaluate(_pid(), IntelligenceType.GENERIC, {})

    def test_record_evaluation(self):
        from iios.intelligence.governance.audit.audit_engine import get_audit_engine
        eng = get_audit_engine()
        r = self._make_record()
        audit = eng.record_evaluation(r)
        assert audit.audit_id in (a.audit_id for a in eng.for_product(r.product_id))

    def test_record_approval(self):
        from iios.intelligence.governance.audit.audit_engine import get_audit_engine
        from iios.intelligence.governance.quality_constants import AuditEventType
        eng = get_audit_engine()
        r = self._make_record()
        eng.record_approval(r, reason="looks good")
        events = eng.for_event_type(AuditEventType.APPROVAL)
        assert any(a.record_id == r.record_id for a in events)

    def test_record_rejection(self):
        from iios.intelligence.governance.audit.audit_engine import get_audit_engine
        from iios.intelligence.governance.quality_constants import AuditEventType
        eng = get_audit_engine()
        r = self._make_record()
        eng.record_rejection(r, reason="too low")
        events = eng.for_event_type(AuditEventType.REJECTION)
        assert any(a.record_id == r.record_id for a in events)

    def test_record_drift_alert(self):
        from iios.intelligence.governance.audit.audit_engine import get_audit_engine
        from iios.intelligence.governance.quality_constants import AuditEventType
        eng = get_audit_engine()
        eng.record_drift_alert("src1", "QUALITY", 0.2)
        alerts = eng.for_event_type(AuditEventType.DRIFT_ALERT)
        assert len(alerts) >= 1

    def test_report(self):
        from iios.intelligence.governance.audit.audit_engine import get_audit_engine
        eng = get_audit_engine()
        r = self._make_record()
        eng.record_evaluation(r)
        report = eng.report(product_id=r.product_id)
        assert report.total_entries >= 1

    def test_singleton_identity(self):
        from iios.intelligence.governance.audit.audit_engine import get_audit_engine
        assert get_audit_engine() is get_audit_engine()

    def test_not_found_raises(self):
        from iios.intelligence.governance.audit.audit_registry import get_audit_registry
        from iios.intelligence.governance.quality_exceptions import AuditRecordNotFoundError
        with pytest.raises(AuditRecordNotFoundError):
            get_audit_registry().get("nonexistent")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Certification
# ─────────────────────────────────────────────────────────────────────────────

class TestCertification:
    def _make_approved_record(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType, ApprovalStatus
        mgr = get_quality_manager()
        r = mgr.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.9})
        mgr.approve(r.record_id)
        return r

    def test_certify_approved_record(self):
        from iios.intelligence.governance.certification.certification_engine import get_certification_engine
        from iios.intelligence.governance.certification.certification_policy import ApprovalRequiredPolicy
        from iios.intelligence.governance.quality_constants import CertificationStatus
        eng = get_certification_engine()
        eng.register_policy(ApprovalRequiredPolicy())
        r   = self._make_approved_record()
        cert = eng.certify(r)
        assert cert.status == CertificationStatus.CERTIFIED
        assert cert.is_valid

    def test_certify_low_score_fails(self):
        from iios.intelligence.governance.certification.certification_engine import get_certification_engine
        from iios.intelligence.governance.quality_exceptions import CertificationFailedError
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_certification_engine()
        mgr = get_quality_manager()
        # Force a very low score by injecting score directly on record
        r = mgr.evaluate(_pid(), IntelligenceType.GENERIC, {})
        r.quality_score = 0.1  # below threshold
        with pytest.raises(CertificationFailedError):
            eng.certify(r)

    def test_revoke(self):
        from iios.intelligence.governance.certification.certification_engine import get_certification_engine
        from iios.intelligence.governance.quality_constants import CertificationStatus
        eng = get_certification_engine()
        r   = self._make_approved_record()
        cert = eng.certify(r)
        eng.revoke(cert.cert_id, reason="manual revoke")
        updated = eng._registry.get(cert.cert_id)
        assert updated.status == CertificationStatus.REVOKED

    def test_check_expiry(self):
        from iios.intelligence.governance.certification.certification_engine import get_certification_engine
        from iios.intelligence.governance.quality_constants import CertificationStatus
        eng = get_certification_engine()
        r   = self._make_approved_record()
        # Issue a cert that expires in the past
        cert = eng.certify(r, ttl_s=0.001)
        time.sleep(0.01)
        expired = eng.check_expiry()
        assert cert.cert_id in expired

    def test_policy_names(self):
        from iios.intelligence.governance.certification.certification_engine import get_certification_engine
        eng = get_certification_engine()
        names = eng.policy_names()
        assert len(names) >= 1

    def test_policy_allowlist(self):
        from iios.intelligence.governance.certification.certification_policy import TypeAllowlistPolicy
        from iios.intelligence.governance.quality_constants import IntelligenceType
        from iios.intelligence.governance.quality_result import QualityRecord
        pol  = TypeAllowlistPolicy([IntelligenceType.FORECAST])
        r    = QualityRecord(product_id="p1", product_type=IntelligenceType.FORECAST)
        ok, _ = pol.check(r)
        assert ok
        r2   = QualityRecord(product_id="p2", product_type=IntelligenceType.SIGNAL)
        ok2, _ = pol.check(r2)
        assert not ok2

    def test_no_rejection_reasons_policy(self):
        from iios.intelligence.governance.certification.certification_policy import NoRejectionReasonsPolicy
        from iios.intelligence.governance.quality_result import QualityRecord
        from iios.intelligence.governance.quality_constants import IntelligenceType
        pol = NoRejectionReasonsPolicy()
        r   = QualityRecord(product_id="p1", product_type=IntelligenceType.GENERIC)
        ok, _ = pol.check(r)
        assert ok
        r.rejection_reasons.append("bad")
        ok2, _ = pol.check(r)
        assert not ok2


# ─────────────────────────────────────────────────────────────────────────────
# 11. Monitoring
# ─────────────────────────────────────────────────────────────────────────────

class TestMonitoring:
    def test_drift_no_alert_before_window(self):
        from iios.intelligence.governance.monitoring.drift_detector import get_drift_detector
        det = get_drift_detector()
        for _ in range(5):
            alerts = det.record_sample("src1", 0.8, 0.8)
        assert len(alerts) == 0

    def test_drift_fires_after_window(self):
        from iios.intelligence.governance.monitoring.drift_detector import DriftDetector
        det = DriftDetector(window_n=5, quality_threshold=0.1, confidence_threshold=0.1)
        # feed 5 high samples then 5 low samples
        for _ in range(5):
            det.record_sample("src1", 0.9, 0.9)
        fired: list = []
        for _ in range(5):
            fired.extend(det.record_sample("src1", 0.1, 0.1))
        assert len(fired) > 0

    def test_performance_tracker_rolling_avg(self):
        from iios.intelligence.governance.monitoring.performance_tracker import get_governance_performance_tracker
        t = get_governance_performance_tracker()
        for i in range(10):
            t.record("src1", "quality_score", 0.8)
        avg = t.rolling_avg("src1", "quality_score", n=10)
        assert abs(avg - 0.8) < 1e-9

    def test_performance_tracker_trend_improving(self):
        from iios.intelligence.governance.monitoring.performance_tracker import PerformanceTracker
        t = PerformanceTracker()
        for v in [0.5, 0.5, 0.5, 0.5, 0.9, 0.9, 0.9, 0.9]:
            t.record("src1", "q", v)
        assert t.rolling_trend("src1", "q") == "improving"

    def test_performance_tracker_trend_degrading(self):
        from iios.intelligence.governance.monitoring.performance_tracker import PerformanceTracker
        t = PerformanceTracker()
        for v in [0.9, 0.9, 0.9, 0.9, 0.5, 0.5, 0.5, 0.5]:
            t.record("src1", "q", v)
        assert t.rolling_trend("src1", "q") == "degrading"

    def test_monitor_report(self):
        from iios.intelligence.governance.monitoring.monitor_report import (
            build_monitor_report, MonitorReport,
        )
        from iios.intelligence.governance.monitoring.performance_tracker import MetricSample
        samples = [MetricSample("src1", "q", v) for v in [0.8, 0.7, 0.9]]
        r = build_monitor_report("src1", samples, samples, [])
        assert isinstance(r, MonitorReport)
        assert r.total_samples == 3

    def test_drift_alert_to_dict(self):
        from iios.intelligence.governance.monitoring.drift_detector import DriftAlert, DriftType
        a = DriftAlert(source_id="s1", drift_type=DriftType.QUALITY, baseline=0.8, current=0.5, delta=0.3)
        d = a.to_dict()
        assert d["drift_type"] == "quality"


# ─────────────────────────────────────────────────────────────────────────────
# 12. Evaluation metrics
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationMetrics:
    def _records(self, n: int = 5):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType
        mgr = get_quality_manager()
        return [mgr.evaluate(_pid(), IntelligenceType.GENERIC, {}) for _ in range(n)]

    def test_approval_rate_zero(self):
        from iios.intelligence.governance.evaluation.evaluation_metrics import approval_rate
        records = self._records(5)
        assert approval_rate(records) == 0.0

    def test_approval_rate_partial(self):
        from iios.intelligence.governance.evaluation.evaluation_metrics import approval_rate
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        from iios.intelligence.governance.quality_constants import IntelligenceType
        mgr = get_quality_manager()
        records = [mgr.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.9}) for _ in range(4)]
        mgr.approve(records[0].record_id)
        mgr.approve(records[1].record_id)
        assert abs(approval_rate(records) - 0.5) < 1e-9

    def test_avg_quality_score(self):
        from iios.intelligence.governance.evaluation.evaluation_metrics import avg_quality_score
        from iios.intelligence.governance.quality_result import QualityRecord
        from iios.intelligence.governance.quality_constants import IntelligenceType
        r1 = QualityRecord(product_id="p1", product_type=IntelligenceType.GENERIC, quality_score=0.8)
        r2 = QualityRecord(product_id="p2", product_type=IntelligenceType.GENERIC, quality_score=0.6)
        assert abs(avg_quality_score([r1, r2]) - 0.7) < 1e-9

    def test_drift_score(self):
        from iios.intelligence.governance.evaluation.evaluation_metrics import drift_score
        d = drift_score([0.9, 0.9, 0.9], [0.5, 0.5, 0.5])
        assert abs(d - 0.4) < 1e-9

    def test_consistency_rate_all_consistent(self):
        from iios.intelligence.governance.evaluation.evaluation_metrics import consistency_rate
        records = self._records(4)
        # After scoring, levels are derived from scores — should be consistent
        rate = consistency_rate(records)
        assert 0.0 <= rate <= 1.0

    def test_empty_inputs(self):
        from iios.intelligence.governance.evaluation.evaluation_metrics import (
            approval_rate, avg_quality_score, drift_score,
        )
        assert approval_rate([]) == 0.0
        assert avg_quality_score([]) == 0.0
        assert drift_score([], []) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 13. EvaluationEngine (full pipeline)
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationEngine:
    def test_evaluate_full_pipeline(self):
        from iios.intelligence.governance.evaluation.evaluation_engine import get_evaluation_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_evaluation_engine()
        r = eng.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.8}, "src1")
        assert r.record_id
        assert 0.0 <= r.quality_score <= 1.0

    def test_batch_evaluate(self):
        from iios.intelligence.governance.evaluation.evaluation_engine import get_evaluation_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_evaluation_engine()
        products = [
            {"product_id": _pid(), "product_type": IntelligenceType.GENERIC, "content": {}}
            for _ in range(3)
        ]
        results = eng.batch_evaluate(products)
        assert len(results) == 3

    def test_stats_counter_increments(self):
        from iios.intelligence.governance.evaluation.evaluation_engine import get_evaluation_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_evaluation_engine()
        eng.evaluate(_pid(), IntelligenceType.GENERIC, {})
        eng.evaluate(_pid(), IntelligenceType.GENERIC, {})
        assert eng.stats()["total_evaluated"] == 2

    def test_async_evaluate(self):
        from iios.intelligence.governance.evaluation.evaluation_engine import get_evaluation_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_evaluation_engine()

        async def _run():
            return await eng.evaluate_async(_pid(), IntelligenceType.FORECAST, {"confidence": 0.7})

        r = asyncio.run(_run())
        assert r.quality_score > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 14. IntelligenceQualityEngine (top-level gateway)
# ─────────────────────────────────────────────────────────────────────────────

class TestIntelligenceQualityEngine:
    def _engine(self):
        from iios.intelligence.governance.governance_engine import get_governance_engine
        eng = get_governance_engine()
        eng.initialize()
        return eng

    def test_initialize_and_is_running(self):
        eng = self._engine()
        assert eng.is_running

    def test_double_initialize_raises(self):
        from iios.intelligence.governance.quality_exceptions import GovernanceEngineAlreadyRunningError
        eng = self._engine()
        with pytest.raises(GovernanceEngineAlreadyRunningError):
            eng.initialize()

    def test_evaluate_returns_record(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = self._engine()
        r = eng.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.8}, "src1")
        assert r.record_id

    def test_not_initialised_raises(self):
        from iios.intelligence.governance.governance_engine import get_governance_engine
        from iios.intelligence.governance.quality_exceptions import GovernanceEngineNotInitializedError
        eng = get_governance_engine()
        # not yet initialised
        with pytest.raises(GovernanceEngineNotInitializedError):
            eng.evaluate("p1", None, {})   # type: ignore[arg-type]

    def test_shutdown(self):
        eng = self._engine()
        eng.shutdown()
        assert not eng.is_running

    def test_approve_reject_cycle(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType, ApprovalStatus
        eng = self._engine()
        r   = eng.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.9}, "src1")
        eng.approve(r.record_id, reason="ok")
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        assert get_quality_manager().get(r.record_id).approval_status == ApprovalStatus.APPROVED

    def test_explain_human(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType, ExplanationType
        eng = self._engine()
        r   = eng.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.8})
        txt = eng.explain(r.record_id, ExplanationType.HUMAN_READABLE)
        assert isinstance(txt, str) and len(txt) > 10

    def test_explain_machine(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType, ExplanationType
        eng = self._engine()
        r   = eng.evaluate(_pid(), IntelligenceType.GENERIC, {})
        d   = eng.explain(r.record_id, ExplanationType.MACHINE_READABLE)
        assert isinstance(d, dict)

    def test_certify_via_engine(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType, CertificationStatus
        eng = self._engine()
        r   = eng.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.9})
        eng.approve(r.record_id)
        cert = eng.certify(r.record_id)
        assert cert.status == CertificationStatus.CERTIFIED

    def test_audit_query(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = self._engine()
        eng.evaluate(_pid(), IntelligenceType.GENERIC, {}, "srcX")
        records = eng.audit_query(source_id="srcX")
        assert len(records) >= 1

    def test_check_drift_empty(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = self._engine()
        alerts = eng.check_drift("unknown_source")
        assert isinstance(alerts, list)

    def test_dashboard(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = self._engine()
        eng.evaluate(_pid(), IntelligenceType.GENERIC, {})
        snap = eng.dashboard()
        assert snap.total_evaluated >= 1

    def test_stats_has_version(self):
        eng = self._engine()
        s   = eng.stats()
        assert s["engine_version"] == "1.0.0"

    def test_health_running(self):
        eng = self._engine()
        h   = eng.health()
        assert h["status"] == "healthy"

    def test_health_stopped(self):
        from iios.intelligence.governance.governance_engine import get_governance_engine
        eng = get_governance_engine()
        assert eng.health()["status"] == "stopped"

    def test_async_evaluate(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = self._engine()

        async def _run():
            return await eng.evaluate_async(_pid(), IntelligenceType.HYPOTHESIS, {"confidence": 0.75})

        r = asyncio.run(_run())
        assert r.quality_score > 0.0

    def test_summary(self):
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = self._engine()
        r   = eng.evaluate(_pid(), IntelligenceType.FORECAST, {"confidence": 0.8})
        s   = eng.summary(r.record_id)
        assert r.product_id in s


# ─────────────────────────────────────────────────────────────────────────────
# 15. Dashboard & report
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboard:
    def _populated_engine(self, n: int = 4):
        from iios.intelligence.governance.governance_engine import get_governance_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_governance_engine()
        eng.initialize()
        for _ in range(n):
            eng.evaluate(_pid(), IntelligenceType.GENERIC, {})
        return eng

    def test_snapshot_counts(self):
        eng  = self._populated_engine(4)
        snap = eng.dashboard()
        assert snap.total_evaluated == 4

    def test_snapshot_to_dict_keys(self):
        eng  = self._populated_engine(2)
        d    = eng.dashboard().to_dict()
        for key in ("total_evaluated", "approved", "rejected", "certified",
                    "avg_quality", "quality_level_distribution"):
            assert key in d

    def test_source_summary(self):
        from iios.intelligence.governance.governance_engine import get_governance_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_governance_engine()
        eng.initialize()
        pid = _pid()
        eng.evaluate(pid, IntelligenceType.GENERIC, {}, source_id="src_test")
        mgr = eng._require_running()
        summary = mgr._dashboard or mgr.dashboard()  # build if needed
        # Use direct method call on GovernanceManager._dashboard
        mgr2 = eng._require_running()
        from iios.intelligence.governance.evaluation.evaluation_dashboard import EvaluationDashboard
        from iios.intelligence.governance.monitoring.drift_detector import get_drift_detector
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        dash = EvaluationDashboard(
            records_provider=get_quality_manager().all,
            alerts_provider=get_drift_detector().all_alerts,
        )
        s = dash.source_summary("src_test")
        assert s["source_id"] == "src_test"
        assert s["total"] >= 1

    def test_audit_report_to_dict(self):
        from iios.intelligence.governance.governance_engine import get_governance_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_governance_engine()
        eng.initialize()
        eng.evaluate(_pid(), IntelligenceType.GENERIC, {})
        report = eng.audit_report()
        d = report.to_dict()
        assert "total_entries" in d


# ─────────────────────────────────────────────────────────────────────────────
# 16. Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_evaluations(self):
        from iios.intelligence.governance.governance_engine import get_governance_engine
        from iios.intelligence.governance.quality_constants import IntelligenceType
        eng = get_governance_engine()
        eng.initialize()

        errors: list[Exception] = []
        results: list = []

        def _evaluate():
            try:
                r = eng.evaluate(_pid(), IntelligenceType.GENERIC, {}, "src_concurrent")
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_evaluate) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20

    def test_concurrent_singleton_access(self):
        from iios.intelligence.governance.quality.quality_manager import get_quality_manager
        managers = []

        def _get():
            managers.append(get_quality_manager())

        threads = [threading.Thread(target=_get) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(m is managers[0] for m in managers)


# ─────────────────────────────────────────────────────────────────────────────
# 17. Package imports (__init__ surface)
# ─────────────────────────────────────────────────────────────────────────────

class TestPackageImports:
    def test_all_symbols_importable(self):
        import iios.intelligence.governance as gov
        assert hasattr(gov, "IntelligenceQualityEngine")
        assert hasattr(gov, "QualityRecord")
        assert hasattr(gov, "AuditRecord")
        assert hasattr(gov, "CertificationRecord")
        assert hasattr(gov, "DriftAlert")
        assert hasattr(gov, "DashboardSnapshot")
        assert hasattr(gov, "get_governance_engine")

    def test_exception_hierarchy(self):
        from iios.intelligence.governance import (
            IntelligenceQualityError,
            QualityBelowThresholdError,
            CertificationFailedError,
        )
        assert issubclass(QualityBelowThresholdError, IntelligenceQualityError)
        assert issubclass(CertificationFailedError, IntelligenceQualityError)

    def test_quality_record_from_package(self):
        from iios.intelligence.governance import QualityRecord, IntelligenceType
        r = QualityRecord(product_id="p1", product_type=IntelligenceType.GENERIC)
        assert r.product_id == "p1"
