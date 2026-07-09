"""iios/investment/portfolio/risk/risk_profile.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import RiskCategory, RiskLevel


@dataclass
class RiskProfile:
    """Comprehensive risk characterisation of a portfolio."""

    risk_id:                 str            = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:            str            = ""

    # Composite & dimension scores (0–100; higher = MORE risky)
    overall_risk_score:      float          = 50.0
    market_risk_score:       float          = 50.0
    concentration_risk_score: float         = 50.0
    liquidity_risk_score:    float          = 50.0
    volatility_risk_score:   float          = 50.0
    drawdown_risk_score:     float          = 50.0
    correlation_risk_score:  float          = 50.0

    risk_level:              RiskLevel      = RiskLevel.UNKNOWN
    primary_risk_categories: list[RiskCategory] = field(default_factory=list)
    risk_factors:            list[str]      = field(default_factory=list)
    risk_warnings:           list[str]      = field(default_factory=list)
    metadata:                dict[str, Any] = field(default_factory=dict)
    timestamp:               float          = field(default_factory=time.time)

    def add_warning(self, warning: str) -> None:
        if warning not in self.risk_warnings:
            self.risk_warnings.append(warning)

    def add_factor(self, factor: str) -> None:
        if factor not in self.risk_factors:
            self.risk_factors.append(factor)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id":                  self.risk_id,
            "portfolio_id":             self.portfolio_id,
            "overall_risk_score":       self.overall_risk_score,
            "market_risk_score":        self.market_risk_score,
            "concentration_risk_score": self.concentration_risk_score,
            "liquidity_risk_score":     self.liquidity_risk_score,
            "volatility_risk_score":    self.volatility_risk_score,
            "drawdown_risk_score":      self.drawdown_risk_score,
            "correlation_risk_score":   self.correlation_risk_score,
            "risk_level":               self.risk_level.value,
            "primary_risk_categories":  [c.value for c in self.primary_risk_categories],
            "risk_factors":             self.risk_factors,
            "risk_warnings":            self.risk_warnings,
            "metadata":                 self.metadata,
            "timestamp":                self.timestamp,
        }
