"""iios/investment/portfolio/core/portfolio_intelligence.py
Top-level intelligence product produced by the Portfolio & Risk Intelligence Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    PortfolioHealthStatus,
    RiskLevel,
    HEALTH_EXCELLENT_THRESHOLD,
    HEALTH_GOOD_THRESHOLD,
    HEALTH_FAIR_THRESHOLD,
    HEALTH_POOR_THRESHOLD,
)
from iios.investment.portfolio.risk.risk_profile import RiskProfile
from iios.investment.portfolio.risk.drawdown_engine import DrawdownAnalysis
from iios.investment.portfolio.exposure.exposure_report import ExposureReport


@dataclass
class PortfolioIntelligence:
    """
    Comprehensive portfolio intelligence produced by PortfolioManager.analyze().

    Scores are 0–100 unless noted. Higher scores are always better
    except for risk_score (higher = more risky).
    """

    intelligence_id:      str                    = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                    = ""
    portfolio_name:       str                    = ""
    request_id:           str                    = ""

    # Composite health scores (0–100; higher = better)
    health_score:         float                  = 50.0
    risk_score:           float                  = 50.0    # higher = more risky
    diversification_score: float                 = 50.0
    concentration_score:  float                  = 50.0
    liquidity_score:      float                  = 50.0
    performance_score:    float                  = 50.0
    allocation_score:     float                  = 50.0

    # Classifications
    health_status:        PortfolioHealthStatus  = PortfolioHealthStatus.UNKNOWN
    risk_level:           RiskLevel              = RiskLevel.UNKNOWN

    # Drill-down intelligence products
    risk_profile:         RiskProfile  | None    = None
    drawdown:             DrawdownAnalysis | None = None
    exposure_report:      ExposureReport  | None  = None

    # Narrative intelligence
    observations:         list[str]              = field(default_factory=list)
    warnings:             list[str]              = field(default_factory=list)
    recommendations:      list[str]              = field(default_factory=list)
    risk_factors:         list[str]              = field(default_factory=list)

    # Meta
    confidence:           float                  = 0.0
    metadata:             dict[str, Any]         = field(default_factory=dict)
    created_at:           float                  = field(default_factory=time.time)
    duration_ms:          float                  = 0.0

    # ── mutation helpers ──────────────────────────────────────────────────────

    def add_observation(self, obs: str) -> None:
        if obs and obs not in self.observations:
            self.observations.append(obs)

    def add_warning(self, warning: str) -> None:
        if warning and warning not in self.warnings:
            self.warnings.append(warning)

    def add_recommendation(self, rec: str) -> None:
        if rec and rec not in self.recommendations:
            self.recommendations.append(rec)

    def add_risk_factor(self, factor: str) -> None:
        if factor and factor not in self.risk_factors:
            self.risk_factors.append(factor)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def classify_health(score: float) -> PortfolioHealthStatus:
        if score >= HEALTH_EXCELLENT_THRESHOLD:
            return PortfolioHealthStatus.EXCELLENT
        elif score >= HEALTH_GOOD_THRESHOLD:
            return PortfolioHealthStatus.GOOD
        elif score >= HEALTH_FAIR_THRESHOLD:
            return PortfolioHealthStatus.FAIR
        elif score >= HEALTH_POOR_THRESHOLD:
            return PortfolioHealthStatus.POOR
        else:
            return PortfolioHealthStatus.CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "intelligence_id":      self.intelligence_id,
            "portfolio_id":         self.portfolio_id,
            "portfolio_name":       self.portfolio_name,
            "request_id":           self.request_id,
            "health_score":         self.health_score,
            "risk_score":           self.risk_score,
            "diversification_score": self.diversification_score,
            "concentration_score":  self.concentration_score,
            "liquidity_score":      self.liquidity_score,
            "performance_score":    self.performance_score,
            "allocation_score":     self.allocation_score,
            "health_status":        self.health_status.value,
            "risk_level":           self.risk_level.value,
            "risk_profile":         self.risk_profile.to_dict() if self.risk_profile else None,
            "drawdown":             self.drawdown.to_dict() if self.drawdown else None,
            "exposure_report":      self.exposure_report.to_dict() if self.exposure_report else None,
            "observations":         self.observations,
            "warnings":             self.warnings,
            "recommendations":      self.recommendations,
            "risk_factors":         self.risk_factors,
            "confidence":           self.confidence,
            "metadata":             self.metadata,
            "created_at":           self.created_at,
            "duration_ms":          self.duration_ms,
        }
