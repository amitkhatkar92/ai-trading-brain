"""iios/decision_policies/rules/rule_result.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..policy_constants import GroupOperator, RuleStatus, RuleType


@dataclass
class RuleResult:
    rule_id:      str
    rule_name:    str
    rule_type:    RuleType    = RuleType.STATIC
    status:       RuleStatus  = RuleStatus.PASS
    reason:       str         = ""
    score:        float       = 1.0
    duration_ms:  float       = 0.0
    metadata:     dict        = field(default_factory=dict)
    evaluated_at: float       = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.status in (RuleStatus.PASS, RuleStatus.SKIP)

    @property
    def failed(self) -> bool:
        return self.status == RuleStatus.FAIL

    @property
    def warned(self) -> bool:
        return self.status == RuleStatus.WARN

    def to_dict(self) -> dict:
        return {
            "rule_id":      self.rule_id,
            "rule_name":    self.rule_name,
            "rule_type":    self.rule_type.value,
            "status":       self.status.value,
            "reason":       self.reason,
            "score":        self.score,
            "duration_ms":  self.duration_ms,
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class RuleGroupResult:
    group_id:    str         = field(default_factory=lambda: str(uuid.uuid4()))
    group_name:  str         = ""
    operator:    GroupOperator = GroupOperator.AND
    results:     list[RuleResult] = field(default_factory=list)
    status:      RuleStatus  = RuleStatus.PASS
    score:       float       = 1.0
    duration_ms: float       = 0.0
    evaluated_at: float      = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.status in (RuleStatus.PASS, RuleStatus.SKIP)

    def to_dict(self) -> dict:
        return {
            "group_id":    self.group_id,
            "group_name":  self.group_name,
            "operator":    self.operator.value,
            "status":      self.status.value,
            "score":       self.score,
            "duration_ms": self.duration_ms,
            "result_count": len(self.results),
        }
