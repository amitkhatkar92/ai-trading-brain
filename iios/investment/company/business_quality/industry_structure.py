"""iios/investment/company/business_quality/industry_structure.py
Industry structure signals derived from single-company financial footprint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IndustryStructureSignals:
    """
    Industry structure signals inferred from a single company's financials.
    Without direct competitor data, we infer from capital intensity and margins.
    """

    # Capital intensity (higher = higher barriers to entry)
    implied_barriers_to_entry: str = "unknown"  # "high" | "moderate" | "low"

    # Fragmentation signal: high asset turnover → fragmented/competitive
    implied_fragmentation: str = "unknown"   # "concentrated" | "fragmented"

    # Commodity vs differentiated
    product_differentiation: str = "unknown"   # "high" | "moderate" | "commodity"

    # Structural score (higher = better structural position)
    structure_score: float = 50.0

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "implied_barriers_to_entry": self.implied_barriers_to_entry,
            "implied_fragmentation":     self.implied_fragmentation,
            "product_differentiation":   self.product_differentiation,
            "structure_score":           round(self.structure_score, 1),
            "flags":                     self.flags,
        }


class IndustryStructureAnalyzer:
    """
    Derives industry structure signals from a company's financial footprint.
    Populated without peer data; extended by peer data when available.
    """

    def analyze(
        self,
        capex_pct: Optional[float],
        gross_margin: Optional[float],
        asset_turnover: Optional[float],
    ) -> IndustryStructureSignals:
        s = IndustryStructureSignals()

        # ── Barriers to entry (capital intensity proxy) ────────────────────────
        if capex_pct is not None:
            if capex_pct >= 15.0:
                s.implied_barriers_to_entry = "high"
                s.structure_score += 15.0
            elif capex_pct >= 5.0:
                s.implied_barriers_to_entry = "moderate"
                s.structure_score += 8.0
            else:
                s.implied_barriers_to_entry = "low"

        # ── Fragmentation (asset turnover proxy) ──────────────────────────────
        if asset_turnover is not None:
            if asset_turnover >= 2.0:
                s.implied_fragmentation = "fragmented"
            elif asset_turnover < 0.7:
                s.implied_fragmentation = "concentrated"
                s.structure_score += 10.0
            else:
                s.implied_fragmentation = "moderate"

        # ── Product differentiation (gross margin) ────────────────────────────
        if gross_margin is not None:
            if gross_margin >= 50.0:
                s.product_differentiation = "high"
                s.structure_score += 20.0
            elif gross_margin >= 30.0:
                s.product_differentiation = "moderate"
                s.structure_score += 10.0
            else:
                s.product_differentiation = "commodity"

        return s
