"""iios/decision_governance/compliance/compliance_result.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class ComplianceViolation:
    violation_id: str   = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id:      str   = ""
    rule_name:    str   = ""
    message:      str   = ""
    is_blocking:  bool  = True
    timestamp:    float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "rule_id":      self.rule_id,
            "rule_name":    self.rule_name,
            "message":      self.message,
            "is_blocking":  self.is_blocking,
            "timestamp":    self.timestamp,
        }


@dataclass
class ComplianceResult:
    result_id:    str                    = field(default_factory=lambda: str(uuid.uuid4()))
    subject_id:   str                    = ""
    rules_checked: int                   = 0
    violations:   list[ComplianceViolation] = field(default_factory=list)
    passed:       bool                   = True
    generated_at: float                  = field(default_factory=time.time)

    @property
    def blocking_violations(self) -> int:
        return sum(1 for v in self.violations if v.is_blocking)

    def to_dict(self) -> dict:
        return {
            "result_id":           self.result_id,
            "subject_id":          self.subject_id,
            "rules_checked":       self.rules_checked,
            "violations":          [v.to_dict() for v in self.violations],
            "blocking_violations": self.blocking_violations,
            "passed":              self.passed,
            "generated_at":        self.generated_at,
        }
