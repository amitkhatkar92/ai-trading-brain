"""iios/investment/decision/risk/position_exposure.py
PositionExposureAnalyzer — estimates position-level exposure risk from evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.risk.risk_constants import (
    DEFAULT_CAPITAL_AT_RISK_PCT,
    MAX_CAPITAL_EXPOSURE_PCT,
)


@dataclass(frozen=True)
class PositionExposureResult:
    estimated_capital_at_risk: float   # fraction 0–1
    position_size_risk:        float   # 0–100
    data_quality_risk:         float   # 0–100 from evidence quality
    position_exposure_risk:    float   # 0–100 composite

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_capital_at_risk": round(self.estimated_capital_at_risk, 4),
            "position_size_risk":        round(self.position_size_risk, 2),
            "data_quality_risk":         round(self.data_quality_risk, 2),
            "position_exposure_risk":    round(self.position_exposure_risk, 2),
        }


class PositionExposureAnalyzer:
    """
    Estimates position exposure risk from EvidenceSnapshot.
    Uses evidence quality and item count as proxies for exposure certainty.
    """

    def analyze(self, snapshot: EvidenceSnapshot) -> PositionExposureResult:
        quality  = snapshot.quality_score   # 0–100
        coverage = snapshot.coverage_fraction  # 0–1

        # Estimated capital at risk: scales with evidence coverage
        # Poor coverage → we can't size correctly → assume max default
        cap_pct = DEFAULT_CAPITAL_AT_RISK_PCT * (1.0 + (1.0 - coverage))
        cap_pct = min(cap_pct, MAX_CAPITAL_EXPOSURE_PCT)

        # Position size risk: inverse relationship with evidence quality
        pos_size_risk  = max(0.0, 100.0 - quality)

        # Data quality risk: directly from quality
        data_qual_risk = max(0.0, 100.0 - quality)

        position_exposure_risk = (
            pos_size_risk  * 0.50
            + data_qual_risk * 0.50
        )

        return PositionExposureResult(
            estimated_capital_at_risk=round(cap_pct, 6),
            position_size_risk=round(pos_size_risk, 4),
            data_quality_risk=round(data_qual_risk, 4),
            position_exposure_risk=round(position_exposure_risk, 4),
        )
