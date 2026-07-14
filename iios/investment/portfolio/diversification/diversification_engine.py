"""iios/investment/portfolio/diversification/diversification_engine.py

Top-level diversification analysis: assembles concentration + correlation
+ overlap into a single DiversificationAnalysis object.
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.diversification.concentration_engine import (
    ConcentrationReport,
    ConcentrationEngine,
)
from iios.investment.portfolio.diversification.correlation_engine import (
    CorrelationReport,
    CorrelationEngine,
)
from iios.investment.portfolio.diversification.diversification_types import (
    ConcentrationLevel,
    DiversificationGrade,
    PositionData,
    compute_entropy,
    compute_hhi,
    effective_n,
)


@dataclass(frozen=True)
class DiversificationAnalysis:
    """
    Complete, immutable diversification analysis for one portfolio snapshot.
    This is the primary output of the DiversificationAnalyzer.
    """

    analysis_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str   = ""
    plan_id:              str   = ""

    # Summary metrics
    n_positions:          int   = 0
    effective_n:          float = 0.0
    hhi:                  float = 0.0
    entropy:              float = 0.0
    max_entropy:          float = 0.0    # ln(n_positions) = max possible entropy
    entropy_ratio:        float = 0.0    # entropy / max_entropy — [0, 1]
    diversification_ratio:float = 0.0    # Σ(w_i σ_i) / σ_portfolio

    # Sector summary
    n_sectors:            int   = 0
    top_sector_weight:    float = 0.0
    sector_hhi:           float = 0.0
    sector_entropy_ratio: float = 0.0

    # Sub-reports
    concentration:        ConcentrationReport = field(default_factory=ConcentrationReport)
    correlation:          CorrelationReport   = field(default_factory=CorrelationReport)

    # Aggregate flags
    has_concentration_risk:bool = False
    has_correlation_risk:  bool = False

    analyzed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id":           self.analysis_id,
            "portfolio_id":          self.portfolio_id,
            "plan_id":               self.plan_id,
            "n_positions":           self.n_positions,
            "effective_n":           round(self.effective_n, 2),
            "hhi":                   round(self.hhi, 6),
            "entropy":               round(self.entropy, 4),
            "entropy_ratio":         round(self.entropy_ratio, 4),
            "diversification_ratio": round(self.diversification_ratio, 4),
            "n_sectors":             self.n_sectors,
            "top_sector_weight":     round(self.top_sector_weight, 4),
            "sector_hhi":            round(self.sector_hhi, 6),
            "sector_entropy_ratio":  round(self.sector_entropy_ratio, 4),
            "has_concentration_risk":self.has_concentration_risk,
            "has_correlation_risk":  self.has_correlation_risk,
            "concentration":         self.concentration.to_dict(),
            "correlation":           self.correlation.to_dict(),
        }


class DiversificationAnalyzer:
    """
    Produces a DiversificationAnalysis from a list of PositionData.
    Delegates sub-analyses to ConcentrationEngine and CorrelationEngine.
    """

    def __init__(
        self,
        concentration_engine: ConcentrationEngine | None = None,
        correlation_engine:   CorrelationEngine   | None = None,
    ) -> None:
        self._conc = concentration_engine or ConcentrationEngine()
        self._corr = correlation_engine   or CorrelationEngine()

    def analyze(
        self,
        positions:    List[PositionData],
        portfolio_id: str = "",
        plan_id:      str = "",
    ) -> DiversificationAnalysis:
        if not positions:
            return DiversificationAnalysis(portfolio_id=portfolio_id, plan_id=plan_id)

        weights   = [p.weight for p in positions]
        hhi_val   = compute_hhi(weights)
        ent_val   = compute_entropy(weights)
        eff_n     = 1.0 / max(hhi_val, 1e-10)
        n         = len(positions)
        max_ent   = math.log(n) if n > 1 else 1.0
        ent_ratio = ent_val / max_ent

        # Sector metrics
        sec_buckets: Dict[str, float] = {}
        for p in positions:
            sec_buckets[p.sector] = sec_buckets.get(p.sector, 0.0) + p.weight
        sec_weights   = list(sec_buckets.values())
        sec_hhi       = compute_hhi(sec_weights)
        sec_ent       = compute_entropy(sec_weights)
        sec_max_ent   = math.log(len(sec_weights)) if len(sec_weights) > 1 else 1.0
        sec_ent_ratio = sec_ent / sec_max_ent
        top_sec_w     = max(sec_weights) if sec_weights else 0.0

        conc_report = self._conc.evaluate(positions, portfolio_id, plan_id)
        corr_report = self._corr.evaluate(positions, portfolio_id, plan_id)

        div_ratio = corr_report.analysis.diversification_ratio

        return DiversificationAnalysis(
            portfolio_id          = portfolio_id,
            plan_id               = plan_id,
            n_positions           = n,
            effective_n           = round(eff_n, 4),
            hhi                   = round(hhi_val, 6),
            entropy               = round(ent_val, 4),
            max_entropy           = round(max_ent, 4),
            entropy_ratio         = round(ent_ratio, 4),
            diversification_ratio = round(div_ratio, 4),
            n_sectors             = len(sec_buckets),
            top_sector_weight     = round(top_sec_w, 4),
            sector_hhi            = round(sec_hhi, 6),
            sector_entropy_ratio  = round(sec_ent_ratio, 4),
            concentration         = conc_report,
            correlation           = corr_report,
            has_concentration_risk= conc_report.has_position_concentration
                                    or conc_report.has_sector_concentration,
            has_correlation_risk  = corr_report.is_high_correlation,
        )
