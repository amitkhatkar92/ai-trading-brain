"""iios/investment/company/valuation/valuation_quality.py
Quality assessment of the valuation estimate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_model import ValuationResult, ValuationStatus
from iios.investment.company.valuation.valuation_statistics import clamp


@dataclass
class ValuationQuality:
    """Qualitative assessment of the overall valuation estimate."""
    has_dcf:         bool = False
    has_relative:    bool = False
    has_rim:         bool = False
    has_ddm:         bool = False
    model_count:     int  = 0
    history_depth:   int  = 0
    fcf_positive:    bool = False
    issues:          List[str] = field(default_factory=list)
    quality_label:   str  = "poor"   # "excellent" | "good" | "fair" | "poor"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_dcf":       self.has_dcf,
            "has_relative":  self.has_relative,
            "has_rim":       self.has_rim,
            "has_ddm":       self.has_ddm,
            "model_count":   self.model_count,
            "history_depth": self.history_depth,
            "fcf_positive":  self.fcf_positive,
            "quality_label": self.quality_label,
            "issues":        self.issues,
        }


def assess_valuation_quality(
    dcf_result:      Optional[ValuationResult],
    relative_result: Optional[ValuationResult],
    rim_result:      Optional[ValuationResult],
    ddm_result:      Optional[ValuationResult],
    history_depth:   int   = 0,
    fcf_base:        Optional[float] = None,
) -> ValuationQuality:
    q = ValuationQuality()

    def _ok(r: Optional[ValuationResult]) -> bool:
        return bool(r and r.status == ValuationStatus.COMPUTED and r.intrinsic_value)

    q.has_dcf      = _ok(dcf_result)
    q.has_relative = _ok(relative_result)
    q.has_rim      = _ok(rim_result)
    q.has_ddm      = _ok(ddm_result)
    q.model_count  = sum([q.has_dcf, q.has_relative, q.has_rim, q.has_ddm])
    q.history_depth= history_depth
    q.fcf_positive = bool(fcf_base and fcf_base > 0)

    if not q.has_dcf:
        q.issues.append("DCF not computed — limited intrinsic value basis")
    if not q.has_relative:
        q.issues.append("Relative valuation not available")
    if history_depth < 3:
        q.issues.append(f"Limited financial history ({history_depth} periods)")
    if not q.fcf_positive:
        q.issues.append("Negative or zero FCF — DCF reliability reduced")

    if q.model_count >= 3 and history_depth >= 5 and q.fcf_positive:
        q.quality_label = "excellent"
    elif q.model_count >= 2 and history_depth >= 3:
        q.quality_label = "good"
    elif q.model_count >= 1:
        q.quality_label = "fair"
    else:
        q.quality_label = "poor"

    return q
