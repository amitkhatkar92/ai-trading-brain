"""iios/investment/company/valuation/discount_analysis.py
Historical premium/discount analysis vs historical valuation multiples.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_statistics import (
    safe_mean, safe_median, percentile_rank,
)


@dataclass
class DiscountAnalysis:
    """How current multiples compare to own historical averages."""

    pe_premium_pct:        Optional[float] = None  # positive = trading above hist avg
    pb_premium_pct:        Optional[float] = None
    ev_ebitda_premium_pct: Optional[float] = None
    pfcf_premium_pct:      Optional[float] = None

    pe_percentile:        Optional[float] = None   # 0–100 vs own history
    pb_percentile:        Optional[float] = None
    ev_ebitda_percentile: Optional[float] = None

    overall_premium_pct:  Optional[float] = None   # simple average
    explanation:          List[str]       = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pe_premium_pct":        self.pe_premium_pct,
            "pb_premium_pct":        self.pb_premium_pct,
            "ev_ebitda_premium_pct": self.ev_ebitda_premium_pct,
            "pfcf_premium_pct":      self.pfcf_premium_pct,
            "pe_percentile":         self.pe_percentile,
            "pb_percentile":         self.pb_percentile,
            "ev_ebitda_percentile":  self.ev_ebitda_percentile,
            "overall_premium_pct":   self.overall_premium_pct,
            "explanation":           self.explanation,
        }


class DiscountAnalysisEngine:
    """Analyse how current trading multiples compare to own historical range."""

    def compute(
        self,
        current_pe:        Optional[float],
        current_pb:        Optional[float],
        current_ev_ebitda: Optional[float],
        current_pfcf:      Optional[float],
        historical_pe:     Optional[List[float]] = None,
        historical_pb:     Optional[List[float]] = None,
        historical_ev_ebitda: Optional[List[float]] = None,
        historical_pfcf:   Optional[List[float]] = None,
    ) -> DiscountAnalysis:
        result = DiscountAnalysis()
        premiums = []

        def _premium(current: Optional[float], history: Optional[List[float]]) -> Optional[float]:
            if current is None or not history:
                return None
            hist_avg = safe_median(history)
            if hist_avg and hist_avg > 0:
                return (current - hist_avg) / hist_avg * 100.0
            return None

        result.pe_premium_pct        = _premium(current_pe, historical_pe)
        result.pb_premium_pct        = _premium(current_pb, historical_pb)
        result.ev_ebitda_premium_pct = _premium(current_ev_ebitda, historical_ev_ebitda)
        result.pfcf_premium_pct      = _premium(current_pfcf, historical_pfcf)

        if current_pe and historical_pe:
            result.pe_percentile = percentile_rank(current_pe, historical_pe)
        if current_pb and historical_pb:
            result.pb_percentile = percentile_rank(current_pb, historical_pb)
        if current_ev_ebitda and historical_ev_ebitda:
            result.ev_ebitda_percentile = percentile_rank(current_ev_ebitda, historical_ev_ebitda)

        premiums = [
            p for p in [
                result.pe_premium_pct,
                result.pb_premium_pct,
                result.ev_ebitda_premium_pct,
                result.pfcf_premium_pct,
            ]
            if p is not None
        ]
        result.overall_premium_pct = safe_mean(premiums) if premiums else None

        if result.overall_premium_pct is not None:
            if result.overall_premium_pct > 20:
                result.explanation.append(
                    f"Trading at {result.overall_premium_pct:.1f}% premium to historical average"
                )
            elif result.overall_premium_pct < -20:
                result.explanation.append(
                    f"Trading at {abs(result.overall_premium_pct):.1f}% discount to historical average"
                )
            else:
                result.explanation.append("Trading near historical average multiples")

        return result
