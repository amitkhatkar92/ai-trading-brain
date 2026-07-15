"""iios/investment/portfolio/risk/portfolio_risk_profile.py

Primary output of the Portfolio Risk Engine: an immutable, comprehensive
snapshot of all risk dimensions for a portfolio.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.risk.risk_types import RiskGrade, RiskLevel


@dataclass(frozen=True)
class PortfolioRiskProfile:
    """
    Comprehensive, immutable risk profile for a portfolio.

    Produced by PortfolioRiskEngine.evaluate() and stored in history.
    All monetary values are expressed as fractions of the portfolio (0-1).
    """

    profile_id:         str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str       = ""
    plan_id:            str       = ""
    version:            int       = 1
    schema_version:     str       = "1.0"
    created_at:         str       = ""

    # Position summary
    n_positions:        int       = 0
    total_capital:      float     = 0.0
    currency:           str       = "INR"

    # ── Market Risk ──────────────────────────────────────────────────
    portfolio_vol_annual:   float = 0.0
    portfolio_vol_daily:    float = 0.0
    var_95_1d:              float = 0.0
    var_99_1d:              float = 0.0
    var_95_10d:             float = 0.0
    cvar_95_1d:             float = 0.0
    beta_proxy:             float = 0.0
    diversification_benefit:float = 0.0
    market_risk_level:      str   = "moderate"

    # ── Credit Risk ──────────────────────────────────────────────────
    avg_credit_quality:     float = 0.0
    default_prob_proxy:     float = 0.0
    junk_weight:            float = 0.0
    credit_risk_level:      str   = "moderate"

    # ── Liquidity Risk ───────────────────────────────────────────────
    avg_liquidity_score:    float = 0.0
    illiquid_weight:        float = 0.0
    lvar_95_1d:             float = 0.0
    estimated_days_to_liq:  int   = 0
    liquidity_risk_level:   str   = "moderate"

    # ── Currency Risk ────────────────────────────────────────────────
    foreign_weight:         float = 0.0
    n_currencies:           int   = 1
    fx_shock_impact_15pct:  float = 0.0
    currency_risk_level:    str   = "very_low"

    # ── Interest Rate Risk ───────────────────────────────────────────
    portfolio_duration_proxy:float = 0.0
    impact_100bps:           float = 0.0
    ir_risk_level:           str   = "very_low"

    # ── Concentration Risk ───────────────────────────────────────────
    position_hhi:            float = 0.0
    sector_hhi:              float = 0.0
    top1_weight:             float = 0.0
    top_sector:              str   = ""
    top_sector_weight:       float = 0.0
    has_high_concentration:  bool  = False
    concentration_risk_level:str   = "moderate"

    # ── Tail Risk ────────────────────────────────────────────────────
    cvar_99_1d:              float = 0.0
    black_swan_1pct_loss:    float = 0.0
    skewness_proxy:          float = 0.0
    tail_risk_level:         str   = "moderate"

    # ── Drawdown ─────────────────────────────────────────────────────
    max_drawdown_proxy:      float = 0.0
    expected_recovery_days:  int   = 0
    drawdown_level:          str   = "none"

    # ── Stress Tests ─────────────────────────────────────────────────
    stress_worst_scenario:   str   = ""
    stress_worst_loss:       float = 0.0
    stress_resilience_score: float = 1.0

    # ── Composite Score ──────────────────────────────────────────────
    overall_risk_score:      float = 0.0   # [0, 1] — lower = less risky
    risk_grade:              str   = "B"
    risk_level:              str   = "moderate"
    is_acceptable:           bool  = True

    # ── Quality & Confidence ─────────────────────────────────────────
    quality_score:           float = 0.0
    confidence_score:        float = 0.0
    confidence_level:        str   = "moderate"

    # ── Alerts ───────────────────────────────────────────────────────
    n_alerts:                int   = 0
    n_critical_alerts:       int   = 0
    all_warnings:            Tuple[str, ...] = field(default_factory=tuple)

    # ── Metadata ─────────────────────────────────────────────────────
    metadata:                Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id":          self.profile_id,
            "portfolio_id":        self.portfolio_id,
            "plan_id":             self.plan_id,
            "n_positions":         self.n_positions,
            "currency":            self.currency,

            "portfolio_vol_annual":    round(self.portfolio_vol_annual, 4),
            "var_95_1d":               round(self.var_95_1d, 4),
            "var_99_1d":               round(self.var_99_1d, 4),
            "cvar_95_1d":              round(self.cvar_95_1d, 4),
            "cvar_99_1d":              round(self.cvar_99_1d, 4),

            "avg_credit_quality":      round(self.avg_credit_quality, 4),
            "default_prob_proxy":      round(self.default_prob_proxy, 4),

            "avg_liquidity_score":     round(self.avg_liquidity_score, 4),
            "illiquid_weight":         round(self.illiquid_weight, 4),

            "foreign_weight":          round(self.foreign_weight, 4),
            "portfolio_duration_proxy":round(self.portfolio_duration_proxy, 4),
            "position_hhi":            round(self.position_hhi, 4),
            "top_sector":              self.top_sector,
            "top_sector_weight":       round(self.top_sector_weight, 4),
            "max_drawdown_proxy":      round(self.max_drawdown_proxy, 4),

            "stress_worst_scenario":   self.stress_worst_scenario,
            "stress_worst_loss":       round(self.stress_worst_loss, 4),
            "stress_resilience_score": round(self.stress_resilience_score, 4),

            "overall_risk_score":      round(self.overall_risk_score, 4),
            "risk_grade":              self.risk_grade,
            "risk_level":              self.risk_level,
            "is_acceptable":           self.is_acceptable,

            "n_alerts":                self.n_alerts,
            "n_critical_alerts":       self.n_critical_alerts,
            "created_at":              self.created_at,
        }
