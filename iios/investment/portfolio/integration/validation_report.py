"""iios/investment/portfolio/integration/validation_report.py

ValidationCheck and ConsistencyValidationReport types.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.integration.integration_types import (
    ValidationStatus, now_utc,
)


@dataclass(frozen=True)
class ValidationCheck:
    check_id:    str
    description: str
    status:      ValidationStatus
    engine_pair: str = ""
    detail:      str = ""
    severity:    str = "info"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":    self.check_id,
            "engine_pair": self.engine_pair,
            "status":      self.status.value,
            "detail":      self.detail,
        }


@dataclass(frozen=True)
class ConsistencyValidationReport:
    report_id:         str                             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str                             = ""
    created_at:        str                             = field(default_factory=now_utc)
    overall_status:    ValidationStatus                = ValidationStatus.PASSED
    is_consistent:     bool                            = True
    checks:            Tuple[ValidationCheck, ...]     = field(default_factory=tuple)
    n_passed:          int                             = 0
    n_warnings:        int                             = 0
    n_failed:          int                             = 0
    consistency_score: float                           = 1.0
    primary_issue:     Optional[str]                   = None
    warnings:          Tuple[str, ...]                 = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status":    self.overall_status.value,
            "is_consistent":     self.is_consistent,
            "consistency_score": round(self.consistency_score, 4),
            "n_passed":          self.n_passed,
            "n_warnings":        self.n_warnings,
            "n_failed":          self.n_failed,
            "primary_issue":     self.primary_issue,
        }
