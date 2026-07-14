"""iios/investment/decision/risk/risk_controls.py
Core value objects: RiskControl, ControlViolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from iios.investment.decision.risk.risk_constants import RiskControlStatus, RiskDimension


@dataclass(frozen=True)
class RiskControl:
    control_id:   str
    name:         str
    description:  str
    dimension:    RiskDimension
    max_allowed:  float          # 0–100 (or 0–1 for fraction controls)
    is_hard_limit: bool = True   # hard limit = blocks execution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id":   self.control_id,
            "name":         self.name,
            "dimension":    self.dimension.value,
            "max_allowed":  self.max_allowed,
            "is_hard_limit": self.is_hard_limit,
        }


@dataclass(frozen=True)
class ControlViolation:
    control:      RiskControl
    actual_value: float
    status:       RiskControlStatus = RiskControlStatus.BREACHED
    message:      str = ""

    @property
    def is_hard_limit_breach(self) -> bool:
        return self.control.is_hard_limit and self.status == RiskControlStatus.BREACHED

    def to_dict(self) -> Dict[str, Any]:
        d = self.control.to_dict()
        d.update({
            "actual_value": round(self.actual_value, 4),
            "status":       self.status.value,
            "message":      self.message,
        })
        return d
