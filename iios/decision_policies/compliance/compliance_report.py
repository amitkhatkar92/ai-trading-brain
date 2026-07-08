"""iios/decision_policies/compliance/compliance_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .compliance_policy import ComplianceResult


@dataclass
class ComplianceReport:
    report_id:          str        = field(default_factory=lambda: str(uuid.uuid4()))
    context_id:         str        = ""
    source_id:          str        = ""
    results:            list[ComplianceResult] = field(default_factory=list)
    passed:             bool       = True
    violations:         list[str]  = field(default_factory=list)
    warnings:           list[str]  = field(default_factory=list)
    categories_checked: list[str]  = field(default_factory=list)
    total_checked:      int        = 0
    mandatory_failures: int        = 0
    generated_at:       float      = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":          self.report_id,
            "context_id":         self.context_id,
            "source_id":          self.source_id,
            "passed":             self.passed,
            "total_checked":      self.total_checked,
            "mandatory_failures": self.mandatory_failures,
            "violations":         self.violations,
            "warnings":           self.warnings,
            "categories_checked": self.categories_checked,
            "generated_at":       self.generated_at,
        }


def build_compliance_report(
    results:    list[ComplianceResult],
    context_id: str = "",
    source_id:  str = "",
) -> ComplianceReport:
    violations  = [r.reason for r in results if r.blocks_decision]
    warnings    = [r.reason for r in results if r.violated and not r.blocks_decision]
    categories  = sorted({r.category.value for r in results})
    mandatory_f = sum(1 for r in results if r.blocks_decision)
    return ComplianceReport(
        context_id         = context_id,
        source_id          = source_id,
        results            = results,
        passed             = mandatory_f == 0,
        violations         = violations,
        warnings           = warnings,
        categories_checked = categories,
        total_checked      = len(results),
        mandatory_failures = mandatory_f,
    )
