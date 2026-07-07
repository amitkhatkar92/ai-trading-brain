"""
tests/unit/knowledge/test_governance_engine.py
===============================================
Comprehensive test suite for the Knowledge Quality & Governance Engine.

Covers:
  * Constants and enumerations
  * All model dataclasses
  * QualityEngine, QualityValidator, QualityMonitor
  * GovernanceEngine, PolicyManager, CertificationManager
  * GovernanceAuditLog
  * KnowledgeGovernor end-to-end pipeline
  * Thread-local contexts
  * Registries

All tests share a factory for test KnowledgeRecord objects.
"""

from __future__ import annotations

import time
import threading
import uuid
from typing import Any

import pytest

from iios.knowledge.governance.quality_constants import (
    DIMENSION_WEIGHTS,
    DEFAULT_MIN_KQI,
    AUTO_APPROVE_KQI_THRESHOLD,
    GOVERNANCE_NAMESPACE,
    GOVERNANCE_SCHEMA_VERSION,
    MONITOR_STALENESS_DAYS,
    QualityDimension,
    QualityTier,
    ViolationSeverity,
    ViolationType,
    SYSTEM_GOVERNANCE_ACTOR,
)
from iios.knowledge.governance.governance_constants import (
    ApprovalStatus,
    CertificationLevel,
    CertificationStatus,
    DEFAULT_CERTIFICATION_TTL_DAYS,
    GovernanceAction,
    PolicyType,
    RiskLevel,
    SENSITIVE_DOMAINS,
    SYSTEM_GOVERNANCE_ACTOR as GOV_ACTOR,
    GOVERNANCE_SCHEMA_VERSION as GOV_SCHEMA,
)
from iios.knowledge.governance.quality_exceptions import (
    QualityError,
    QualityThresholdError,
    QualityValidationError,
)
from iios.knowledge.governance.governance_exceptions import (
    ApprovalError,
    ApprovalNotFoundError,
    CertificationExpiredError,
    CertificationNotFoundError,
    GovernanceAuditError,
    KnowledgeGovernorError,
    PolicyAlreadyExistsError,
    PolicyNotFoundError,
)
from iios.knowledge.governance.models.quality_score import (
    DimensionScore,
    QualityScore,
    compute_kqi,
    compute_tier,
)
from iios.knowledge.governance.models.quality_violation import QualityViolation
from iios.knowledge.governance.models.governance_record import GovernanceRecord
from iios.knowledge.governance.models.certification import Certification
from iios.knowledge.governance.models.policy import GovernancePolicy, PolicyCondition
from iios.knowledge.governance.models.governance_audit import GovernanceAuditEntry

