"""iios/investment/decision/risk/risk_snapshot.py
RiskSnapshot — immutable, versioned, canonical risk output.
All downstream engines consume ONLY this object.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.decision.risk.decision_risk import DecisionRisk
from iios.investment.decision.risk.risk_constants import (
    RiskLevel,
    RiskPolicyStatus,
    RiskQualityGrade,
)


@dataclass(frozen=True)
class RiskSnapshot:
    """
    Canonical, immutable, versioned risk assessment for one decision.
    Does NOT contain investment recommendations or trading instructions.
    """
    snapshot_id:           str
    decision_id:           str
    subject_id:            str
    subject_type:          str
    version:               int
    evidence_snapshot_id:  str
    reasoning_snapshot_id: str
    confidence_snapshot_id: str
    decision_risk:         DecisionRisk
    overall_risk:          float             # 0–100 fast-access copy
    risk_level:            RiskLevel
    policy_status:         RiskPolicyStatus
    quality_grade:         RiskQualityGrade
    is_usable:             bool              # passes policies + below critical
    evaluation_duration_ms: float
    created_at:            datetime

    @property
    def is_elevated(self) -> bool:
        return self.overall_risk >= 60.0

    @property
    def blocks_execution(self) -> bool:
        return (
            self.decision_risk.blocks_execution
            or self.policy_status == RiskPolicyStatus.VIOLATION
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":             self.snapshot_id,
            "decision_id":             self.decision_id,
            "subject_id":              self.subject_id,
            "subject_type":            self.subject_type,
            "version":                 self.version,
            "evidence_snapshot_id":    self.evidence_snapshot_id,
            "reasoning_snapshot_id":   self.reasoning_snapshot_id,
            "confidence_snapshot_id":  self.confidence_snapshot_id,
            "overall_risk":            round(self.overall_risk, 2),
            "risk_level":              self.risk_level.value,
            "policy_status":           self.policy_status.value,
            "quality_grade":           self.quality_grade.value,
            "is_usable":               self.is_usable,
            "blocks_execution":        self.blocks_execution,
            "evaluation_duration_ms":  round(self.evaluation_duration_ms, 2),
            "created_at":              self.created_at.isoformat(),
            "decision_risk":           self.decision_risk.to_dict(),
        }


def build_risk_snapshot(
    decision_risk:          DecisionRisk,
    evidence_snapshot_id:   str,
    reasoning_snapshot_id:  str,
    confidence_snapshot_id: str,
    policy_status:          RiskPolicyStatus,
    quality_grade:          RiskQualityGrade,
    evaluation_start:       datetime,
    version:                int,
) -> RiskSnapshot:
    now = datetime.now(timezone.utc)
    duration_ms = (now - evaluation_start).total_seconds() * 1000.0

    is_usable = (
        decision_risk.risk_level != RiskLevel.CRITICAL
        and policy_status != RiskPolicyStatus.VIOLATION
    )

    return RiskSnapshot(
        snapshot_id=str(uuid.uuid4()),
        decision_id=decision_risk.decision_id,
        subject_id=decision_risk.subject_id,
        subject_type=decision_risk.subject_type,
        version=version,
        evidence_snapshot_id=evidence_snapshot_id,
        reasoning_snapshot_id=reasoning_snapshot_id,
        confidence_snapshot_id=confidence_snapshot_id,
        decision_risk=decision_risk,
        overall_risk=decision_risk.overall_risk,
        risk_level=decision_risk.risk_level,
        policy_status=policy_status,
        quality_grade=quality_grade,
        is_usable=is_usable,
        evaluation_duration_ms=round(duration_ms, 2),
        created_at=now,
    )
