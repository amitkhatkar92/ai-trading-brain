"""
iios/knowledge/governance/knowledge_governor.py
================================================
KnowledgeGovernor — the master façade and authoritative gateway for all
knowledge entering, changing, or leaving the IIOS Knowledge Layer.

No knowledge record may be stored in the knowledge base unless the
Governor has approved it.  The Governor coordinates the full pipeline:

  validate → score → policy_evaluate → (auto/manual) approve → certify

Usage::

    from iios.knowledge.governance.knowledge_governor import get_knowledge_governor

    gov    = get_knowledge_governor()
    result = gov.submit_for_approval(record, actor="user:alice")
    if result.gov_record.is_approved:
        # safe to persist the record
        knowledge_engine.store(record)
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from ..knowledge_constants import KnowledgeStatus
from ..models.knowledge_record import KnowledgeRecord
from .governance_constants import (
    ApprovalStatus,
    CertificationLevel,
    DEFAULT_CERTIFICATION_TTL_DAYS,
    GovernanceAction,
    SENSITIVE_DOMAINS,
    SYSTEM_GOVERNANCE_ACTOR,
)
from .quality_constants import (
    DEFAULT_MIN_KQI,
    SYSTEM_GOVERNANCE_ACTOR as _SGA,
)
from .governance_exceptions import KnowledgeGovernorError
from .quality_engine        import QualityEngine, get_quality_engine
from .quality_validator     import QualityValidator, get_quality_validator
from .quality_monitor       import QualityMonitor, get_quality_monitor
from .governance_engine     import GovernanceEngine, get_governance_engine
from .policy_manager        import PolicyManager, get_policy_manager
from .certification_manager import CertificationManager, get_certification_manager
from .governance_audit      import GovernanceAuditLog, get_governance_audit_log
from .models.quality_score      import QualityScore
from .models.quality_violation  import QualityViolation
from .models.governance_record  import GovernanceRecord
from .models.certification      import Certification
from .models.governance_audit   import GovernanceAuditEntry

__all__ = [
    "ApprovalResult",
    "KnowledgeGovernor",
    "get_knowledge_governor",
    "reset_knowledge_governor",
]

_LOG = logging.getLogger("iios.knowledge.governance.governor")
_lock = threading.Lock()
_governor: Optional["KnowledgeGovernor"] = None


@dataclass
class ApprovalResult:
    """Return value from ``submit_for_approval``."""

    quality_score:   QualityScore
    gov_record:      GovernanceRecord
    violations:      list[QualityViolation] = field(default_factory=list)
    auto_decided:    bool = False
    decision_reason: str  = ""

    @property
    def is_approved(self) -> bool:
        return self.gov_record.is_approved

    @property
    def is_rejected(self) -> bool:
        return self.gov_record.is_rejected

    @property
    def is_pending(self) -> bool:
        return self.gov_record.is_pending


class KnowledgeGovernor:
    """Master knowledge governance façade.

    All subsystems are injected at construction so they can be replaced
    for testing; module-level singletons are used as defaults.
    """

    def __init__(
        self,
        quality_engine:        Optional[QualityEngine]        = None,
        quality_validator:     Optional[QualityValidator]     = None,
        quality_monitor:       Optional[QualityMonitor]       = None,
        governance_engine:     Optional[GovernanceEngine]     = None,
        policy_manager:        Optional[PolicyManager]        = None,
        certification_manager: Optional[CertificationManager] = None,
        audit_log:             Optional[GovernanceAuditLog]   = None,
        min_kqi:               float = DEFAULT_MIN_KQI,
    ) -> None:
        self._qe   = quality_engine        or get_quality_engine()
        self._qv   = quality_validator     or get_quality_validator()
        self._qm   = quality_monitor       or get_quality_monitor()
        self._ge   = governance_engine     or get_governance_engine()
        self._pm   = policy_manager        or get_policy_manager()
        self._cm   = certification_manager or get_certification_manager()
        self._al   = audit_log             or get_governance_audit_log()
        self._min_kqi = min_kqi

    # ── Primary gateway ───────────────────────────────────────────────────────

    def submit_for_approval(
        self,
        record: KnowledgeRecord,
        actor:  str = SYSTEM_GOVERNANCE_ACTOR,
        reason: str = "",
    ) -> ApprovalResult:
        """Full governance pipeline: validate → score → policy → decide.

        Returns an ApprovalResult.  Auto-approve or auto-reject may be
        triggered by policy; otherwise the record is left PENDING for
        manual review.
        """
        # 1 — Validate
        violations = self._qv.validate(record)
        has_critical = self._qv.has_blocking_violations(violations)

        # 2 — Score (with current approval/cert state)
        is_certified = self._cm.is_certified(record.id)
        is_approved  = self._ge.is_approved(record.id)
        qs = self._qe.score(
            record,
            governance_approved = is_approved,
            is_certified        = is_certified,
        )

        # 3 — Build policy evaluation context
        context: dict[str, Any] = {
            "kqi":                    qs.overall_kqi,
            "knowledge_type":         record.knowledge_type.value,
            "domain":                 record.metadata.domain.value,
            "source":                 record.metadata.source.value,
            "status":                 record.status.value,
            "confidence":             record.metadata.confidence,
            "has_critical_violations":has_critical,
            "is_deleted":             record.is_deleted,
        }

        action, policy_reason, policy_ids = self._pm.evaluate(context)

        # 4 — Submit governance record
        gr = self._ge.submit(
            knowledge_id     = record.id,
            submitted_by     = actor,
            kqi              = qs.overall_kqi,
            violations_count = len(violations),
            notes            = reason,
        )
        self._ge.attach_policies(gr.gov_id, policy_ids)

        # 5 — Apply policy action
        auto_decided = False
        decision_reason = policy_reason

        if action == GovernanceAction.REJECT:
            self._ge.reject(gr.gov_id, SYSTEM_GOVERNANCE_ACTOR,
                            f"Auto-rejected by policy: {policy_reason}")
            auto_decided = True
            # Flag record as invalid
            record.status = KnowledgeStatus.INVALID
        elif action == GovernanceAction.AUTO_APPROVE:
            # Extra guard: never auto-approve if domain is sensitive
            if record.metadata.domain.value in SENSITIVE_DOMAINS:
                self._ge.escalate(gr.gov_id, "Sensitive domain — escalated for manual review")
                decision_reason = "Auto-approve blocked: sensitive domain"
            else:
                self._ge.auto_approve(
                    gr.gov_id,
                    f"Auto-approved by policy '{policy_reason}' (KQI={qs.overall_kqi:.2f})"
                )
                auto_decided    = True
                record.status   = KnowledgeStatus.ACTIVE
        # else: REQUIRE_MANUAL / BLOCK / None → stays PENDING

        # 6 — Audit
        self._al.log(
            knowledge_id  = record.id,
            action        = GovernanceAction.SUBMIT,
            actor         = actor,
            reason        = reason,
            gov_record_id = gr.gov_id,
            kqi_before    = None,
            kqi_after     = qs.overall_kqi,
            details       = {
                "policy_ids": policy_ids,
                "action":     action.value if action else "none",
                "violations": len(violations),
            },
        )

        _LOG.info(
            "KnowledgeGovernor: submitted '%s' → status=%s kqi=%.2f",
            record.id[:16], gr.status.value, qs.overall_kqi,
        )

        return ApprovalResult(
            quality_score   = qs,
            gov_record      = gr,
            violations      = violations,
            auto_decided    = auto_decided,
            decision_reason = decision_reason,
        )

    # ── Manual decisions ──────────────────────────────────────────────────────

    def approve(
        self,
        knowledge_id: str,
        gov_id:       str,
        actor:        str = SYSTEM_GOVERNANCE_ACTOR,
        reason:       str = "",
    ) -> GovernanceRecord:
        gr = self._ge.approve(gov_id, actor, reason)
        # Optionally activate the record via record repository — here just audit
        self._al.log(
            knowledge_id  = knowledge_id,
            action        = GovernanceAction.APPROVE,
            actor         = actor,
            reason        = reason,
            gov_record_id = gov_id,
        )
        return gr

    def reject(
        self,
        knowledge_id: str,
        gov_id:       str,
        actor:        str = SYSTEM_GOVERNANCE_ACTOR,
        reason:       str = "",
    ) -> GovernanceRecord:
        gr = self._ge.reject(gov_id, actor, reason)
        self._al.log(
            knowledge_id  = knowledge_id,
            action        = GovernanceAction.REJECT,
            actor         = actor,
            reason        = reason,
            gov_record_id = gov_id,
        )
        return gr

    def revoke_approval(
        self,
        knowledge_id: str,
        gov_id:       str,
        actor:        str = SYSTEM_GOVERNANCE_ACTOR,
        reason:       str = "",
    ) -> GovernanceRecord:
        gr = self._ge.revoke(gov_id, actor, reason)
        self._al.log(
            knowledge_id  = knowledge_id,
            action        = GovernanceAction.REVOKE_APPROVAL,
            actor         = actor,
            reason        = reason,
            gov_record_id = gov_id,
        )
        return gr

    # ── Certification ─────────────────────────────────────────────────────────

    def certify(
        self,
        knowledge_id: str,
        actor:        str              = SYSTEM_GOVERNANCE_ACTOR,
        level:        CertificationLevel = CertificationLevel.STANDARD,
        ttl_days:     int              = DEFAULT_CERTIFICATION_TTL_DAYS,
        notes:        str              = "",
        kqi:          float            = 0.0,
    ) -> Certification:
        # Require prior approval
        gr = self._ge.get_approved(knowledge_id)
        if gr is None:
            raise KnowledgeGovernorError(
                f"Cannot certify '{knowledge_id}' — no approved governance record.",
                code="GE-900",
            )
        cert = self._cm.certify(
            knowledge_id = knowledge_id,
            certified_by = actor,
            level        = level,
            ttl_days     = ttl_days,
            notes        = notes,
            kqi          = kqi or gr.kqi_at_submission,
            gov_id       = gr.gov_id,
        )
        self._al.log(
            knowledge_id = knowledge_id,
            action       = GovernanceAction.CERTIFY,
            actor        = actor,
            cert_id      = cert.cert_id,
            details      = {"level": level.value, "ttl_days": ttl_days},
        )
        return cert

    def revoke_certification(
        self,
        knowledge_id: str,
        actor:        str = SYSTEM_GOVERNANCE_ACTOR,
        reason:       str = "",
    ) -> Certification:
        cert = self._cm.revoke(knowledge_id, actor, reason)
        self._al.log(
            knowledge_id = knowledge_id,
            action       = GovernanceAction.REVOKE_CERT,
            actor        = actor,
            reason       = reason,
            cert_id      = cert.cert_id,
        )
        return cert

    # ── Quality checks ────────────────────────────────────────────────────────

    def score(
        self,
        record: KnowledgeRecord,
    ) -> QualityScore:
        is_approved  = self._ge.is_approved(record.id)
        is_certified = self._cm.is_certified(record.id)
        return self._qe.score(record,
                               governance_approved=is_approved,
                               is_certified=is_certified)

    def validate(self, record: KnowledgeRecord) -> list[QualityViolation]:
        return self._qv.validate(record)

    def monitor(
        self,
        records: list[KnowledgeRecord],
        kqi_scores: Optional[dict[str, float]] = None,
    ):
        return self._qm.scan(records, kqi_scores=kqi_scores)

    def can_enter_knowledge_base(
        self,
        record: KnowledgeRecord,
    ) -> tuple[bool, str]:
        """Quick gate check: is this record already approved?"""
        if record.is_deleted:
            return False, "record is deleted"
        if record.status == KnowledgeStatus.INVALID:
            return False, "record status is INVALID"
        if self._ge.is_approved(record.id):
            return True, "approved"
        return False, "not yet approved by governance"

    # ── State queries ─────────────────────────────────────────────────────────

    def is_approved(self, knowledge_id: str) -> bool:
        return self._ge.is_approved(knowledge_id)

    def is_certified(self, knowledge_id: str) -> bool:
        return self._cm.is_certified(knowledge_id)

    def get_governance_record(self, knowledge_id: str) -> Optional[GovernanceRecord]:
        return self._ge.get_latest(knowledge_id)

    def get_certification(self, knowledge_id: str) -> Optional[Certification]:
        try:
            return self._cm.get(knowledge_id)
        except Exception:
            return None

    def pending_reviews(self) -> list[GovernanceRecord]:
        return self._ge.get_pending()

    # ── Audit ─────────────────────────────────────────────────────────────────

    def audit_trail(
        self,
        knowledge_id: str,
        action: Optional[GovernanceAction] = None,
        limit:  Optional[int] = None,
    ) -> list[GovernanceAuditEntry]:
        return self._al.get_trail(knowledge_id, action=action, limit=limit)

    # ── Statistics & status ───────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        return {
            "governance_engine":     self._ge.statistics(),
            "policy_manager":        self._pm.statistics(),
            "certification_manager": self._cm.statistics(),
            "audit_log":             self._al.statistics(),
            "quality_monitor":       self._qm.statistics(),
        }

    def status(self) -> dict[str, Any]:
        s = self.statistics()
        return {
            "status":              "healthy",
            "total_gov_records":   s["governance_engine"]["total_records"],
            "pending_reviews":     s["governance_engine"]["pending"],
            "active_policies":     s["policy_manager"]["active_policies"],
            "active_certs":        s["certification_manager"]["active_certs"],
            "total_audit_entries": s["audit_log"]["total_entries"],
        }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_knowledge_governor() -> KnowledgeGovernor:
    global _governor
    if _governor is None:
        with _lock:
            if _governor is None:
                _governor = KnowledgeGovernor()
    return _governor


def reset_knowledge_governor() -> None:
    global _governor
    with _lock:
        _governor = None