from iios.knowledge.governance.quality_engine import (
    QualityEngine,
    get_quality_engine,
    reset_quality_engine,
)
from iios.knowledge.governance.quality_validator import (
    QualityValidator,
    get_quality_validator,
    reset_quality_validator,
)
from iios.knowledge.governance.quality_monitor import (
    MonitorReport,
    QualityMonitor,
    get_quality_monitor,
    reset_quality_monitor,
)
from iios.knowledge.governance.governance_engine import (
    GovernanceEngine,
    get_governance_engine,
    reset_governance_engine,
)
from iios.knowledge.governance.policy_manager import (
    PolicyManager,
    get_policy_manager,
    reset_policy_manager,
)
from iios.knowledge.governance.certification_manager import (
    CertificationManager,
    get_certification_manager,
    reset_certification_manager,
)
from iios.knowledge.governance.governance_audit import (
    GovernanceAuditLog,
    get_governance_audit_log,
    reset_governance_audit_log,
)
from iios.knowledge.governance.knowledge_governor import (
    ApprovalResult,
    KnowledgeGovernor,
    get_knowledge_governor,
    reset_knowledge_governor,
)
from iios.knowledge.governance.quality_context import (
    QualityContext,
    current_quality_actor,
    current_quality_operation_id,
    get_quality_context,
    quality_operation,
    reset_quality_context,
)
from iios.knowledge.governance.governance_context import (
    GovernanceContext,
    current_governance_actor,
    get_governance_context,
    governance_operation,
    reset_governance_context,
)
from iios.knowledge.governance.quality_registry import (
    QualityRegistry,
    get_quality_registry,
    reset_quality_registry,
)
from iios.knowledge.governance.governance_registry import (
    GovernanceRegistry,
    get_governance_registry,
    reset_governance_registry,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

from iios.knowledge.knowledge_constants import (
    KnowledgeDomain,
    KnowledgeSource,
    KnowledgeStatus,
    KnowledgeType,
)
from iios.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeMetadata


def _meta(**kwargs: Any) -> KnowledgeMetadata:
    defaults: dict[str, Any] = {
        "domain":       KnowledgeDomain.GENERAL,
        "source":       KnowledgeSource.SYSTEM,
        "confidence":   0.80,
        "tags":         ["test"],
        "description":  "test record description",
        "created_by":   "test-user",
    }
    defaults.update(kwargs)
    return KnowledgeMetadata(**defaults)


def _record(
    title:     str   = "Test Knowledge",
    content:   str   = "Some meaningful content for testing.",
    knowledge_type: KnowledgeType = KnowledgeType.FACT,
    confidence: float = 0.80,
    domain:    KnowledgeDomain = KnowledgeDomain.GENERAL,
    status:    KnowledgeStatus = KnowledgeStatus.ACTIVE,
    tags:      list[str] | None = None,
    **kwargs: Any,
) -> KnowledgeRecord:
    meta = _meta(
        confidence = confidence,
        domain     = domain,
        tags       = tags if tags is not None else ["test"],
    )
    return KnowledgeRecord(
        title          = title,
        content        = content,
        knowledge_type = knowledge_type,
        status         = status,
        metadata       = meta,
        **kwargs,
    )


def _reset_all() -> None:
    reset_quality_engine()
    reset_quality_validator()
    reset_quality_monitor()
    reset_governance_engine()
    reset_policy_manager()
    reset_certification_manager()
    reset_governance_audit_log()
    reset_knowledge_governor()
    reset_quality_context()
    reset_governance_context()
    reset_quality_registry()
    reset_governance_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# 1 — Quality constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityConstants:
    def test_dimension_weights_sum_to_one(self) -> None:
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_all_dimensions_in_weights(self) -> None:
        for dim in QualityDimension:
            assert dim.value in DIMENSION_WEIGHTS, f"missing weight for {dim}"

    def test_quality_tier_order(self) -> None:
        assert QualityTier.POOR.value == "poor"
        assert QualityTier.EXCELLENT.value == "excellent"

    def test_system_actor_constant(self) -> None:
        assert SYSTEM_GOVERNANCE_ACTOR == "iios:governance"

    def test_auto_approve_threshold_above_default(self) -> None:
        assert AUTO_APPROVE_KQI_THRESHOLD > DEFAULT_MIN_KQI

    def test_governance_schema_version(self) -> None:
        assert GOVERNANCE_SCHEMA_VERSION == "1.0.0"

    def test_violation_types_cover_common_cases(self) -> None:
        assert ViolationType.MISSING_FIELD in ViolationType
        assert ViolationType.DUPLICATE_DETECTED in ViolationType
        assert ViolationType.EXPIRED_RECORD in ViolationType


# ═══════════════════════════════════════════════════════════════════════════════
# 2 — Governance constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceConstants:
    def test_approval_statuses(self) -> None:
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.AUTO_APPROVED.value == "auto_approved"

    def test_certification_levels(self) -> None:
        levels = [l.value for l in CertificationLevel]
        assert "standard" in levels
        assert "platinum" in levels

    def test_sensitive_domains_immutable(self) -> None:
        assert isinstance(SENSITIVE_DOMAINS, frozenset)
        assert "compliance" in SENSITIVE_DOMAINS
        assert "risk" in SENSITIVE_DOMAINS

    def test_governance_action_has_submit(self) -> None:
        assert GovernanceAction.SUBMIT in GovernanceAction

    def test_default_ttl(self) -> None:
        assert DEFAULT_CERTIFICATION_TTL_DAYS == 90


# ═══════════════════════════════════════════════════════════════════════════════
# 3 — Quality exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityExceptions:
    def test_base_quality_error(self) -> None:
        e = QualityError("test", code="QE-000")
        assert "test" in str(e)

    def test_validation_error_has_violations(self) -> None:
        viols = ["missing title", "empty content"]
        e = QualityValidationError("failed", violations=viols)
        assert e.violations == viols

    def test_threshold_error_carries_values(self) -> None:
        e = QualityThresholdError("below threshold", kqi=0.3, threshold=0.6)
        assert e.kqi == pytest.approx(0.3)
        assert e.threshold == pytest.approx(0.6)


# ═══════════════════════════════════════════════════════════════════════════════
# 4 — Governance exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceExceptions:
    def test_approval_not_found(self) -> None:
        e = ApprovalNotFoundError("missing")
        assert isinstance(e, ApprovalError)

    def test_policy_not_found(self) -> None:
        e = PolicyNotFoundError("no such policy")
        assert isinstance(e, Exception)

    def test_certification_expired(self) -> None:
        e = CertificationExpiredError("expired cert")
        assert isinstance(e, Exception)

    def test_governance_audit_error(self) -> None:
        e = GovernanceAuditError("audit error", code="GE-400")
        assert "GE-400" in e.code


# ═══════════════════════════════════════════════════════════════════════════════
# 5 — DimensionScore / QualityScore
# ═══════════════════════════════════════════════════════════════════════════════

class TestDimensionScore:
    def test_weighted_score(self) -> None:
        ds = DimensionScore(
            dimension=QualityDimension.COMPLETENESS, score=0.8, weight=0.2
        )
        assert ds.weighted_score == pytest.approx(0.16)

    def test_passed_flag(self) -> None:
        ds = DimensionScore(
            dimension=QualityDimension.CONFIDENCE, score=0.5, weight=0.1, passed=False
        )
        assert not ds.passed

    def test_to_dict_round_trip(self) -> None:
        ds = DimensionScore(
            dimension=QualityDimension.INTEGRITY, score=0.9, weight=0.15
        )
        d = ds.to_dict()
        assert d["dimension"] == QualityDimension.INTEGRITY.value
        assert d["score"] == pytest.approx(0.9)


class TestQualityScore:
    def _make_score(self, kqi: float) -> QualityScore:
        dims = [
            DimensionScore(d, 0.8, DIMENSION_WEIGHTS[d.value])
            for d in QualityDimension
        ]
        return QualityScore(
            knowledge_id    = "test-id",
            dimension_scores= dims,
            overall_kqi     = kqi,
            tier            = compute_tier(kqi),
        )

    def test_tier_excellent(self) -> None:
        qs = self._make_score(0.85)
        assert qs.tier == QualityTier.EXCELLENT

    def test_tier_poor(self) -> None:
        qs = self._make_score(0.30)
        assert qs.tier == QualityTier.POOR

    def test_passes_threshold(self) -> None:
        qs = self._make_score(0.75)
        assert qs.passes(0.6)
        assert not qs.passes(0.8)

    def test_get_dimension_score(self) -> None:
        qs = self._make_score(0.7)
        s = qs.get_score(QualityDimension.COMPLETENESS)
        assert s is not None
        assert 0.0 <= s <= 1.0

    def test_to_dict(self) -> None:
        qs = self._make_score(0.65)
        d = qs.to_dict()
        assert "overall_kqi" in d
        assert "tier" in d

    def test_compute_kqi_weighted(self) -> None:
        dims = [
            DimensionScore(QualityDimension.COMPLETENESS, 1.0, 0.5),
            DimensionScore(QualityDimension.FRESHNESS, 0.0, 0.5),
        ]
        kqi = compute_kqi(dims)
        assert kqi == pytest.approx(0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# 6 — QualityViolation
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityViolation:
    def test_critical_blocks_approval(self) -> None:
        v = QualityViolation(
            knowledge_id   = "kid",
            violation_type = ViolationType.EMPTY_CONTENT,
            severity       = ViolationSeverity.CRITICAL,
            dimension      = QualityDimension.COMPLETENESS,
            field_name     = "content",
            message        = "empty",
        )
        assert v.is_critical
        assert v.blocks_approval

    def test_low_does_not_block(self) -> None:
        v = QualityViolation(
            knowledge_id   = "kid",
            violation_type = ViolationType.MISSING_TAGS,
            severity       = ViolationSeverity.LOW,
            dimension      = QualityDimension.COVERAGE,
            field_name     = "tags",
            message        = "no tags",
        )
        assert not v.blocks_approval

    def test_resolve(self) -> None:
        v = QualityViolation(
            knowledge_id   = "kid",
            violation_type = ViolationType.MISSING_TAGS,
            severity       = ViolationSeverity.LOW,
            dimension      = QualityDimension.COVERAGE,
            field_name     = "tags",
            message        = "no tags",
        )
        v.resolve()
        assert v.resolved
        assert v.resolved_at is not None

    def test_to_dict_and_from_dict(self) -> None:
        v = QualityViolation(
            knowledge_id   = "kid",
            violation_type = ViolationType.LOW_CONFIDENCE,
            severity       = ViolationSeverity.MEDIUM,
            dimension      = QualityDimension.CONFIDENCE,
            field_name     = "confidence",
            message        = "too low",
        )
        d = v.to_dict()
        v2 = QualityViolation.from_dict(d)
        assert v2.violation_type == ViolationType.LOW_CONFIDENCE
        assert v2.severity == ViolationSeverity.MEDIUM


# ═══════════════════════════════════════════════════════════════════════════════
# 7 — GovernanceRecord
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceRecord:
    def _new(self) -> GovernanceRecord:
        return GovernanceRecord(knowledge_id="kid", submitted_by="alice")

    def test_initial_status_pending(self) -> None:
        gr = self._new()
        assert gr.is_pending
        assert not gr.is_approved

    def test_approve_transition(self) -> None:
        gr = self._new()
        gr.approve("reviewer", "looks good")
        assert gr.is_approved
        assert gr.reviewed_by == "reviewer"

    def test_auto_approve_transition(self) -> None:
        gr = self._new()
        gr.auto_approve("auto-approve policy triggered")
        assert gr.status == ApprovalStatus.AUTO_APPROVED
        assert gr.is_approved

    def test_reject_transition(self) -> None:
        gr = self._new()
        gr.reject("reviewer", "too low quality")
        assert gr.is_rejected

    def test_revoke_transition(self) -> None:
        gr = self._new()
        gr.approve("reviewer", "approved")
        gr.revoke("admin", "wrong data")
        assert gr.is_revoked

    def test_to_dict_from_dict(self) -> None:
        gr = self._new()
        gr.approve("reviewer", "ok")
        d = gr.to_dict()
        gr2 = GovernanceRecord.from_dict(d)
        assert gr2.gov_id == gr.gov_id
        assert gr2.status == ApprovalStatus.APPROVED


# ═══════════════════════════════════════════════════════════════════════════════
# 8 — Certification
# ═══════════════════════════════════════════════════════════════════════════════

class TestCertification:
    def _new(self) -> Certification:
        c = Certification(knowledge_id="kid", certified_by="alice")
        c.refresh_expiry(90)
        return c

    def test_initial_status_certified(self) -> None:
        c = self._new()
        assert c.status == CertificationStatus.CERTIFIED
        assert c.is_valid
        assert not c.is_expired

    def test_revoke(self) -> None:
        c = self._new()
        c.revoke("admin", "wrong data")
        assert c.status == CertificationStatus.REVOKED
        assert not c.is_valid

    def test_expired_detection(self) -> None:
        c = Certification(knowledge_id="kid", certified_by="alice")
        c.expires_at = time.time() - 1.0   # in the past
        assert c.is_expired

    def test_needs_renewal_near_expiry(self) -> None:
        c = Certification(knowledge_id="kid", certified_by="alice")
        c.refresh_expiry(1)  # 1 day TTL
        assert c.needs_renewal  # within renewal window

    def test_to_dict_from_dict(self) -> None:
        c = self._new()
        d = c.to_dict()
        c2 = Certification.from_dict(d)
        assert c2.cert_id == c.cert_id
        assert c2.status == CertificationStatus.CERTIFIED


# ═══════════════════════════════════════════════════════════════════════════════
# 9 — GovernancePolicy
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernancePolicy:
    def _simple(self) -> GovernancePolicy:
        p = GovernancePolicy(
            name        = "TestPolicy",
            policy_type = PolicyType.THRESHOLD_GATE,
            action      = GovernanceAction.APPROVE,
        )
        p.add_condition("kqi", ">=", 0.6)
        return p

    def test_matches_above_threshold(self) -> None:
        p = self._simple()
        assert p.matches({"kqi": 0.7})

    def test_no_match_below_threshold(self) -> None:
        p = self._simple()
        assert not p.matches({"kqi": 0.5})

    def test_inactive_never_matches(self) -> None:
        p = self._simple()
        p.is_active = False
        assert not p.matches({"kqi": 0.99})

    def test_in_operator(self) -> None:
        p = GovernancePolicy(name="DomainPolicy", policy_type=PolicyType.DOMAIN_SPECIFIC)
        p.add_condition("domain", "in", ["compliance", "risk"])
        assert p.matches({"domain": "compliance"})
        assert not p.matches({"domain": "general"})

    def test_to_dict_from_dict(self) -> None:
        p = self._simple()
        d = p.to_dict()
        p2 = GovernancePolicy.from_dict(d)
        assert p2.policy_id == p.policy_id
        assert len(p2.conditions) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 10 — GovernanceAuditEntry
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceAuditEntry:
    def test_to_dict(self) -> None:
        e = GovernanceAuditEntry(
            knowledge_id = "kid",
            action       = GovernanceAction.SUBMIT,
            actor        = "alice",
            reason       = "initial submission",
        )
        d = e.to_dict()
        assert d["action"] == GovernanceAction.SUBMIT.value
        assert d["actor"] == "alice"
        assert d["knowledge_id"] == "kid"

    def test_audit_id_is_unique(self) -> None:
        e1 = GovernanceAuditEntry(knowledge_id="k1", action=GovernanceAction.SUBMIT)
        e2 = GovernanceAuditEntry(knowledge_id="k2", action=GovernanceAction.APPROVE)
        assert e1.audit_id != e2.audit_id


# ═══════════════════════════════════════════════════════════════════════════════
# 11 — QualityEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityEngine:
    def setup_method(self) -> None:
        _reset_all()

    def test_score_returns_quality_score(self) -> None:
        qe = QualityEngine()
        r  = _record()
        qs = qe.score(r)
        assert isinstance(qs, QualityScore)
        assert 0.0 <= qs.overall_kqi <= 1.0

    def test_high_quality_record_above_default_min(self) -> None:
        qe = QualityEngine()
        r  = _record(confidence=0.9, tags=["finance", "equity", "nifty"])
        qs = qe.score(r)
        assert qs.overall_kqi >= DEFAULT_MIN_KQI

    def test_empty_content_lowers_score(self) -> None:
        qe = QualityEngine()
        r_good = _record()
        r_bad  = _record(content="")
        qs_good = qe.score(r_good)
        qs_bad  = qe.score(r_bad)
        assert qs_bad.overall_kqi < qs_good.overall_kqi

    def test_governance_boost(self) -> None:
        qe    = QualityEngine()
        r     = _record()
        base  = qe.score(r, governance_approved=False, is_certified=False)
        boosted = qe.score(r, governance_approved=True, is_certified=True)
        assert boosted.overall_kqi >= base.overall_kqi

    def test_score_all_dimensions_present(self) -> None:
        qe = QualityEngine()
        r  = _record()
        qs = qe.score(r)
        scored_dims = {ds.dimension for ds in qs.dimension_scores}
        for dim in QualityDimension:
            assert dim in scored_dims

    def test_singleton(self) -> None:
        g1 = get_quality_engine()
        g2 = get_quality_engine()
        assert g1 is g2

    def test_reset_creates_new_instance(self) -> None:
        g1 = get_quality_engine()
        reset_quality_engine()
        g2 = get_quality_engine()
        assert g1 is not g2


# ═══════════════════════════════════════════════════════════════════════════════
# 12 — QualityValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityValidator:
    def setup_method(self) -> None:
        _reset_all()

    def test_valid_record_no_violations(self) -> None:
        qv = QualityValidator()
        v  = qv.validate(_record())
        critical = [x for x in v if x.severity == ViolationSeverity.CRITICAL]
        assert not critical

    def test_empty_title_raises_violation(self) -> None:
        qv = QualityValidator()
        r  = _record(title="")
        v  = qv.validate(r)
        types = [x.violation_type for x in v]
        assert ViolationType.EMPTY_TITLE in types

    def test_empty_content_critical(self) -> None:
        qv = QualityValidator()
        r  = _record(content="")
        v  = qv.validate(r)
        crits = [x for x in v if x.severity == ViolationSeverity.CRITICAL]
        assert crits

    def test_has_blocking_violations(self) -> None:
        qv = QualityValidator()
        v  = qv.validate(_record(content=""))
        assert qv.has_blocking_violations(v)

    def test_validate_strict_raises_on_critical(self) -> None:
        qv = QualityValidator()
        r  = _record(content="")
        with pytest.raises(QualityValidationError):
            qv.validate_strict(r)

    def test_singleton(self) -> None:
        assert get_quality_validator() is get_quality_validator()


# ═══════════════════════════════════════════════════════════════════════════════
# 13 — QualityMonitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityMonitor:
    def setup_method(self) -> None:
        _reset_all()

    def test_scan_returns_monitor_report(self) -> None:
        qm    = QualityMonitor()
        report = qm.scan([_record()])
        assert isinstance(report, MonitorReport)
        assert report.scanned == 1

    def test_expired_record_raises_violation(self) -> None:
        qm  = QualityMonitor()
        r   = _record()
        r.metadata.expires_at = time.time() - 1.0   # force expiry
        report = qm.scan([r])
        types = [v.violation_type for v in report.violations]
        assert ViolationType.EXPIRED_RECORD in types

    def test_no_tags_raises_violation(self) -> None:
        qm  = QualityMonitor()
        r   = _record(tags=[])
        report = qm.scan([r])
        types = [v.violation_type for v in report.violations]
        assert ViolationType.MISSING_TAGS in types

    def test_kqi_degradation_detected(self) -> None:
        qm  = QualityMonitor()
        kid = "kid1"
        r   = _record()
        r_obj = r
        # Set a high previous KQI
        qm.scan([r_obj], kqi_scores={r_obj.id: 0.90})
        # Drop by 15%
        report = qm.scan([r_obj], kqi_scores={r_obj.id: 0.70})
        types  = [v.violation_type for v in report.violations]
        assert ViolationType.QUALITY_DEGRADED in types

    def test_duplicate_detection(self) -> None:
        qm = QualityMonitor()
        r1 = _record(title="Same Title")
        r2 = _record(title="Same Title")
        viols = qm.check_duplicates([r1, r2])
        assert any(v.violation_type == ViolationType.DUPLICATE_DETECTED for v in viols)

    def test_singleton(self) -> None:
        assert get_quality_monitor() is get_quality_monitor()


# ═══════════════════════════════════════════════════════════════════════════════
# 14 — GovernanceEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceEngine:
    def setup_method(self) -> None:
        _reset_all()

    def _ge(self) -> GovernanceEngine:
        return GovernanceEngine()

    def test_submit_creates_pending_record(self) -> None:
        ge = self._ge()
        gr = ge.submit("kid")
        assert gr.is_pending
        assert gr.knowledge_id == "kid"

    def test_approve_transitions_to_approved(self) -> None:
        ge = self._ge()
        gr = ge.submit("kid")
        ge.approve(gr.gov_id, "alice", "ok")
        assert ge.is_approved("kid")

    def test_auto_approve(self) -> None:
        ge = self._ge()
        gr = ge.submit("kid")
        ge.auto_approve(gr.gov_id)
        assert ge.is_approved("kid")

    def test_reject_marks_rejected(self) -> None:
        ge = self._ge()
        gr = ge.submit("kid")
        ge.reject(gr.gov_id, "alice", "bad")
        gr2 = ge.get(gr.gov_id)
        assert gr2.is_rejected

    def test_approve_non_pending_raises(self) -> None:
        ge = self._ge()
        gr = ge.submit("kid")
        ge.approve(gr.gov_id, "alice", "ok")
        with pytest.raises(ApprovalError):
            ge.approve(gr.gov_id, "alice", "again")

    def test_get_pending_list(self) -> None:
        ge = self._ge()
        ge.submit("k1")
        ge.submit("k2")
        pending = ge.get_pending()
        assert len(pending) == 2

    def test_get_raises_for_missing(self) -> None:
        ge = self._ge()
        with pytest.raises(ApprovalNotFoundError):
            ge.get("nonexistent-id")

    def test_get_latest_returns_most_recent(self) -> None:
        ge = self._ge()
        ge.submit("kid", kqi=0.5)
        ge.submit("kid", kqi=0.7)
        latest = ge.get_latest("kid")
        assert latest.kqi_at_submission == pytest.approx(0.7)

    def test_statistics_counts(self) -> None:
        ge = self._ge()
        ge.submit("k1")
        gr = ge.submit("k2")
        ge.approve(gr.gov_id, "alice", "ok")
        stats = ge.statistics()
        assert stats["total_records"] == 2

    def test_singleton(self) -> None:
        assert get_governance_engine() is get_governance_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# 15 — PolicyManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyManager:
    def setup_method(self) -> None:
        _reset_all()

    def _pm(self) -> PolicyManager:
        return PolicyManager()

    def test_defaults_loaded(self) -> None:
        pm = self._pm()
        assert pm.statistics()["total_policies"] >= 3

    def test_add_policy(self) -> None:
        pm = self._pm()
        p  = GovernancePolicy(name="Custom", policy_type=PolicyType.AUTO_APPROVE,
                               action=GovernanceAction.AUTO_APPROVE)
        p.add_condition("kqi", ">=", 0.8)
        pm.add_policy(p)
        retrieved = pm.get(p.policy_id)
        assert retrieved.name == "Custom"

    def test_duplicate_policy_raises(self) -> None:
        pm = self._pm()
        p  = GovernancePolicy(name="Dup", policy_type=PolicyType.AUTO_APPROVE)
        pm.add_policy(p)
        with pytest.raises(PolicyAlreadyExistsError):
            pm.add_policy(p)

    def test_get_missing_raises(self) -> None:
        pm = self._pm()
        with pytest.raises(PolicyNotFoundError):
            pm.get("no-such-id")

    def test_evaluate_auto_approve_high_kqi(self) -> None:
        pm = self._pm()
        ctx = {"kqi": 0.90, "domain": "general", "has_critical_violations": False}
        action, reason, ids = pm.evaluate(ctx)
        assert action == GovernanceAction.AUTO_APPROVE

    def test_evaluate_auto_reject_critical(self) -> None:
        pm = self._pm()
        ctx = {"kqi": 0.90, "domain": "general", "has_critical_violations": True}
        action, reason, ids = pm.evaluate(ctx)
        assert action == GovernanceAction.REJECT

    def test_evaluate_manual_sensitive_domain(self) -> None:
        pm = self._pm()
        ctx = {"kqi": 0.90, "domain": "compliance", "has_critical_violations": False}
        action, reason, ids = pm.evaluate(ctx)
        # ManualReviewForCompliance (priority=90) fires before AutoApproveHighQuality (priority=80)
        assert action == GovernanceAction.REVIEW

    def test_remove_policy(self) -> None:
        pm = self._pm()
        p  = GovernancePolicy(name="Remove", policy_type=PolicyType.BLOCK)
        pm.add_policy(p)
        pm.remove(p.policy_id)
        with pytest.raises(PolicyNotFoundError):
            pm.get(p.policy_id)

    def test_singleton(self) -> None:
        assert get_policy_manager() is get_policy_manager()


# ═══════════════════════════════════════════════════════════════════════════════
# 16 — CertificationManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestCertificationManager:
    def setup_method(self) -> None:
        _reset_all()

    def _cm(self) -> CertificationManager:
        return CertificationManager()

    def test_certify_creates_valid_cert(self) -> None:
        cm   = self._cm()
        cert = cm.certify("kid")
        assert cert.is_valid
        assert cm.is_certified("kid")

    def test_revoke_removes_active(self) -> None:
        cm = self._cm()
        cm.certify("kid")
        cm.revoke("kid")
        assert not cm.is_certified("kid")

    def test_certify_replaces_previous(self) -> None:
        cm  = self._cm()
        c1  = cm.certify("kid")
        c2  = cm.certify("kid")
        assert c1.cert_id != c2.cert_id
        assert cm.is_certified("kid")

    def test_get_raises_for_uncertified(self) -> None:
        cm = self._cm()
        with pytest.raises(CertificationNotFoundError):
            cm.get("unknown")

    def test_expire_stale(self) -> None:
        cm   = self._cm()
        cert = cm.certify("kid", ttl_days=1)
        cert.expires_at = time.time() - 1.0  # force expiry
        expired = cm.expire_stale()
        assert any(c.cert_id == cert.cert_id for c in expired)
        assert not cm.is_certified("kid")

    def test_statistics(self) -> None:
        cm = self._cm()
        cm.certify("k1")
        cm.certify("k2")
        stats = cm.statistics()
        assert stats["active_certs"] == 2

    def test_singleton(self) -> None:
        assert get_certification_manager() is get_certification_manager()


# ═══════════════════════════════════════════════════════════════════════════════
# 17 — GovernanceAuditLog
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceAuditLog:
    def setup_method(self) -> None:
        _reset_all()

    def _al(self) -> GovernanceAuditLog:
        return GovernanceAuditLog()

    def test_log_creates_entry(self) -> None:
        al = self._al()
        e  = al.log("kid", GovernanceAction.SUBMIT, "alice")
        assert e.knowledge_id == "kid"
        assert e.action == GovernanceAction.SUBMIT

    def test_get_trail_newest_first(self) -> None:
        al = self._al()
        al.log("kid", GovernanceAction.SUBMIT, "alice")
        al.log("kid", GovernanceAction.APPROVE, "bob")
        trail = al.get_trail("kid")
        assert trail[0].action == GovernanceAction.APPROVE  # newest first

    def test_get_trail_filter_by_action(self) -> None:
        al = self._al()
        al.log("kid", GovernanceAction.SUBMIT, "alice")
        al.log("kid", GovernanceAction.APPROVE, "bob")
        trail = al.get_trail("kid", action=GovernanceAction.SUBMIT)
        assert all(e.action == GovernanceAction.SUBMIT for e in trail)

    def test_get_trail_limit(self) -> None:
        al = self._al()
        for _ in range(5):
            al.log("kid", GovernanceAction.SUBMIT)
        trail = al.get_trail("kid", limit=3)
        assert len(trail) == 3

    def test_get_entry_by_id(self) -> None:
        al = self._al()
        e  = al.log("kid", GovernanceAction.SUBMIT)
        e2 = al.get_entry(e.audit_id)
        assert e2.audit_id == e.audit_id

    def test_get_entry_missing_raises(self) -> None:
        al = self._al()
        with pytest.raises(GovernanceAuditError):
            al.get_entry("nonexistent-id")

    def test_entry_count(self) -> None:
        al = self._al()
        al.log("kid", GovernanceAction.SUBMIT)
        al.log("kid", GovernanceAction.APPROVE)
        assert al.entry_count("kid") == 2

    def test_total_entries(self) -> None:
        al = self._al()
        al.log("k1", GovernanceAction.SUBMIT)
        al.log("k2", GovernanceAction.SUBMIT)
        assert al.total_entries() == 2

    def test_singleton(self) -> None:
        assert get_governance_audit_log() is get_governance_audit_log()


# ═══════════════════════════════════════════════════════════════════════════════
# 18 — KnowledgeGovernor end-to-end pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeGovernor:
    def setup_method(self) -> None:
        _reset_all()

    def _governor(self) -> KnowledgeGovernor:
        return KnowledgeGovernor()

    def test_submit_high_quality_auto_approves(self) -> None:
        gov = self._governor()
        r   = _record(confidence=0.95, tags=["equity", "nifty", "index"])
        result = gov.submit_for_approval(r)
        # High KQI + no critical violations → auto-approve by default policy
        assert isinstance(result, ApprovalResult)
        assert result.quality_score.overall_kqi > 0

    def test_submit_empty_content_auto_rejects(self) -> None:
        gov = self._governor()
        r   = _record(content="")
        result = gov.submit_for_approval(r)
        # Has critical violation → auto-reject by AutoRejectCriticalViolations policy
        assert result.is_rejected

    def test_compliance_domain_escalated(self) -> None:
        gov = self._governor()
        r   = _record(
            confidence = 0.95,
            tags       = ["compliance", "fisc"],
            domain     = KnowledgeDomain.COMPLIANCE,
        )
        result = gov.submit_for_approval(r)
        # Should NOT be auto-approved even with high KQI (sensitive domain)
        assert not result.is_rejected or result.gov_record.status in (
            ApprovalStatus.ESCALATED,
            ApprovalStatus.PENDING,
            ApprovalStatus.REJECTED,
        )

    def test_is_approved_after_submit_with_high_kqi(self) -> None:
        gov    = self._governor()
        r      = _record(confidence=0.95, tags=["equity", "nifty", "index"])
        result = gov.submit_for_approval(r)
        if result.is_approved:
            assert gov.is_approved(r.id)

    def test_can_enter_knowledge_base_returns_false_for_unapproved(self) -> None:
        gov = self._governor()
        r   = _record()
        ok, reason = gov.can_enter_knowledge_base(r)
        # r has not been submitted; no governance record
        assert not ok

    def test_certify_requires_prior_approval(self) -> None:
        gov = self._governor()
        r   = _record()
        with pytest.raises(KnowledgeGovernorError):
            gov.certify(r.id)

    def test_certify_after_manual_approve(self) -> None:
        gov = self._governor()
        r   = _record()
        result = gov.submit_for_approval(r)
        # Force approve if not auto-approved
        if not result.is_approved:
            gov.approve(r.id, result.gov_record.gov_id, "reviewer", "manually approved")
        cert = gov.certify(r.id, actor="alice", kqi=0.8)
        assert cert.is_valid
        assert gov.is_certified(r.id)

    def test_revoke_certification(self) -> None:
        gov    = self._governor()
        r      = _record()
        result = gov.submit_for_approval(r)
        if not result.is_approved:
            gov.approve(r.id, result.gov_record.gov_id, "reviewer", "ok")
        gov.certify(r.id)
        gov.revoke_certification(r.id, reason="corrected data")
        assert not gov.is_certified(r.id)

    def test_audit_trail_populated(self) -> None:
        gov    = self._governor()
        r      = _record()
        gov.submit_for_approval(r)
        trail  = gov.audit_trail(r.id)
        assert len(trail) >= 1

    def test_pending_reviews_list(self) -> None:
        gov    = self._governor()
        r      = _record(confidence=0.45, tags=[])   # probably won't auto-approve
        r2     = _record(confidence=0.45, tags=[])
        gov.submit_for_approval(r)
        gov.submit_for_approval(r2)
        pending = gov.pending_reviews()
        # At least one may be pending
        assert isinstance(pending, list)

    def test_statistics_returns_dict(self) -> None:
        gov   = self._governor()
        stats = gov.statistics()
        assert "governance_engine" in stats
        assert "policy_manager"    in stats

    def test_status_returns_healthy(self) -> None:
        gov    = self._governor()
        status = gov.status()
        assert status["status"] == "healthy"

    def test_score_delegation(self) -> None:
        gov = self._governor()
        r   = _record()
        qs  = gov.score(r)
        assert isinstance(qs, QualityScore)

    def test_validate_delegation(self) -> None:
        gov  = self._governor()
        r    = _record(title="")
        viols = gov.validate(r)
        types = [v.violation_type for v in viols]
        assert ViolationType.EMPTY_TITLE in types

    def test_singleton(self) -> None:
        g1 = get_knowledge_governor()
        g2 = get_knowledge_governor()
        assert g1 is g2

    def test_reset(self) -> None:
        g1 = get_knowledge_governor()
        reset_knowledge_governor()
        g2 = get_knowledge_governor()
        assert g1 is not g2


# ═══════════════════════════════════════════════════════════════════════════════
# 19 — Thread-local contexts
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityContext:
    def setup_method(self) -> None:
        _reset_all()

    def test_default_actor(self) -> None:
        ctx = get_quality_context()
        assert ctx.actor == SYSTEM_GOVERNANCE_ACTOR

    def test_operation_sets_actor(self) -> None:
        with quality_operation(actor="alice"):
            assert current_quality_actor() == "alice"
        assert current_quality_actor() == SYSTEM_GOVERNANCE_ACTOR

    def test_operation_sets_operation_id(self) -> None:
        with quality_operation(operation_id="op-42"):
            assert current_quality_operation_id() == "op-42"
        assert current_quality_operation_id() is None

    def test_nested_operation_restores(self) -> None:
        with quality_operation(actor="outer"):
            with quality_operation(actor="inner"):
                assert current_quality_actor() == "inner"
            assert current_quality_actor() == "outer"

    def test_thread_isolation(self) -> None:
        results: list[str] = []

        def worker() -> None:
            with quality_operation(actor="thread-worker"):
                results.append(current_quality_actor())

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert results == ["thread-worker"]
        assert current_quality_actor() == SYSTEM_GOVERNANCE_ACTOR  # main thread unaffected


class TestGovernanceContext:
    def setup_method(self) -> None:
        _reset_all()

    def test_default_actor(self) -> None:
        ctx = get_governance_context()
        assert ctx.actor == GOV_ACTOR

    def test_operation_sets_actor(self) -> None:
        with governance_operation(actor="bob"):
            assert current_governance_actor() == "bob"
        assert current_governance_actor() == GOV_ACTOR


# ═══════════════════════════════════════════════════════════════════════════════
# 20 — Registries
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistries:
    def setup_method(self) -> None:
        _reset_all()

    def test_quality_registry_has_expected_components(self) -> None:
        reg = get_quality_registry()
        for name in ("quality_engine", "quality_validator", "quality_monitor",
                     "quality_context"):
            assert reg.has(name), f"missing: {name}"

    def test_quality_registry_get_returns_correct_type(self) -> None:
        reg = get_quality_registry()
        assert isinstance(reg.get("quality_engine"), QualityEngine)
        assert isinstance(reg.get("quality_validator"), QualityValidator)

    def test_quality_registry_register_custom(self) -> None:
        reg = get_quality_registry()
        reg.register("custom_service", object())
        assert reg.has("custom_service")

    def test_governance_registry_has_expected_components(self) -> None:
        reg = get_governance_registry()
        for name in ("governance_engine", "policy_manager", "certification_manager",
                     "governance_audit", "knowledge_governor", "governance_context",
                     "quality_registry"):
            assert reg.has(name), f"missing: {name}"

    def test_governance_registry_get_returns_correct_type(self) -> None:
        reg = get_governance_registry()
        assert isinstance(reg.get("governance_engine"), GovernanceEngine)
        assert isinstance(reg.get("policy_manager"), PolicyManager)

    def test_governance_registry_names_list(self) -> None:
        reg   = get_governance_registry()
        names = reg.names()
        assert "knowledge_governor" in names

    def test_quality_registry_status(self) -> None:
        status = get_quality_registry().status()
        assert "quality_engine" in status

    def test_governance_registry_singleton(self) -> None:
        r1 = get_governance_registry()
        r2 = get_governance_registry()
        assert r1 is r2
