"""iios/investment/portfolio/risk/risk_statistics.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskStatistics:
    """Running risk statistics for a single portfolio."""

    portfolio_id:      str   = ""
    analysis_count:    int   = 0
    avg_risk_score:    float = 50.0
    max_risk_score:    float = 0.0
    min_risk_score:    float = 100.0
    breach_count:      int   = 0   # number of limit breaches observed

    def update(self, risk_score: float, *, had_breach: bool = False) -> None:
        self.analysis_count += 1
        prev_avg = self.avg_risk_score * (self.analysis_count - 1)
        self.avg_risk_score = (prev_avg + risk_score) / self.analysis_count
        if risk_score > self.max_risk_score:
            self.max_risk_score = risk_score
        if risk_score < self.min_risk_score:
            self.min_risk_score = risk_score
        if had_breach:
            self.breach_count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":   self.portfolio_id,
            "analysis_count": self.analysis_count,
            "avg_risk_score": round(self.avg_risk_score, 2),
            "max_risk_score": round(self.max_risk_score, 2),
            "min_risk_score": round(self.min_risk_score, 2),
            "breach_count":   self.breach_count,
        }
