"""iios/investment/decision/risk/exposure_engine.py
ExposureEngine — aggregates position, capital, and concentration analyses
into a single ExposureReport.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.risk.capital_exposure import (
    CapitalExposureAnalyzer,
    CapitalExposureResult,
)
from iios.investment.decision.risk.concentration_analysis import (
    ConcentrationAnalyzer,
    ConcentrationResult,
)
from iios.investment.decision.risk.position_exposure import (
    PositionExposureAnalyzer,
    PositionExposureResult,
)


@dataclass(frozen=True)
class ExposureReport:
    position: PositionExposureResult
    capital:  CapitalExposureResult
    concentration: ConcentrationResult
    exposure_risk: float   # 0–100 composite

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position":       self.position.to_dict(),
            "capital":        self.capital.to_dict(),
            "concentration":  self.concentration.to_dict(),
            "exposure_risk":  round(self.exposure_risk, 2),
        }


class ExposureEngine:
    """Aggregates position, capital, and concentration exposure analyses."""

    def __init__(self) -> None:
        self._position_analyzer      = PositionExposureAnalyzer()
        self._capital_analyzer       = CapitalExposureAnalyzer()
        self._concentration_analyzer = ConcentrationAnalyzer()

    def analyze(self, snapshot: EvidenceSnapshot) -> ExposureReport:
        position      = self._position_analyzer.analyze(snapshot)
        capital       = self._capital_analyzer.analyze(snapshot)
        concentration = self._concentration_analyzer.analyze(snapshot)

        exposure_risk = (
            position.position_exposure_risk   * 0.40
            + capital.capital_risk_score      * 0.40
            + concentration.concentration_score * 0.20
        )
        exposure_risk = min(100.0, max(0.0, exposure_risk))

        return ExposureReport(
            position=position,
            capital=capital,
            concentration=concentration,
            exposure_risk=round(exposure_risk, 4),
        )
