"""iios/investment/portfolio/core/portfolio_snapshot.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    DEFAULT_SNAPSHOT_TTL_SEC,
    DrawdownSeverity,
    PortfolioHealthStatus,
    RiskLevel,
)


@dataclass
class PortfolioSnapshot:
    """Point-in-time record of a portfolio's key metrics."""

    snapshot_id:          str                  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                  = ""
    timestamp:            float                = field(default_factory=time.time)

    # NAV
    total_nav:            float                = 0.0
    cash:                 float                = 0.0
    invested_value:       float                = 0.0
    cash_pct:             float                = 0.0

    # PnL
    unrealized_pnl:       float                = 0.0
    unrealized_pnl_pct:   float                = 0.0

    # Composition
    position_count:       int                  = 0
    long_exposure:        float                = 0.0    # fraction of NAV
    short_exposure:       float                = 0.0
    gross_exposure:       float                = 0.0
    net_exposure:         float                = 0.0

    # Scores (0–100)
    health_score:         float                = 50.0
    risk_score:           float                = 50.0
    diversification_score: float               = 50.0
    concentration_score:  float                = 50.0
    liquidity_score:      float                = 50.0
    performance_score:    float                = 50.0

    # Risk
    top_position_weight:  float                = 0.0
    hhi:                  float                = 0.0    # Herfindahl-Hirschman Index
    drawdown_pct:         float                = 0.0
    drawdown_severity:    DrawdownSeverity      = DrawdownSeverity.NONE
    risk_level:           RiskLevel            = RiskLevel.UNKNOWN
    health_status:        PortfolioHealthStatus = PortfolioHealthStatus.UNKNOWN

    metadata:             dict[str, Any]       = field(default_factory=dict)
    created_at:           float                = field(default_factory=time.time)

    @property
    def age_sec(self) -> float:
        return time.time() - self.created_at

    def is_stale(self, ttl_sec: float = DEFAULT_SNAPSHOT_TTL_SEC) -> bool:
        return self.age_sec > ttl_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":          self.snapshot_id,
            "portfolio_id":         self.portfolio_id,
            "timestamp":            self.timestamp,
            "total_nav":            self.total_nav,
            "cash":                 self.cash,
            "invested_value":       self.invested_value,
            "cash_pct":             self.cash_pct,
            "unrealized_pnl":       self.unrealized_pnl,
            "unrealized_pnl_pct":   self.unrealized_pnl_pct,
            "position_count":       self.position_count,
            "long_exposure":        self.long_exposure,
            "short_exposure":       self.short_exposure,
            "gross_exposure":       self.gross_exposure,
            "net_exposure":         self.net_exposure,
            "health_score":         self.health_score,
            "risk_score":           self.risk_score,
            "diversification_score": self.diversification_score,
            "concentration_score":  self.concentration_score,
            "liquidity_score":      self.liquidity_score,
            "performance_score":    self.performance_score,
            "top_position_weight":  self.top_position_weight,
            "hhi":                  self.hhi,
            "drawdown_pct":         self.drawdown_pct,
            "drawdown_severity":    self.drawdown_severity.value,
            "risk_level":           self.risk_level.value,
            "health_status":        self.health_status.value,
            "metadata":             self.metadata,
            "created_at":           self.created_at,
        }
