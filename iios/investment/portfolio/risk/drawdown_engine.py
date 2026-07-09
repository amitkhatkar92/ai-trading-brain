"""iios/investment/portfolio/risk/drawdown_engine.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    DRAWDOWN_CRITICAL_THRESHOLD,
    DRAWDOWN_MINOR_THRESHOLD,
    DRAWDOWN_MODERATE_THRESHOLD,
    DRAWDOWN_SEVERE_THRESHOLD,
    DRAWDOWN_SIGNIFICANT_THRESHOLD,
    DrawdownSeverity,
)
from iios.investment.portfolio.core.portfolio import Portfolio


@dataclass
class DrawdownAnalysis:
    """Drawdown characterisation for a portfolio at a single point in time."""

    portfolio_id:          str              = ""
    current_nav:           float            = 0.0
    peak_nav:              float            = 0.0
    current_drawdown_pct:  float            = 0.0    # fraction (0.10 = 10%)
    max_drawdown_pct:      float            = 0.0    # historical max (if tracked)
    drawdown_severity:     DrawdownSeverity = DrawdownSeverity.NONE
    is_in_drawdown:        bool             = False
    recovery_required_pct: float            = 0.0    # gain needed to return to peak
    drawdown_risk_score:   float            = 0.0    # 0–100; higher = more risk
    metadata:              dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":          self.portfolio_id,
            "current_nav":           self.current_nav,
            "peak_nav":              self.peak_nav,
            "current_drawdown_pct":  self.current_drawdown_pct,
            "max_drawdown_pct":      self.max_drawdown_pct,
            "drawdown_severity":     self.drawdown_severity.value,
            "is_in_drawdown":        self.is_in_drawdown,
            "recovery_required_pct": self.recovery_required_pct,
            "drawdown_risk_score":   self.drawdown_risk_score,
            "metadata":              self.metadata,
        }


class DrawdownEngine:
    """
    Computes drawdown metrics from the current portfolio NAV and
    the historical peak NAV maintained by PortfolioProfile.
    """

    def analyze(
        self,
        portfolio: Portfolio,
        peak_nav:  float,
    ) -> DrawdownAnalysis:
        current_nav = portfolio.total_nav

        if peak_nav <= 0:
            peak_nav = current_nav

        if current_nav <= 0:
            return DrawdownAnalysis(portfolio_id=portfolio.portfolio_id)

        dd_pct = max(0.0, (peak_nav - current_nav) / peak_nav)
        is_in_drawdown = dd_pct > 0.001   # > 0.1% threshold to avoid float noise

        severity    = self._classify(dd_pct)
        recovery    = (peak_nav / current_nav - 1.0) if current_nav > 0 and dd_pct > 0 else 0.0
        risk_score  = self._risk_score(dd_pct)

        return DrawdownAnalysis(
            portfolio_id          = portfolio.portfolio_id,
            current_nav           = current_nav,
            peak_nav              = peak_nav,
            current_drawdown_pct  = round(dd_pct, 6),
            drawdown_severity     = severity,
            is_in_drawdown        = is_in_drawdown,
            recovery_required_pct = round(recovery, 6),
            drawdown_risk_score   = round(risk_score, 2),
            metadata              = {"source": "DrawdownEngine"},
        )

    @staticmethod
    def _classify(dd: float) -> DrawdownSeverity:
        if dd < DRAWDOWN_MINOR_THRESHOLD:
            return DrawdownSeverity.NONE
        elif dd < DRAWDOWN_MODERATE_THRESHOLD:
            return DrawdownSeverity.MINOR
        elif dd < DRAWDOWN_SIGNIFICANT_THRESHOLD:
            return DrawdownSeverity.MODERATE
        elif dd < DRAWDOWN_SEVERE_THRESHOLD:
            return DrawdownSeverity.SIGNIFICANT
        elif dd < DRAWDOWN_CRITICAL_THRESHOLD:
            return DrawdownSeverity.SEVERE
        else:
            return DrawdownSeverity.CRITICAL

    @staticmethod
    def _risk_score(dd: float) -> float:
        """Map drawdown fraction to 0–100 risk score."""
        if dd >= DRAWDOWN_CRITICAL_THRESHOLD:
            return 100.0
        elif dd >= DRAWDOWN_SEVERE_THRESHOLD:
            return 80.0
        elif dd >= DRAWDOWN_SIGNIFICANT_THRESHOLD:
            return 60.0
        elif dd >= DRAWDOWN_MODERATE_THRESHOLD:
            return 40.0
        elif dd >= DRAWDOWN_MINOR_THRESHOLD:
            return 20.0
        else:
            return 0.0
