"""iios/investment/portfolio/diversification/concentration_engine.py

Orchestrates all concentration analyses into a single ConcentrationReport.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.diversification.concentration_analysis import (
    PositionConcentrationResult,
    analyze_position_concentration,
)
from iios.investment.portfolio.diversification.diversification_types import (
    ConcentrationLevel,
    PositionData,
    SECTOR_CRITICAL_THRESHOLD,
    SECTOR_WARNING_THRESHOLD,
    TOP1_WARNING_THRESHOLD,
    TOP5_WARNING_THRESHOLD,
)
from iios.investment.portfolio.diversification.factor_concentration import (
    FactorExposure,
    analyze_factor_concentration,
)
from iios.investment.portfolio.diversification.sector_concentration import (
    SectorConcentrationReport,
    analyze_sector_concentration,
)


@dataclass(frozen=True)
class ConcentrationReport:
    """All concentration dimensions in one place."""

    report_id:   str                      = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:str                      = ""
    plan_id:     str                      = ""

    position:    PositionConcentrationResult    = field(default_factory=PositionConcentrationResult)
    sector:      SectorConcentrationReport      = field(default_factory=SectorConcentrationReport)
    factor:      FactorExposure                 = field(default_factory=FactorExposure)

    # Aggregate flags
    has_position_concentration: bool = False
    has_sector_concentration:   bool = False
    worst_concentration_level:  ConcentrationLevel = ConcentrationLevel.MINIMAL
    warnings:    tuple = field(default_factory=tuple)

    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":                  self.report_id,
            "portfolio_id":               self.portfolio_id,
            "plan_id":                    self.plan_id,
            "position":                   self.position.to_dict(),
            "sector":                     self.sector.to_dict(),
            "factor":                     self.factor.to_dict(),
            "has_position_concentration": self.has_position_concentration,
            "has_sector_concentration":   self.has_sector_concentration,
            "worst_concentration_level":  self.worst_concentration_level.value,
            "warnings":                   list(self.warnings),
            "evaluated_at":               self.evaluated_at,
        }


class ConcentrationEngine:
    """Computes a full ConcentrationReport from a list of PositionData."""

    def evaluate(
        self,
        positions:    List[PositionData],
        portfolio_id: str = "",
        plan_id:      str = "",
    ) -> ConcentrationReport:
        if not positions:
            return ConcentrationReport(portfolio_id=portfolio_id, plan_id=plan_id)

        pos_result = analyze_position_concentration(positions)
        sec_report = analyze_sector_concentration(positions)
        fac_result = analyze_factor_concentration(positions)

        pos_conc = pos_result.concentration_level not in (
            ConcentrationLevel.MINIMAL, ConcentrationLevel.LOW
        )
        sec_conc = sec_report.sector.top1_weight >= SECTOR_WARNING_THRESHOLD

        levels = [pos_result.concentration_level, sec_report.sector.concentration_level]
        severity_order = [
            ConcentrationLevel.MINIMAL, ConcentrationLevel.LOW,
            ConcentrationLevel.MODERATE, ConcentrationLevel.HIGH,
            ConcentrationLevel.EXTREME,
        ]
        worst = max(levels, key=lambda l: severity_order.index(l))

        warnings = []
        if pos_result.top1_weight >= TOP1_WARNING_THRESHOLD:
            warnings.append(
                f"Single position {pos_result.top1_symbol} is {pos_result.top1_weight:.1%} of portfolio"
            )
        if pos_result.top5_weight >= TOP5_WARNING_THRESHOLD:
            warnings.append(
                f"Top-5 positions represent {pos_result.top5_weight:.1%} of portfolio"
            )
        if sec_report.sector.top1_weight >= SECTOR_CRITICAL_THRESHOLD:
            warnings.append(
                f"Sector '{sec_report.sector.top1_bucket}' is {sec_report.sector.top1_weight:.1%} — critical"
            )
        elif sec_report.sector.top1_weight >= SECTOR_WARNING_THRESHOLD:
            warnings.append(
                f"Sector '{sec_report.sector.top1_bucket}' is {sec_report.sector.top1_weight:.1%} — above warning"
            )

        return ConcentrationReport(
            portfolio_id              = portfolio_id,
            plan_id                   = plan_id,
            position                  = pos_result,
            sector                    = sec_report,
            factor                    = fac_result,
            has_position_concentration= pos_conc,
            has_sector_concentration  = sec_conc,
            worst_concentration_level = worst,
            warnings                  = tuple(warnings),
        )
