"""iios/investment/decision/risk/capital_exposure.py
CapitalExposureAnalyzer — estimates capital concentration and allocation risk.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.risk.risk_constants import (
    ExposureLevel,
    MAX_CAPITAL_EXPOSURE_PCT,
    MAX_SECTOR_CONCENTRATION,
)


@dataclass(frozen=True)
class CapitalExposureResult:
    exposure_fraction:   float         # 0–1 estimated
    exposure_level:      ExposureLevel
    capital_risk_score:  float         # 0–100
    allocation_risk:     float         # 0–100 from evidence diversity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exposure_fraction":  round(self.exposure_fraction, 4),
            "exposure_level":     self.exposure_level.value,
            "capital_risk_score": round(self.capital_risk_score, 2),
            "allocation_risk":    round(self.allocation_risk, 2),
        }


class CapitalExposureAnalyzer:
    """Estimates capital exposure risk from EvidenceSnapshot."""

    def analyze(self, snapshot: EvidenceSnapshot) -> CapitalExposureResult:
        coverage  = snapshot.coverage_fraction   # 0–1
        quality   = snapshot.quality_score       # 0–100
        item_count = snapshot.item_count

        # Proxy: exposure fraction ≈ 1 - coverage (unknown positions = higher assumed exposure)
        exposure_fraction = min(1.0, MAX_CAPITAL_EXPOSURE_PCT * (2.0 - coverage))

        level = ExposureLevel.from_fraction(exposure_fraction)

        # Capital risk: penalise low coverage (can't verify exposure)
        capital_risk = max(0.0, (1.0 - coverage) * 70.0 + (100.0 - quality) * 0.30)
        capital_risk = min(100.0, capital_risk)

        # Allocation risk: fewer items = less diversified information
        allocation_risk = max(0.0, 60.0 - item_count * 4.0)

        return CapitalExposureResult(
            exposure_fraction=round(exposure_fraction, 6),
            exposure_level=level,
            capital_risk_score=round(capital_risk, 4),
            allocation_risk=round(allocation_risk, 4),
        )
