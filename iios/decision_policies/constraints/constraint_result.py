"""iios/decision_policies/constraints/constraint_result.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..policy_constants import ConstraintType


@dataclass
class ConstraintResult:
    constraint_id:   str
    constraint_name: str
    constraint_type: ConstraintType = ConstraintType.CUSTOM
    passed:          bool           = True
    is_hard:         bool           = True
    actual_value:    Any            = None
    limit_value:     Any            = None
    reason:          str            = ""
    severity:        str            = "INFO"
    duration_ms:     float          = 0.0
    metadata:        dict           = field(default_factory=dict)
    evaluated_at:    float          = field(default_factory=time.time)

    @property
    def violated(self) -> bool:
        return not self.passed

    @property
    def blocks_decision(self) -> bool:
        """True when violation is hard (blocking)."""
        return self.violated and self.is_hard

    def to_dict(self) -> dict:
        return {
            "constraint_id":   self.constraint_id,
            "constraint_name": self.constraint_name,
            "constraint_type": self.constraint_type.value,
            "passed":          self.passed,
            "is_hard":         self.is_hard,
            "violated":        self.violated,
            "blocks_decision": self.blocks_decision,
            "reason":          self.reason,
            "severity":        self.severity,
            "duration_ms":     self.duration_ms,
        }
